# -*- coding: utf-8 -*-
# runner: both
"""煎锅场景里节点的动作（Shared/Rules/HandsOn/PanNodes.py）：Diegesis 的 Tween / NodeInstance 的 moveTo、hopTo、rotateTo、scaleTo、shake，
和 SkilletBehavior 的 after 排队器。数值照 Tween.java（inOutCubic 缓动，弧用不缓动的时间）。"""
from __future__ import print_function

import fdtest

Nodes = fdtest.load("Shared.Rules.HandsOn.PanNodes")


def near(a, b, eps=1e-9):
    return abs(a - b) < eps


def testInOutCubicIsSlowAtBothEnds():
    ease = Nodes.inOutCubic
    assert ease(0.0) == 0.0 and ease(1.0) == 1.0 and near(ease(0.5), 0.5)
    assert near(ease(0.25), 4 * 0.25 ** 3), "前半是 4t^3"
    assert near(ease(0.75), 1.0 - 0.5 ** 3 / 2.0), "后半是 1 - (2 - 2t)^3 / 2"
    assert ease(-1.0) == 0.0 and ease(2.0) == 1.0, "夹进 0..1"


def testATweenEasesFromWhereItIs():
    tween = Nodes.Tween(0.0, 0.0, 0.0)
    tween.start(10.0, 0.0, 0.0, 1.0)
    assert tween.running
    tween.update(0.5)
    assert near(tween.value[0], 5.0), "走了一半的时间，缓动也是一半"
    tween.start(0.0, 0.0, 0.0, 1.0)                      # 半路改道：从此刻的值出发，不跳
    assert near(tween.value[0], 5.0)
    tween.update(0.5)
    assert near(tween.value[0], 2.5)
    tween.update(5.0)
    assert near(tween.value[0], 0.0) and not tween.running, "到了就停在终点"


def testAHopLiftsInTheMiddleByTheGivenHeight():
    tween = Nodes.Tween(0.0, 1.0, 0.0)
    tween.start(4.0, 1.0, 0.0, 1.0, height=2.0)
    tween.update(0.5)
    assert near(tween.value[1], 3.0), "中点比直线高 height（弧用不缓动的时间：sin(pi * 0.5)）"
    tween.update(0.5)
    assert near(tween.value[1], 1.0, 1e-6) and near(tween.value[0], 4.0)


def testZeroSecondsJumps():
    tween = Nodes.Tween()
    tween.start(1.0, 2.0, 3.0, 0.0)
    assert tween.value == [1.0, 2.0, 3.0] and not tween.running


def testANodeAddsItsMovesToItsBase():
    node = Nodes.Node("piece_0", (0.0, 1.01, 0.0), False)
    assert node.pos == (0.0, 1.01, 0.0) and node.rot == (0.0, 0.0, 0.0) and node.scale == 1.0 and not node.visible
    node.moveTo(2.0, 0.5, -1.0, 0.0)
    node.rotateTo(0.0, 30.0, 0.0, 0.0)
    node.scaleTo(1.4, 0.0)
    assert node.pos == (2.0, 1.51, -1.0) and node.rot == (0.0, 30.0, 0.0) and node.scale == 1.4
    node.hopTo(0.0, 0.0, 0.0, 1.0, 0.5)
    assert node.moving
    node.update(0.5)
    assert not node.moving, "isMoving 只看位移"


def testPlaceSetsEverythingAtOnce():
    node = Nodes.Node("hand_0", (0.0, 0.0, 0.0))
    node.place((8.0, 3.0, 9.0), (16.0, 180.0, -20.0), 0.7)
    assert node.pos == (8.0, 3.0, 9.0) and node.rot == (16.0, 180.0, -20.0) and node.scale == 0.7 and not node.moving


def testShakeFadesOutOverItsTime():
    node = Nodes.Node("x")
    node.shake(1.0, 0.5)
    node.update(0.25, lambda: 1.0)
    assert near(node.pos[0], 0.5), "幅度从 1 线性减到 0：过了一半还剩 0.5"
    node.update(0.25, lambda: 1.0)
    assert node.pos == (0.0, 0.0, 0.0), "抖完归零"
    node.update(0.1, lambda: 1.0)
    assert node.pos == (0.0, 0.0, 0.0)


def testStepsRunInTheOrderTheyWereQueued():
    steps, seen = Nodes.Steps(), []
    steps.after(0.2, lambda: seen.append("late"))
    steps.after(0.1, lambda: seen.append("early"))
    steps.advance(0.05)
    assert seen == []
    steps.advance(0.2)
    assert seen == ["late", "early"], "到期的按排进来的次序跑（Java 是 filter 之后 forEach），不按时刻排"
    steps.after(0.1, lambda: seen.append("again"))
    steps.advance(0.1)
    assert seen[-1] == "again" and len(steps) == 0


def testAStepMayQueueAnother():
    steps, seen = Nodes.Steps(), []
    steps.after(0.1, lambda: steps.after(0.1, lambda: seen.append("second")))
    steps.advance(0.15)
    assert seen == []
    steps.advance(0.1)
    assert seen == ["second"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
