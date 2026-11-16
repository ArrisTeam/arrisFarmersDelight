# -*- coding: utf-8 -*-
# runner: both
"""抓着锅柄颠锅的手势（Shared/Rules/HandsOn/PanStroke.py）：数值照 SkilletBehavior.stroked——往上超过 30 像素每秒算一颠，110 是最大力度，
一次按住最多颠一回，不到 0.35 秒的一按算点一下（力度 0.4），按久了没颠锅放回原位。"""
from __future__ import print_function

import fdtest

Stroke = fdtest.load("Shared.Rules.HandsOn.PanStroke")
FRAME = 1.0 / 60.0


def near(a, b, eps=1e-9):
    return abs(a - b) < eps


class Tosses(object):
    def __init__(self, accept=True):
        self.calls, self.accept = [], accept

    def __call__(self, strength):
        self.calls.append(strength)
        return self.accept


def testConstantsAreJavas():
    assert (Stroke.CLICK, Stroke.FLICK, Stroke.HARDEST) == (0.35, 30.0, 110.0)
    assert Stroke.CLICK_STRENGTH == 0.4 and Stroke.TOSS_GAP == 0.42
    assert Stroke.LIFT == (0.0, 0.5, 0.3) and Stroke.LIFT_TIME == 0.08 and Stroke.SET_DOWN_TIME == 0.12


def testStrengthRunsFromTheFlickSpeedToTheHardestSpeed():
    assert Stroke.strengthOf(30.0) == 0.0 and Stroke.strengthOf(110.0) == 1.0
    assert near(Stroke.strengthOf(70.0), 0.5) and Stroke.strengthOf(500.0) == 1.0 and Stroke.strengthOf(5.0) == 0.0


def testAQuickPullUpTossesAtOnceAsHardAsThePull():
    stroke, toss = Stroke.Stroke(), Tosses()
    stroke.start(0.0, 0.0)
    stroke.move(0.1, FRAME, toss)                          # 6 像素每秒：太慢
    assert toss.calls == []
    stroke.move(0.1 + 0.9, 2 * FRAME, toss)                # 这一帧 54 像素每秒
    assert len(toss.calls) == 1 and near(toss.calls[0], (54.0 - 30.0) / 80.0)
    assert stroke.tossedThisPress


def testOnlyOneTossPerPress():
    stroke, toss = Stroke.Stroke(), Tosses()
    stroke.start(0.0, 0.0)
    for i in range(1, 10):
        stroke.move(i * 2.0, i * FRAME, toss)              # 每帧 2 像素 = 120 像素每秒，一直在甩
    assert len(toss.calls) == 1, "一次按住最多颠一回"


def testARefusedTossLeavesRoomForAnotherInTheSamePress():
    stroke, toss = Stroke.Stroke(), Tosses(accept=False)
    stroke.start(0.0, 0.0)
    stroke.move(2.0, FRAME, toss)
    stroke.move(4.0, 2 * FRAME, toss)
    assert len(toss.calls) == 2 and not stroke.tossedThisPress, "被拒的（锅空着、上一颠还在空中）不占这一按的名额"


def testMovingDownOrSlowlyNeverTosses():
    stroke, toss = Stroke.Stroke(), Tosses()
    stroke.start(5.0, 0.0)
    for i in range(1, 30):
        stroke.move(5.0 - i * 0.2, i * FRAME, toss)        # 往下
    for i in range(30, 60):
        stroke.move(-1.0 + (i - 30) * 0.2, i * FRAME, toss)    # 每帧 0.2 = 12 像素每秒：太慢
    assert toss.calls == []


def testAQuickClickTossesGently():
    stroke, toss = Stroke.Stroke(), Tosses()
    stroke.start(0.0, 1.0)
    assert stroke.end(1.2, toss) is False
    assert toss.calls == [0.4], "不到 0.35 秒松手：点一下，力度 0.4，不用找手势"


def testAClickThatCouldNotTossSetsThePanBackDown():
    stroke, toss = Stroke.Stroke(), Tosses(accept=False)
    stroke.start(0.0, 1.0)
    assert stroke.end(1.2, toss) is True, "锅空着时点锅柄：锅放回原位（HoD 里它会停在拎起来的位置）"


def testHoldingLongWithoutTossingSetsThePanBackDown():
    stroke, toss = Stroke.Stroke(), Tosses()
    stroke.start(0.0, 1.0)
    assert stroke.end(1.5, toss) is True and toss.calls == []


def testAfterATossTheReleaseLeavesThePanToTheToss():
    stroke, toss = Stroke.Stroke(), Tosses()
    stroke.start(0.0, 0.0)
    stroke.move(5.0, FRAME, toss)
    assert stroke.end(0.2, toss) is False and len(toss.calls) == 1, "颠成了就不再补一颠、也不放回（颠锅自己收）"
    assert not stroke.held


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
