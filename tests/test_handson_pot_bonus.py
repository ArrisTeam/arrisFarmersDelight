# -*- coding: utf-8 -*-
# runner: both
"""PotBonus 星级奖励与出锅结算测试。

移植自 Hands-On Delight 的 PotTests：aBonusIsCarriedOn、theFirstTimeHasOneStar（开星数部分）、
aCookWhoKnowsTheDishGetsMore（奖励份数部分）、theSetsSavedGoBack、theSetsSavedStayWhenTheCookLeft。
"""
from __future__ import print_function


import fdtest

Bonus = fdtest.load("Shared.Rules.HandsOn.PotBonus")


def testABonusIsCarriedOn():
    assert Bonus.bonus(1, 3, 0.0) == 0, "one serving at three stars brings half of one"
    assert Bonus.bonus(1, 3, 0.5) == 1, "the next one makes it whole"
    assert Bonus.bonus(4, 2, 0.0) == 1 and Bonus.bonus(3, 2, 0.0) == 0, "two stars one for every four"
    assert Bonus.bonus(16, 3, 0.0) == 8, "a full pot at three stars half again"
    assert Bonus.bonus(16, 1, 0.9) == 0, "one star none"


def testBonusRounding():
    assert Bonus.bonusPercent(0) == 0 and Bonus.bonusPercent(1) == 0
    assert Bonus.bonusPercent(2) == 25 and Bonus.bonusPercent(3) == 50
    assert Bonus.bonusRate(3) == 0.5 and Bonus.bonusRate(2) == 0.25
    # 零头只差一丝没到整份时（1.5 + 0.4999999 = 1.9999999），BONUS_EPS 让它算整份，浮点误差吃不掉一整份
    assert Bonus.bonus(3, 3, 0.4999999) == 2
    assert Bonus.bonus(3, 3, 0.49) == 1, "差得多就不算"


def testOpenStarsFollowHowMuchOfTheDishWasMade():
    assert Bonus.openStars(0) == 1, "the first time has one star"
    assert Bonus.openStars(7) == 1 and Bonus.openStars(8) == 2
    assert Bonus.openStars(31) == 2 and Bonus.openStars(32) == 3
    assert Bonus.openStars(40) == 3 and Bonus.openStars(10000) == 3


def testNextStarIsHowFarTheNextOneIs():
    assert Bonus.nextStar(0) == 0.0 and Bonus.nextStar(4) == 0.5 and abs(Bonus.nextStar(7) - 0.875) < 1e-12
    assert Bonus.nextStar(8) == 0.0, "第二颗星刚开，离第三颗从零算起"
    assert Bonus.nextStar(20) == 0.5
    assert Bonus.nextStar(32) == 1.0 and Bonus.nextStar(99) == 1.0


def testACookWhoKnowsTheDishGetsMore():
    # 做过 40 份的菜 3 星：两份出三份；第一次做的 1 星：两份还是两份
    plan = Bonus.servePlan(batch=2, mealCount=1, resultCount=1, maxStack=16, grade=3, carried=0.0)
    assert (plan.cooked, plan.servings, plan.bonus, plan.saved) == (2, 3, 1, 0), plan
    assert plan.carried == 0.0, "两套料正好换来一份奖励，没有零头"
    plan = Bonus.servePlan(batch=2, mealCount=1, resultCount=1, maxStack=16, grade=1, carried=0.0)
    assert (plan.cooked, plan.servings, plan.bonus) == (2, 2, 0), plan


def testTheSetsSavedGoBack():
    # 锅里已有 12 份加刚出的第一份 = 13；成品最大 16，只容得下 (16-13)/1+1 = 4 份；6 套料，3 星
    plan = Bonus.servePlan(batch=6, mealCount=13, resultCount=1, maxStack=16, grade=3, carried=0.0, here=True)
    assert plan.cooked == 3 and plan.servings == 4 and plan.bonus == 1, plan
    assert plan.saved == 1, "four fit, three sets make four: the fourth set is saved for the cook"
    assert abs(plan.carried - 0.5) < 1e-12, "3 * 0.5 - 1 = 0.5 的零头带到下一批"


def testTheSetsSavedStayWhenTheCookLeft():
    plan = Bonus.servePlan(batch=6, mealCount=13, resultCount=1, maxStack=16, grade=3, carried=0.0, here=False)
    assert plan.cooked == 3 and plan.servings == 4, plan
    assert plan.saved == 0, "厨师走了：省下的料留在锅里接着煮，不会发给事后来开锅的人"


def testAMealPastItsStackIsOnlyTheFirstServing():
    # 锅允许成品涨过堆叠上限：那一份之后就只剩它自己
    plan = Bonus.servePlan(batch=5, mealCount=17, resultCount=1, maxStack=16, grade=3, carried=0.0)
    assert (plan.cooked, plan.servings, plan.bonus) == (1, 1, 0), plan
    plan = Bonus.servePlan(batch=5, mealCount=17, resultCount=2, maxStack=16, grade=3, carried=0.0)
    assert (plan.cooked, plan.servings) == (1, 1), "整数除法向零取整：(16-17)/2 = 0，再加 1"


def testNoSizeOfBatchEarnsMoreThanAnother():
    # 十套一批，和十批一套，三星拿到的奖励一样多（零头带到下一批）
    big = Bonus.servePlan(batch=10, mealCount=1, resultCount=1, maxStack=64, grade=3, carried=0.0)
    assert big.bonus == 5, big
    carried, total = 0.0, 0
    for _ in range(10):
        plan = Bonus.servePlan(batch=1, mealCount=1, resultCount=1, maxStack=64, grade=3, carried=carried)
        carried = plan.carried
        total += plan.bonus
    assert total == 5, "ten single servings, five bonus"


def testTheCarriedPartStaysUnderOne():
    # 成品堆叠满了、奖励发不出去：0.9 + 0.5 = 1.4 的零头只带 0.999 到下一批，不会攒出两份
    plan = Bonus.servePlan(batch=5, mealCount=17, resultCount=1, maxStack=16, grade=3, carried=0.9)
    assert (plan.cooked, plan.servings, plan.bonus) == (1, 1, 0) and plan.carried == Bonus.CARRY_CAP == 0.999, plan
    plan = Bonus.servePlan(batch=1, mealCount=1, resultCount=1, maxStack=64, grade=0, carried=0.0)
    assert plan.carried == 0.0 and plan.bonus == 0


def testExtraItemsFollowTheResultCount():
    # 一套料出两件（蜂蜜瓶）：多送的每一份是两件
    plan = Bonus.servePlan(batch=4, mealCount=2, resultCount=2, maxStack=16, grade=3, carried=0.0)
    assert plan.bonus >= 1 and plan.extraItems == plan.bonus * 2, plan


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
