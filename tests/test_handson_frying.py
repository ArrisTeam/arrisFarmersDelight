# -*- coding: utf-8 -*-
# runner: both
"""Frying 煎锅两面状态机测试。

移植自 Hands-On Delight 的 SkilletTests：aBatchFriesInHalvesAndWaitsToBeTurned、anEggFriesWithoutATurn、
theFryingTimeFollowsTheConfig、moreFoodTakesLongerButKeepsWhatWasDone，以及 farmersDelightsRightClickCooksItsWay、
theFoodComesBackAndOnlyFoodGoesIn（数量部分）。
时间以秒计；FD 的煎锅煎牛肉要 120 刻（6 秒）：一块牛肉一面 40 刻，两块 57 刻。
"""
from __future__ import print_function


import fdtest

Fry = fdtest.load("Shared.Rules.HandsOn.Frying")
_Mth = fdtest.load("Shared.Rules.HandsOn.Mth")
TICK = _Mth.TICK


BEEF = 6.0                                   # 原 120 刻
TWO_BEEF_SIDE = Fry.sideSeconds(BEEF, 2, 1.0)   # 原 57 刻


def advance(pan, seconds, side, oneSided=False):
    """每步一刻往前煎 seconds 秒。"""
    done = False
    for _ in range(int(round(seconds / TICK))):
        done = pan.step(TICK, side, oneSided)
    return done


def testSideTimes():
    assert abs(TWO_BEEF_SIDE - 57 / 20.0) < 1e-12, "two beef fry a side in 57 ticks"
    assert abs(Fry.sideSeconds(BEEF, 1, 1.0) - 40 / 20.0) < 1e-12, "one beef a side in 40 ticks"
    assert abs(Fry.sideSeconds(BEEF, 4, 1.0) - 80 / 20.0) < 1e-12, "four: twice as long as one"
    assert abs(Fry.sideSeconds(BEEF, 16, 1.0) - 160 / 20.0) < 1e-12
    assert abs(Fry.sideSeconds(BEEF, 1, 2.0) - 80 / 20.0) < 1e-12, "the config doubles it"
    assert abs(Fry.sideSeconds(BEEF, 0, 1.0) - Fry.sideSeconds(BEEF, 1, 1.0)) < 1e-12, "批量至少算 1"
    assert abs(Fry.sideSeconds(BEEF, 2, 1.0, quantize=False) - 6.0 * 2 ** 0.5 / 3.0) < 1e-12, "连续值：不取整到刻"
    assert Fry.sideSeconds(0.001, 1, 1.0) == TICK, "never less than a tick"


def testABatchFriesInHalvesAndWaitsToBeTurned():
    pan = Fry.Frying()
    pan.layByHand()
    pan.resize(2)
    advance(pan, TWO_BEEF_SIDE + 0.5, TWO_BEEF_SIDE)
    assert pan.down >= 1.0 and pan.up == 0.0, "the side on the pan is done, the top raw"
    assert pan.waits(), "it waits to be turned"
    advance(pan, TWO_BEEF_SIDE + 0.5, TWO_BEEF_SIDE)
    assert pan.down >= 1.0 and pan.up == 0.0 and not pan.isDone(), "untouched, nothing more happens: it is not done"
    assert pan.toss(100.0), "颠锅被接受"
    assert pan.up >= 1.0 and pan.down == 0.0, "a toss turns it over"
    assert not pan.waits() and pan.waits() is False
    done = advance(pan, TWO_BEEF_SIDE + 0.5, TWO_BEEF_SIDE)
    assert done and pan.isDone(), "both sides done: the batch is cooked"


def testFrySideTimesAreExactlyOneSidesWorth():
    pan = Fry.Frying()
    pan.layByHand()
    pan.resize(2)
    assert not advance(pan, TWO_BEEF_SIDE - 0.1, TWO_BEEF_SIDE) and pan.down < 1.0
    advance(pan, 0.1, TWO_BEEF_SIDE)
    assert pan.down >= 1.0, "整 57 刻后贴锅面熟"


