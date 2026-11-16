# -*- coding: utf-8 -*-
# runner: both
"""厨锅在本客户端的场景（Compat/Diegesis 的 PotScene / PotHands / PotSceneFx / PotModel，假引擎）。"""
from __future__ import print_function

import potclient as C

world = C.world
Scenes = C.load("Compat.Diegesis.PotScenes")
BrothColors = C.load("Shared.Data.BrothColors")
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


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
