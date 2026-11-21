# -*- coding: utf-8 -*-
# runner: both
"""煎锅 / 炉灶上煎着的东西朝上那面的熟色在本客户端怎么画（Compat/Diegesis/FryTints 接在 PanScene、StoveScene 上，假引擎）：
朝上那面半熟的件躺稳之后叠一颗图标粒子 arris:fry_tint（颜色、不透明度、半边长、UV 是变量），和那件掉落物朝上那面严丝合缝；颠起来、翻面时收着，
停稳了再亮；熟了、拿走了、场景没了就删；蛋、没有颜色的、方块物品不叠；图集和粒子系统还没好时不画、好了再画，老引擎一件都不染；歇着的锅不碰引擎。
对应 HoD 的 SkilletBehavior.drawPiece / StoveBehavior.draw 的 node.setTint(KitchenLooks.fryingTint(...))。"""
from __future__ import print_function

import math

import panclient as C

world = C.install()
PanScenes = C.load("Compat.Diegesis.PanScenes")
StoveScenes = C.load("Compat.Diegesis.StoveScenes")
FryTints = C.load("Compat.Diegesis.FryTints")
BlockItems = C.load("Client.BlockItems")
Tint = C.load("Shared.Rules.FryingTint")
Overlay = C.load("Shared.Rules.TopOverlay")
Cooking = C.load("Shared.Data.Cooking")
POS = C.POS
DT = 1.0 / 60.0
BEEF, COOKED, EGG = "minecraft:beef", "minecraft:cooked_beef", "minecraft:egg"
VARIABLES = ("variable.u", "variable.v", "variable.w", "variable.h", "variable.half", "variable.r", "variable.g", "variable.b", "variable.alpha")


def near(a, b, eps=1e-6):
    return abs(a - b) < eps


def close(u, v, eps=1e-6):
    return all(near(a, b, eps) for a, b in zip(u, v))


def item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def run(scene, seconds, near_=True):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, near_)


def tints():
    """还在的熟色粒子。"""
    return [p for p in world.particles if p["id"] == FryTints.PARTICLE and not p["removed"]]


def lit():
    return [p for p in tints() if p["vars"].get("variable.alpha", 0.0) > 0.0]


def colorOf(name, up):
    return Tint.overlay(Tint.tintOf(name, Cooking.CanCookedFoodDict.get(name, name), up))


def fresh():
    world.reset()
    FryTints._icons.clear()
    FryTints._blocks.clear()
    FryTints._engine["icons"] = None
    BlockItems._hidden.clear()
    BlockItems._last.clear()


# ---------------------------------------------------------------- 几何：粒子贴在掉落物朝上那面上

