# -*- coding: utf-8 -*-
# runner: both
"""一批煮好的收尾（Shared/Rules/HandsOn/PotFinish.py）：数值照 Hands-On Delight 的 PotBehavior.cookedThrough / melt / burst。

Java：SWELL_TIME 0.16 秒从 1 胀到 SWELL 1.4，再按 SWELL * (1 - (age - 0.16) / 0.39) 的平方缩到 MELT_TIME 0.55 秒的 0，每秒下沉 0.7 像素，
每个错开 MELT_STAGGER 0.07 秒；起头 10 个气泡 + 一圈 0.3 的涟漪；每个收尾汽 x4 / 闪光 x3 / 涟漪 0.35 / 炸开的声音（音量 0.55、音高 0.95 + 0.05 * 槽位）；
碎料等 n * 0.07 + 0.55 + 0.25 秒。
"""
from __future__ import print_function

import fdtest

Finish = fdtest.load("Shared.Rules.HandsOn.PotFinish")
DT = 0.01
POS = {0: (1.0, -5.0, 2.0), 2: (-1.5, -5.0, 0.5), 5: (0.0, -5.0, -2.0)}


def go(state, seconds, dt=DT):
    """推进 seconds 秒；返回 [(时刻, poses, events)]（时刻 = 这一步结束时）。"""
    out = []
    for index in range(int(round(seconds / dt))):
        poses, events = state.step(dt)
        out.append((round((index + 1) * dt, 6), poses, events))
    return out


def eventsOf(timeline, kind):
    return [(at, e) for at, _poses, events in timeline for e in events if e["type"] == kind]


def testConstantsAreJavas():
    assert (Finish.SWELL_TIME, Finish.SWELL, Finish.MELT_TIME, Finish.MELT_STAGGER, Finish.PIECES_WAIT) == (0.16, 1.4, 0.55, 0.07, 0.25)
    assert Finish.SINK_SPEED == 0.7 and Finish.GLINT_COLOR == 0xFFFFE9A0
    assert Finish.RISE == (0.0, 3.5, 0.0) and Finish.PUFF_UP == (0.0, 4.0, 0.0)


def testTheCopySwellsThenShrinksAway():
    scale = Finish.meltScale
    assert scale(-0.3) == 1.0 and scale(0.0) == 1.0, "在等的和刚开始的都是 1"
    assert abs(scale(0.08) - 1.2) < 1e-9, "胀的时候 lerp(age / 0.16, 1, 1.4)"
    assert abs(scale(0.16) - 1.4) < 1e-9, "0.16 秒胀到最大"
    assert abs(scale(0.355) - 1.4 * 0.25) < 1e-9, "缩的那段 1.4 * (1 - (age - 0.16) / 0.39) 的平方：一半时 0.35"
    assert abs(scale(0.55)) < 1e-9, "0.55 秒缩没"
    assert scale(0.3) > scale(0.4) > scale(0.5) > 0.0, "缩的时候一直变小"
    assert scale(0.1) < scale(0.16) and scale(0.2) < scale(0.16), "0.16 秒是最大的"


def testPiecesWaitForTheWholeBatch():
    for copies in (1, 3, 6):
        assert abs(Finish.piecesWait(copies) - (copies * 0.07 + 0.55 + 0.25)) < 1e-12
    state = Finish.start([0, 2, 5], POS, 100.0)
    assert abs(state.wait - 1.01) < 1e-9 and abs(state.piecesAt - 101.01) < 1e-9 and state.waiting


def testTheStartBurstIsTenBubblesAndARipple():
    state = Finish.start([0, 2, 5], POS, 0.0, bubbleColor=0xE0AABBCC)
    _poses, events = state.step(DT)
    assert events[0] == {"type": "bubbles", "count": 10, "rise": (0.0, 3.5, 0.0), "color": 0xE0AABBCC}
    assert events[1] == {"type": "ripple", "x": 8.0, "z": 8.0, "strength": 0.3}
    assert len(events) == 2
    _poses, later = state.step(DT)
    assert not later, "起头的那一串只发一次"


