# -*- coding: utf-8 -*-
# runner: both
"""熄着的炉灶在本客户端：场景（Compat/Diegesis 的 StoveScene / StoveScenes / GrillPieces）和没有前置包时世界里的展示（Client/BlockItems，假引擎）。
对照 HoD 的 StoveBehavior：站点和场景不看 LIT 都画烤架上的东西、落下 / 翻面 / 取走的动作；只有 heat（java:261-306）的开头 !LIT 就 sizzle = 0 返回：
熄着没有热浪、蒸汽、烟、嗞嗞声；落到烤架上的嘶声和蒸汽（hitsTheGrill）只在点着时（refresh 里 if (lit)，:172）；翻面落下的汽和声音不看 LIT（:394-398）。"""
from __future__ import print_function

import math
import random

import panclient as C

world = C.install()
Scene = C.load("Compat.Diegesis.StoveScene")
Scenes = C.load("Compat.Diegesis.StoveScenes")
BlockItems = C.load("Client.BlockItems")
Blocks = C.load("Shared.Rules.GrillBlocks")
POS = C.POS
DT = 1.0 / 60.0
LIT, UNLIT = "arris:stove", "arris:stove_extinguish"
BEEF, COOKED = "minecraft:beef", "minecraft:cooked_beef"


class Clock(object):
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


clock = Clock()
Scenes.time = clock


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def slot(name, hand=False, down=0.0, up=0.0):
    return {"item": item(name), "hand": hand, "down": down, "up": up}


def payload(slots=None):
    full = [dict(slots or {}).get(place, {}) for place in range(6)]
    return {"dimensionId": 0, "pos": list(POS), "slots": full}


def setup(blockName=UNLIT, aux=2, slots=None):
    """干净的假世界、这个方块（点着的或熄着的）的场景；给了 slots 就先广播一份并走一帧。"""
    world.reset()
    world.blocks[POS] = (blockName, aux)
    Scenes._scenes.clear()
    Scenes._state.update(on=False, last=None, tick=0, check=0.0)
    BlockItems._hidden.clear()
    BlockItems._last.clear()
    Scenes.enable()
    random.seed(3)
    scene = Scenes.ensure(0, POS)
    if slots is not None:
        Scenes.OnStoveLook(payload(slots))
        run(scene, DT)
    return scene


def run(scene, seconds, near=True):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, near)


def drops(name=None):
    return [d for d in world.drops.values() if name is None or d["item"]["newItemName"] == name]


def centerOf(drop):
    x, y, z = [math.radians(angle) for angle in drop["euler"]]
    half = 8.0 / 16.0 * drop["scale"] * 0.5
    up = (-math.sin(z) * math.cos(x), math.cos(z) * math.cos(x), math.sin(x))
    return tuple(drop["pivot"][axis] + up[axis] * half for axis in range(3))


def particles(identifier=None):
    return [p for p in world.particles if identifier is None or p["id"] == identifier]


def sounds(name):
    return [s for s in world.sounds if s["name"] == name]


def silent():
    """热浪、蒸汽、烟、嗞嗞声一样都没有。"""
    return world.particles == [] and sounds("ambient.skillet.sizzle") == []


# ---------------------------------------------------------------- 场景认得熄着的炉灶

def testAnUnlitStoveGetsASceneThatKnowsItIsUnlitAndTheLitOneKnowsItIsLit():
    scene = setup(UNLIT)
    assert scene is not None and Scenes.sceneAt(0, POS) is scene and scene.pieces.lit is False
    scene = setup(LIT)
    assert scene.pieces.lit is True
    world.blocks[(3, 3, 3)] = ("minecraft:stone", 0)
    assert Scenes.ensure(0, (3, 3, 3)) is None


def testAnUnlitStoveDrawsItsPiecesWhereTheLitOneDoesAndTurnsWithItsFacing():
    for aux in range(4):
        slots = dict((place, slot(BEEF)) for place in range(6))
        setup(LIT, aux, slots)
        lit = sorted((round(centerOf(d)[0], 4), round(centerOf(d)[1], 4), round(centerOf(d)[2], 4), tuple(round(v, 3) for v in d["euler"])) for d in drops(BEEF))
        scene = setup(UNLIT, aux, slots)
        unlit = sorted((round(centerOf(d)[0], 4), round(centerOf(d)[1], 4), round(centerOf(d)[2], 4), tuple(round(v, 3) for v in d["euler"])) for d in drops(BEEF))
        assert len(unlit) == 6 and unlit == lit, aux
        assert scene.yaw == {0: 180, 1: 270, 2: 0, 3: 90}[aux], "朝向照方块的 aux 读，和点着的一个读法"


