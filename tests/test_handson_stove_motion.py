# -*- coding: utf-8 -*-
# runner: both
"""StoveMotion（烤架上一件的动作）：落下、翻面跳起转半圈、取走的虚影、被拒绝弹回、悬停抬起。数字来自 Hands-On Delight 的
client/StoveBehavior.java（land 235-243、turned 378-399、taken 501-517、REFUSED 482-490）和 Diegesis 的 Tween / Easing / NodeInstance。"""
from __future__ import print_function

import math

import fdtest

M = fdtest.load("Shared.Rules.HandsOn.StoveMotion")
DT = 0.01


def near(a, b, eps=1.0e-6):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def run(node, seconds, hovered=False):
    """走 seconds 秒（每步 0.01），返回按先后到点的事件名。"""
    fired = []
    for _ in range(int(round(seconds / DT))):
        fired += node.update(DT, hovered)
    return fired


def testTheEasingIsDiegesisInOutCubic():
    assert M.inOutCubic(0.0) == 0.0 and M.inOutCubic(1.0) == 1.0
    near(M.inOutCubic(0.5), 0.5)
    near(M.inOutCubic(0.25), 4 * 0.25 ** 3)
    near(M.inOutCubic(0.75), 1.0 - 0.5 ** 3 / 2.0)
    assert M.inOutCubic(-1.0) == 0.0 and M.inOutCubic(2.0) == 1.0, "夹在 0..1 里"


def testATweenGoesFromWhereItIsAndAHopAddsAnArcOnTop():
    tween = M.Tween(0.0, 0.0, 0.0)
    tween.start(10.0, 0.0, 4.0, 1.0)
    tween.update(0.5)
    near(tween.current[0], 5.0)
    near(tween.current[2], 2.0)
    assert tween.running
    tween.update(0.5)
    assert tween.current == [10.0, 0.0, 4.0] and not tween.running
    tween.start(0.0, 0.0, 0.0, 1.0, 3.0)
    tween.update(0.5)
    near(tween.current[1], 3.0)
    near(tween.current[0], 5.0)
    tween.update(0.5)
    near(tween.current[1], 0.0)
    tween.start(7.0, 8.0, 9.0, 0.0)
    assert tween.current == [7.0, 8.0, 9.0], "0 秒就是直接跳过去"


def testAPieceAddedAloneDropsFromAboveWithAHop():
    piece = M.Piece(-30.0)
    piece.arrive()
    assert piece.visible
    near(piece.pose()[0][1], M.LAND_FROM)
    run(piece, 0.1)
    near(piece.pose()[0][1], M.LAND_FROM / 2.0 + M.LAND_ARC, 0.01)
    assert run(piece, 0.1) == ["landed"], "0.2 秒后落到烤架上：冒汽、嗞一声"
    offset, rotation, scale = piece.pose()
    assert offset == (0.0, offset[1], 0.0) and abs(offset[1]) < 1.0e-9 and rotation == (0.0, -30.0, 0.0) and scale == 1.0


def testSeveralAtOnceComeFromThePlayersSideOneAfterTheOther():
    first, second = M.Piece(0.0), M.Piece(0.0)
    first.arrive(0.0, (1.0, -16.0))
    second.arrive(M.STAGGER, (2.0, -16.0))
    assert first.visible and not second.visible, "后面的先等着，还没出现"
    near(first.pose()[0][0], 1.0)
    near(first.pose()[0][2], -16.0)
    near(first.pose()[0][1], M.LAND_FROM)
    assert run(first, M.PLAYER_LAND_TIME) == ["landed"]
    assert run(second, M.STAGGER) == ["appear"] and second.visible
    near(second.pose()[0][0], 2.0, 0.05)
    assert run(second, M.PLAYER_LAND_TIME) == ["landed"]
    assert abs(second.pose()[0][2]) < 1.0e-9


def testATurnHopsAndHalfTurnsThenSwapsTheLookEdgeOnThenLandsFlat():
    piece = M.Piece(15.0)
    piece.turn()
    assert run(piece, M.FLIGHT / 2.0 - 3 * DT) == []
    offset, rotation, _ = piece.pose()
    assert 2.8 < offset[1] <= 3.0 + 1.0e-9 and 80.0 < rotation[0] < 90.0 and rotation[1] == 15.0, "半程：升到 3 px、转到快立起来"
    assert run(piece, 3 * DT) == ["swap"]
    near(piece.pose()[1][0], -90.0, 1.0e-6)             # 换了另一面的样子之后从 -90 度转回来
    rising = []
    for _ in range(int(round(M.FLIGHT / 2.0 / DT))):
        piece.update(DT)
        rising.append(piece.pose()[1][0])
    assert rising == sorted(rising) and rising[-1] == 0.0, "后半程：-90 -> 0，单调"
    assert abs(piece.pose()[0][1]) < 1.0e-9 and piece.pose()[1] == (0.0, 15.0, 0.0), "平躺着落回原位"


