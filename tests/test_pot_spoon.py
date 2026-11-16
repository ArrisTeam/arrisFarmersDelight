# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点的勺子手感（Compat/Diegesis/PotSpoon.py）：跟手、够不着就收回、汤转起来、报服务端的节奏、松手回锅沿。"""
from __future__ import print_function

import math

import fdtest

PotSpoon = fdtest.load("Compat.Diegesis.PotSpoon")
StirSkill = fdtest.load("Shared.Rules.HandsOn.StirSkill")

FRAME = 1.0 / 60.0


def _circle(hand, seconds, turnsPerSecond=1.0, radius=2.5):
    """手在汤里按圈搅 seconds 秒（60 帧/秒），返回 [(时刻, x, z)] 报给服务端的勺尖（-1..1）。"""
    sent, t = [], 0.0
    for _ in range(int(seconds / FRAME)):
        t += FRAME
        angle = 2.0 * math.pi * turnsPerSecond * t
        hand.aim(math.cos(angle) * radius, math.sin(angle) * radius)
        if hand.step(FRAME, True, True, None, True):
            sent.append((t, hand.tip[0] / PotSpoon.SPOON_REACH, hand.tip[1] / PotSpoon.SPOON_REACH))
    return sent


def testTheTipFollowsTheHandButStaysInThePot():
    hand = PotSpoon.SpoonHand()
    hand.aim(30.0, 0.0)
    assert abs(hand.want[0] - PotSpoon.SPOON_REACH) < 1.0e-9 and hand.want[1] == 0.0
    for _ in range(60):
        hand.step(FRAME, True, True)
    assert abs(hand.tip[0] - PotSpoon.SPOON_REACH) < 0.01 and hand.lift < 0.01


def testStirringSpinsTheSoupAndReportsAboutEightTimesASecond():
    hand = PotSpoon.SpoonHand()
    sent = _circle(hand, 3.0)
    assert 20 <= len(sent) <= 26, len(sent)
    gaps = [b[0] - a[0] for a, b in zip(sent, sent[1:])]
    assert min(gaps) >= PotSpoon.SEND_INTERVAL - 1.0e-9
    assert hand.swirl > 0.5 and hand.swirlSign > 0.9, "逆时针搅：汤朝同一个方向转"
    stars, grade = StirSkill.scoreSamples(sent, cooking=True, openStars=3)
    assert grade >= 2, "宽圈、一秒一圈、稳速：报上去的勺尖能评到高星（%.2f）" % stars


def testAStillHandSendsNothingAndTheSoupCalmsDown():
    hand = PotSpoon.SpoonHand()
    _circle(hand, 1.0)
    swirl = hand.swirl
    sends = 0
    for _ in range(120):
        sends += hand.step(FRAME, True, True, None, True)
    assert sends <= 1, "手不动就不报"
    assert hand.swirl < swirl * 0.5


def testLettingGoLeavesTheSpoonThenItGoesBackToTheRim():
    hand = PotSpoon.SpoonHand()
    _circle(hand, 1.0)
    left = list(hand.tip)
    for _ in range(30):
        hand.step(FRAME, False, True)
    assert math.hypot(hand.tip[0] - left[0], hand.tip[1] - left[1]) < 0.05, "锅还算被搅着：勺子停在松手处"
    for _ in range(int(PotSpoon.HAND_MEMORY / FRAME) + 120):
        hand.step(FRAME, False, False)
    home = PotSpoon.SPOON_HOME
    assert math.hypot(hand.tip[0] - home[0], hand.tip[1] - home[1]) < 0.05 and hand.lift > 0.95


def testAPressAfterStirringStartsCountingTravelAfresh():
    """实机：搅完一圈再短按一块漂着的料，旧的勺尖位置被算进了挪动距离，点击被当成拖动、没取回。"""
    hand = PotSpoon.SpoonHand()
    _circle(hand, 1.0)
    hand.press()
    hand.aim(-2.0, 1.5)
    assert hand.travel == 0.0, hand.travel
    hand.aim(-2.1, 1.5)
    assert abs(hand.travel - 0.1) < 1.0e-9


def testSomebodyElsesSpoonFollowsTheSyncedTip():
    hand = PotSpoon.SpoonHand()
    for _ in range(120):
        assert not hand.step(FRAME, False, True, (-2.0, 1.0), True), "不是本人握着就不报"
    assert math.hypot(hand.tip[0] + 2.0, hand.tip[1] - 1.0) < 0.05


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
