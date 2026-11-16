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


def testPumpkinPieIsPlacedUnlessTheConfigAsksForSneaking():
    # JE PlacePumpkinPieMixin：enablePumpkinPieSneakToPlace 缺省 false，一律放成方块；为 true 时只有潜行才放，不潜行照常吃
    assert Placement.placesPumpkinPie(False, False) is True
    assert Placement.placesPumpkinPie(True, False) is True
    assert Placement.placesPumpkinPie(False, True) is False
    assert Placement.placesPumpkinPie(True, True) is True
    assert Placement.placesPumpkinPie(None, True) is False, "读不到潜行状态按没潜行"


def _run(pacer, key, start, seconds, step=0.05):
    """按 20 刻 / 秒喂 pacer，返回放行的时刻。"""
    fired = []
    ticks = int(round(seconds / step))
    for index in range(ticks + 1):
        now = start + index * step
        if pacer.due(key, now):
            fired.append(now)
    return fired


def testThePacerFiresOncePerPeriodWhateverTheWorldTimeDoes():
    """实机：/gamerule doDaylightCycle false 冻住世界时间后，旧的按世界时间错峰让煎锅、厨锅不工作。"""
    pacer = Ticks.Pacer(1.0)
    fired = _run(pacer, (0, (5, 64, 9)), 1000.0, 10.0)
    assert 9 <= len(fired) <= 10
    gaps = [b - a for a, b in zip(fired, fired[1:])]
    assert all(abs(gap - 1.0) < 0.051 for gap in gaps), gaps


def testThePacerStaggersPositionsAndNeverBursts():
    pacer = Ticks.Pacer(1.0)
    firsts = set()
    for x in range(-10, 10):
        key = (0, (x, 64, 3))
        firsts.add(round(_run(pacer, key, 0.0, 2.0)[0] % 1.0, 2))
    assert len(firsts) > 5, "不同位置落在不同相位上"
    late = Ticks.Pacer(0.2)
    key = (0, (1, 2, 3))
    late.due(key, 0.0)
    assert late.due(key, 60.0) and not late.due(key, 60.05), "落后很久只补一次，不连发"
    late.forget(key)
    assert len(late) == 0 and not late.due(key, 61.0), "方块没了再出现：重新错开相位"


def testPosHashIsStableAndNonNegative():
    assert Ticks.posHash((1, 2, 3)) == Ticks.posHash((1.0, 2.0, 3.0))
    assert Ticks.posHash((-30000000, -64, -30000000)) >= 0


def testProbabilityBounds():
    assert Ticks.probability(0) is False
    assert Ticks.probability(-5) is False
    assert Ticks.probability(100) is True
    hits = sum(1 for _ in range(2000) if Ticks.probability(30))
    assert 400 < hits < 800


def testAimingAtABlockNeverEatsThePumpkinPie():
    eats = Placement.eatsPumpkinPie
    assert eats(False, False, False) and eats(False, True, True), "对着空气照常吃"
    assert not eats(True, False, False) and not eats(True, True, False), "JE 缺省：对着方块只放不吃（放不下也不吃）"
    assert eats(True, False, True), "配置要潜行才放：没潜行对着方块照常吃"
    assert not eats(True, True, True)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
