# -*- coding: utf-8 -*-
# runner: both
"""Grill 灶台两面烧烤状态机测试。

移植自 Hands-On Delight 的 StoveTests：aPieceGrillsInHalvesAndWaitsToBeTurned、theGrillingTimeFollowsTheConfig、
onlyFoodGoesOnAnOpenGrill（位置部分）、piecesLaidByHandGoFarmersDelightsWay（交还时长部分）。
时间以秒计；FD 的灶台烤牛肉要 600 刻（30 秒）：一面 200 刻（10 秒）。
"""
from __future__ import print_function


import fdtest

G = fdtest.load("Shared.Rules.HandsOn.Grill")
_Mth = fdtest.load("Shared.Rules.HandsOn.Mth")
TICK = _Mth.TICK


BEEF = 30.0                              # 原 600 刻
BEEF_SIDE = G.sideSeconds(BEEF, 1.0)     # 原 200 刻


def advance(grill, place, seconds, side=BEEF_SIDE, oneSided=False, lit=True):
    done = False
    for _ in range(int(round(seconds / TICK))):
        done = grill.step(place, TICK, side, oneSided, lit)
    return done


def newTop(pieces):
    """放上 pieces 件（手放），返回 (grill, 放了哪些位置)。"""
    grill = G.Grill()
    laid = G.laidPlaces([False] * G.PLACES, -1, pieces)
    for place in laid:
        grill.farmersDelightsWay(place)
        grill.layByHand(place)
    return grill, laid


def testSideTimes():
    assert abs(BEEF_SIDE - 200 / 20.0) < 1e-12, "a side in today's 200 ticks"
    assert abs(G.sideSeconds(BEEF, 2.0) - 400 / 20.0) < 1e-12
    assert G.sideSeconds(0.001, 1.0) == TICK
    assert abs(G.sideSeconds(BEEF, 1.0, quantize=False) - 10.0) < 1e-12


def testAPieceGrillsInHalvesAndWaitsToBeTurned():
    grill, laid = newTop(3)
    assert laid == [0, 1, 2], "a stack goes on one by one, a piece a place"
    assert grill.byHand(0), "all three, laid by hand"
    for place in laid:
        advance(grill, place, BEEF_SIDE + 0.5)
    assert grill.waits(0) and grill.up(0) == 0.0, "the lower side is done, the piece waits"
    assert grill.toss(0, 100.0), "a click turns it over"
    assert grill.up(0) >= 1.0 and grill.down(0) == 0.0
    done = advance(grill, 0, BEEF_SIDE + 0.5)
    assert done and grill.isDone(0), "turned once, it is done"
    assert grill.waits(1), "the others still wait to be turned"
    grill.done(0)
    assert (grill.down(0), grill.up(0)) == (0.0, 0.0), "它变成了成品，从零重新计"
    grill.farmersDelightsWay(0)
    assert not grill.byHand(0), "a take resets byHand: the place starts over"


def testAPieceNotTurnedStaysRawOnTop():
    grill, _ = newTop(1)
    advance(grill, 0, 3 * BEEF_SIDE)
    assert grill.waits(0) and not grill.isDone(0), "不翻就永远只熟一面"
    assert grill.up(0) == 0.0


def testTheGrillingTimeFollowsTheConfig():
    steps = []
    for times in (1.0, 2.0):
        grill, _ = newTop(1)
        grill.step(0, TICK, G.sideSeconds(BEEF, times))
        steps.append(grill.down(0))
    assert abs(steps[0] - 1.0 / 200) < 1e-12, "1.0: a side in today's 200 ticks"
    assert abs(steps[0] - 2.0 * steps[1]) < 1e-12, "2.0: half as far a tick"
    assert abs(G.handOverSeconds(BEEF, False, 2.0) - 60.0) < 1e-12, "handed over at 2.0: twice Farmer's Delight's 600 ticks (1200)"
    assert G.handOverSeconds(BEEF, False, 1.0) == 30.0


def testAPieceDoneIsHandedOverAtOnce():
    assert G.handOverSeconds(BEEF, True, 2.0) == TICK, "两面都熟的交还 FD：1 刻就弹出，不乘倍率"
    assert G.handOverSeconds(0.0, False, 2.0) == TICK, "没有配方时间：1 刻"


def testOnlyFoodGoesOnAnOpenGrill():
    occupied = [False] * G.PLACES
    laid = G.laidPlaces(occupied, -1, 10)
    assert laid == [0, 1, 2, 3, 4, 5], "six places, six pieces"
    assert 10 - len(laid) == 10 - G.PLACES == 4
    assert G.laidPlaces([True] * G.PLACES, -1, 10) == [], "a full grill takes nothing"
    occupied = [True, True, True, True, False, True]
    assert G.laidPlaces(occupied, -1, 10) == [4], "只放空位"
    assert G.laidPlaces(occupied, -1, 0) == []
    assert G.laidPlaces([False] * G.PLACES, 4, 1) == [4], "one onto the place picked"
    assert G.laidPlaces([False] * G.PLACES, 4, 3) == [4], "指定位置只放一件"
    assert G.laidPlaces(occupied, 0, 1) == [], "指定的位置被占了"
    assert G.laidPlaces([False] * 4, -1) == [0, 1, 2, 3], "灶台位置少于 6：按它自己的"


