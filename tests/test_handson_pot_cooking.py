# -*- coding: utf-8 -*-
# runner: both
"""PotCooking 厨锅批量烹饪的速度与时长测试（谁在搅、料是谁放的见 test_pot_clock.py）。

移植自 Hands-On Delight 的 PotTests：theWholeBatchCooksAtOnce、aModdedRecipeCooksAsABatch、
moreRiceThanAStackStillCooks、riceAddedWhileCookingKeepsTheProgress、theCookingTimeFollowsTheConfig、
theSmallestStackSetsTheBatch（批量部分）。时间以秒计；原测试的刻数 / 20。每步 0.05 秒（一刻）。
"""
from __future__ import print_function


import fdtest
from optkit import Config

Pot = fdtest.load("Shared.Rules.HandsOn.PotCooking")
_Mth = fdtest.load("Shared.Rules.HandsOn.Mth")
TICK = _Mth.TICK


def newClock():
    """一口厨师手放了料的锅，厨师一直在工位。"""
    clock = Pot.PotClock()
    clock.watchFood(0)
    clock.feedByHand()
    clock.watchFood(6)
    assert clock.byHand
    return clock


def run(clock, start, until, total, batch, probes=()):
    """从 start 到 until 逐步推进，每秒搅一下。返回 (出第一份的时刻, {探测时刻: 进度})。"""
    finishedAt, seen = None, {}
    for index in range(int(round((until - start) / TICK))):
        now = start + index * TICK
        if abs(now - round(now)) < 1.0e-9:
            clock.stir(now)
        clock.attend(now)
        clock.advance(now, TICK, total, batch)
        if finishedAt is None and clock.finished(total):
            finishedAt = now + TICK
        for probe in probes:
            if abs(now + TICK - probe) < 1.0e-9:
                seen[probe] = clock.progress(total, batch)
    return finishedAt, seen


def testBatchSpeedIsTheSquareRootOfTheBatch():
    assert Pot.batchSpeed(1) == 1.5
    assert Pot.batchSpeed(4) == 0.75, "four servings take twice the time of one"
    assert abs(Pot.batchSpeed(16) - 0.375) < 1e-12, "sixteen take four times"
    assert Pot.batchSpeed(64) == Pot.batchSpeed(16), "a whole stack no longer"
    assert Pot.batchSpeed(0) == 1.5, "夹进 1..16"


def testTheWholeBatchCooksAtOnce():
    # 四份、10 秒的配方，一直在搅：10 * 2 / 1.5 = 13.3 秒；10 秒时过半但还没出
    finishedAt, seen = run(newClock(), 0.0, 15.0, 10.0, 4, probes=(10.0,))
    assert seen[10.0] > 0.5, "the batch is more than half done: %r" % seen[10.0]
    assert abs(seen[10.0] - 0.75) < 1e-9
    assert finishedAt is not None and 13.2 < finishedAt < 13.5, "all four come out together, in about thirteen seconds: %r" % finishedAt


def testAModdedRecipeCooksAsABatch():
    # 五份、2 秒的配方：2 s * sqrt(5) / 1.5 = 2.98 秒
    finishedAt, _ = run(newClock(), 0.0, 7.0, Pot.timeFor(2.0), 5)
    assert finishedAt is not None and abs(finishedAt - 2.0 * 5 ** 0.5 / 1.5) < 0.1, finishedAt


def testMoreRiceThanAStackStillCooks():
    # 十六份、5 秒的配方：5 s * 4 / 1.5 = 13.3 秒
    finishedAt, _ = run(newClock(), 0.0, 15.0, Pot.timeFor(5.0), 16)
    assert finishedAt is not None and abs(finishedAt - 5.0 * 4 / 1.5) < 0.1, finishedAt


def testRiceAddedWhileCookingKeepsTheProgress():
    # 60 个米，批量按成品堆叠 16；搅到 5 秒时再放一堆米，批量不变，进度接着走
    clock = newClock()
    _, seen = run(clock, 0.0, 5.0, 5.0, 16, probes=(5.0,))
    before = seen[5.0]
    assert before > 0.2 and abs(before - 5.0 * 0.375 / 5.0) < 1e-9, "十六份的速度是 0.375，总时长 5 秒：%r" % before
    _, seen = run(clock, 5.0, 5.5, 5.0, 16, probes=(5.5,))
    assert seen[5.5] > before, "the progress goes on, %r -> %r" % (before, seen[5.5])


