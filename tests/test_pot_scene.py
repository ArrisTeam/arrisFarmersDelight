# -*- coding: utf-8 -*-
# runner: both
"""厨锅在本客户端的场景（Compat/Diegesis 的 PotScene / PotHands / PotSceneFx / PotModel，假引擎）。"""
from __future__ import print_function

import random

import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
PotLiquid = C.load("Shared.Rules.HandsOn.PotLiquid")
LiquidColor = C.load("Shared.Rules.HandsOn.PotLiquidColor")
Tint = C.load("Shared.Rules.PotTint")
PotDriftExtras = C.load("Shared.Rules.HandsOn.PotDriftExtras")
POS = C.POS
DT = 1.0 / 60.0


def setup():
    C.reset()
    Scenes._scenes.clear()
    Scenes.enable(BrothColors.BrothColors.get)
    return Scenes.ensure(0, POS)


def run(scene, seconds, near=True):
    for _ in range(int(round(seconds / DT))):
        scene.frame(DT, near)


def testASceneBuildsAndTakesTheFirstLook():
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 2)]))
    run(scene, 0.5)
    assert scene.look.items[0]["newItemName"] == "minecraft:carrot"
    assert any(drop["item"]["newItemName"] == "minecraft:carrot" for drop in world.drops.values()), "漂着的料是客户端掉落物"
    assert world.molang[(POS, "variable.mod_open")] == 1.0, "场景接管：开盖"


def sounds(name):
    return [sound for sound in world.sounds if sound["name"] == name]


def testAnotherEggStackedIntoTheSameSlotGetsItsOwnHandAndTheNextOneWaitsItsTurn():
    # PotBehavior.java:719-723（more）、757-763（手忙着就记 again）、1428-1431（走完再来一次）
    scene = setup()
    scene.apply(C.look([("minecraft:egg", 1)], sunk=[0]))
    run(scene, 0.2)
    assert scene.hands.going == {}, "刚看到这口锅：蛋本来就在汤里，没有手"
    scene.apply(C.look([("minecraft:egg", 2)], sunk=[0]))
    run(scene, 0.1)
    first = scene.hands.going[0]["motion"]
    scene.apply(C.look([("minecraft:egg", 3)], sunk=[0]))
    run(scene, 0.2)
    assert scene.hands.going[0]["motion"] is first and scene.drift.arrivals.again[0] == 1, "手还忙着：排上队，不丢"
    run(scene, 2.0)
    second = scene.hands.going[0]["motion"]
    assert second is not first and scene.drift.arrivals.again[0] == 0, "第一只走完，排着的那只来了"
    run(scene, 2.5)
    assert scene.hands.going == {} and not scene.drift.arrivals.again[0]
    assert len(sounds("block.turtle_egg.crack")) == 2, "磕了两次（第三个蛋放进来时第二只还没来，一共两只手）"


def testSeveralMoreEggsStackedWhileTheHandIsBusyBringOnlyOneMoreHand():
    # PotBehavior.java:279-280（again 是 boolean[]）、757-763、1428-1431：手忙着时无论又放了几次，走完只再来一次（原来放几回排几只）
    scene = setup()
    scene.apply(C.look([("minecraft:egg", 1)], sunk=[0]))
    run(scene, 0.2)
    scene.apply(C.look([("minecraft:egg", 2)], sunk=[0]))
    run(scene, 0.1)
    hands = [scene.hands.going[0]["motion"]]
    for count in (3, 4, 5):                                 # 第一只手还在演：又放了三回
        scene.apply(C.look([("minecraft:egg", count)], sunk=[0]))
        run(scene, 0.1)
    assert scene.hands.going[0]["motion"] is hands[0] and scene.drift.arrivals.again[0] is True
    for _ in range(int(7.0 / DT)):
        scene.frame(DT, True)
        entry = scene.hands.going.get(0)
        if entry is not None and entry["motion"] is not hands[-1]:
            hands.append(entry["motion"])
    assert len(hands) == 2, "第一只之后只再来一只（放了三回也一样）：%d 只" % len(hands)
    assert scene.hands.going == {} and scene.drift.arrivals.again[0] is False
    assert len(sounds("block.turtle_egg.crack")) == 2, "一共磕了两次"