def testOnlyTheTurnedPieceMoves():
    grill, laid = newTop(2)
    for place in laid:
        advance(grill, place, BEEF_SIDE + 0.5)
    assert grill.toss(0, 50.0)
    assert grill.up(0) >= 1.0 and grill.down(0) == 0.0
    assert grill.down(1) >= 1.0 and grill.up(1) == 0.0 and grill.waits(1), "另一件原封不动"
    assert grill.turnedAt(1) < 0 and grill.turnedAt(0) == 50.0


def testTheTurnGapIsSixTicksPerPiece():
    grill, _ = newTop(2)
    assert grill.toss(0, 10.0)
    assert not grill.toss(0, 10.2), "still in the air"
    assert grill.canTurn(1, 10.0), "间隔是每件各自的"
    assert grill.toss(1, 10.0)
    assert not grill.canTurn(0, 10.29)
    assert grill.toss(0, 10.3), "6 刻之后可以再翻"


def testNothingToTurnNothingHappens():
    grill, _ = newTop(1)
    assert not grill.toss(3, 10.0, hasFood=False)
    assert grill.turnedAt(3) < 0


def testAPlaceNumberFromTheClientIsChecked():
    # 位置序号来自客户端：-1 在 Python 里会绕回最后一个位置，不能放过
    grill, _ = newTop(6)
    for bad in (-1, 6, 99, 1.5, "0", None, float("nan")):
        assert not grill.has(bad) and not grill.canTurn(bad, 10.0) and not grill.toss(bad, 10.0), repr(bad)
    assert all(grill.turnedAt(place) < 0 for place in range(G.PLACES)), "没有任何位置被翻过"
    assert grill.has(0) and grill.has(5) and grill.has(2.0)
    assert grill.toss(2.0, 10.0) and grill.turnedAt(2) == 10.0


def testTurningFarmersDelightsPieceTakesItOverFromRaw():
    grill = G.Grill()
    grill.grill(2, 0.6)
    assert not grill.byHand(2)
    assert grill.toss(2, 10.0)
    assert grill.byHand(2) and grill.down(2) == 0.0 and grill.up(2) == 0.0, "FD 烤着的，翻一下归厨师，从生开始"


def testAnUnlitStoveGrillsNothing():
    grill, _ = newTop(1)
    advance(grill, 0, 5.0, lit=False)
    assert grill.down(0) == 0.0
    advance(grill, 0, 1.0, lit=True)
    assert grill.down(0) > 0.0


def testAnEggGrillsThroughWithoutATurn():
    grill, _ = newTop(1)
    advance(grill, 0, BEEF_SIDE + 0.25, oneSided=True)
    assert not grill.waits(0) and grill.up(0) == grill.down(0) and grill.down(0) > 0.5
    done = advance(grill, 0, BEEF_SIDE + 0.25, oneSided=True)
    assert done and grill.isDone(0)


def testPiecesLaidByHandArePerPlaceState():
    grill = G.Grill(places=4)
    assert grill.places == 4
    grill.layByHand(3)
    assert grill.byHand(3) and not grill.byHand(0)
    try:
        grill.down(4)
    except IndexError:
        pass
    else:
        raise AssertionError("位置越界应当报错")


def testTheClientsHearOfEveryStepNotEveryTick():
    grill, _ = newTop(2)
    assert grill.dueToSend()
    assert not grill.dueToSend()
    grill.grill(0, 0.01)
    assert not grill.dueToSend(), "没走满 1/16"
    grill.grill(0, 0.06)
    assert grill.dueToSend()
    grill.layByHand(5)
    assert grill.dueToSend(), "手放标记变了"


def testTheSyncStepIsSharedWithTheSkillet():
    assert G.syncStep(0.5) == 0.5 and G.syncStep(1.0) == 1.0 and G.STEPS == 16


def testTheGrillIsSavedAndReadBackLikeJes():
    """Grill.save / load（100-126 行）：每个位置是不是手放的、两面烤到哪；坏的、缺的当没有，进度夹进 0..1。"""
    grill, laid = newTop(3)
    advance(grill, 0, BEEF_SIDE + 0.5)
    advance(grill, 1, BEEF_SIDE * 0.5)
    saved = grill.saved()
    assert saved["byHand"] == [1, 1, 1, 0, 0, 0] and saved["down"][0] == 1.0 and 0.4 < saved["down"][1] < 0.6 and saved["up"] == [0.0] * 6
    fresh = G.Grill()
    assert fresh.load(saved)
    assert [fresh.byHand(place) for place in range(6)] == [True] * 3 + [False] * 3
    assert fresh.waits(0) and not fresh.waits(1) and abs(fresh.down(1) - grill.down(1)) < 1e-12
    assert fresh.turnedAt(0) < 0, "翻面的时间不存（JE 也不存）"
    assert not fresh.load(None) and not fresh.load([1, 2]) and not fresh.load("x")
    bad = G.Grill()
    assert bad.load({"byHand": [1, "x"], "down": [5.0, -2.0, "soon", None], "up": "oops"})
    assert [bad.down(place) for place in range(4)] == [1.0, 0.0, 0.0, 0.0] and [bad.up(place) for place in range(6)] == [0.0] * 6
    assert bad.byHand(0) and bad.byHand(1) and not bad.byHand(2), "缺的当没有"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
