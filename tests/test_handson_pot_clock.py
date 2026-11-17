# -*- coding: utf-8 -*-
# runner: both
"""PotClock 谁在搅、料是谁放的、出锅结算测试（速度与时长见 test_pot_cooking.py）。

移植自 Hands-On Delight 的 PotTests：nothingCooksWithoutStirring、aPotLeftByItsCookCooksOn、
aHopperFedPotCooksByItself、aHopperFeedsThePotByItselfBesideACook，以及 theSetsSavedGoBack /
theSetsSavedStayWhenTheCookLeft 里"省下的料给谁"的部分。时间以秒计；原测试的刻数 / 20。
"""
from __future__ import print_function

import math

import fdtest
import linkkit

linkkit.link()        # 缺省的 stirringRequired 读配置：联动了才生效（没联动时 HandsOnOptions 说 HoD 不在，不要搅）
PotBonus = fdtest.load("Shared.Rules.HandsOn.PotBonus")
Pot = fdtest.load("Shared.Rules.HandsOn.PotCooking")
_Mth = fdtest.load("Shared.Rules.HandsOn.Mth")
TICK = _Mth.TICK
_Spoon = fdtest.load("Shared.Rules.HandsOn.Spoon")
Spoon = _Spoon.Spoon


def newClock(byHand):
    """byHand 为真：料是厨师在工位放的；否则是漏斗之类自己进来的（走和游戏里一样的 feedByHand / watchFood 路径）。"""
    clock = Pot.PotClock()
    clock.watchFood(0)
    if byHand:
        clock.feedByHand()
    clock.watchFood(6)
    assert clock.byHand == byHand
    return clock


def run(clock, start, until, total, batch, attendUntil=None, probes=()):
    """从 start 到 until 逐步推进（不搅；要搅自己先 clock.stir）。返回 (出第一份的时刻, 最后一步的模式, {探测时刻: 进度})。"""
    finishedAt, mode, seen = None, None, {}
    for index in range(int(round((until - start) / TICK))):
        now = start + index * TICK
        if attendUntil is not None and now <= attendUntil + 1.0e-9:
            clock.attend(now)
        mode = clock.advance(now, TICK, total, batch)
        if finishedAt is None and clock.finished(total):
            finishedAt = now + TICK
        for probe in probes:
            if abs(now + TICK - probe) < 1.0e-9:
                seen[probe] = clock.progress(total, batch)
    return finishedAt, mode, seen


def testNothingCooksWithoutStirring():
    clock = newClock(True)
    _, mode, seen = run(clock, 0.0, 1.5, 10.0, 3, attendUntil=100.0, probes=(1.5,))
    assert mode == Pot.WAITING and seen[1.5] == 0.0, "left alone it does not cook"
    clock.stir(1.5)
    _, mode, seen = run(clock, 1.5, 3.0, 10.0, 3, attendUntil=100.0, probes=(3.0,))
    assert mode == Pot.STIRRED and seen[3.0] > 0.0, "stirred it cooks"
    atThree = seen[3.0]
    # 搅一下管 2 秒（原 40 刻）：3.5 秒起不再被搅，进度停在原处
    _, mode, seen = run(clock, 3.0, 6.0, 10.0, 3, attendUntil=100.0, probes=(3.5, 5.0, 6.0))
    assert seen[3.5] > atThree, "the stir lasts until 3.5"
    assert seen[5.0] == seen[3.5] == seen[6.0], "and it stops where it got to: %r" % seen
    assert mode == Pot.WAITING


def testAPotLeftByItsCookCooksOn():
    # 厨师放的料，厨师在场时等勺子；他走了（最后在场 2.0 秒）再过 2 秒起，按 FD 原样一份 10 秒自己煮
    clock = newClock(True)
    finishedAt, mode, seen = run(clock, 0.0, 16.0, 10.0, 3, attendUntil=2.0, probes=(2.0, 4.0))
    assert seen[2.0] == 0.0 and seen[4.0] == 0.0, "with the cook there it waits"
    assert finishedAt is not None and 14.0 < finishedAt < 14.2, "one stew without the cook: %r" % finishedAt
    assert mode == Pot.FD_WAY


def testAHopperFedPotCooksByItself():
    finishedAt, mode, _ = run(newClock(False), 0.0, 13.5, 10.0, 3)
    assert mode == Pot.FD_WAY and finishedAt is not None and abs(finishedAt - 10.0) < 0.1, finishedAt


