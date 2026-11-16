# -*- coding: utf-8 -*-
# runner: both
"""长榻榻米垫 / 短榻榻米垫的放置与拆除规则（Shared/Rules/TatamiMat.py，朝向换算在 Shared/Rules/Placement.py）。

JE 的 TatamiMatBlock（床一样的两格）：getStateForPlacement 用玩家面朝的方向，脚在点到的格子、头在面朝方向的下一格，
头那一格要能被顶替、两格下面都不是空气（canSurvive）；拆哪一半另一半都跟着没；脚下没了方块这一半碎掉。
"""
from __future__ import print_function

import fdtest

Placement = fdtest.load("Shared.Rules.Placement")
Mat = fdtest.load("Shared.Rules.TatamiMat")

STONE = "minecraft:stone"
AIR = "minecraft:air"
FLOOR_Y = 63


def _world(*solid):
    """只有 solid 里这些格子有方块（其余是空气）的小世界，返回 nameAt。"""
    cells = dict((pos, STONE) for pos in solid)

    def nameAt(pos):
        return cells.get(tuple(pos), AIR)
    nameAt.cells = cells
    return nameAt


def _floor(x0, x1, z0, z1):
    return [(x, FLOOR_Y, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)]


# ---- 朝向换算（Placement 里新增的那几个）----

def testFacingOfYawMatchesJavaDirectionFromYRot():
    # yaw：0 朝南、90 朝西、180 朝北、-90 朝东；每 90° 一档，档与档的分界在 45° 的奇数倍
    assert [Placement.facingOfYaw(y) for y in (0, 90, 180, -90, -180, 270, 360)] == [0, 1, 2, 3, 2, 3, 0]
    assert Placement.facingOfYaw(44.9) == 0 and Placement.facingOfYaw(45.1) == 1
    assert Placement.facingOfYaw(-44.9) == 0 and Placement.facingOfYaw(-45.1) == 3
    assert Placement.facingOfYaw(134.9) == 1 and Placement.facingOfYaw(135.1) == 2


def testDirectionIsTheOppositeOfTheLookDirection():
    # 官方文档：玩家放置时 north 贴图面向玩家，方块的面向 = 准心的反方向；表：south 0、west 1、north 2、east 3
    assert [Placement.directionOfFacing(f) for f in range(4)] == [2, 3, 0, 1]
    for facing in range(4):
        assert Placement.facingOfDirection(Placement.directionOfFacing(facing)) == facing


def testStepFacingWalksAlongTheHorizontalAxes():
    assert Placement.stepFacing((10, 64, 10), 0) == (10, 64, 11)       # 南 +z
    assert Placement.stepFacing((10, 64, 10), 1) == (9, 64, 10)        # 西 -x
    assert Placement.stepFacing((10, 64, 10), 2) == (10, 64, 9)        # 北 -z
    assert Placement.stepFacing((10, 64, 10), 3) == (11, 64, 10)       # 东 +x
    assert Placement.stepFacing((10, 64, 10), 3, -2) == (8, 64, 10)


# ---- 放长垫子 ----

def testHeadGoesWhereThePlayerIsLooking():
    # 点地面（脚下的方块顶面，face 1）：脚在点到方块上面一格，头在面朝的下一格，direction 是反方向
    nameAt = _world(*_floor(0, 10, 0, 10))
    expected = {0: ((5, 64, 5), (5, 64, 6), 2), 90: ((5, 64, 5), (4, 64, 5), 3),
                180: ((5, 64, 5), (5, 64, 4), 0), -90: ((5, 64, 5), (6, 64, 5), 1)}
    for yaw, plan in sorted(expected.items()):
        assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, yaw, nameAt) == plan, yaw


def testPlanKeepsHeadAndFootConsistentWithTheirDirection():
    nameAt = _world(*_floor(0, 10, 0, 10))
    for yaw in (0, 90, 180, -90, 30, 100, 200, 300):
        foot, head, direction = Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, yaw, nameAt)
        assert Mat.partnerPos(Mat.FOOT, foot, direction) == head
        assert Mat.partnerPos(Mat.HEAD, head, direction) == foot


def testClickingTheSideOfABlockPutsTheFootBesideIt():
    # 点方块侧面（face 3 = 南面）：脚在南边那一格；那一格和头的下面都要有方块
    nameAt = _world(*(_floor(0, 10, 0, 10) + [(5, 64, 5)]))
    plan = Mat.placementPlan((5, 64, 5), 3, STONE, 90, nameAt)
    assert plan == ((5, 64, 6), (4, 64, 6), 3)


def testNeedsGroundUnderBothHalves():
    # 头那一格下面是空气：JE 的 canSurvive 不过，整个放不下
    nameAt = _world(*_floor(0, 10, 0, 5))                 # 只有 z <= 5 有地面
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 0, nameAt) is None       # 头在 z=6，下面是空气
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 180, nameAt) is not None
    # 脚那一格下面是空气：点方块侧面放到悬空的格子
    nameAt = _world((5, 64, 5), (5, 64, 4))
    assert Mat.placementPlan((5, 64, 5), 3, STONE, 180, nameAt) is None


