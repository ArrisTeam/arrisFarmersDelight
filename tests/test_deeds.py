# -*- coding: utf-8 -*-
# runner: both
"""Server/Helpers/Deeds：玩家做成了某件事的登记点（玩法模块报、成就联动这类模块订阅）。

没有订阅者时什么都不做；同一个函数订阅两次只调一次；订阅者出错不连累报事的一方，也不挡后面的订阅者；退订以后不再调。
各处报事的地方在各自的测试里（test_classic_cutting_board、test_skillet_hand、test_item_to_block、test_farm_server_glue、test_board_chop_faults）。
"""
from __future__ import print_function

import fdtest

Deeds = fdtest.load("Server.Helpers.Deeds")


def testNobodyListeningMeansNothingHappens():
    Deeds._subscribers.clear()
    Deeds.done("p1", Deeds.CUT_ON_BOARD, "arris:cabbage")
    assert Deeds._subscribers == {}


def testSubscribersGetThePlayerAndTheDetailOnceEachEvenIfSubscribedTwice():
    Deeds._subscribers.clear()
    seen = []

    def first(playerId, detail):
        seen.append(("first", playerId, detail))

    def second(playerId, detail):
        seen.append(("second", playerId, detail))

    Deeds.subscribe(Deeds.PLACED_BLOCK, first)
    Deeds.subscribe(Deeds.PLACED_BLOCK, first)
    Deeds.subscribe(Deeds.PLACED_BLOCK, second)
    Deeds.done("p1", Deeds.PLACED_BLOCK, "arris:skillet")
    Deeds.done("p1", Deeds.HARVESTED, "arris:tomatoes_vine_stage3")
    assert seen == [("first", "p1", "arris:skillet"), ("second", "p1", "arris:skillet")]
    Deeds.unsubscribe(Deeds.PLACED_BLOCK, first)
    Deeds.unsubscribe(Deeds.HARVESTED, first)
    Deeds.done("p2", Deeds.PLACED_BLOCK)
    assert seen[-1] == ("second", "p2", None) and len(seen) == 3


def testAFailingSubscriberDoesNotStopTheOthersNorTheCaller():
    Deeds._subscribers.clear()
    seen = []

    def broken(playerId, detail):
        raise RuntimeError("injected")

    def fine(playerId, detail):
        seen.append(playerId)

    Deeds.subscribe(Deeds.SKILLET_COOKED, broken)
    Deeds.subscribe(Deeds.SKILLET_COOKED, fine)
    Deeds.done("p1", Deeds.SKILLET_COOKED, "minecraft:beef")
    assert seen == ["p1"]
    Deeds._subscribers.clear()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