def testAHopperFeedsThePotByItselfBesideACook():
    # 漏斗喂的料，即便厨师一直在工位也不等勺子
    finishedAt, mode, _ = run(newClock(False), 0.0, 13.5, 10.0, 3, attendUntil=100.0)
    assert mode == Pot.FD_WAY and finishedAt is not None and abs(finishedAt - 10.0) < 0.1, finishedAt


def testWhoFedThePotDecidesWhoCooksIt():
    clock = Pot.PotClock()
    clock.watchFood(0)
    clock.feedByHand()
    clock.watchFood(3)
    assert clock.byHand, "手放的料"
    clock.watchFood(3)
    assert clock.byHand, "没有新料进来，不变"
    clock.watchFood(5)
    assert not clock.byHand, "没有 feedByHand 就进来的料（漏斗、管道、锅自己的菜单）：FD 原样"
    clock.restore(True, 0.5)
    clock.watchFood(9)
    assert clock.byHand, "刚读档：读回来的料早就在锅里，只有此后进来的才说明谁在喂"
    clock.watchFood(10)
    assert not clock.byHand and abs(clock.bonusCarried - 0.5) < 1e-12


def testFarmersDelightsWayTruthTable():
    clock = newClock(True)
    now = 10.0
    clock.attend(now)
    assert not clock.farmersDelightsWay(now), "手放的料、厨师在场、没被搅：等勺子"
    assert clock.farmersDelightsWay(now, stirringRequired=False), "配置里关了搅拌"
    assert clock.farmersDelightsWay(now, inMenu=True), "在锅自己的菜单里操作"
    assert clock.farmersDelightsWay(now + 2.5), "厨师走开超过 AWAY"
    clock.stir(now)
    assert not clock.farmersDelightsWay(now + 0.5) and not clock.farmersDelightsWay(now, inMenu=True), "被搅着永远不走原样"
    clock.attend(now + 2.5)
    assert not clock.farmersDelightsWay(now + 2.5), "搅动过期（now + 2.0）后，厨师还在场：又回到等勺子"
    assert newClock(False).farmersDelightsWay(now), "自动化喂的料"


def testTheStirLastsTwoSeconds():
    clock = Pot.PotClock()
    clock.stir(1.0)
    assert clock.isStirred(1.0) and clock.isStirred(2.95)
    assert not clock.isStirred(3.0), "原版 gameTime < stirredUntil：第 40 刻就不算了"


def testTheCookIsAtTheStationForAWhile():
    clock = Pot.PotClock()
    clock.attend(5.0)
    assert clock.here(5.0) and clock.here(5.1) and not clock.here(5.15)
    assert clock.attended(7.0) and not clock.attended(7.05)


def stirRounds(clock, spoon, who, lastTick, heated=True, batch=2, openStars=3):
    """原 stirWell：宽圈、稳速地搅，每 2 刻一下，到 lastTick（刻）为止。"""
    accepted = True
    for tick in range(0, lastTick + 1, 2):
        angle = tick * math.pi / 10.0
        accepted = Pot.stirStroke(clock, spoon, who, tick / 20.0, math.cos(angle) * 0.9, math.sin(angle) * 0.9,
                                  heated, batch, openStars) and accepted
    return accepted


def testACookWhoKnowsTheDishGetsMore():
    # 做过 40 份的菜开 3 星：宽圈稳速搅 6 秒，两份料出三份；第一次做只开 1 星：两份还是两份（theFirstTimeHasOneStar）
    for made, servings in ((40, 3), (0, 2)):
        clock = newClock(True)
        assert stirRounds(clock, Spoon(), "cook", 120, openStars=PotBonus.openStars(made))
        clock.attend(6.0)
        clock.batch = 2
        plan = clock.serve(6.0, 1, 1, 16)
        assert plan.servings == servings and clock.grade == PotBonus.openStars(made) and clock.bonus == servings - 2, plan


def testAStrokeFromASecondCookIsIgnored():
    clock, spoon = newClock(True), Spoon()
    assert Pot.stirStroke(clock, spoon, "a", 0.0, 0.5, 0.0, True, 3, 3)
    assert clock.isStirred(0.0)
    assert not Pot.stirStroke(clock, spoon, "b", 0.1, -0.5, 0.0, True, 3, 3), "the spoon stays in the first cook's hand"
    assert Pot.stirStroke(clock, spoon, "b", 1.0, -0.5, 0.0, True, 3, 3), "left still, it is the second cook's"
    assert spoon.holder == "b"


