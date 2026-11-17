# -*- coding: utf-8 -*-
# runner: both
"""厨锅模型的坐标换算（Shared/Rules/PotModelMath.py）：方块朝向、勺子骨骼的位移和欧拉角。

骨骼 rotation 在 JE 坐标里是 Q = Rz(rz)·Ry(-ry)·Rx(-rx)（Strata 知识库 GEOMETRY_ENGINE.md §5，实机核对过靠着的勺子朝 +x 歪）。
"""
from __future__ import print_function

import math

import fdtest

Math = fdtest.load("Shared.Rules.PotModelMath")


def _rotX(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _rotY(degrees):
    c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _fromBone(rotation):
    """骨骼的 rotation（度）-> JE 坐标里的矩阵。"""
    rx, ry, rz = rotation
    return Math.multiply(Math.multiply(Math.rotZ(rz), _rotY(-ry)), _rotX(-rx))


def _close(a, b, eps=1.0e-6):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def testFacingFollowsTheBlockAux():
    assert [Math.facingOf(aux) for aux in (0, 1, 2, 3)] == ["south", "west", "north", "east"]
    assert [Math.facingOf(aux) for aux in (4, 8, 12)] == ["west", "north", "east"], "假日创造者实验玩法下 direction 1 / 2 / 3 的 aux 是 4 / 8 / 12"
    assert Math.facingOf(None) == "south" and Math.facingOf(6) == "south", "读不到、别的值按 0 朝南（Placement.directionOfAux；原来只取低两位，8 读成朝南、6 读成朝北）"


def testLocalAndWorldOffsetsAreInverse():
    for facing in ("north", "east", "south", "west"):
        wx, wz = Math.localToWorld(facing, 3.0, -2.0)
        assert Math.worldToLocal(facing, wx, wz) == (3.0, -2.0), facing
    assert Math.localToWorld("north", 1.0, 0.0) == (1.0, 0.0)
    assert Math.localToWorld("south", 1.0, 0.0) == (-1.0, 0.0), "朝南的锅整个转了半圈"
    assert Math.localToWorld("east", 0.0, -1.0) == (1.0, 0.0), "朝东：模型正面（-z）朝世界 +x"
    assert Math.localToWorld("west", 0.0, -1.0) == (-1.0, 0.0)


def testTheRestingLadleLeansTowardsPlusX():
    position, rotation = Math.ladleBone(Math.LADLE_PIVOT)
    assert _close(position, (0.0, 0.0, 0.0)) and _close(rotation, (0.0, 0.0, -22.5))
    handle = Math.apply(_fromBone(rotation), (0.0, 1.0, 0.0))
    assert handle[0] > 0.38 and abs(handle[2]) < 1.0e-9, "JE：柄朝 +x 歪 22.5 度"


def testAnyTurnRoundTripsThroughTheBoneAngles():
    for turn in (_rotX(20.0), _rotY(-35.0), Math.multiply(_rotX(7.0), _rotY(140.0)), Math.multiply(Math.rotZ(15.0), _rotX(-6.0))):
        _, rotation = Math.ladleBone(Math.LADLE_PIVOT, turn)
        want = Math.multiply(turn, Math.rotZ(Math.LADLE_REST))
        got = _fromBone(rotation)
        assert all(_close(got[row], want[row]) for row in range(3)), rotation


def testTheBonePositionMirrorsX():
    position, _ = Math.ladleBone((10.0, 4.5, 6.0))
    assert _close(position, (-2.0, 1.5, -2.0)), "几何文件的 x 和 JE 反着"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