def testAStackThatFloatsGrowsWithoutAHand():
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    scene.apply(C.look([("minecraft:carrot", 5)]))
    run(scene, 0.3)
    assert scene.hands.going == {} and scene.drift.events == [], "浮着的料叠多了：什么动作也没有（JE 一样）"



def handsStart(scene, slot):
    return scene.hands.going[slot]["motion"].start


def withEgg(scene, slots=1):
    """锅里先有一根胡萝卜（第一眼不演动作），再放进 slots 个会沉的蛋（一起放进）。"""
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    items = [("minecraft:carrot", 1)] + [("minecraft:egg", 1)] * slots
    scene.apply(C.look(items, sunk=list(range(1, 1 + slots))))


def testTheCooksHandComesDownFromWhereTheCursorIsAboveTheSoup():
    # PotBehavior.java:786-790：splashIn 里会沉的走 goesIn(view.cursorOn(液面上方 9 像素那一层).orElse(锅口正上方))
    scene = setup()
    asked = []
    scene.cursorOn = lambda height: (asked.append(height), (5.0, 11.0))[1]
    withEgg(scene)
    run(scene, 0.05)
    assert len(asked) == 1 and abs(asked[0] - (scene.liquid.surfaceY() + 9.0)) < 0.2, "问的是液面上方 9 像素那一层：%r" % (asked,)
    assert handsStart(scene, 1) == (5.0, asked[0], 11.0), "手从光标落在那一层的点来"


def testWithoutACursorOrForBystandersTheHandComesFromRightAboveTheMiddle():
    for cursorOn in (None, lambda height: None):                  # 旁观的人没有光标；触屏点完也没有
        scene = setup()
        scene.cursorOn = cursorOn
        withEgg(scene)
        run(scene, 0.05)
        start = handsStart(scene, 1)
        assert start[0] == 8.0 and start[2] == 8.0 and abs(start[1] - (scene.liquid.surfaceY() + 9.0)) < 0.2, start


def testSeveralSinkersPutInTogetherEachComeFromTheirOwnPointAndTheFirstFromTheCursor():
    # PotBehavior.java:746-751、859：一次放好几件，轮到的那一件从 FromPlayer 给的各自的点来；第一件错开 0 秒走不到那一支，
    # 飞满 0.4 秒后走 splashIn，手从光标来
    scene = setup()
    scene.startsOf = lambda count: [(-4.0, 6.0), (0.0, 6.0), (4.0, 6.0)][:count]
    scene.cursorOn = lambda height: (5.0, 11.0)
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    scene.apply(C.look([("minecraft:carrot", 1), ("minecraft:egg", 1), ("minecraft:egg", 1), ("minecraft:egg", 1)], sunk=[1, 2, 3]))
    run(scene, 0.2)
    assert sorted(scene.hands.going) == [2], "晚 0.16 秒出发的第二件先轮到；第三件（晚 0.32 秒）、第一件（要飞满 0.4 秒）还没"
    run(scene, 0.25)
    assert sorted(scene.hands.going) == [1, 2, 3]
    assert handsStart(scene, 2)[0::2] == (8.0 + 0.0, 8.0 + 6.0), handsStart(scene, 2)
    assert handsStart(scene, 3)[0::2] == (8.0 + 4.0, 8.0 + 6.0), handsStart(scene, 3)
    assert handsStart(scene, 1)[0::2] == (5.0, 11.0), "第一件的手从光标来"



def targetOf(names, poured=()):
    """锅里放着这些料（还没成菜）、进度 0 时汤面的目标色（PotBehavior.colour 的结果）。"""
    return LiquidColor.brothTarget(PotLiquid.waterColor(), [Tint.colorOf(name) for name in names], False, 0.0, None, list(poured), 0)[0]


MILK = BrothColors.PouredColors["minecraft:milk_bucket"]


def testMilkTintsTheWaterOnlyOnceItStartsToFlowOutOfTheBucket():
    # PotBehavior.java:1050-1060、833-834：倒的液体 waiting（手端着还没流）时不染水，Pour 的 onFlow 才 recolour
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    scene.apply(C.look([("minecraft:carrot", 1), ("minecraft:milk_bucket", 1)], sunk=[1]))
    names = ["minecraft:carrot", "minecraft:milk_bucket"]
    carrying, flowing = targetOf(names), targetOf(names, [MILK])
    assert carrying != flowing
    seconds = 0.0
    while 1 in scene.tint.waiting and seconds < 3.0:
        assert scene.liquid.target == carrying, "手端着还没倒：汤色只带着料的颜色（奶桶本身算一件食物）"
        run(scene, DT)
        seconds += DT
    assert abs(seconds - 0.5) < 0.1, "倒的手端过来 0.3 秒、倾 0.2 秒才开始流：%r" % seconds
    assert scene.hands.going[1]["motion"].flowing and scene.liquid.target == flowing, "开始流的那一帧就按奶色重算"
    run(scene, 2.0)
    assert scene.liquid.target == flowing and scene.hands.going == {}