def testAddingFoodMidwayRescalesTheProgress():
    # 四份煮到 6 秒（进度 4.5/10），又放进料变成十六份：已搅的真实时间不变，按新速度折算
    clock = newClock()
    _, seen = run(clock, 0.0, 6.0, 10.0, 4, probes=(6.0,))
    assert abs(seen[6.0] - 0.45) < 1e-9
    clock.advance(6.0, TICK, 10.0, 16)
    assert abs(clock.cookTime - (4.5 * 0.375 / 0.75 + TICK * 0.375)) < 1e-9


def testKeepTimeAtKeepsTheRealTimeAlreadyCooked():
    clock = Pot.PotClock()
    clock.pace = 0.75
    clock.cookTime = 6.0
    clock.keepTimeAt(0.375, 10.0)
    assert abs(clock.cookTime - 3.0) < 1e-12, "料加多了变慢：折算后的进度对应同样的真实搅拌时间"
    clock.keepTimeAt(0.75, 10.0)
    assert abs(clock.cookTime - 6.0) < 1e-12 and clock.pace == 0.75
    clock.keepTimeAt(1.0, 10.0)
    assert abs(clock.cookTime - 8.0) < 1e-12, "从批量速度切回 FD 原样"
    clock.cookTime = 9.9
    clock.pace = 0.375
    clock.keepTimeAt(0.75, 10.0)
    assert abs(clock.cookTime - (10.0 - TICK)) < 1e-12, "折算后至少还差一刻，不会凭空出锅"


def testKeepTimeAtDoesNothingTheFirstTime():
    clock = Pot.PotClock()
    clock.cookTime = 4.0
    clock.keepTimeAt(0.75, 10.0)
    assert clock.cookTime == 4.0 and clock.pace == 0.75, "pace 为 0（还不知道）时只记下速度"
    clock.keepTimeAt(0.75, 0.0)
    assert clock.cookTime == 4.0


def testTheCookingTimeFollowsTheConfig():
    assert Pot.timeFor(5.0, 1.0) == 5.0, "1.0: the recipe's own time"
    assert Pot.timeFor(5.0, 2.0) == 10.0, "2.0: twice the recipe's time"
    assert Pot.timeFor(0.001, 1.0) == TICK, "never less than a tick"
    assert abs(Pot.timeFor(0.33, 1.0) - 0.35) < 1e-12, "取整到整刻"


def testTheSmallestStackSetsTheBatch():
    assert Pot.batchOf(1, 0, 1, 16) == 1, "one potato makes one stew"
    assert Pot.batchOf(60, 0, 1, 16) == 16, "米：料有 60 份，但成品一堆只放 16"
    assert Pot.batchOf(16, 0, 1, 64) == 16, "sixteen loaves, as many as there are feathers"
    assert Pot.batchOf(5, 0, 2, 16) == 5 and Pot.batchOf(10, 0, 2, 16) == 8, "一套出两件：(16-0)/2 = 8"
    assert Pot.batchOf(5, 15, 1, 16) == 1, "成品快满了只容得下 1 份"
    assert Pot.batchOf(5, 20, 1, 16) == 0, "成品已经超过上限：不出负数"
    assert Pot.batchOf(5, 0, 1, 16, sameMeal=False) == 0, "锅里是别的菜"


def testCookSecondsLeftIsWholeSecondsRoundedUp():
    assert Pot.cookSecondsLeft(10.0, 0.0, 1.0) == 10
    assert Pot.cookSecondsLeft(10.0, 0.5, 0.75) == 7, "5 / 0.75 = 6.67 -> 7"
    assert Pot.cookSecondsLeft(10.0, 1.0, 0.75) == 0


