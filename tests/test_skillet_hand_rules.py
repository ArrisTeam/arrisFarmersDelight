# -*- coding: utf-8 -*-
# runner: both
"""手持煎锅烹饪的规则（Shared/Rules/SkilletHandRules.py）：右键按住的上报与记录、一次烹饪的计时、滋滋声概率。"""
from __future__ import print_function

import fdtest

Hand = fdtest.load("Shared.Rules.SkilletHandRules")


def testHoldTrackerExpiresWhenTheClientGoesQuiet():
    holds = Hand.HoldTracker()
    assert holds.held("p", 0.0) is False
    holds.beat("p", 10.0)
    assert holds.held("p", 10.5) is True and holds.held("p", 10.0 + Hand.HOLD_TIMEOUT - 0.01) is True
    assert holds.held("p", 10.0 + Hand.HOLD_TIMEOUT + 0.01) is False
    holds.beat("p", 20.0)
    holds.release("p")
    assert holds.held("p", 20.1) is False
    assert Hand.HOLD_BEAT < Hand.HOLD_TIMEOUT                  # 客户端按住时的报告间隔要短于服务端的超时，否则按着也会被当成松手


def testHoldTrackerKeepsPlayersApart():
    holds = Hand.HoldTracker()
    holds.beat("a", 1.0)
    assert holds.held("a", 1.1) is True and holds.held("b", 1.1) is False
    holds.release("b")
    assert holds.held("a", 1.1) is True


def testHandCookFinishesAfterItsSeconds():
    cook = Hand.HandCook("minecraft:beef", "minecraft:cooked_beef", 6.0, 100.0)
    assert not cook.finished(105.9) and cook.finished(106.0)


def testSizzleChanceAccumulatesTheJePerTickChance():
    assert abs(Hand.sizzleChance(1.0 / 20) - 0.02) < 1e-9
    assert abs(Hand.sizzleChance(0.25) - (1 - 0.98 ** 5)) < 1e-9


def testReporterSendsHeldWhileTheSkilletIsInHandAndTheButtonIsDown():
    reporter = Hand.HoldReporter()
    assert reporter.press(0.0, carrying=False) is None and reporter.down is False       # 拿别的东西右键：不报
    assert reporter.press(10.0, carrying=True) is True and reporter.down is True
    asked = []
    carrying = lambda: asked.append(1) or True                                         # noqa: E731
    assert reporter.tick(10.1, carrying) is None and asked == []                       # 没到 HOLD_BEAT：不去问手里拿的什么
    assert reporter.tick(10.0 + Hand.HOLD_BEAT + 0.001, carrying) is True and len(asked) == 1
    assert reporter.tick(10.0 + Hand.HOLD_BEAT + 0.05, carrying) is None and len(asked) == 1
    assert reporter.tick(10.0 + 2 * Hand.HOLD_BEAT + 0.01, carrying) is True
    assert reporter.release() is False and reporter.down is False
    assert reporter.release() is None and reporter.tick(99.0, carrying) is None         # 松开之后不再报


def testReporterReleasesWhenTheSkilletLeavesTheHand():
    reporter = Hand.HoldReporter()
    reporter.press(0.0, True)
    assert reporter.tick(0.05, lambda: False) is None                                  # 还没到该报告的时候
    assert reporter.tick(0.3, lambda: False) is False and reporter.down is False       # 按住时换了物品：下一次报告时报松开
    assert reporter.tick(1.0, lambda: False) is None and reporter.tick(1.0, lambda: True) is None


def testTheSkilletCanBeInEitherHand():
    skillet = "arris:skillet_item"
    assert Hand.skilletHand(skillet, "minecraft:beef", skillet) == Hand.MAIN
    assert Hand.skilletHand("minecraft:beef", skillet, skillet) == Hand.OFF
    assert Hand.skilletHand(skillet, skillet, skillet) == Hand.MAIN, "JE 先试主手"
    assert Hand.skilletHand("minecraft:beef", None, skillet) is None and Hand.skilletHand(None, None, skillet) is None


def testEatingGivesWayToCookingOnlyWithAnOffHandSkilletNearHeat():
    skillet = "arris:skillet_item"
    cooks = Hand.cooksInsteadOfEating
    assert cooks("minecraft:beef", skillet, skillet, True, True)
    assert not cooks("minecraft:beef", skillet, skillet, True, False), "身边没热源：照常吃"
    assert not cooks("minecraft:bread", skillet, skillet, False, True), "没有营火配方的食物：照常吃"
    assert not cooks("minecraft:beef", None, skillet, True, True), "副手没煎锅"
    assert not cooks(skillet, "minecraft:beef", skillet, True, True), "煎锅在主手：主手这件不是食物，用不着取消"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
