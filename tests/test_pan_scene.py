# -*- coding: utf-8 -*-
# runner: both
"""煎锅在本客户端的场景（Compat/Diegesis 的 PanScene / PanScenes / PanModel / PanFx，假引擎）：服务端广播来了摆出食物（客户端掉落物，
平躺、跟着锅走）、模型的 molang 变量（锅转着挪着、锅柄描边、油膜）、粒子和声音、歇着时收拾干净、区块晚加载按方块实体数据补、
别的维度和别的方块的广播丢掉。"""
from __future__ import print_function

import panclient as C

world = C.install()
Scene = C.load("Compat.Diegesis.PanScene")
Scenes = C.load("Compat.Diegesis.PanScenes")
Fx = C.load("Compat.Diegesis.PanFx")
BlockItems = C.load("Client.BlockItems")
Math = C.load("Shared.Rules.PanModelMath")
POS = C.POS
DT = 1.0 / 60.0


def near(a, b, eps=1e-3):
    return abs(a - b) < eps


def item(name="minecraft:beef", count=2):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def payload(name="minecraft:beef", count=2, down=0.0, up=0.0, rate=0.0, byHand=True, heated=True, **extra):
    data = {"dimensionId": 0, "pos": list(POS), "item": item(name, count) if name else {}, "batch": count if name else 0, "byHand": byHand,
            "heated": heated, "down": down, "up": up, "rate": rate, "both": False}
    data.update(extra)
    return data


def setup():
    world.reset()
    Scenes._scenes.clear()
    Scenes.enable()
    BlockItems._hidden.clear()
    return Scenes.ensure(0, POS)


def run(scene, seconds, near_=True):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, near_)


def mol(name):
    return world.molang.get((POS, name))


def testASceneIsOnlyBuiltForASkillet():
    scene = setup()
    assert scene is not None and Scenes.sceneAt(0, POS) is scene
    world.blocks[(1, 2, 3)] = ("minecraft:stone", 0)
    assert Scenes.ensure(0, (1, 2, 3)) is None and Scenes.ensure(0, (7, 7, 7)) is None


def testTheOldFoodDisplayIsOnlyCoveredOnceTheSceneHasDrawnItsLook():
    """场景刚建出来（开站点这类先到）还不知道锅里有什么：这时把 Client/BlockItems 那份展示收掉，锅里就什么都没有了（和炉灶同一个道理，
    它们的广播走同一套 LookWatch）。要等场景真画出样子的那一帧才接手。"""
    scene = setup()
    assert (0, POS) not in BlockItems._hidden, "场景建出来了，还没有样子：展示留着"
    run(scene, 0.5)
    assert scene.look is None and (0, POS) not in BlockItems._hidden, "一直没有样子：展示一直留着"
    Scenes.OnPanLook(payload())
    assert (0, POS) not in BlockItems._hidden, "样子来了，下一帧才画"
    run(scene, DT)
    assert (0, POS) in BlockItems._hidden, "场景画出样子了：锅里的东西从此由场景画，Client/BlockItems 那份不再画"


def testTheBroadcastDrawsTheFoodAsLyingDropItemsOnThePan():
    scene = setup()
    Scenes.OnPanLook(payload())
    run(scene, 0.1)
    drops = [d for d in world.drops.values() if d["item"]["newItemName"] == "minecraft:beef"]
    assert len(drops) == 2 and all(d["item"]["count"] == 1 for d in drops)
    for drop in drops:
        assert near(drop["scale"], 7.5 / 8.0), "两块：每块 7.5 像素（边长 / 8 = 缩放）"
        assert abs(drop["pivot"][0] - (POS[0] + 0.5)) < 0.4 and abs(drop["pivot"][2] - (POS[2] + 0.5)) < 0.4
        assert POS[1] <= drop["pivot"][1] < POS[1] + 0.3, "躺在锅底上"
    xs = sorted(d["pivot"][0] for d in drops)
    assert xs[1] - xs[0] > 0.2, "两块摆开：一块在 (2.6, 0.4)，一块在 (-2.6, -0.4)"