def testProgressIsZeroWithoutABatch():
    clock = Pot.PotClock()
    clock.cookTime = 4.0
    assert clock.progress(10.0, 3) == 0.4
    assert clock.progress(10.0, 0) == 0.0 and clock.progress(0.0, 3) == 0.0
    clock.cookTime = 40.0
    assert clock.progress(10.0, 3) == 1.0


def testTheCookingTimeConfigIsClampedAndFollowedByTheTimesAndTheBook():
    assert Pot.potTime() == 1.0, "HandsOnConfig 的缺省"
    assert abs(Pot.bookSeconds(10.0) - 10.0 / 1.5) < 1e-9, "一份在站点里 10 / 1.5 = 6.7 秒"
    with Config(cooking_pot_time=2.0):
        assert Pot.timeFor(5.0) == 10.0 and abs(Pot.bookSeconds(10.0) - 20.0 / 1.5) < 1e-9
    with Config(cooking_pot_time=100.0):
        assert Pot.potTime() == 10.0, "上限 10"
    with Config(cooking_pot_time=0.0):
        assert Pot.potTime() == 0.1 and Pot.timeFor(5.0) == 0.5, "下限 0.1"
    with Config(cooking_pot_time=2.0, cooking_pot=False):
        assert Pot.potTime() == 1.0 and Pot.timeFor(5.0) == 5.0, "厨锅站点关了：这口锅是 FD 自己的，倍率算 1"
    with Config(cooking_pot_time=2.0, skillet=False, stove=False, cutting_board=False):
        assert Pot.timeFor(5.0) == 10.0, "别的站点关了不相干"
    assert Pot.timeFor(5.0) == 5.0, "with 块出来放回原样"


def _waitingOrCooking(*args, **kwargs):
    """厨师在场、料是他手放的、锅没被搅：这一步锅怎么煮（WAITING 等勺子 / FD_WAY 自己煮）。"""
    clock = newClock()
    clock.attend(0.0)
    return clock.advance(0.0, TICK, 10.0, 3, *args, **kwargs)


def testTheStirringGateFollowsTheConfig():
    # PotCooking.beforeCooking 的 farmersDelightsWay：不在被搅 && (料不是手放的 || 厨师走开了 || 不要求搅 || 在锅自己的菜单里)
    assert _waitingOrCooking() == Pot.WAITING, "缺省（stirring_required 真）：厨师在场、手放的料、不搅，等勺子"
    with Config(stirring_required=False):
        assert _waitingOrCooking() == Pot.FD_WAY, "stirring_required 关了：不搅也照 FD 原样自己煮"
        assert _waitingOrCooking(stirringRequired=True) == Pot.WAITING, "调用方明说的比配置大"
    with Config(cooking_pot=False):
        assert _waitingOrCooking() == Pot.FD_WAY, "没有厨锅站点就没有勺子：HandsOnConfig.stirringRequired() 是 stirringRequired && cookingPot"
    with Config(cooking_pot=False, stirring_required=False):
        assert _waitingOrCooking() == Pot.FD_WAY
    with Config(skillet=False, stove=False, cutting_board=False, cooking_pot_time=3.0):
        assert _waitingOrCooking() == Pot.WAITING, "别的站点和别的倍率不相干"
    assert _waitingOrCooking() == Pot.WAITING, "with 块出来放回原样"


def testStirringStillCooksTheWholeBatchAtOnceWhenItIsNotRequired():
    # HoD 配置的说明文字：关了不搅也煮（FD 的煮法），"stirring still cooks the whole pot at once and earns stars"
    with Config(stirring_required=False):
        clock = newClock()
        mode = None
        for index in range(int(round(2.0 / TICK))):
            now = index * TICK
            clock.attend(now)
            clock.stir(now)
            mode = clock.advance(now, TICK, 10.0, 4)
        assert mode == Pot.STIRRED and clock.pace == Pot.batchSpeed(4), "搅着的照样按批量速度整批煮"
        unstirred = newClock()
        unstirred.attend(0.0)
        assert unstirred.advance(0.0, TICK, 10.0, 4) == Pot.FD_WAY and unstirred.batch == 0, "没人搅：一份一份煮，不按批量"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
