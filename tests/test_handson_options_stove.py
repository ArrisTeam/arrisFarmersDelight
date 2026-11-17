# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里炉灶的烤制时间倍率 stove_time 和炉灶站点的开关（Shared/Rules/GrillStation + Server/HandGrill + Server/Stove + StationBooks）：
站点里手放的件一面烤多久按倍率走，农夫乐事自己的右键放上去的照旧 30 秒；站点关了（存档里留下的手放的件）交给 FD 原样烤、烤好的马上弹出来；书上写的是同一个时间。
JE 的对照：StoveTests.theGrillingTimeFollowsTheConfig / piecesLaidByHandGoFarmersDelightsWay，StoveCooking.sideTicks / tick / handOver。引擎是 potfake 里的假的。"""
from __future__ import print_function

import math

import fdtest
import stovekit as K
from optkit import Config
from stovekit import BEEF, EGG, fake

Rules = K.Rules
Books = fdtest.load("Shared.Rules.StationBooks")
COOKED = "minecraft:cooked_beef"
BEEF_TICKS = 600                         # 营火配方 600 刻（JE：FD 的炉灶按它烤）


def javaRound(value):
    return int(math.floor(value + 0.5))


def jeSideTicks(ticks, times):
    """StoveCooking.sideTicks（55-58 行）：Math.max(1, Math.round(ticks * times / PACE / 2.0F))，PACE 是 1.5。"""
    return max(1, javaRound(ticks * times / 1.5 / 2.0))


def beef(count=1):
    return {"newItemName": BEEF, "newAuxValue": 0, "count": count}


def _thrown():
    """炉灶往世界里弹出来的东西的名字（弹出熟的用 itemName，原样退回的用 newItemName）。"""
    return sorted(item.get("newItemName") or item.get("itemName") for item, dim, pos in fake.spawned)


def _placeByHand(manager, count=1):
    fake.give("a", 3, BEEF, count)
    K.opened(manager)
    K.do(manager, "a", K.click(K.inv(3), kind="QUICK_MOVE"))


def testASideTakesTheRecipeTimeTimesTheConfigLikeJEsSideTicks():
    assert abs(Rules.sideSeconds() - 10.0) < 1e-9, "缺省：600 刻一面 200 刻"
    for times in (1.0, 2.0, 0.5, 0.1, 10.0, 3.3, 7.77):
        with Config(stove_time=times):
            assert round(Rules.sideSeconds() * 20) == jeSideTicks(BEEF_TICKS, times), times
    with Config(stove_time=2.0, stove=False):
        assert abs(Rules.sideSeconds() - 10.0) < 1e-9, "站点关了倍率算 1.0"
    with Config(stove_time=2.0, skillet=False, cooking_pot=False, cutting_board=False):
        assert abs(Rules.sideSeconds() - 20.0) < 1e-9, "别的站点关了不相干"
    with Config(stove_time=0.0):
        assert round(Rules.sideSeconds() * 20) == jeSideTicks(BEEF_TICKS, 0.1) == 20, "夹进 0.1"


def testTheGrillingTimeFollowsTheConfig():
    # StoveTests.theGrillingTimeFollowsTheConfig：1.0 一面是平常的 200 刻，2.0 同一步只走一半
    steps = []
    for times in (1.0, 2.0):
        manager, data = K.setup()
        with Config(stove_time=times):
            _placeByHand(manager, 1)
            K.step(2.0, manager=manager)
            steps.append(K.hand_of().grill.down(0))
    assert 0.15 < steps[0] <= 0.2 and abs(steps[0] - 2.0 * steps[1]) < 1e-9, steps         # 2 秒是 7 或 8 步，每步 0.25 秒 / 10 秒一面


def testAPieceLaidByHandIsDoneAfterBothSidesAtTheConfiguredPace():
    manager, data = K.setup()
    with Config(stove_time=2.0):
        _placeByHand(manager, 1)
        K.step(19.0, manager=manager)                  # 一面 20 秒
        assert K.hand_of().grill.down(0) < 1.0 and K.names(data)[0] == BEEF
        K.step(2.0, manager=manager)
        assert K.hand_of().grill.waits(0), "一面熟了等翻"
        assert K.do(manager, "a", K.custom("turn", place=0))
        K.step(21.0, manager=manager)
        assert K.names(data)[0] == COOKED


def testFarmersDelightsOwnRightClickKeepsItsThirtySecondsWhateverTheConfigSays():
    for times in (3.0, 0.5):
        manager, data = K.setup()
        data["1"] = {"itemDict": beef(), "cookTimer": 30}
        with Config(stove_time=times):
            K.step(29.0)
            assert K.names(data)[1] == BEEF and fake.spawned == [], times
            K.step(2.0)
            assert K.names(data)[1] is None and _thrown() == [COOKED], times


def testAStationTurnedOffHandsWhatWasGrilledByHandToFarmersDelight():
    # StoveCooking.tick：!HandsOnConfig.stove() -> handOver：不再等人翻，按 FD 的时间烤，烤好的 1 刻就弹出来
    manager, data = K.setup()
    _placeByHand(manager, 2)
    K.step(Rules.sideSeconds() + 0.5, manager=manager)
    assert K.hand_of().grill.waits(0) and K.hand_of().grill.byHand(1), "站点还开着：一面熟了等翻"
    done = {"newItemName": COOKED, "newAuxValue": 0, "count": 1}
    data["2"] = {"itemDict": done, "cookTimer": 30}         # 两面都烤好了、留在烤架上等人取的一件
    K.hand_of().grill.layByHand(2)
    manager.close("a")
    with Config(stove=False, stove_time=5.0):
        K.step(0.3)
        grill = K.hand_of().grill
        assert not any(grill.byHand(place) for place in range(6)), "手放的记号都清了"
        assert K.names(data)[2] is None and _thrown() == [COOKED], "烤好的马上弹出来"
        assert 29.0 < data["0"]["cookTimer"] <= 30 and 29.0 < data["1"]["cookTimer"] <= 30, "生的、半熟的重新按 FD 的 30 秒算（站点关了倍率是 1）"
        K.step(29.0)
        assert K.names(data)[:2] == [BEEF, BEEF]
        K.step(2.0)
        assert K.names(data)[:2] == [None, None] and _thrown() == [COOKED] * 3
    assert data["handGrill"] is None or data["handGrill"]["byHand"] == [0] * 6, "存档里也不是手放的了"


def testWithTheStationOnTheSameStateIsNotHandedOver():
    manager, data = K.setup()
    _placeByHand(manager, 1)
    K.step(Rules.sideSeconds() + 0.5, manager=manager)
    manager.close("a")
    K.step(60.0)
    assert K.hand_of().grill.byHand(0) and K.names(data)[0] == BEEF and fake.spawned == [], "等翻的就一直等翻"


def testTheBookWritesTheScaledTimeOfBothSides():
    # StoveBook：2 * sideTicks(配方时间, CookingTimes.stove())，Math.round(刻数 / 20)
    def note(name=BEEF):
        return next(page for page in Books.grillPages() if page["key"] == name)["note"]
    assert note() == "20 秒"
    for times, literal in ((2.0, "40 秒"), (0.5, "10 秒"), (0.1, "2 秒"), (10.0, "200 秒")):
        with Config(stove_time=times):
            assert note() == literal, times
    for times in (1.3, 3.3, 0.35, 7.77):
        with Config(stove_time=times):
            assert note() == "%d 秒" % javaRound(2 * jeSideTicks(BEEF_TICKS, times) / 20.0), times
    with Config(stove_time=3.0, stove=False):
        assert note() == "20 秒", "站点关了书也不乘"
    assert all(page["key"] != EGG for page in Books.grillPages()), "炉灶的书还是不列蛋"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