def testTheTurnEventsComeAtTheMiddleAndTheEnd():
    piece = M.Piece()
    piece.turn()
    fired = []
    for step in range(31):
        for name in piece.update(DT):
            fired.append((name, step))
    assert [name for name, _ in fired] == ["swap", "turned"]
    assert fired[0][1] in (14, 15) and fired[1][1] in (29, 30), fired


def testAPieceTurnedAgainAfterLandingFlipsAgain():
    piece = M.Piece(0.0)
    piece.turn()
    run(piece, 0.4)
    piece.turn()
    assert run(piece, 0.4) == ["swap", "turned"]
    assert piece.pose()[1] == (0.0, 0.0, 0.0)


def testTheTakenGhostRisesAndShrinksAwayThenIsGone():
    ghost = M.Ghost()
    assert not ghost.visible
    ghost.taken(15.0)
    assert ghost.visible and ghost.pose()[2] == 1.0
    run(ghost, M.AWAY_TIME / 2.0)
    offset, _, scale = ghost.pose()
    assert 0.0 < scale < 1.0 and offset[1] > 1.0
    assert run(ghost, M.AWAY_TIME / 2.0 + DT) == ["gone"] and not ghost.visible
    near(ghost.pose()[2], 0.0)
    near(ghost.pose()[0][1], M.AWAY_RISE, 1.0e-6)


def testARefusedPieceDropsToTheGrillThenBouncesBackAndIsGone():
    ghost = M.Ghost()
    ghost.refused()
    near(ghost.pose()[0][1], M.REFUSE_START)
    assert run(ghost, M.REFUSE_DROP_TIME) == ["bounce"]
    near(ghost.pose()[0][1], M.REFUSE_DOWN, 0.01)
    assert run(ghost, M.REFUSE_BOUNCE_TIME) == ["gone"] and not ghost.visible
    offset = ghost.pose()[0]
    near(offset[1], M.REFUSE_START, 0.01)
    near(offset[2], M.REFUSE_BACK, 0.01)


def testAHoveredPieceLiftsAPixelAndLetsGoAgain():
    piece = M.Piece()
    run(piece, 1.0, hovered=True)
    near(piece.pose()[0][1], M.HOVER_LIFT, 1.0e-3)
    run(piece, 1.0, hovered=False)
    assert piece.pose()[0][1] < 1.0e-3
    half = M.Piece()
    run(half, M.HOVER_HALF_LIFE, hovered=True)
    near(half.pose()[0][1], M.HOVER_LIFT / 2.0, 0.01)       # 半衰期 0.06 秒：走完一半


def testTheStickerLiesFlatFacingUpAndTheNodeAnglesTurnItLikeTheScene():
    flat = M.poseRows(0.0, 0.0, 0.0)
    assert [[round(v, 9) for v in row] for row in flat] == [[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]]

    def apply(rows, vector):
        return tuple(round(sum(rows[i][k] * vector[k] for k in range(3)), 9) for i in range(3))

    assert apply(flat, (0.0, 0.0, -1.0)) == (0.0, 1.0, 0.0), "贴图的正面朝上"
    assert apply(flat, (0.0, 1.0, 0.0)) == (0.0, 0.0, 1.0), "顶边朝远处（+z）"
    turned = M.poseRows(0.0, 90.0, 0.0)
    assert apply(turned, (0.0, 0.0, -1.0)) == (0.0, 1.0, 0.0), "偏航绕竖轴转，正面还是朝上"
    assert apply(turned, (0.0, 1.0, 0.0)) == (1.0, 0.0, 0.0), "顶边从远处转到 +x"
    assert apply(M.poseRows(90.0, 0.0, 0.0), (0.0, 0.0, -1.0)) == (0.0, 0.0, 1.0), "转到立起来：正面朝 +z（背朝镜头）"
    assert apply(M.poseRows(-90.0, 0.0, 0.0), (0.0, 0.0, -1.0)) == (0.0, 0.0, -1.0), "-90 度：立着、正面朝镜头"
    top = apply(M.poseRows(0.0, 30.0, 0.0), (0.0, 1.0, 0.0))
    near(top[0], math.sin(math.radians(30.0)), 1.0e-6)
    near(top[2], math.cos(math.radians(30.0)), 1.0e-6)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
