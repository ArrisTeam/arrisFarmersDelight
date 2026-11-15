# -*- coding: utf-8 -*-
# runner: both
"""放置朝向、放置位置、假日实验玩法 aux 映射、tick 错峰（Shared/Rules/Placement.py、Ticks.py）。"""
from __future__ import print_function

import fdtest

Placement = fdtest.load("Shared.Rules.Placement")
Ticks = fdtest.load("Shared.Rules.Ticks")


def testAuxFromAngleQuadrants():
    # 方块在原点，玩家分别在 +x、+y(=+z)、-x、-y 方向
    assert Placement.auxFromAngle(0, 0, 5, 0) == 3
    assert Placement.auxFromAngle(0, 0, 0, 5) == 0
    assert Placement.auxFromAngle(0, 0, -5, 0.1) == 1
    assert Placement.auxFromAngle(0, 0, -5, -0.1) == 1
    assert Placement.auxFromAngle(0, 0, 0, -5) == 2
    # 恰好在分界线上（45°）沿用旧实现归入 2
    assert Placement.auxFromAngle(0, 0, 5, 5) == 2


def testPlacePositions():
    pos = Placement.placePositions(10, 64, -3)
    assert pos == {0: (10, 63, -3), 1: (10, 65, -3), 2: (10, 64, -4), 3: (10, 64, -2), 4: (9, 64, -3), 5: (11, 64, -3)}


def testHolidayAuxMap():
    assert Placement.holidayAuxMap(True) == {0: 0, 4: 1, 8: 2, 12: 3}
    assert Placement.holidayAuxMap(False) == {0: 0, 1: 1, 2: 2, 3: 3}
    # 旧代码的用法：查不到时原样返回
    assert Placement.holidayAuxMap(True).get(2, 2) == 2


def testEntityFaceCoversAllFourDirections():
    assert sorted(Placement.ENTITY_FACE) == [0, 1, 2, 3]


def testStaggeredTicksSpreadEvenly():
    stride = 4
    hits = [0] * stride
    for x in range(-20, 20):
        for z in range(-20, 20):
            for tick in range(stride):
                if Ticks.isStaggeredTick(tick, (x, 64, z), stride):
                    hits[tick] += 1
    # 每个位置在一个周期里恰好轮到一次
    assert sum(hits) == 40 * 40
    assert min(hits) > 0


def testPosHashIsStableAndNonNegative():
    assert Ticks.posHash((1, 2, 3)) == Ticks.posHash((1.0, 2.0, 3.0))
    assert Ticks.posHash((-30000000, -64, -30000000)) >= 0


def testProbabilityBounds():
    assert Ticks.probability(0) is False
    assert Ticks.probability(-5) is False
    assert Ticks.probability(100) is True
    hits = sum(1 for _ in range(2000) if Ticks.probability(30))
    assert 400 < hits < 800


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