def testTheHandleSideOfThePanFollowsTheBlockFacing():
    scene = setup()
    world.blocks[POS] = ("arris:skillet", 0)               # aux 0 = 南：锅柄朝南
    scene = Scenes._scenes[(0, POS)]
    assert scene.world((8.0, 0.0, 27.0))[2] > POS[2] + 1.0, "锅柄尖在方块南边"
    for aux, axis, sign in ((1, 0, -1), (2, 2, -1), (3, 0, 1)):
        world.blocks[POS] = ("arris:skillet", aux)
        Scenes._scenes.clear()
        rotated = Scenes.ensure(0, POS)
        tip = rotated.world((8.0, 0.0, 27.0))
        assert sign * (tip[axis] - (POS[axis] + 0.5)) > 1.0, (aux, tip)


def testTheModelVariablesFollowTheScene():
    scene = setup()
    Scenes.OnPanLook(payload())
    run(scene, 0.1)
    assert mol("variable.mod_scene") == 1.0 and POS in world.armed
    assert near(mol("variable.mod_pan_rx"), 0.0) and near(mol("variable.mod_pan_y"), 0.0)
    scene.event("tossed", {"strength": 1.0})
    run(scene, 0.07)
    assert near(mol("variable.mod_pan_rx"), 11.0, 0.3), "颠：绕 x 转 11 度"
    assert near(mol("variable.mod_pan_y"), 1.2, 0.1) and near(mol("variable.mod_pan_z"), -0.9, 0.1), "往上 1.2、往锅柄 0.9"
    run(scene, 0.3)
    assert near(mol("variable.mod_pan_rx"), 0.0, 0.3), "0.2 秒落回原位"


def testTheFoodRidesThePanWhenItIsTossed():
    scene = setup()
    Scenes.OnPanLook(payload(count=1))
    run(scene, 0.1)
    before = [d for d in world.drops.values()][0]["pivot"]
    scene.event("tossed", {"strength": 1.0})
    best = 0.0
    for _ in range(int(0.5 / DT)):
        scene.frame(DT, True)
        best = max(best, [d for d in world.drops.values()][0]["pivot"][1] - before[1])
    assert best > 4.5 / 16.0, "飞起来至少 4.5 像素"


def testTheOilFilmShowsUpWhileFrying():
    scene = setup()
    Scenes.OnPanLook(payload(rate=0.5))
    run(scene, 2.0)
    assert mol("variable.mod_oil_a") > 0.3 and mol("variable.mod_oil_s0") > 1.0 and mol("variable.mod_oil_s1") > 1.0
    assert mol("variable.mod_oil_s2") == 0.0, "两块只有两摊"
    assert mol("variable.mod_oil_x0") is not None and mol("variable.mod_oil_z0") is not None
    Scenes.OnPanLook(payload(name=None))
    run(scene, 2.0)
    assert mol("variable.mod_oil_a") == 0.0, "锅空了：油慢慢收干"


def testTheHandleGlowsUnderTheCursorAndWhileTheFoodWaits():
    scene = setup()
    Scenes.OnPanLook(payload(down=1.0, up=0.0))
    run(scene, 0.2)
    assert mol("variable.mod_handle_lit") == 0.0, "旁人看着等翻面的锅：只有光标放上去才描"
    scene.hovered = True
    run(scene, 0.05)
    assert mol("variable.mod_handle_lit") == 1.0
    scene.hovered = False
    scene.show.focused = True
    run(scene, 0.2)
    assert mol("variable.mod_handle_lit") == 1.0, "本人在锅边、食物等着翻：锅柄描边"


def testParticlesAndSoundsOnlyNearby():
    scene = setup()
    Scenes.OnPanLook(payload(down=1.0))
    run(scene, 0.3, near_=False)
    assert world.particles == [] and world.sounds == [], "离得远不放"
    run(scene, 2.0, near_=True)
    assert world.particles and world.sounds, "在附近：等翻面时的烟、滋滋声、油噗"
    ids = set(p["id"] for p in world.particles)
    assert ids & {"arris_diegesis:droplet", "arris_diegesis:bubble_pop", "arris_diegesis:steam", "arris:pan_heat"}, ids