def testAnEggNeverTintsTheWaterOnlyTheFoodColour():
    # PotBehavior.java:1050：染水的只有 poured；蛋只走食物色（FoodColors.of(egg) = EGG）
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    scene.apply(C.look([("minecraft:carrot", 1), ("minecraft:egg", 1)], sunk=[1]))
    expected = targetOf(["minecraft:carrot", "minecraft:egg"])
    assert scene.tint.waiting == set()
    for _ in range(12):
        assert scene.liquid.target == expected
        run(scene, 0.25)
    assert len(sounds("block.turtle_egg.crack")) == 1, "这期间手磕过蛋了"


def testALiquidAlreadyInThePotWhenItIsFirstSeenTintsAtOnce():
    scene = setup()
    scene.apply(C.look([("minecraft:milk_bucket", 1)], sunk=[0]))
    assert scene.tint.waiting == set() and scene.liquid.target == targetOf(["minecraft:milk_bucket"], [MILK])


def testAnotherBottleStackedInTheSlotKeepsTheWaterTinted():
    # JE 的 waiting 里有 !sunk[i]：这格里第一份倒进去了，再叠一份来倒时不会把已经染上的色收回去
    scene = setup()
    scene.apply(C.look([("arris:milk_bottle", 1)], sunk=[0]))
    tinted = scene.liquid.target
    scene.apply(C.look([("arris:milk_bottle", 2)], sunk=[0]))
    run(scene, 0.1)
    assert 0 in scene.hands.going, "第二瓶有自己的手"
    for _ in range(10):
        assert scene.liquid.target == tinted and scene.tint.waiting == set()
        run(scene, 0.2)


def testTakingTheLiquidBackWhileItIsBeingPouredStopsTheHandAndTheWait():
    # PotBehavior.java:728-735：格子里换了东西，going[i].stop()
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    scene.apply(C.look([("minecraft:carrot", 1), ("minecraft:milk_bucket", 1)], sunk=[1]))
    run(scene, 0.2)
    assert 1 in scene.hands.going and scene.tint.waiting == set([1])
    scene.apply(C.look([("minecraft:carrot", 1)]))
    assert scene.hands.going == {} and scene.tint.waiting == set()
    assert scene.liquid.target == targetOf(["minecraft:carrot"])
    assert [drop["item"]["newItemName"] for drop in world.drops.values()] == ["minecraft:carrot"], "手端着的桶也收掉了"



def testTheShellBitsOfACrackedEggAreTheDiegesisDustParticleInTheShellColour():
    # KitchenLooks.java:113-116（磕的那下 5 颗）、KitchenMotions.java:510（壳裂开 4 颗）：DiegesisParticles.DUST
    scene = setup()
    withEgg(scene)
    run(scene, 3.0)
    dust = [spec for spec in world.particles if spec["id"] == "arris_diegesis:dust"]
    assert sorted(spec["vars"]["variable.count"] for spec in dust) == [4.0, 5.0], [spec["vars"] for spec in dust]
    for spec in dust:
        rgb = tuple(int(round(spec["vars"][name] * 255.0)) for name in ("variable.tint_r", "variable.tint_g", "variable.tint_b"))
        assert rgb == (0xEA, 0xD9, 0xB8), "壳色"
    assert not [spec for spec in world.particles if spec["id"] == "arris_diegesis:droplet" and spec["vars"].get("variable.scale") == 0.6]


