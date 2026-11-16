# -*- coding: utf-8 -*-
# runner: both
"""刀切派、蛋糕、南瓜（Shared/Data/Slicing.py、Shared/Rules/Slicing.py）。

期望值抄自 JE：PieBlock（4 口，BITES 0 到 3）、CakeBlock（7 口，BITES 0 到 6）、PastrySlicingModifier（拆一个方块掉
"最大口数 - 已吃口数"片）、slicing_candle_cake.json（插蜡烛的蛋糕拆掉额外 7 片）、scavenging_pumpkin.json（南瓜换 4 片）。
"""
from __future__ import print_function

import fdtest

Data = fdtest.load("Shared.Data.Slicing")
Rules = fdtest.load("Shared.Rules.Slicing")
Food = fdtest.load("Shared.Data.Food")
Cutting = fdtest.load("Shared.Data.Cutting")


def testPieSlicesLeftIsFourMinusBitesEaten():
    assert [Rules.pieSlicesLeft(bites) for bites in (0, 1.0, 2.0, 3.0, 4.0)] == [4, 3, 2, 1, 0]
    assert Rules.pieSlicesLeft(None) == 4        # 方块没存过口数（/setblock 放的）按整个派算
    assert Rules.pieSlicesLeft(9) == 0


def testCakeSlicesLeftIsSevenMinusBitesEaten():
    assert [Rules.cakeSlicesLeft(bites) for bites in range(7)] == [7, 6, 5, 4, 3, 2, 1]
    assert Rules.cakeSlicesLeft(None) == 7


def testCakeLosesOneBiteUntilTheLastSliceIsCutAway():
    assert [Rules.cakeAfterCut(bites) for bites in range(7)] == [1, 2, 3, 4, 5, 6, None]


def testCandleCakeNamesAndTheirCandles():
    assert len(Data.CANDLE_CAKES) == 17 and len(set(Data.CANDLE_CAKES)) == 17
    assert Rules.candleOf("minecraft:candle_cake") == "minecraft:candle"
    assert Rules.candleOf("minecraft:red_candle_cake") == "minecraft:red_candle"
    assert Rules.candleOf("minecraft:light_blue_candle_cake") == "minecraft:light_blue_candle"
    assert Rules.candleOf("minecraft:cake") is None
    for name in Data.CANDLE_CAKES:
        assert Rules.candleOf(name).endswith("candle")


def testEveryPieHasASliceAndTheCutBoardGivesTheSame():
    assert sorted(Data.pieSliceItems) == sorted(Food.pieList)
    placedBy = dict((block, item) for item, block in Food.itemChangeBlockDict.items())
    for pie, sliceItem in Data.pieSliceItems.items():
        # 砧板上切 4 片整派用的就是同一种切片；整派的物品是放出这个方块的那件（多数叫 *_item，南瓜派是原版的 minecraft:pumpkin_pie）
        assert pie in placedBy, pie
        assert (sliceItem, 4) in [(d["itemName"], d["count"]) for d in Cutting.CuttingBoardDict[(placedBy[pie], 0)]["itemList"]]


def testSliceDrops():
    assert Rules.sliceDrops("arris:apple_pie", 3) == [("arris:apple_pie_slice", 3)]
    assert Rules.sliceDrops("minecraft:cake", 7) == [("arris:cake_slice", 7)]
    assert Rules.sliceDrops("minecraft:red_candle_cake", 7) == [("arris:cake_slice", 7)]
    assert Rules.sliceDrops("arris:apple_pie", 0) == []


def testTicketIsCashedOnceByTheSamePlayerInTime():
    tickets = Rules.SliceTickets()
    key = (0, 1, 64, 1)
    tickets.put(key, [("arris:cake_slice", 7)], "p1", 100.0)
    assert tickets.take(key, "p1", 101.0) == [("arris:cake_slice", 7)]
    assert tickets.take(key, "p1", 101.0) == [], "同一张单子只兑现一次"
    assert len(tickets) == 0


def testTicketIsRefusedForOtherPlayersAndAfterItExpires():
    tickets = Rules.SliceTickets()
    key = (0, 1, 64, 1)
    tickets.put(key, [("arris:cake_slice", 7)], "p1", 100.0)
    assert tickets.take(key, "p2", 100.5) == []
    tickets.put(key, [("arris:cake_slice", 7)], "p1", 100.0)
    assert tickets.take(key, "p1", 100.0 + Rules.TICKET_SECONDS + 1) == []


def testNewTicketReplacesTheOldOneAndStaleOnesAreSwept():
    tickets = Rules.SliceTickets()
    key = (0, 1, 64, 1)
    tickets.put(key, [("arris:cake_slice", 7)], "p1", 100.0)
    tickets.put(key, [("arris:cake_slice", 5)], "p1", 101.0)
    assert tickets.take(key, "p1", 102.0) == [("arris:cake_slice", 5)]
    for index in range(80):
        tickets.put((0, index, 64, 0), [("arris:cake_slice", 1)], "p1", 200.0)
    assert len(tickets) <= 80
    tickets.put((0, 999, 64, 0), [("arris:cake_slice", 1)], "p1", 300.0)   # 之前的都过期了，放新单子时清掉
    assert len(tickets) == 1


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