def testAnEggFriesWithoutATurn():
    pan = Fry.Frying()
    pan.layByHand()
    pan.resize(2)
    advance(pan, TWO_BEEF_SIDE + 0.25, TWO_BEEF_SIDE, oneSided=True)
    assert not pan.waits(), "and does not wait to be turned"
    assert pan.up == pan.down and pan.down > 0.4, "it cooks through from below"
    assert not pan.isDone()
    advance(pan, TWO_BEEF_SIDE + 0.25, TWO_BEEF_SIDE, oneSided=True)
    assert pan.isDone(), "done in the time of both sides, never tossed"


def testTheFryingTimeFollowsTheConfig():
    steps = []
    for times in (1.0, 2.0):
        pan = Fry.Frying()
        pan.layByHand()
        pan.resize(1)
        pan.step(TICK, Fry.sideSeconds(BEEF, 1, times))
        steps.append(pan.down)
    assert abs(steps[0] - 1.0 / 40) < 1e-12, "1.0: a side in today's 40 ticks, got %r" % steps[0]
    assert abs(steps[0] - 2.0 * steps[1]) < 1e-12, "2.0: half as far a tick, %r" % steps[1]


def testMoreFoodTakesLongerButKeepsWhatWasDone():
    pan = Fry.Frying()
    pan.layByHand()
    pan.resize(1)
    advance(pan, 1.0, Fry.sideSeconds(BEEF, 1, 1.0))
    one = pan.down
    assert one > 0.3, "one beef is well on its way"
    pan.resize(4)
    assert abs(pan.down - one * 0.5) < 1e-12, "四块的一面是一块的两倍时间：已煎的进度折半，没丢"
    pan.step(TICK, Fry.sideSeconds(BEEF, 4, 1.0))
    assert 0.15 < pan.down < 0.3, "four fry slower: how far it got is shared out, not lost: %r" % pan.down


def testTakingFoodOutSpeedsTheRestUp():
    pan = Fry.Frying()
    pan.resize(4)
    pan.down, pan.up = 0.3, 0.6
    pan.resize(1)
    assert abs(pan.down - 0.6) < 1e-12 and pan.up == 1.0, "拿走三块：剩下那块该有的进度翻倍，夹到 1"
    pan.resize(1)
    assert pan.batch == 1
    pan.resize(0)
    assert pan.batch == 0 and abs(pan.down - 0.6) < 1e-12 and pan.up == 1.0, "批量为 0（锅空了）不折算"


def testTossIsAllowedAnytimeButNotTooOften():
    pan = Fry.Frying()
    pan.layByHand()
    pan.resize(1)
    pan.down = 0.3
    assert pan.toss(10.0), "it does NOT need the lower side to be done: a turn is a swap at any time"
    assert pan.down == 0.0 and pan.up == 0.3
    assert not pan.toss(10.2), "the last toss is still in the air"
    assert not pan.canTurn(10.39)
    assert pan.toss(10.4), "8 刻之后可以再颠"
    assert pan.down == 0.3 and pan.up == 0.0


def testNothingToTossNothingHappens():
    pan = Fry.Frying()
    assert not pan.toss(10.0, hasFood=False)
    assert not pan.byHand and pan.turnedAt < 0


def testTossingFarmersDelightsPanTakesItOverFromRaw():
    pan = Fry.Frying()
    pan.down, pan.up, pan.batch = 0.7, 0.2, 2
    assert not pan.byHand
    assert pan.toss(10.0)
    assert pan.byHand and pan.down == 0.0 and pan.up == 0.0, "FD 煎着的锅被颠一下就归厨师，从生开始（先清零再翻）"
    assert pan.batch == 0, "reset 也清批量，下一步按 resize 重新数"


def testWaitsOnlyForFoodFriedByHand():
    pan = Fry.Frying()
    pan.down = 1.0
    assert not pan.waits(), "FD 自己煎的不等翻"
    pan.layByHand()
    assert pan.waits()
    pan.up = 1.0
    assert not pan.waits() and pan.isDone()


