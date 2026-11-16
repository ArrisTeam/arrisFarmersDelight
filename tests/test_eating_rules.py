# -*- coding: utf-8 -*-
# runner: both
"""吃一份食物的饥饿值 / 饱和度结算（Shared/Rules/Eating.py），算法照 Java 版 FoodData.eat。"""
from __future__ import print_function

import fdtest

Eating = fdtest.load("Shared.Rules.Eating")


def _near(actual, expected):
    return abs(actual - expected) < 1e-9


def testPieSliceGivesThreeHungerAndOnePointEightSaturation():
    # JE 的 PIE_SLICE：营养 3，饱和度修饰 0.3 -> 饱和度 3 × 0.3 × 2 = 1.8
    hunger, saturation = Eating.eatenFood(10, 5.0, 3, 0.3)
    assert hunger == 13 and _near(saturation, 6.8)


def testNothingGoesPastTheCaps():
    assert Eating.eatenFood(19, 19.0, 3, 0.3) == (20, 20)
    assert Eating.eatenFood(20, 20.0, 3, 0.3) == (20, 20)


def testSaturationCannotExceedTheNewHungerLevel():
    hunger, saturation = Eating.eatenFood(0, 0.0, 3, 0.8)
    assert hunger == 3 and _near(saturation, 3)      # 3 × 0.8 × 2 = 4.8，被饥饿值 3 封顶


def testNoModifierKeepsSaturation():
    assert Eating.eatenFood(10, 5.0, 4, 0) == (14, 5.0)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