def testTheSoundsAreVanillaOrFlavouredAndTheLoudOnesAreDividedBack():
    scene = setup()
    Fx_ = Fx.PanFx(POS, Scenes.PanModelMath.facingOf(0))
    Fx_.play([{"type": "sound", "name": "sizzle", "volume": 0.3, "pitch": 1.2}, {"type": "sound", "name": "lava_pop", "volume": 0.4, "pitch": 1.3},
              {"type": "sound", "name": "lantern_step", "volume": 0.35, "pitch": 1.0}, {"type": "sound", "name": "nope", "volume": 1.0, "pitch": 1.0}])
    names = [(s["name"], round(s["volume"], 4)) for s in world.sounds]
    assert names == [("ambient.skillet.sizzle", 0.015), ("liquid.lavapop", 0.4), ("block.lantern.step", 0.35)], names
    del world.sounds[:]
    Fx_.play([{"type": "sound", "name": "lantern_place", "volume": 0.5, "pitch": 1.0}])
    assert [(s["name"], s["volume"], round(s["pitch"], 6)) for s in world.sounds] == [("block.lantern.place", 0.5, round(1.0 / 1.1, 6))],         "原版挂灯放置声每个采样自带 1.1 倍音调：除回去才是 JE 的 1.0（原来煎锅这边没除，炉灶除了）"
    assert all(near(s["pos"][0], POS[0] + 0.5) for s in world.sounds), "声音在锅心"


def testAParticleIsTintedFromItsArgbAndFliesTheWayTheSceneSaid():
    setup()
    fx = Fx.PanFx(POS, Scenes.PanModelMath.facingOf(0))
    fx.play([{"type": "particle", "style": "oil_pop", "pos": (8.0, 1.2, 8.0), "vel": (0.0, 0.6, 0.0), "spread": 0.0, "count": 3, "color": 0}])
    assert len(world.particles) == 3
    variables = world.particles[0]["vars"]
    assert variables["variable.tint_r"] == 0xF7 / 255.0 and variables["variable.tint_b"] == 0x7A / 255.0
    assert near(variables["variable.alpha"], 0xE6 / 255.0) and variables["variable.speed_set"] == 1.0, "缺省色 E6F7C27A"
    world.reset()
    fx.play([{"type": "particle", "style": "steam", "pos": (8.0, 1.6, 8.0), "vel": (0.0, 3.0, 0.0), "spread": 0.0, "count": 1, "color": 0x60FFFFFF}])
    assert near(world.particles[0]["vars"]["variable.alpha"], 0x60 / 255.0), "事件自己给了色就用它的"


def testAnIdleColdPanGoesToSleepAndCleansUp():
    scene = setup()
    Scenes.OnPanLook(payload(heated=False))
    run(scene, 0.5)
    assert world.drops
    Scenes.OnPanLook(payload(name=None, heated=False))
    run(scene, 0.5)
    assert not world.drops, "空锅：掉落物都收了"
    run(scene, 6.0)
    assert scene.frame(DT) is False, "没动静就歇着"
    assert near(mol("variable.mod_pan_rx"), 0.0) and mol("variable.mod_handle_lit") == 0.0 and mol("variable.mod_oil_a") == 0.0


def testChangingTheKindOfFoodSwapsTheDropItems():
    scene = setup()
    Scenes.OnPanLook(payload(count=1))
    run(scene, 0.1)
    first = list(world.drops)
    Scenes.OnPanLook(payload(name="minecraft:porkchop", count=1))
    run(scene, 0.1)
    assert [d["item"]["newItemName"] for d in world.drops.values()] == ["minecraft:porkchop"]
    assert first[0] in world.deleted


def testWhenTheModelIsRebuiltTheVariablesArePushedAgain():
    scene = setup()
    Scenes.OnPanLook(payload())
    run(scene, 0.7)
    assert mol("variable.mod_scene") == 1.0
    world.molang.clear()                                    # 方块实体在本端重建：引擎那边的值全丢了
    run(scene, 0.6)
    assert mol("variable.mod_scene") == 1.0, "隔 0.5 秒读回 mod_scene，对不上就整份重推"


def testABroadcastForAnotherDimensionOrAnotherBlockIsDropped():
    setup()
    Scenes.OnPanLook(dict(payload(), dimensionId=7))
    Scenes.OnPanLook(dict(payload(), pos=[1, 2, 3]))
    Scenes.OnPanLook("junk")
    Scenes.OnPanLook({"dimensionId": 0, "pos": [1, 2]})
    assert list(Scenes._scenes) == [(0, POS)]
    assert Scenes._scenes[(0, POS)].look is None, "只有那一口煎锅的广播才算"