def testTheOpenedEggDropsIntoTheSoupAsTheRawWhiteNotAsAFriedEgg():
    # KitchenMotions.java:447-452：Crack 的蛋液是煎蛋的图标按 RAW_EGG（0xC8E6E2D8，半透明发灰）着色；烤好的小图标 egg_look_0 就是这一档
    scene = setup()
    withEgg(scene)
    inside, everything = set(), set()
    for _ in range(int(3.0 / DT)):
        scene.frame(DT, True)
        for entry in scene.hands.going.values():
            if "inside" in entry["props"]:
                inside.add(entry["props"]["inside"][1])
        everything.update(drop["item"]["newItemName"] for drop in world.drops.values())
    assert inside == set(["arris:egg_look_0"]), "蛋液落进汤里：生蛋清"
    assert "arris:fried_egg" not in everything, "整个过程里没有煎蛋的熟样子：%r" % sorted(everything)


def freeze(scene):
    """让料不再漂、不再转（漂移的角度一直在变，摆出来的 pivot 相对位置跟着变一点点）：这样不抬时每一帧的偏移都一样，抬了多少看得准。"""
    scene.drift.step = lambda *args, **kwargs: None


def raisedBy(scene, slot, surfaceServed=False):
    """这一件的掉落物的 pivot 比它的位置（漂移的位置 / 盛好的位置）的世界高度高出多少（方块；要先 freeze，不抬时的偏移才是定的）。"""
    drift = scene.drift
    if surfaceServed:
        base = scene.world(*PotDriftExtras.servedAt(scene.liquid.surfaceY()))[1]
    else:
        base = scene.world(drift.x[slot], drift.y[slot], drift.z[slot])[1]
    return world.drops[scene.props[slot][0]]["pivot"][1] - base


def testAHoveredFloatingItemRisesPointSixPixelsAndSettlesBackWhenTheCursorLeaves():
    # NodeInstance.java:808-810：被光标指着的槽节点 y 加 0.6 * hoverAmount；半衰期 0.06 秒追 1 / 0（HOVER_HALF_LIFE）
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1), ("minecraft:potato", 1)]))
    run(scene, 1.0)
    freeze(scene)
    run(scene, 0.1)
    rest = [raisedBy(scene, 0), raisedBy(scene, 1)]
    scene.lift.target = 0
    frames = 4
    run(scene, frames * DT)
    amount = 1.0 - 0.5 ** (frames * DT / 0.06)
    assert abs(raisedBy(scene, 0) - rest[0] - amount * 0.6 / 16.0) < 1e-6, "悬停量按半衰期 0.06 秒追 1，抬 0.6 像素乘它"
    run(scene, 1.0)
    assert abs(raisedBy(scene, 0) - rest[0] - 0.6 / 16.0) < 1e-3, "最后抬 0.6 像素（1/16 格为 1 像素）"
    assert abs(raisedBy(scene, 1) - rest[1]) < 1e-9, "没指着的那件不动"
    scene.lift.target = None
    run(scene, 1.0)
    assert abs(raisedBy(scene, 0) - rest[0]) < 1e-4, "光标移开：落回去"


def testTheServedSlotRisesToo():
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)], served=C.item("arris:pumpkin_soup"), meal=C.item("arris:pumpkin_soup", 3)))
    run(scene, 1.0)
    freeze(scene)
    run(scene, 0.1)
    rest = raisedBy(scene, 6, True)
    scene.lift.target = 6
    run(scene, 1.0)
    assert abs(raisedBy(scene, 6, True) - rest - 0.6 / 16.0) < 1e-3


def testARestingPotStillFramesWhileAnItemIsPointedAtAndWhileItFallsBack():
    # 场景静了一阵就歇着（awake 用完）；指着一件料时要接着画，不然抬不起来
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 6.0)
    assert scene.frame(DT, True) is False, "什么都没动：歇着"
    freeze(scene)
    rest = raisedBy(scene, 0)
    scene.lift.target = 0
    assert scene.frame(DT, True) is True, "光标指着：不歇着"
    run(scene, 0.5)
    assert raisedBy(scene, 0) - rest > 0.6 / 16.0 * 0.99
    scene.lift.target = None
    run(scene, 0.2)
    assert scene.lift.active or raisedBy(scene, 0) - rest > 0.0, "刚移开还没落回去"
    frames = 0
    while scene.frame(DT, True) and frames < 600:
        frames += 1
    assert frames < 600, "落回去之后又歇着了"
    assert abs(raisedBy(scene, 0) - rest) < 1e-4


def splashes(since=0):
    return [spec for spec in world.particles[since:] if spec["id"] == "arris_diegesis:splash"]