def testAnEmptiedPanStartsOver():
    pan = Fry.Frying()
    pan.layByHand()
    pan.resize(3)
    pan.step(TICK, 2.0)
    pan.farmersDelightsWay()
    assert not pan.byHand and (pan.down, pan.up, pan.batch) == (0.0, 0.0, 0)


def testSkilletSecondsAreAFifthOfTheCampfireTimeToWholeSeconds():
    assert Fry.skilletSeconds(30.0) == 6.0, "营火 600 刻 -> 120 刻"
    assert Fry.skilletSeconds(30.0, 1) == 4.0, "火焰附加 1：15%% -> 4.5 取整 4 秒"
    assert Fry.skilletSeconds(30.0, 2) == 3.0
    assert Fry.skilletSeconds(30.0, 3) == 3.0, "不低于 3 秒（60 刻）"
    assert Fry.skilletSeconds(10.0) == 3.0, "10 * 0.2 = 2 秒，抬到下限"
    assert Fry.skilletSeconds(0.0) == 6.0 and Fry.skilletSeconds(-5.0) == 6.0, "没写时间按 600 刻算"
    assert Fry.skilletSeconds(45.5) == 9.0, "秒数先取整：45 * 0.2 = 9"


def testHowManyGoIntoThePan():
    assert Fry.placeCount(20, 0, 64) == Fry.BATCH == 16, "a batch at most goes in"
    assert Fry.placeCount(3, 0, 64) == 3
    assert Fry.placeCount(3, 14, 64) == 2 and Fry.placeCount(3, 16, 64) == 0
    assert Fry.placeCount(20, 0, 64, one=True) == 1
    assert Fry.placeCount(20, 0, 8) == 8, "堆叠上限比 16 小的取小的"
    assert Fry.placeCount(5, 20, 64) == 0, "不会出负数"


def testSyncStepsForTheClients():
    assert Fry.syncStep(0.0) == 0.0 and Fry.syncStep(1.0) == 1.0 and Fry.syncStep(1.5) == 1.0
    assert Fry.syncStep(0.5) == 0.5 and Fry.syncStep(0.51) == 0.5
    assert abs(Fry.syncStep(0.9) - 28 / 32.0) < 1e-12 and abs(Fry.syncStep(0.999) - 31 / 32.0) < 1e-12


def testTheClientsHearOfEveryStepNotEveryTick():
    pan = Fry.Frying()
    assert pan.dueToSend(), "第一次总要发"
    assert not pan.dueToSend()
    pan.fry(0.01)
    assert not pan.dueToSend(), "没走满 1/16"
    pan.fry(0.06)
    assert pan.dueToSend(), "0.07 过了 1/16"
    pan.layByHand()
    assert pan.dueToSend(), "手放标记变了"
    pan.resize(3)
    assert pan.dueToSend(), "批量变了"


def testTheStateSurvivesARestart():
    """HoD 的 Frying.save / load：锅里的食物接着煎，站点关了、玩家走了、服务器重启都不丢。"""
    pan = Fry.Frying()
    assert pan.save() is None, "什么都没发生过：没东西可存"
    pan.layByHand()
    pan.resize(3)
    pan.down, pan.up = 0.75, 0.125
    saved = pan.save()
    assert saved == {"byHand": True, "down": 0.75, "up": 0.125, "batch": 3}
    again = Fry.Frying().load(saved)
    assert again.byHand and again.down == 0.75 and again.up == 0.125 and again.batch == 3
    fresh = Fry.Frying().load(None)
    assert not fresh.byHand and (fresh.down, fresh.up, fresh.batch) == (0.0, 0.0, 0)
    junk = Fry.Frying().load({"byHand": "yes", "down": "x", "up": 7, "batch": 10 ** 6})
    assert not junk.byHand and junk.down == 0.0 and junk.up == 1.0 and junk.batch == 0, "不对的类型当没有，进度夹进 0..1"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