def testTheWorldDisplayWithoutTheSceneDrawsTheUnlitStoveToo():
    """没装前置包：Client/BlockItems 按方块名挑摆法，熄着的炉灶也是炉灶；位置、朝向和点着的一样。"""
    assert BlockItems.kindOf(UNLIT) == "stove" and BlockItems.kindOf(LIT) == "stove" and BlockItems.kindOf("arris:skillet") == "skillet"
    assert BlockItems.kindOf("minecraft:stone") is None
    for aux in range(4):
        shown = {}
        for name in (LIT, UNLIT):
            world.reset()
            world.blocks[POS] = (name, aux)
            BlockItems._hidden.clear()
            BlockItems._last.clear()
            BlockItems.OnBlockItems({"dimensionId": 0, "pos": list(POS), "kind": "stove", "items": dict((str(place), item(BEEF)) for place in range(6))})
            shown[name] = sorted((round(centerOf(d)[0], 4), round(centerOf(d)[2], 4), tuple(round(v, 3) for v in d["euler"])) for d in drops(BEEF))
            BlockItems.clear(0, POS)
        assert len(shown[UNLIT]) == 6 and shown[UNLIT] == shown[LIT], aux


def testTheBlockEntityOfTheUnlitBlockIsDrawnFromItsSavedDataOnLoad():
    world.reset()
    world.blocks[POS] = (UNLIT, 2)
    world.exData[POS] = {"0": {"itemDict": item(BEEF), "cookTimer": 12}, "3": {"itemDict": item(BEEF), "cookTimer": 30}}
    BlockItems._hidden.clear()
    BlockItems._last.clear()
    BlockItems.OnBlockEntityLoaded({"blockName": UNLIT, "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert len(drops(BEEF)) == 2, "区块晚加载：熄着的炉灶上的东西照样补出来"


# ---------------------------------------------------------------- 熄着没有热气、烟、嗞嗞声

def testAnUnlitGrillHasNoShimmerSteamSmokeOrSizzleWhateverLiesOnIt():
    scene = setup(UNLIT, 2, {0: slot(BEEF, True, 1.0, 0.0), 1: slot(BEEF, True, 0.3, 0.0), 2: slot(COOKED, True, 1.0, 1.0), 3: slot(BEEF)})
    run(scene, 8.0)
    assert silent(), (particles(), world.sounds)
    scene = setup(UNLIT, 2, {})
    run(scene, 8.0)
    assert silent(), "空烤架也没有热浪"
    assert len(drops()) == 0


def testTheSameGrillWhenLitDoesShimmerSteamSmokeAndSizzle():
    """对照：点着的那一份在同样的状态下一样都有（不然上面的"没有"什么也说明不了）。"""
    scene = setup(LIT, 2, {0: slot(BEEF, True, 1.0, 0.0), 1: slot(BEEF, True, 0.3, 0.0)})
    run(scene, 8.0)
    kinds = set(p["id"] for p in world.particles)
    assert {"arris:pan_heat", "arris_diegesis:steam"} <= kinds and sounds("ambient.skillet.sizzle")


def testLightingItStartsTheHeatAndPuttingItOutStopsItWhicheverWayTheSceneLearnsOfIt():
    scene = setup(UNLIT, 2, {0: slot(BEEF, True, 1.0, 0.0), 1: slot(BEEF, True, 0.3, 0.0)})
    run(scene, 3.0)
    assert silent()
    # 点着了：服务端换了方块，客户端重建方块实体、加载事件带着新方块名
    world.blocks[POS] = (LIT, 2)
    Scenes.OnBlockEntityLoaded({"blockName": LIT, "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert Scenes.sceneAt(0, POS) is scene and scene.pieces.lit is True, "场景留着，只是点着了"
    Scenes.OnStoveLook(payload({0: slot(BEEF, True, 1.0, 0.0), 1: slot(BEEF, True, 0.3, 0.0)}))
    run(scene, 5.0)
    assert {"arris:pan_heat", "arris_diegesis:steam"} <= set(p["id"] for p in world.particles) and sounds("ambient.skillet.sizzle")
    # 灭了：这回没有收到加载事件，只有一份广播（ensure 读方块名）
    world.blocks[POS] = (UNLIT, 2)
    Scenes.OnStoveLook(payload({0: slot(BEEF, True, 1.0, 0.0), 1: slot(BEEF, True, 0.3, 0.0)}))
    assert scene.pieces.lit is False
    del world.particles[:], world.sounds[:]
    run(scene, 5.0)
    assert silent(), "灭了：热浪、蒸汽、烟、嗞嗞声都停"


def testTheScenePicksUpTheNewStateFromTheBlockEvenWithoutAnyEvent():
    """点火 / 灭火换方块，没收到移除 / 加载事件、也没来广播：每隔一会儿的核对（本来就为了看方块还在不在）顺手读方块名。"""
    scene = setup(LIT, 2, {0: slot(BEEF, True, 0.3, 0.0)})
    world.blocks[POS] = (UNLIT, 2)
    for _ in range(30):
        clock.now += 0.1
        Scenes.OnRenderTick()
    assert Scenes.sceneAt(0, POS) is scene and scene.pieces.lit is False, "熄着的炉灶是炉灶：场景不会被当成没了收掉"
    world.blocks[POS] = (LIT, 2)
    for _ in range(30):
        clock.now += 0.1
        Scenes.OnRenderTick()
    assert Scenes.sceneAt(0, POS) is scene and scene.pieces.lit is True


def testAnUnlitSceneStaysThroughManySecondsOfRenderTicks():
    scene = setup(UNLIT, 2, {0: slot(BEEF), 1: slot(BEEF)})
    for _ in range(300):
        clock.now += 0.1
        Scenes.OnRenderTick()
    assert Scenes.sceneAt(0, POS) is scene and len(drops(BEEF)) == 2


# ---------------------------------------------------------------- 落下、翻面、取走照样

def testAPieceLandingOnAnUnlitGrillMakesNoHissAndNoSteamButStillLands():
    scene = setup(UNLIT, 2, {0: slot(BEEF)})
    Scenes.OnStoveLook(payload({0: slot(BEEF), 2: slot(BEEF)}))
    run(scene, DT)
    assert scene.pieces.motion[2].pose()[0][1] > 3.0, "新放上来的照样从烤架上方落下"
    run(scene, 0.6)
    assert abs(centerOf(drops()[0])[1] - (POS[1] + 16.3 / 16.0)) < 0.02, "落回烤架面"
    assert not sounds("ambient.skillet.addfood") and not particles("arris_diegesis:steam"), "熄着的灶上落下没有嘶声和蒸汽"
    scene = setup(LIT, 2, {0: slot(BEEF)})
    Scenes.OnStoveLook(payload({0: slot(BEEF), 2: slot(BEEF)}))
    run(scene, 0.6)
    assert sounds("ambient.skillet.addfood") and particles("arris_diegesis:steam"), "对照：点着的有"


def testPlacingTurningAndTakingMakeTheirOwnNoisesOnAnUnlitGrillToo():
    """JE：放上去的灯笼声、翻面的起跳声和落下的下料声 + 汽、取走的拾取声都不看 LIT（只有落下那一下的嘶声和平时的热气看）。"""
    scene = setup(UNLIT, 2, {0: slot(BEEF), 1: slot(BEEF)})
    del world.sounds[:]
    Scenes.OnStoveLook({"dimensionId": 0, "pos": list(POS), "event": "placed", "places": [0]})
    assert [s["name"] for s in world.sounds] == ["block.lantern.place"]
    del world.sounds[:]
    scene.pieces.turned(0)
    run(scene, 0.8)
    names = [s["name"] for s in world.sounds]
    assert "block.lantern.step" in names and "ambient.skillet.addfood" in names and particles("arris_diegesis:steam"), names
    del world.sounds[:]
    Scenes.OnStoveLook({"dimensionId": 0, "pos": list(POS), "event": "taken", "place": 1, "stack": item(BEEF)})
    assert [s["name"] for s in world.sounds] == ["random.pop"]


def testALoadEventForTheTwinKeepsTheStoveAndReplaysNothing():
    """换方块时客户端的方块实体重建（加载事件带新方块名）：场景留着，件重画、不演落下。"""
    scene = setup(LIT, 2, {0: slot(BEEF), 1: slot(BEEF)})
    world.exData[POS] = {"0": {"itemDict": item(BEEF), "cookTimer": 12}, "1": {"itemDict": item(BEEF), "cookTimer": 30}, "handGrill": None}
    world.blocks[POS] = (UNLIT, 2)
    del world.sounds[:]
    Scenes.OnBlockEntityLoaded({"blockName": UNLIT, "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    run(scene, 0.5)
    assert Scenes.sceneAt(0, POS) is scene and len(drops(BEEF)) == 2 and scene.pieces.lit is False
    assert all(piece.pose()[0][1] == 0.0 for piece in scene.pieces.motion), "重建不演落下"
    assert not sounds("ambient.skillet.addfood")


if __name__ == "__main__":
    raise SystemExit(C.dgtest.run(globals()))