def testEachCopyWaitsItsTurnThenSwellsAtTheSpot():
    state = Finish.start([0, 2, 5], POS, 0.0)
    timeline = go(state, 0.2)
    byAt = dict((at, poses) for at, poses, _events in timeline)
    # 0.1 秒时：第一个胀了一半多（0.1 / 0.16），第二个（晚 0.07）才 0.03 秒，第三个（晚 0.14）还在等
    first, second, third = byAt[0.1]
    assert first["slot"] == 0 and abs(first["scale"] - (1.0 + 0.4 * 0.1 / 0.16)) < 1e-9
    assert second["slot"] == 2 and abs(second["scale"] - (1.0 + 0.4 * 0.03 / 0.16)) < 1e-9
    assert third["slot"] == 5 and third["scale"] == 1.0 and third["visible"], "在等的替身已经摆在原处，是看得见的"
    assert third["pos"] == POS[5], "等的时候不动"
    assert abs(first["pos"][1] - (-5.0 - 0.1 * 0.7)) < 1e-9, "胀的时候就开始下沉：每秒 0.7 像素"
    assert first["pos"][0] == 1.0 and first["pos"][2] == 2.0, "只往下沉，水平不动"


def testTheCopiesBurstOneAfterTheOtherAtTheirOwnTime():
    state = Finish.start([0, 2, 5], POS, 0.0)
    timeline = go(state, 1.2)
    bursts = eventsOf(timeline, "sound")
    assert [round(at, 2) for at, _e in bursts] == [0.55, 0.62, 0.69], "k * 0.07 + 0.55"
    assert [e["pitch"] for _at, e in bursts] == [0.95, 0.95 + 0.05 * 2, 0.95 + 0.05 * 5]
    assert all(e["name"] == "burst" and e["volume"] == 0.55 and e["at"] == "broth" for _at, e in bursts)
    # 走完的那一帧 visible 是 False，之后不再有这个替身
    ended = [(at, p) for at, poses, _events in timeline for p in poses if not p["visible"]]
    assert [p["slot"] for _at, p in ended] == [0, 2, 5]
    assert max(at for at, poses, _events in timeline if any(p["slot"] == 5 for p in poses)) == 0.69


def testEachBurstIsSteamGlintRippleAndSoundAtTheStartingSpot():
    state = Finish.start([0], POS, 0.0)
    timeline = go(state, 0.6)
    at = (8.0 + 1.0, 8.0 - 5.0, 8.0 + 2.0)
    steam = eventsOf(timeline, "steam")
    assert len(steam) == 1 and steam[0][1] == {"type": "steam", "count": 4, "pos": at, "rise": (0.0, 4.0, 0.0), "spread": 0.5, "color": 0}
    glint = eventsOf(timeline, "glint")[0][1]
    assert glint == {"type": "glint", "count": 3, "pos": at, "rise": (0.0, 4.0, 0.0), "spread": 0.9, "color": 0xFFFFE9A0}
    ripples = eventsOf(timeline, "ripple")
    assert [e["strength"] for _at, e in ripples] == [0.3, 0.35], "起头 0.3，收尾 0.35"
    assert (ripples[1][1]["x"], ripples[1][1]["z"]) == (at[0], at[2]), "涟漪在炸开的位置，不是下沉后的位置"
    order = [e["type"] for _at, _poses, events in timeline for e in events if e["type"] in ("steam", "glint", "sound")]
    assert order == ["steam", "glint", "sound"]


def testThePiecesComeUpWhenTheWaitIsOver():
    state = Finish.start([0, 2, 5], POS, 0.0)
    timeline = go(state, 1.2)
    pieces = eventsOf(timeline, "pieces")
    assert len(pieces) == 1 and abs(pieces[0][0] - 1.01) <= DT + 1e-9, pieces
    assert not state.waiting and state.done and not state.copies


def testNothingToMeltIsAlreadyDone():
    state = Finish.start([], POS, 5.0)
    assert state.done and not state.waiting and state.piecesAt is None
    assert state.step(0.5) == ([], [])


def testWorksWithAListOfPositionsAndOneTickSteps():
    positions = [(0.0, -5.0, 0.0)] * 6
    state = Finish.start([1, 4], positions, 0.0)
    timeline = go(state, 1.0, dt=0.05)
    assert [round(e["pitch"], 3) for _at, e in eventsOf(timeline, "sound")] == [0.95 + 0.05 * 1, 0.95 + 0.05 * 4]
    assert len(eventsOf(timeline, "pieces")) == 1 and state.done
    assert state.step(0.05) == ([], []), "完事之后再推进什么都没有"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
