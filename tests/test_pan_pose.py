# -*- coding: utf-8 -*-
# runner: both
"""锅里的节点怎么摆（Shared/Rules/PanPose.py）：锅一颠，上面的食物跟着转着挪着；蛋的手不跟锅；换成世界里的矩阵。"""
from __future__ import print_function

import fdtest

Pose = fdtest.load("Shared.Rules.PanPose")
Math = fdtest.load("Shared.Rules.PanModelMath")
Pot = fdtest.load("Shared.Rules.PotModelMath")


def near(a, b, eps=1e-9):
    return abs(a - b) < eps


def nearAll(a, b, eps=1e-9):
    return all(near(x, y, eps) for x, y in zip(a, b)) and len(a) == len(b)


def testAnUntiltedPanLeavesPiecesWhereTheyAre():
    assert nearAll(Pose.inPan((8.0, 0.0, 8.0), (0.0, 0.0, 0.0), (2.6, 1.01, 0.4)), (10.6, 1.01, 8.4))
    assert nearAll(Pose.inPan((8.0, 1.2, 8.9), (0.0, 0.0, 0.0), (0.0, 1.01, 0.0)), (8.0, 2.21, 8.9)), "锅被拽起来，食物跟着"


def testTiltingThePanRaisesItsFarSide():
    far = Pose.inPan((8.0, 0.0, 8.0), (90.0, 0.0, 0.0), (0.0, 0.0, -5.0))
    assert nearAll(far, (8.0, 5.0, 8.0)), "绕 x 转正的角：远沿（-z，离镜头远）翘起来，和 HoD 的颠锅一致"
    near_ = Pose.inPan((8.0, 0.0, 8.0), (90.0, 0.0, 0.0), (0.0, 0.0, 5.0))
    assert nearAll(near_, (8.0, -5.0, 8.0)), "锅柄这一头往下"


def testPiecesTurnWithThePanAndWithTheirOwnAngles():
    flat = Pose.lying((0.0, 0.0, 0.0))
    assert nearAll(flat[1], (0.0, 0.0, -1.0)) and nearAll(flat[2], (0.0, 1.0, 0.0)), "没转的一块就是 Rx(90)：先躺平"
    tilted = Pose.lying((0.0, 0.0, 0.0), (11.0, 0.0, 0.0))
    assert tilted != flat, "锅转了，食物的矩阵也变"
    both = Pose.lying((90.0, 30.0, 0.0), (11.0, 0.0, 0.0))
    assert len(both) == 3 and all(len(row) == 3 for row in both)


def testTheEulerOrderIsYXZ():
    m = Pose.euler((90.0, 90.0, 0.0))
    # Ry(90)·Rx(90)：+z 先被 Rx 转到 -y，Ry 不动它；要是次序反了（Rx·Ry）会得到 +x
    assert nearAll(Pot.apply(m, (0.0, 0.0, 1.0)), (0.0, -1.0, 0.0))
    first = Pose.euler((90.0, 0.0, 0.0))
    assert nearAll(Pot.apply(first, (0.0, 1.0, 0.0)), (0.0, 0.0, 1.0)), "绕 x 转 90 度：+y 变 +z"
    assert nearAll(Pot.apply(Pose.euler((0.0, 90.0, 0.0)), (0.0, 0.0, 1.0)), (1.0, 0.0, 0.0)), "绕 y 转 90 度：+z 变 +x"


def testWorldMatrixTurnsByTheBlocksFacing():
    ident = Pot.IDENTITY
    for facing in (Pot.NORTH, Pot.EAST, Pot.SOUTH, Pot.WEST):
        world = Pose.toWorld(facing, ident)
        toward = Pot.apply(world, (0.0, 0.0, 1.0))         # 场景里朝镜头的方向 -> 锅柄朝的方向
        dx, dz = Math.handleSide(facing)
        assert nearAll((toward[0], toward[2]), (dx, dz), 1e-6), facing


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