def _rx(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _ry(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rz(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _column(m, j):
    return (m[0][j], m[1][j], m[2][j])


def sitsOn(particle, drop):
    """粒子是不是贴在这件掉落物朝上那面上：掉落物 SetDropItemTransform 的转角是 R = Rz(z)·Rx(x)·Ry(y)（ItemPose），粒子 SetRot 是 E = Rz·Ry·Rx；
    图标右 E.x = R·(-1, 0, 0)、图标上 -E.z = R·(0, 1, 0)、法线 E.y = R·(0, 0, -1)；位置在贴图正中沿法线抬 lift；半边长是贴图边长的一半。"""
    x, y, z = drop["euler"]
    item = _mul(_mul(_rz(z), _rx(x)), _ry(y))
    a, b, c = particle["rot"]
    quad = _mul(_mul(_rz(c), _ry(b)), _rx(a))
    right, up, front = [-v for v in _column(item, 0)], _column(item, 1), [-v for v in _column(item, 2)]
    half = 7.2 / 16.0 * drop["scale"] * 0.5
    center = [drop["pivot"][k] + up[k] * half for k in range(3)]
    lift = Overlay.lift(drop["scale"]) / 16.0
    return (close(_column(quad, 0), right, 2e-3) and close([-v for v in _column(quad, 2)], up, 2e-3) and close(_column(quad, 1), front, 2e-3)
            and close(particle["pos"], [center[k] + front[k] * lift for k in range(3)], 1e-3)
            and near(particle["vars"]["variable.half"], 7.2 * drop["scale"] / 32.0, 1e-3))


def pairs(name):
    """每颗熟色粒子配上它贴着的那件 name 掉落物（正好一件；配不上、配上好几件的是 None）。"""
    drops = [d for d in world.drops.values() if d["item"]["newItemName"] == name]
    found = []
    for particle in tints():
        on = [drop for drop in drops if sitsOn(particle, drop)]
        found.append((particle, on[0] if len(on) == 1 else None))
    return found


def allPaired(name):
    """每颗熟色粒子都贴着一件 name 掉落物，一件只有一颗。"""
    found = pairs(name)
    return found and all(drop is not None for _, drop in found) and len(set(id(drop) for _, drop in found)) == len(found)


# ---------------------------------------------------------------- 煎锅

def panSetup():
    fresh()
    PanScenes._scenes.clear()
    PanScenes.enable()
    return PanScenes.ensure(0, POS)


def panLook(name=BEEF, count=2, down=0.0, up=0.5, heated=False, both=False):
    return {"dimensionId": 0, "pos": list(POS), "item": item(name, count) if name else {}, "batch": count if name else 0, "byHand": True,
            "heated": heated, "down": down, "up": up, "rate": 0.0, "both": both}


def testAHalfDoneTopIsTintedOnceThePiecesLieStillExactlyOverTheirTopFaces():
    """两块生牛肉、朝上那面煎到一半（厨师没等贴锅那面熟透就颠过）：每块一颗粒子，躺稳两个游戏刻之后才亮；颜色是 FryingTint 的 (q, a)，
    UV 是这件物品的图标在图集里的位置。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook())
    run(scene, 0.05)
    assert len([d for d in world.drops.values() if d["item"]["newItemName"] == BEEF]) == 2 and lit() == [], "刚摆上：还没停稳，不亮"
    run(scene, 0.2)
    assert len(lit()) == 2 == len(tints()), "两块各一颗"
    r, g, b, a = colorOf(BEEF, 0.5)
    assert near(a, 23.0 / 255.0) and near(g, 6.0 / 23.0)
    for particle in lit():
        values = particle["vars"]
        assert sorted(values) == sorted(VARIABLES)
        assert close([values[name] for name in ("variable.r", "variable.g", "variable.b", "variable.alpha")], (r, g, b, a), 1e-4)
        assert close([values[name] for name in ("variable.u", "variable.v", "variable.w", "variable.h")], C.ICON, 1e-4)
    assert allPaired(BEEF), "每颗都贴在一块牛肉朝上那面上"


def testEachSkilletFacingAndAFullPanStillPutsEveryQuadOnItsPiece():
    """锅柄朝哪（方块的 aux）都对得上；一锅 6 件：上面 4 块、垫着 2 块，垫着的也染（JE 的 drawPiece 给 under_N 同一个颜色）。"""
    for aux in range(4):
        scene = panSetup()
        world.blocks[POS] = ("arris:skillet", aux)
        PanScenes._scenes.clear()
        scene = PanScenes.ensure(0, POS)
        PanScenes.OnPanLook(panLook(count=6, up=0.75))
        run(scene, 0.3)
        assert len(lit()) == 6, aux
        assert allPaired(BEEF), aux


def testATossDimsTheTintUntilThePiecesHaveLandedAndStoppedAgain():
    """颠锅：飞着、翻着的时候粒子收着（不透明度 0，粒子还在），落回锅里停稳了再亮——翻过来朝上的是原来贴锅那面（0.6），颜色跟着换。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(down=0.6, up=0.5))
    run(scene, 0.3)
    before = set(p["particle"] for p in lit())
    assert len(before) == 2
    scene.event("tossed", {"strength": 1.0})
    run(scene, 0.15)
    assert len(tints()) == 2 and lit() == [], "飞着：收着"
    run(scene, 1.5)
    assert set(p["particle"] for p in lit()) == before, "落回去、停稳了：同一颗粒子再亮"
    r, g, b, a = colorOf(BEEF, 0.6)
    assert all(near(p["vars"]["variable.alpha"], round(a, 4), 1e-4) and near(p["vars"]["variable.g"], round(g, 4), 1e-4) for p in lit())
    assert allPaired(BEEF)


def testNoTintWhileTheTopIsRawAndTheParticleGoesWhenItIsDone():
    """朝上那面一点没煎：白，不叠；煎到一半叠上；熟了（换成熟的图）粒子删掉，不在世界里留着。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(up=0.0))
    run(scene, 0.3)
    assert tints() == []
    PanScenes.OnPanLook(panLook(up=0.5))
    run(scene, 0.3)
    assert len(lit()) == 2
    PanScenes.OnPanLook(panLook(up=1.0))
    run(scene, 0.3)
    assert tints() == [] and len([p for p in world.particles if p["id"] == FryTints.PARTICLE and p["removed"]]) == 2
    assert [d["item"]["newItemName"] for d in world.drops.values()] == [COOKED] * 2


def testAnEggAndFoodWithoutColoursAndBlockItemsGetNoParticle():
    """蛋是 EggLook 那几件预染色的显示物品，不再叠；下游模组追加的、MainColors 里没有的不染；物品类型是方块的不叠（图标不在 atlas.items 里）。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook(name=EGG, count=1, down=0.5, up=0.5, both=True))
    run(scene, 0.3)
    assert tints() == [] and [d["item"]["newItemName"] for d in world.drops.values()] == ["arris:egg_look_1"]
    Cooking.CanCookedFoodDict["othermod:raw_steak"] = "othermod:steak"
    try:
        scene = panSetup()
        PanScenes.OnPanLook(panLook(name="othermod:raw_steak"))
        run(scene, 0.3)
        assert tints() == [] and len(world.drops) == 2, "照样画，只是不染"
    finally:
        del Cooking.CanCookedFoodDict["othermod:raw_steak"]
    scene = panSetup()
    world.itemTypes["minecraft:kelp"] = "block"
    PanScenes.OnPanLook(panLook(name="minecraft:kelp"))
    run(scene, 0.3)
    assert tints() == []
    world.itemTypes.clear()
    FryTints._blocks.clear()
    run(scene, 0.1)
    assert len(lit()) == 2, "不是方块的海带照染"


def testAOneSidedFoodThatIsNotAnEggIsTintedOnThePanAndOnTheStove():
    """HoD 的 one_sided 不是 cracked：fryingTint 只给蛋（isCracked）走 RAW_EGG 那一支。下游往 OneSidedList 里加的马铃薯在锅里、烤架上
    都画它自己、照别的食物染（服务端给只煎一面的发 both）；蛋照旧画 EggLook 的显示物品、不叠，烤架上（FD 自己的右键放得上去）也一样。"""
    Cooking.OneSidedList.append("minecraft:potato")
    try:
        scene = panSetup()
        PanScenes.OnPanLook(panLook(name="minecraft:potato", count=2, down=0.5, up=0.5, both=True))
        run(scene, 0.3)
        assert [d["item"]["newItemName"] for d in world.drops.values()] == ["minecraft:potato"] * 2, "不画成煎蛋"
        assert len(lit()) == 2 and allPaired("minecraft:potato"), "照染"
        alpha = colorOf("minecraft:potato", 0.5)[3]
        assert alpha > 0.0 and all(near(p["vars"]["variable.alpha"], round(alpha, 4), 1e-4) for p in lit())
        scene = stoveSetup({1: piece("minecraft:potato", 0.0, 0.5)})
        run(scene, 0.3)
        assert [d["item"]["newItemName"] for d in world.drops.values()] == ["minecraft:potato"], "烤架上也不画成煎蛋"
        assert len(lit()) == 1 and allPaired("minecraft:potato")
    finally:
        Cooking.OneSidedList.remove("minecraft:potato")
    assert Cooking.OneSidedList == [EGG]
    scene = stoveSetup({1: piece(EGG, 0.0, 0.5)})
    run(scene, 0.3)
    assert tints() == [] and [d["item"]["newItemName"] for d in world.drops.values()] == ["arris:egg_look_1"], "蛋照旧"


def testNothingIsDrawnUntilTheAtlasAndTheParticleSystemAreReady():
    """进世界头几秒 GetIconInfo 回 None、粒子 Create 回 0：那时不画，之后再试；问到的图标记下，不再问。"""
    scene = panSetup()
    world.iconsReady = False
    PanScenes.OnPanLook(panLook())
    run(scene, 0.5)
    assert world.particles == []
    world.iconsReady, world.particleFails = True, 2
    run(scene, DT)
    assert tints() == [] and world.particleFails == 0, "两块各试了一回，都没建出来"
    run(scene, DT)
    assert len(lit()) == 2
    world.counts.clear()
    PanScenes.OnPanLook(panLook(up=0.75))
    run(scene, 0.3)
    assert "GetIconInfo" not in world.counts and len(lit()) == 2


def testAnOldEngineWithoutIconInfoTintsNothing():
    scene = panSetup()
    world.oldEngine = True
    PanScenes.OnPanLook(panLook())
    run(scene, 0.5)
    assert world.particles == [] and len(world.drops) == 2


def testTheParticlesGoWithTheFoodAndWithTheScene():
    scene = panSetup()
    PanScenes.OnPanLook(panLook())
    run(scene, 0.3)
    PanScenes.OnPanLook(panLook(count=1))
    run(scene, 0.3)
    assert len(tints()) == 1 and len(lit()) == 1, "拿走了一块：它那颗删掉"
    PanScenes.OnPanLook(panLook(name=None))
    run(scene, 0.3)
    assert tints() == []
    PanScenes.OnPanLook(panLook())
    run(scene, 0.2)
    assert lit() == [], "放进来的两块一块接一块落下：落着的时候不亮"
    run(scene, 0.6)
    assert len(lit()) == 2 and allPaired(BEEF)
    PanScenes.OnBlockEntityRemoved({"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert tints() == [] and not world.drops, "锅没了：粒子和掉落物一起收掉"


def testATintedPanThatRestsDoesNotTouchTheEngine():
    """凉锅里半熟的两块躺着：亮了之后歇着，一次引擎也不碰（只剩每 0.5 秒的核对）；醒着（本人开着站点）也不再发粒子。"""
    scene = panSetup()
    PanScenes.OnPanLook(panLook())
    run(scene, 6.0)
    assert len(lit()) == 2 and scene.frame(DT) is False, "歇着了"
    world.counts.clear()
    run(scene, 3.0)
    assert set(world.counts) <= {"GetBlockEntityMolangValue"}, world.counts
    scene.show.focused = True
    run(scene, 0.5)
    world.counts.clear()
    run(scene, 1.0)
    assert not set(world.counts) & {"Create", "SetPos", "SetRot", "SetVariable", "Remove", "GetIconInfo", "GetItemBasicInfo"}, world.counts


# ---------------------------------------------------------------- 炉灶

def stoveSetup(slots, aux=2):
    fresh()
    world.blocks[POS] = ("arris:stove", aux)
    StoveScenes._scenes.clear()
    StoveScenes._state.update(on=False, last=None, tick=0, check=0.0)
    StoveScenes.enable()
    scene = StoveScenes.ensure(0, POS)
    StoveScenes.OnStoveLook(stoveLook(slots))
    run(scene, DT)
    return scene


def stoveLook(slots):
    full = [dict(slots).get(place, {}) for place in range(6)]
    return {"dimensionId": 0, "pos": list(POS), "slots": full}


def piece(name, down=0.0, up=0.0):
    return {"item": item(name), "hand": True, "down": down, "up": up}


def event(name, place=None, **data):
    body = dict(data, dimensionId=0, pos=list(POS), event=name)
    if place is not None:
        body["place"] = place
    return body


def testAHalfDoneGrillPieceIsTintedAndATurnDimsItUntilItLiesStillAgain():
    """烤架上一件朝上那面烤到 1/4（翻得早了）：亮着这件自己的颜色；别人翻了它（服务端先发效果、再发对调过的状态）：跳起、翻着时收着，
    落下停稳之后按翻过来朝上的那面（0.5）再亮；拿走了就删。炉灶朝哪都贴得上。"""
    for aux in (2, 0, 3):
        scene = stoveSetup({0: piece(BEEF, 0.5, 0.25), 4: piece(BEEF)}, aux)
        run(scene, 0.2)
        assert len(lit()) == 1, "只有朝上那面烤过的那件"
        particle = lit()[0]
        assert near(particle["vars"]["variable.alpha"], round(colorOf(BEEF, 0.25)[3], 4), 1e-4)
        assert allPaired(BEEF), aux
        StoveScenes.OnStoveLook(event("turned", 0, up=0.5))
        StoveScenes.OnStoveLook(stoveLook({0: piece(BEEF, 0.25, 0.5), 4: piece(BEEF)}))
        run(scene, 0.1)
        assert lit() == [] and len(tints()) == 1, "翻着：收着"
        run(scene, 0.5)
        assert [p["particle"] for p in lit()] == [particle["particle"]] and allPaired(BEEF)
        assert near(particle["vars"]["variable.alpha"], round(colorOf(BEEF, 0.5)[3], 4), 1e-4), "翻过来朝上的那面烤到一半"
        StoveScenes.OnStoveLook(event("taken", 0, stack=item(BEEF)))
        StoveScenes.OnStoveLook(stoveLook({4: piece(BEEF)}))
        run(scene, DT)
        assert tints() == [], "拿走了：删"


def testADoneTopAndAStoveThatGoesAwayLeaveNoParticles():
    scene = stoveSetup({1: piece(BEEF, 0.0, 1.0)})
    run(scene, 0.3)
    assert tints() == [], "朝上那面熟了：画熟的图，不染"
    StoveWorld = C.load("Compat.Diegesis.StoveWorld")
    keep = StoveWorld.addDropItem
    StoveWorld.addDropItem = lambda item, dimensionId, pos: None          # 引擎没给实体：WorldProp 没有姿态
    try:
        scene = stoveSetup({1: piece(BEEF, 0.0, 0.5)})
        run(scene, 0.3)
        assert tints() == [] and world.drops == {}, "掉落物没建成：不叠，也不拿空的姿态去算"
    finally:
        StoveWorld.addDropItem = keep
    scene = stoveSetup({1: piece(BEEF, 0.0, 0.5), 2: piece("minecraft:potato", 0.0, 0.5)})
    run(scene, 0.3)
    assert len(lit()) == 2
    StoveScenes.OnBlockEntityLoaded({"blockName": "arris:stove", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert tints() == [], "方块实体重建：件全收掉，粒子跟着"
    StoveScenes.OnStoveLook(stoveLook({1: piece(BEEF, 0.0, 0.5)}))
    run(scene, 0.3)
    assert len(lit()) == 1
    world.blocks[POS] = ("arris:stove", 0)
    StoveScenes.OnBlockEntityLoaded({"blockName": "arris:stove", "dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert tints() == [], "炉灶转了向：照新朝向重画，旧的粒子删掉"
    StoveScenes.OnStoveLook(stoveLook({1: piece(BEEF, 0.0, 0.5)}))
    run(scene, 0.3)
    assert len(lit()) == 1
    StoveScenes.OnBlockEntityRemoved({"dimensionId": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2]})
    assert tints() == []


if __name__ == "__main__":
    raise SystemExit(C.fdtest.run(globals()))