def testAnotherPlayersScoopSplashesFourSeparateSpotsOnTheSoupThatJumpSevenPixelsPerSecond():
    # PotBehavior.java:119,690：spawnOnLiquid(SPLASH, "broth", 4, 汤色, SPLASH_UP = (0, 7, 0))，一颗一个点，在汤面中间 80% 里随机
    random.seed(3)
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    before = len(world.particles)
    scene.event("scooped", {})
    found = splashes(before)
    assert len(found) == 4, [spec["vars"] for spec in found]
    spots = set()
    for spec in found:
        assert spec["vars"]["variable.count"] == 1.0, "一颗一个点"
        for axis, want in (("variable.vx", 0.0), ("variable.vy", 7.0), ("variable.vz", 0.0)):
            assert abs(spec["vars"][axis] - want) < 5 * 0.875, spec["vars"]       # SceneParticles.spawn：每轴再抖 gauss * max(0.3, 7 * 0.25)，标准差 0.875（分布在 test_scene_scatter.py）
        assert spec["vars"]["variable.speed_set"] == 1.0
        x, y, z = scene.local(*spec["pos"])
        assert 4.8 - 1e-6 <= x <= 11.2 + 1e-6 and 4.8 - 1e-6 <= z <= 11.2 + 1e-6, "汤面中间那一块里：%r" % ((x, z),)
        assert abs(y - scene.liquid.surfaceY()) < 1e-6
        spots.add((round(x, 6), round(z, 6)))
    assert len(spots) == 4, "四个点各不相同"


def testTheCooksOwnScoopAddsNoSplashSinceTheBowlAlreadySplashedWhereItWentIn():
    # PotBehavior.java:688：dip == null && time - scoopedHere > 1 才溅（盛的人自己那边碗落下去的地方已经溅过了）；声音照放
    scene = setup()
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 0.2)
    before = len(world.particles)
    scene.event("scooped", {}, True)
    assert splashes(before) == [] and sounds("handson.pot.scoop")


def testAnItemThatLandsSplashesFiveWithTheStyleDefaultSpeedNotAnInventedOne():
    # PotBehavior.java:793：spawnParticles(SPLASH, 节点, 5, 汤色)——走节点那个重载，速度是样式缺省的 (0, 16, 0)，水花粒子不给速度就是这个
    scene = setup()
    scene.apply(C.look([]))
    run(scene, 0.2)
    before = len(world.particles)
    scene.apply(C.look([("minecraft:carrot", 1)]))
    run(scene, 2.0)
    found = splashes(before)
    assert len(found) == 1 and found[0]["vars"]["variable.count"] == 5.0
    assert "variable.speed_set" not in found[0]["vars"] and "variable.vy" not in found[0]["vars"], found[0]["vars"]


def testTheEggInsideSplashesThreeAtSixPixelsPerSecondWhereItLands():
    # KitchenMotions.java:541：spawnParticles(SPLASH, 落点, (0, 6, 0), 0.5, 3, 蛋白色)
    scene = setup()
    withEgg(scene)
    before = len(world.particles)
    run(scene, 3.0)
    found = splashes(before)
    assert len(found) == 1 and found[0]["vars"]["variable.count"] == 3.0, [spec["vars"] for spec in found]
    assert (found[0]["vars"]["variable.vx"], found[0]["vars"]["variable.vy"], found[0]["vars"]["variable.vz"]) == (0.0, 6.0, 0.0)
    assert found[0]["vars"]["variable.speed_set"] == 1.0


def testAParticleTheEngineDidNotMakeIsNotTouched():
    """进世界头几秒粒子系统还没好、或者没有这个粒子：Create 回 0（不是 None）——不能拿 0 当编号去设变量（内核的 view.particles 同一个规矩）。"""
    PotFx = C.load("Compat.Diegesis.PotFx")
    comp, touched = C.C.Comp, []
    create, setVariable = comp.Create, comp.SetVariable
    comp.Create = lambda self, identifier, pos: 0
    comp.SetVariable = lambda self, *args: touched.append(args)
    try:
        assert PotFx.particle(PotFx.SPLASH, (0.5, 1.0, 0.5), color=0x3F76E4, alpha=0.5, scale=1.0, velocity=(0.0, 1.0, 0.0)) is None
    finally:
        comp.Create, comp.SetVariable = create, setVariable
    assert touched == []


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