def testAnEventFromTheServerReachesTheSceneCleaned():
    scene = setup()
    Scenes.OnPanLook(payload(count=2))
    run(scene, 0.1)
    Scenes.OnPanLook({"dimensionId": 0, "pos": list(POS), "event": "taken", "stack": {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}})
    assert not scene.show.nodes["piece_0"].visible and scene.show.nodes["lift_0"].visible and scene.show.nodes["lift_1"].visible
    Scenes.OnPanLook({"dimensionId": 0, "pos": list(POS), "event": "tossed", "strength": 5})
    assert scene.show.tossing(), "力度夹进 0..1 后照演"


def testALateLoadingChunkBuildsTheLookFromTheBlockEntityData():
    setup()
    Scenes._scenes.clear()
    world.exData[POS] = {"cookingDict": {"__type__": "dict", "__value__": {"newItemName": {"__type__": "str", "__value__": "minecraft:beef"},
                                                                         "newAuxValue": {"__type__": "int", "__value__": 0},
                                                                         "count": {"__type__": "int", "__value__": 3}}},
                         "heatEnable": {"__type__": "byte", "__value__": True},
                         "panFrying": {"__type__": "dict", "__value__": {"byHand": True, "down": 1.0, "up": 0.25, "batch": 3}}}
    Scenes.OnBlockEntityLoaded({"blockName": "arris:skillet", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    scene = Scenes.sceneAt(0, POS)
    assert scene.look.item["count"] == 3 and scene.look.heated and scene.look.byHand and scene.look.down == 1.0
    assert scene.show.shown["newItemName"] == "minecraft:beef" and scene.show.shownPieces == 3
    run(scene, 0.1)
    assert len(world.drops) == 3 and not scene.show.landings.landing(0, False), "刚加载：东西本来就在，不落"
    Scenes.OnBlockEntityLoaded({"blockName": "minecraft:stone", "dimensionId": 0, "posX": 1, "posY": 2, "posZ": 3})
    assert len(Scenes._scenes) == 1


def testRemovingTheBlockDropsTheSceneAndTheDimensionChangeDropsAll():
    scene = setup()
    Scenes.OnPanLook(payload())
    run(scene, 0.1)
    Scenes.OnBlockEntityRemoved({"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert Scenes.sceneAt(0, POS) is None and not world.drops
    assert (0, POS) not in BlockItems._hidden, "方块没了：以后别的东西（砧板……）放在这个位置不会被当成还在隐藏"
    Scenes.ensure(0, POS)
    Scenes.OnDimensionChange()
    assert not Scenes._scenes and (0, POS) not in BlockItems._hidden


class Clock(object):
    now = 100.0

    @classmethod
    def time(cls):
        cls.now += 1.0 / 60.0
        return cls.now


def testTheRenderTickDrivesNearScenesEveryFrameAndFarOnesEveryFourth():
    scene = setup()
    Scenes.OnPanLook(payload())
    realTime, Scenes.time = Scenes.time, Clock
    try:
        Scenes._state["last"] = None
        world.foot = (10.5, 64.0, 10.5)
        Scenes.OnRenderTick()
        Scenes.OnRenderTick()
        assert scene.clock > 0.0, "近处：每帧算"
        clock = scene.clock
        world.foot = (10.5, 64.0, 10.5 + 36.0)                  # 36 格：过了 32（不放粒子声音、隔帧算），还在 40 以内（照画）
        Scenes._state["tick"] = 0
        for _ in range(3):
            Scenes.OnRenderTick()
        assert scene.clock == clock, "远处三帧不算"
        Scenes.OnRenderTick()
        assert scene.clock > clock, "第四帧算一次（带上前几帧的时间）"
        world.foot = (10.5, 64.0, 10.5 + 41.0)                  # 过了 40：不算
        clock = scene.clock
        for _ in range(8):
            Scenes.OnRenderTick()
        assert scene.clock == clock, "太远不算"
    finally:
        Scenes.time = realTime


def testNothingHappensWhenThePrerequisiteIsNotThere():
    world.reset()
    Scenes._scenes.clear()
    Scenes._state["on"] = False
    Scenes.OnPanLook(payload())
    Scenes.OnBlockEntityLoaded({"blockName": "arris:skillet", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    Scenes.OnRenderTick()
    assert not Scenes._scenes and not world.drops
    Scenes._state["on"] = True


if __name__ == "__main__":
    raise SystemExit(C.fdtest.run(globals()))