def testAColdPotOrAnEmptyBatchEarnsNoStars():
    for heated, batch in ((False, 3), (True, 0)):
        clock = newClock(True)
        stirRounds(clock, Spoon(), "cook", 120, heated=heated, batch=batch)
        assert clock.skill.stars(6.0) == 0.0, (heated, batch)
        assert clock.isStirred(6.0 - 0.1), "搅了照样算被搅过，只是不攒星"


def testServeSettlesTheBatchAndResetsTheClock():
    clock = newClock(True)
    clock.attend(100.0)
    clock.batch = 6
    clock.cookTime = 10.0
    plan = clock.serve(100.0, 13, 1, 16, grade=3)
    assert (plan.cooked, plan.servings, plan.saved) == (3, 4, 1), plan
    assert clock.grade == 3 and clock.bonus == 1 and clock.setsSaved == 1
    assert abs(clock.bonusCarried - 0.5) < 1e-12
    assert clock.cookTime == 0.0 and clock.batch == 0
    assert clock.takeSaved(100.1) == 1, "还在工位的厨师拿到省下的料"
    assert clock.takeSaved(100.1) == 0, "只给一次"


def testSavedSetsAreNeverHandedToWhoOpensItLater():
    clock = newClock(True)
    clock.attend(100.0)
    clock.batch = 6
    clock.serve(100.0, 13, 1, 16, grade=3)
    assert clock.takeSaved(100.5) == 0, "结算后过了 HERE，不再发给事后来开锅的人"
    clock = newClock(True)
    clock.attend(50.0)
    clock.batch = 6
    plan = clock.serve(100.0, 13, 1, 16, grade=3)
    assert plan.saved == 0, "the cook left: the saved set stays in the pot"


def testDumpAndRestore():
    clock = newClock(True)
    clock.bonusCarried = 0.25
    other = Pot.PotClock()
    saved = clock.dump()
    other.restore(saved["byHand"], saved["bonus"])
    assert other.byHand and other.bonusCarried == 0.25
    other.restore(None, None)    # 老存档没有这两项：引擎取出来是 None，按默认值
    assert not other.byHand and other.bonusCarried == 0.0
    for broken in (float("nan"), float("inf"), -3.0, 7.0):
        other.restore(True, broken)
        assert 0.0 <= other.bonusCarried <= 0.999, broken


def testLeftoversAreKeptForTheCookWhileHeIsHereAndThrownOutWhenNobodyTookThem():
    clock = newClock(True)
    clock.attend(5.0)
    assert clock.keepLeftover("bucket", 5.0) and clock.keepLeftover("bottle", 5.05)
    assert not clock.keepLeftover("late", 5.2), "厨师不在场（过了 HERE）：不留，由锅掉在锅边"
    assert clock.takeLeftovers() == ["bucket", "bottle"] and clock.takeLeftovers() == [], "只给一次"
    clock.attend(10.0)
    clock.keepLeftover("bowl", 10.0)
    assert clock.forgotten(10.05) == [], "他还在：站点马上会来取"
    assert clock.forgotten(10.5) == ["bowl"] and clock.leftovers == [], "他正好那一刻走了：没人取的掉在锅边"
    assert clock.forgotten(11.0) == []


def testAPotThatCannotCookLosesItsProgressTwoSecondsPerSecond():
    clock = Pot.PotClock()
    clock.cookTime = 5.0
    clock.fall(0.2)
    assert abs(clock.cookTime - 4.6) < 1e-9, "FD 每刻 cookTime - 2"
    clock.fall(1.0)
    assert abs(clock.cookTime - 2.6) < 1e-9
    clock.fall(10.0)
    assert clock.cookTime == 0.0, "掉到 0 为止"


def testByHandSurvivesAReloadOnlyThroughTheSavedFlag():
    clock = newClock(True)
    saved = clock.dump()
    other = Pot.PotClock()
    other.restore(saved["byHand"], saved["bonus"])
    assert other.byHand, "手放的料存档后读回来还是手放的：厨师在场就等勺子"
    other.watchFood(10)
    assert other.byHand, "读回来的料早就在锅里：没有新料进来，不变"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