def testHeadCellMustBeReplaceable():
    nameAt = _world(*_floor(0, 10, 0, 10))
    nameAt.cells[(5, 64, 6)] = STONE                       # 头的位置被占了
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 0, nameAt) is None
    nameAt.cells[(5, 64, 6)] = "minecraft:short_grass"     # 草可以被顶替
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 0, nameAt) == ((5, 64, 5), (5, 64, 6), 2)
    nameAt.cells[(5, 64, 6)] = "minecraft:oak_fence"       # 栅栏不行
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 0, nameAt) is None


def testClickingAReplaceablePlantPlacesIntoItsCell():
    # JE：点到的方块能被顶替时脚就放在它那一格，不是它旁边
    nameAt = _world(*_floor(0, 10, 0, 10))
    nameAt.cells[(5, 64, 5)] = "minecraft:tall_grass"
    assert Mat.placementPlan((5, 64, 5), 1, "minecraft:tall_grass", 0, nameAt) == ((5, 64, 5), (5, 64, 6), 2)


def testUnloadedCellsStopThePlacement():
    # 没加载的格子（nameAt 给 None）既不能当头的位置，也不能当地面
    nameAt = _world(*_floor(0, 10, 0, 10))
    real = nameAt

    def partlyUnloaded(pos):
        return None if tuple(pos) == (5, 64, 6) else real(pos)
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 0, partlyUnloaded) is None

    def groundUnloaded(pos):
        return None if tuple(pos) == (5, FLOOR_Y, 6) else real(pos)
    assert Mat.placementPlan((5, FLOOR_Y, 5), 1, STONE, 0, groundUnloaded) is None


def testReplaceableTable():
    for name in (AIR, "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:vine", "minecraft:water"):
        assert Mat.isReplaceable(name), name
    for name in (STONE, "minecraft:snow_layer", "minecraft:oak_fence", Mat.FOOT, Mat.HEAD, Mat.HALF, None):
        assert not Mat.isReplaceable(name), name
    assert Mat.hasGround("minecraft:water") and Mat.hasGround(STONE)
    assert not Mat.hasGround(AIR) and not Mat.hasGround(None)


# ---- 短垫子 ----

def testHalfMatNeedsGroundUnderItsCell():
    nameAt = _world(*_floor(0, 10, 0, 10))
    assert Mat.halfMatPlaceable((5, FLOOR_Y, 5), 1, STONE, nameAt)                  # 放在地面上
    nameAt = _world((5, 64, 5))
    assert not Mat.halfMatPlaceable((5, 64, 5), 3, STONE, nameAt)                   # 点侧面放到悬空的格子
    nameAt = _world(*_floor(0, 10, 0, 10))
    nameAt.cells[(5, 64, 5)] = "minecraft:short_grass"
    assert Mat.halfMatPlaceable((5, 64, 5), 1, "minecraft:short_grass", nameAt)     # 点草：放进草那一格，下面有地


# ---- 邻居变化 ----

def testSupportLostOnlyWhenTheBlockBelowBecomesAir():
    pos = (5, 64, 5)
    assert Mat.supportLost(pos, (5, 63, 5), AIR)
    assert not Mat.supportLost(pos, (5, 63, 5), STONE)               # 换成别的方块
    assert not Mat.supportLost(pos, (5, 63, 5), "minecraft:water")   # 水不算空（isEmptyBlock 只认空气）
    assert not Mat.supportLost(pos, (6, 64, 5), AIR)                 # 不是脚下那一格
    assert not Mat.supportLost(pos, (5, 65, 5), AIR)


def testPartnerLostWhenTheOtherHalfCellIsNoLongerTheOtherHalf():
    for direction in range(4):
        foot = (5, 64, 5)
        head = Mat.partnerPos(Mat.FOOT, foot, direction)
        assert Mat.isSideNeighbor(foot, head) and Mat.isSideNeighbor(head, foot)
        assert Mat.partnerLost(Mat.FOOT, foot, direction, head, AIR)
        assert Mat.partnerLost(Mat.FOOT, foot, direction, head, STONE)
        assert not Mat.partnerLost(Mat.FOOT, foot, direction, head, Mat.HEAD)       # 头放上来了
        assert Mat.partnerLost(Mat.HEAD, head, direction, foot, AIR)
        assert not Mat.partnerLost(Mat.HEAD, head, direction, foot, Mat.FOOT)
        # 别的邻居变化与另一半无关
        other = Mat.stepFacing(foot, (Placement.facingOfDirection(direction) + 1) & 3)
        assert not Mat.partnerLost(Mat.FOOT, foot, direction, other, AIR)
        # 短垫子没有另一半
        assert not Mat.partnerLost(Mat.HALF, foot, direction, head, AIR)


def testSideNeighborIsOnlyTheFourHorizontalCells():
    pos = (5, 64, 5)
    assert [Mat.isSideNeighbor(pos, other) for other in ((6, 64, 5), (4, 64, 5), (5, 64, 6), (5, 64, 4))] == [True] * 4
    assert not any(Mat.isSideNeighbor(pos, other) for other in ((5, 65, 5), (5, 63, 5), (6, 64, 6), (5, 64, 5), (7, 64, 5)))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
