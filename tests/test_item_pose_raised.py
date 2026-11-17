# -*- coding: utf-8 -*-
# runner: both
"""画成一张平面图的方块物品（花、树苗、野生作物）怎么摆才不浮：Shared/Rules/ItemPose.raisedShift。

实机（3.10.0.448891，2026-11-18）：胡萝卜（贴图物品）、虞美人、野生胡萝卜（物品类型 block，掉落物却是一张贴图）、原木并排做成客户端掉落物，
同一个轴心高度，竖着（rot (0, 90, 0)）、平躺（rot (90, 0, 0)）各一排，从侧面平视着量，缩放 1 和 2 各一次：
- 平躺：虞美人 / 野生胡萝卜的贴图平面比胡萝卜的高 0.20 格，缩放 1 和 2 都是 0.20（不跟缩放走）；
- 竖着：它们的底边比轴心高 0.044 格（缩放 1）、低 0.11 格（缩放 2）——轴心在离贴图底边 5/16 处（0.2 - 0.15625 x 缩放）；
- 平躺时贴图中心离轴心 0.09 格（缩放 1，贴图物品是 0.25）。
所以引擎画它是 T(0, 0.2, 0)·S·R 再画一张轴心在离底边 5/16 处的半格贴图；贴图物品是 S·R 再画轴心在底边中点的。
"""
from __future__ import print_function

import fdtest

Pose = fdtest.load("Shared.Rules.ItemPose")

LIFT = 3.2                 # 0.2 格（站点像素）
SPAN = 8.0                 # 缩放 1 时贴图边长
ROW = 2.5                  # 轴心离贴图底边：16 像素的贴图里从下往上第 5 行 = 5/16 x 8


def _engineCentre(pivot, matrix, scale):
    """引擎把这类物品的贴图中心画在哪（站点像素）：轴心 + 抬高 + R·(0, 贴图中心离轴心, 0)。"""
    reach = (SPAN / 2.0 - ROW) * scale
    return (pivot[0] + matrix[0][1] * reach, pivot[1] + LIFT + matrix[1][1] * reach, pivot[2] + matrix[2][1] * reach)


def _spritePivot(center, matrix, scale):
    """照贴图物品的规矩从中心算轴心（前置包的 PropMath.pivotFor、本包的 ItemPose.pivotFor 都是这个，单位换成站点像素）。"""
    half = SPAN / 2.0 * scale
    return (center[0] - matrix[0][1] * half, center[1] - matrix[1][1] * half, center[2] - matrix[2][1] * half)


def testTheConstantsAreTheMeasuredOnes():
    assert Pose.BLOCK_LIFT == LIFT and Pose.RAISED_PIVOT == ROW and Pose.ITEM_SPAN == SPAN
    assert abs(Pose.RAISED_PIVOT - 5.0 / 16.0 * Pose.ITEM_SPAN) < 1e-12, "离底边 5/16 个边长"


def testAfterTheShiftTheEngineDrawsTheSpriteExactlyWhereItWasWanted():
    """什么姿态、多大都一样：平躺朝各个方向、竖着、斜着。"""
    wanted = (8.0, 6.5, 8.0)
    poses = [Pose.flatMatrix(1.0, 0.0), Pose.flatMatrix(0.0, 1.0), Pose.flatMatrix(-0.6, 0.8), Pose.uprightMatrix(0.0, -1.0, 0.0),
             Pose.uprightMatrix(1.0, 0.0, 30.0), Pose.lyingMatrix(40.0, 10.0, -5.0)]
    for matrix in poses:
        for scale in (0.5, 1.0, 1.25, 2.0):
            shift = Pose.raisedShift(matrix, scale)
            reported = tuple(a + b for a, b in zip(wanted, shift))
            drawn = _engineCentre(_spritePivot(reported, matrix, scale), matrix, scale)
            assert all(abs(a - b) < 1e-9 for a, b in zip(drawn, wanted)), (matrix, scale, drawn)


def testLyingFlatItComesDownByTheLiftWhateverTheScaleAndSlidesAlongItsOwnUp():
    """平躺：贴图自己的上方向是水平的，所以高度只扣那段抬高（不跟缩放走），水平方向沿贴图的上方向挪 5/16 个边长（跟缩放走）。"""
    for scale in (1.0, 1.25, 2.0):
        matrix = Pose.flatMatrix(1.0, 0.0)
        shift = Pose.raisedShift(matrix, scale)
        assert abs(shift[1] + LIFT) < 1e-9, "不扣的话浮起 0.2 格"
        up = (matrix[0][1], matrix[2][1])
        assert abs(shift[0] - up[0] * ROW * scale) < 1e-9 and abs(shift[2] - up[1] * ROW * scale) < 1e-9
        assert abs((shift[0] ** 2 + shift[2] ** 2) ** 0.5 - ROW * scale) < 1e-9


def testUprightTheMeasuredBottomEdgesComeOut():
    """竖着量到的两个数：底边比轴心高 0.044 格（缩放 1）、低 0.11 格（缩放 2）。"""
    matrix = Pose.uprightMatrix(0.0, -1.0, 0.0)
    for scale, measured in ((1.0, 0.044), (2.0, -0.1125)):
        centre = _engineCentre((0.0, 0.0, 0.0), matrix, scale)
        bottom = (centre[1] - SPAN / 2.0 * scale) / 16.0
        assert abs(bottom - measured) < 0.004, (scale, bottom)


def testWithoutTheShiftItFloats():
    """照贴图物品的规矩直接摆（修之前）：平躺的整张浮在该在的面上 0.2 格。"""
    matrix = Pose.flatMatrix(1.0, 0.0)
    wanted = (8.0, 3.0, 8.0)
    drawn = _engineCentre(_spritePivot(wanted, matrix, 1.25), matrix, 1.25)
    assert abs(drawn[1] - wanted[1] - LIFT) < 1e-9


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
