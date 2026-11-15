# -*- coding: utf-8 -*-
# runner: both
"""Mth 的 Java 取整/取余语义测试（Math.round、整数除法、wrapDegrees、取整到刻）。"""
from __future__ import print_function

import math

import fdtest

Mth = fdtest.load("Shared.Rules.HandsOn.Mth")


def testClampAndSign():
    assert Mth.clamp(5, 1, 3) == 3
    assert Mth.clamp(-5, 1, 3) == 1
    assert Mth.clamp(2.5, 1, 3) == 2.5
    assert Mth.sign(-0.2) == -1 and Mth.sign(0.0) == 0 and Mth.sign(7) == 1


def testLerpIsStartPlusDeltaTimesSpan():
    # Mth.lerp(delta, start, end)：StirSkill 的手速基准就靠它
    assert Mth.lerp(0.4, 10.0, 20.0) == 14.0
    assert Mth.lerp(0.0, 3.0, 9.0) == 3.0 and Mth.lerp(1.0, 3.0, 9.0) == 9.0


def testRoundIsFloorOfXPlusHalf():
    # Java 的 Math.round 向正无穷进位；Python 3 的 round(2.5) 是 2（银行家舍入），所以不能直接用
    assert Mth.roundInt(0.5) == 1 and Mth.roundInt(2.5) == 3
    assert Mth.roundInt(-0.5) == 0 and Mth.roundInt(-1.5) == -1
    assert Mth.roundInt(56.57) == 57 and Mth.roundInt(56.49) == 56
    assert Mth.floorInt(-0.2) == -1 and Mth.floorInt(2.9999) == 2


def testIntegerDivisionTruncatesTowardZero():
    # (maxStack - mealCount) / resultCount 在成品涨过堆叠上限时是负数：Java 向零取整，Python 的 // 向下取整
    assert Mth.truncDiv(7, 2) == 3
    assert Mth.truncDiv(-7, 2) == -3
    assert Mth.truncDiv(-1, 2) == 0
    assert Mth.truncDiv(0, 5) == 0
    assert Mth.truncDiv(16, 1) == 16


def testWrapRadiansFoldsIntoMinusPiToPi():
    assert abs(Mth.wrapRadians(0.5) - 0.5) < 1e-12
    assert abs(Mth.wrapRadians(2.0 * math.pi)) < 1e-12
    assert abs(Mth.wrapRadians(math.pi) - (-math.pi)) < 1e-12, "[-pi, pi)：正好 pi 折成 -pi"
    assert abs(Mth.wrapRadians(-math.pi) - (-math.pi)) < 1e-12
    assert abs(Mth.wrapRadians(3.5 * math.pi) - (-0.5 * math.pi)) < 1e-9
    assert abs(Mth.wrapRadians(-3.5 * math.pi) - (0.5 * math.pi)) < 1e-9
    # 过零点的小转角：atan2 从 +pi 附近跳到 -pi 附近，折回来应当是一个小角度
    assert abs(Mth.wrapRadians(-math.pi + 0.1 - (math.pi - 0.1)) - 0.2) < 1e-9


def testRoundToTickIsWholeTicksAndAtLeastOne():
    assert Mth.roundToTick(0.001) == Mth.TICK, "原版 Math.max(1, ...)：至少一刻"
    assert abs(Mth.roundToTick(2.8284) - 2.85) < 1e-12, "56.57 刻 -> 57 刻"
    assert abs(Mth.roundToTick(2.8149) - 2.8) < 1e-12, "56.3 刻 -> 56 刻"
    assert abs(Mth.roundToTick(10.0) - 10.0) < 1e-12


def testReachedToleratesAccumulatedError():
    total = 0.0
    for _ in range(57):
        total += 1.0 / 57.0
    assert Mth.reached(total), "逐步累加 1/57 共 57 次，可能停在 0.9999999999999999"
    assert not Mth.reached(0.999)
    assert Mth.reached(1.0) and Mth.reached(1.5)


def testIsFinite():
    assert Mth.isFinite(1.0) and Mth.isFinite(0)
    assert not Mth.isFinite(float("nan")) and not Mth.isFinite(float("inf")) and not Mth.isFinite(-float("inf"))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
