# -*- coding: utf-8 -*-
# runner: both
"""厨锅漂着的料、盛好的那格的悬停抬起（Shared/Rules/HandsOn/PotHover.HoverLift，Diegesis NodeInstance.hoverAmount）：
指着的追 1、别的追 0，半衰期 0.06 秒；悬停量大过 0.001 才抬，抬 0.6 像素乘悬停量，只抬 y。"""
from __future__ import print_function

import fdtest

Hover = fdtest.load("Shared.Rules.HandsOn.PotHover")
POSE = (6.0, 5.0, 9.0, 10.0, 20.0, 30.0)


def run(lift, seconds):
    lift.step(seconds)               # 缓动是精确的指数，一步走 seconds 秒和分成很多小步一样（下面有一条专门比）


def testTheConstantsAreDiegesisNodeInstances():
    assert Hover.HOVER_HALF_LIFE == 0.06 and Hover.HOVER_LIFT == 0.6 and Hover.HOVER_MIN == 0.001     # NodeInstance.java:33,809,808


def testNothingIsLiftedUntilTheCursorPointsAtSomething():
    lift = Hover.HoverLift(7)
    run(lift, 1.0)
    assert lift.amount == [0.0] * 7 and not lift.active
    assert lift.raised(3, POSE) == POSE, "没指着：姿态原样"


def testThePointedAtOneClosesHalfTheGapEveryHalfLifeAndTheOthersStay():
    lift = Hover.HoverLift(7)
    lift.target = 2
    run(lift, Hover.HOVER_HALF_LIFE)
    assert abs(lift.amount[2] - 0.5) < 1e-9, "半衰期 0.06 秒：走掉一半"
    run(lift, Hover.HOVER_HALF_LIFE)
    assert abs(lift.amount[2] - 0.75) < 1e-9
    assert [lift.amount[index] for index in (0, 1, 3, 4, 5, 6)] == [0.0] * 6, "只有指着的那一个抬"
    run(lift, 1.0)
    assert lift.amount[2] > 0.999 and lift.amount[2] < 1.0, "追 1 而不到：指数缓动"


def testTheFrameLengthDoesNotMatterToTheEasing():
    a, b = Hover.HoverLift(1), Hover.HoverLift(1)
    a.target = b.target = 0
    for _ in range(30):
        a.step(0.01)
    b.step(0.3)
    assert abs(a.amount[0] - b.amount[0]) < 1e-9


def testRaisedAddsPointSixTimesTheAmountToYOnly():
    lift = Hover.HoverLift(7)
    lift.target = 1
    run(lift, 1.0)
    out = lift.raised(1, POSE)
    assert out[0] == POSE[0] and out[2:] == POSE[2:], "只动 y"
    assert abs(out[1] - (POSE[1] + Hover.HOVER_LIFT * lift.amount[1])) < 1e-12 and 5.59 < out[1] < 5.6
    assert lift.raised(0, POSE) == POSE, "别的件不动"


def testTheLiftFallsBackWhenTheCursorLeavesAndTheLastTraceBelowTheThresholdIsIgnored():
    lift = Hover.HoverLift(7)
    lift.target = 4
    run(lift, 0.5)
    lift.target = None
    assert lift.active, "刚移开：还没落回去，场景不能歇着"
    run(lift, Hover.HOVER_HALF_LIFE)
    assert abs(lift.amount[4] - 0.5 * (1.0 - 0.5 ** (0.5 / Hover.HOVER_HALF_LIFE))) < 1e-9, "落回去也是半衰期 0.06 秒"
    run(lift, 1.0)
    assert lift.amount[4] < Hover.HOVER_MIN and not lift.active
    assert lift.raised(4, POSE) == POSE, "小于 0.001 不抬（NodeInstance.java:808）"


def testAnotherItemTakesOverWhileTheFirstFallsBack():
    lift = Hover.HoverLift(7)
    lift.target = 0
    run(lift, 0.5)
    lift.target = 5
    run(lift, Hover.HOVER_HALF_LIFE)
    assert lift.amount[0] < 0.51 and abs(lift.amount[5] - 0.5) < 1e-9


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
