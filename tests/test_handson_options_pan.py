# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里煎锅的煎制时间倍率 skillet_time 和煎锅站点的开关（Shared/Rules/PanStation + Server/HandFrying + StationBooks）：
站点里手放的一批一面煎多久按倍率走（还是按批量的平方根和火焰附加）；站点关了，存档里留下的手放的锅交给 FD 原样煎（HandFrying.fry 返回 False）；书上写的是同一个时间。
JE 的对照：SkilletTests.theFryingTimeFollowsTheConfig / aStationTurnedOffHandsThePanToFarmersDelight，SkilletCooking.sideTicks / fry。
FD 自己的右键放进去的照旧 6 秒一件那一半在 test_handson_options_skillet.py（用 Server/Skillet 的真处理函数）。引擎是 panfake 里的假的。"""
from __future__ import print_function

import math

import fdtest
import panfake as P
from optkit import Config

Books = fdtest.load("Shared.Rules.StationBooks")
Rules = P.Rules
BEEF, EGG = P.BEEF, P.EGG
FD_TICKS = {0: 120, 1: 80, 2: 60, 3: 60}   # SkilletBlock.getSkilletCookingTime(600, 火焰附加)：6 / 4 / 3 秒


def javaRound(value):
    return int(math.floor(value + 0.5))


def jeSideTicks(skilletTicks, batch, times):
    """SkilletCooking.sideTicks（56-58 行）：Math.max(1, Math.round(skilletTicks * times * sqrt(max(1, batch)) / PACE / 2.0F))，PACE 是 1.5。"""
    return max(1, javaRound(skilletTicks * times * math.sqrt(max(1, batch)) / 1.5 / 2.0))


def _place(manager, name=BEEF, count=1):
    P.opened(manager)
    P.hold("a", 35, name, count)
    assert P.do(manager, "a", P.click(P.inv(35)))
    assert P.do(manager, "a", P.custom("place"))


def testASideTakesTheSkilletTimeTimesTheConfigAndTheSquareRootOfTheBatchLikeJEsSideTicks():
    for times in (1.0, 2.0, 0.5, 0.1, 10.0, 3.3):
        for aspect in (0, 1, 2, 3):
            for batch in (1, 2, 4, 9, 16):
                with Config(skillet_time=times):
                    assert round(Rules.sideSeconds(batch, aspect) * 20) == jeSideTicks(FD_TICKS[aspect], batch, times), (times, aspect, batch)
    assert abs(Rules.sideSeconds(1) - 2.0) < 1e-9 and abs(Rules.sideSeconds(16) - 8.0) < 1e-9, "缺省没变"
    with Config(skillet_time=2.0, skillet=False):
        assert abs(Rules.sideSeconds(1) - 2.0) < 1e-9, "站点关了倍率算 1.0"
    with Config(skillet_time=2.0, stove=False, cooking_pot=False, cutting_board=False):
        assert abs(Rules.sideSeconds(1) - 4.0) < 1e-9, "别的站点关了不相干"


def testTheFryingTimeFollowsTheConfig():
    # SkilletTests.theFryingTimeFollowsTheConfig：1.0 一面是平常的 40 刻，2.0 同一步只走一半
    steps = []
    for times in (1.0, 2.0):
        manager, data = P.setup()
        with Config(skillet_time=times):
            _place(manager)
            P.step(1.0)
            steps.append(P.HandFrying.peek(0, P.PAN).frying.down)
    assert abs(steps[0] - 0.5) < 1e-9 and abs(steps[0] - 2.0 * steps[1]) < 1e-9, steps


def testABatchIsDoneInTheConfiguredTimeOfBothSides():
    manager, data = P.setup()
    with Config(skillet_time=2.0):
        _place(manager, BEEF, 4)
        side = Rules.sideSeconds(4)                      # 6 秒 x 2（倍率）x 2（批量 4 的平方根）/ 1.5 / 2 = 8 秒一面
        assert abs(side - 8.0) < 1e-9
        P.run(manager, side - 0.5)
        hand = P.HandFrying.peek(0, P.PAN)
        assert hand.frying.down < 1.0
        P.run(manager, 1.0)
        assert hand.frying.waits(), "一面熟了等颠锅"
        assert P.do(manager, "a", P.custom("toss", strength=0.5))
        P.run(manager, side + 0.5)
        assert P.inPan() == (P.COOKED, 4)


def testAnEggFriesThroughInTheTimeOfBothSidesAtTheConfiguredPace():
    for times, done in ((1.0, 4.0), (2.0, 8.0)):
        manager, data = P.setup()
        with Config(skillet_time=times):
            _place(manager, EGG, 1)
            P.run(manager, done - 0.6)
            assert P.inPan() == (EGG, 1), times
            P.run(manager, 1.2)
            assert P.inPan() == ("arris:fried_egg", 1), (times, P.inPan())


def testAStationTurnedOffHandsThePanToFarmersDelight():
    # SkilletTests.aStationTurnedOffHandsThePanToFarmersDelight：站点开着放进去的等颠锅；关了没人能颠，按 FD 的煎法煎（fry 返回 False 就是交给 Server/Skillet）
    manager, data = P.setup()
    _place(manager)
    hand = P.HandFrying.peek(0, P.PAN)
    assert hand.frying.byHand and data["panFrying"]["byHand"] is True
    with Config(skillet=False):
        assert P.HandFrying.fry(hand, 0, P.PAN, data, 0.25, 0) is False, "不归手工管了"
        assert not hand.frying.byHand and data["panFrying"] is None, "手放的记号清了，存档里也清了"
        assert P.inPan() == (BEEF, 1), "锅里的东西还在，等 FD 煎"
    assert P.HandFrying.fry(P.HandFrying.handOf(0, P.PAN, data), 0, P.PAN, data, 0.25, 0) is False, "之后它就是 FD 的锅了，开着站点也不会再变回手放的"


def testWithTheStationOnAHandFriedPanStaysTheCooksAndWaitsForTheToss():
    manager, data = P.setup()
    _place(manager)
    P.run(manager, 6.0)
    hand = P.HandFrying.peek(0, P.PAN)
    assert hand.frying.byHand and hand.frying.waits() and P.inPan() == (BEEF, 1), "等翻的就一直等翻"


def testTheBookWritesTheScaledTimeOfBothSides():
    # SkilletBook：2 * sideTicks(FD 煎锅的时间, 1, CookingTimes.skillet())，Math.round(刻数 / 20)
    def note(name=BEEF):
        return next(page for page in Books.panPages() if page["key"] == name)["note"]
    assert note() == "4 秒" and note(EGG) == "4 秒", "蛋用的也是两面的时间"
    for times, literal in ((2.0, "8 秒"), (0.5, "2 秒"), (0.1, "0 秒"), (10.0, "40 秒"), (3.0, "12 秒")):
        with Config(skillet_time=times):
            assert note() == literal and note(EGG) == literal, times
    for times in (1.3, 3.3, 0.35, 7.77):
        with Config(skillet_time=times):
            assert note() == "%d 秒" % javaRound(2 * jeSideTicks(120, 1, times) / 20.0), times
    with Config(skillet_time=3.0, skillet=False):
        assert note() == "4 秒", "站点关了书也不乘"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
