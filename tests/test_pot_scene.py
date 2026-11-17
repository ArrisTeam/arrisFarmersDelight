# -*- coding: utf-8 -*-
# runner: both
"""厨锅在本客户端的场景（Compat/Diegesis 的 PotScene / PotHands / PotSceneFx / PotModel，假引擎）。"""
from __future__ import print_function

import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
PotLiquid = C.load("Shared.Rules.HandsOn.PotLiquid")
LiquidColor = C.load("Shared.Rules.HandsOn.PotLiquidColor")
Tint = C.load("Shared.Rules.PotTint")
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
