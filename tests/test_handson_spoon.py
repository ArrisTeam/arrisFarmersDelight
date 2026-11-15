# -*- coding: utf-8 -*-
# runner: both
"""Spoon 一把勺子一只手的测试。移植自 Hands-On Delight 的 PotTests.oneSpoonOneHand。时间以秒计。"""
from __future__ import print_function


import fdtest

_Spoon = fdtest.load("Shared.Rules.HandsOn.Spoon")
SPOON_FREE = _Spoon.SPOON_FREE
Spoon = _Spoon.Spoon


def testOneSpoonOneHand():
    spoon = Spoon()
    assert spoon.take("first", 0.0)
    assert not spoon.take("second", 0.0), "the spoon stays in the first cook's hand"
    assert spoon.take("first", 0.2), "第一个人可以接着搅"
    assert not spoon.take("second", 0.6), "最近一次是 0.2 秒，0.6 秒时才过去 0.4 秒"
    assert spoon.take("second", 1.0), "left still, it is the second cook's"
    assert not spoon.take("first", 1.2)


def testOneSecondStillIsLongEnough():
    # 原测试：第一个人搅了一下，20 刻（1 秒）之后第二个人搅，勺子归他
    spoon = Spoon()
    assert spoon.take("first", 0.0) and not spoon.take("second", 0.0)
    assert spoon.take("second", 1.0) and spoon.holder == "second"


def testSpoonFreesAfterHalfASecond():
    assert SPOON_FREE == 0.5
    spoon = Spoon()
    spoon.take("a", 0.0)
    assert not spoon.take("b", 0.45) and spoon.take("b", 0.5), "原版 now - stirredAt < 10 刻"


def testAnUnusedSpoonBelongsToNobody():
    spoon = Spoon()
    assert spoon.holder is None and not spoon.isStirring(0.0)
    assert spoon.take("anyone", 0.0) and spoon.holder == "anyone"


def testOpeningThePotMakesYouItsCookOnlyWhenNobodyStirs():
    spoon = Spoon()
    spoon.open("a", 0.0)
    assert spoon.holder == "a"
    spoon.take("a", 1.0)
    spoon.open("b", 1.2)
    assert spoon.holder == "a", "有人正在搅：打开锅不换厨师"
    spoon.open("b", 2.0)
    assert spoon.holder == "b"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
