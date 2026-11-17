# -*- coding: utf-8 -*-
# runner: both
"""东西从方块里掉出来 / 弹出去（Shared/Rules/ItemDrops.py 的位置和初速，Server/Helpers/Drops.py 把它们交给引擎）对 JE：
Containers.dropItemStack（ItemUtils.dropItems 对炉灶的每个烤位调它）：x、z 在 0.125 .. 0.875，y 在 0 .. 0.75，一次掉 10..30 个，初速三角分布（横向 0、竖直 0.2，偏差 0.11485）；
FD 的 ItemUtils.spawnItemEntity 烤好弹出：横向高斯乘 0.01、往上 0.1；砧板切出一件（CuttingBoardBlockEntity.java:89-92）：从板的 FACING 逆时针那一边、离中心 0.2、离底 0.2 弹出，
初速 stepX * 0.2、0、stepZ * 0.2；煎锅煎好一件（SkilletBlockEntity.java:102-105）：从锅心上 0.3、FACING 顺时针那一边，初速 stepX * 0.08、0.25、stepZ * 0.08。
"""
from __future__ import print_function

import random

import fdtest
import potfake

fake = potfake.install()
Drops = potfake.load("Server.Helpers.Drops")
Rules = fdtest.load("Shared.Rules.ItemDrops")
LIMIT = 0.11485000171139836


class _Rand(object):
    """每个函数按给的数列吐值的假随机数：random() 一个个吐，randint 取下限，gauss 吐 1。"""

    def __init__(self, values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)

    def randint(self, low, high):
        return low

    def gauss(self, mu, sigma):
        return mu + sigma


def testTriangleStaysWithinTheDeviationAroundItsMode():
    assert Rules.triangle(0.2, 0.1, _Rand([1.0, 0.0])) == 0.2 + 0.1
    assert Rules.triangle(0.2, 0.1, _Rand([0.0, 1.0])) == 0.2 - 0.1
    assert Rules.triangle(0.2, 0.1, _Rand([0.4, 0.4])) == 0.2


def testAStackIsDroppedFromOnePointInsideTheBlockInChunksOfTenToThirty():
    rand = random.Random(7)
    for count in (1, 9, 10, 31, 64, 200):
        drops = Rules.scatter(count, rand)
        assert sum(amount for amount, _at, _motion in drops) == count, count
        assert all(1 <= amount <= 30 for amount, _at, _motion in drops), count
        assert all(amount >= 10 for amount, _at, _motion in drops[:-1]), "除了最后一块，每块 10 个以上"
        assert len(set(at for _amount, at, _motion in drops)) == 1, "一叠的位置只掷一次"
        x, y, z = drops[0][1]
        assert 0.125 <= x <= 0.875 and 0.0 <= y <= 0.75 and 0.125 <= z <= 0.875, (count, drops[0][1])
        for _amount, _at, motion in drops:
            assert abs(motion[0]) <= LIMIT and abs(motion[1] - 0.2) <= LIMIT and abs(motion[2]) <= LIMIT, motion
    assert Rules.scatter(0, rand) == [] and Rules.scatter(-3, rand) == []


def testTheCornersOfThePositionRangeAreJavasNotTheWholeBlock():
    low = Rules.scatter(1, _Rand([0.0, 0.0, 0.0] + [0.5] * 6))[0][1]
    high = Rules.scatter(1, _Rand([1.0, 1.0, 1.0] + [0.5] * 6))[0][1]
    assert low == (0.125, 0.0, 0.125) and high == (0.875, 0.75, 0.875)


def testAPoppedItemRisesAtATenthWithAGaussianSidewaysSpeedOfAHundredth():
    assert Rules.popMotion(_Rand([])) == (0.01, 0.1, 0.01)        # 假随机数的 gauss 吐 1
    for _ in range(200):
        x, y, z = Rules.popMotion(random)
        assert y == 0.1 and abs(x) < 0.1 and abs(z) < 0.1


# ---- 砧板切出来 / 煎锅煎好：往方块侧面弹，朝哪边看方块的朝向 ----

CLOCKWISE = {"north": "east", "east": "south", "south": "west", "west": "north"}          # Direction.getClockWise
COUNTER = dict((after, before) for before, after in CLOCKWISE.items())                    # Direction.getCounterClockWise
STEP = {"north": (0, -1), "east": (1, 0), "south": (0, 1), "west": (-1, 0)}               # (getStepX, getStepZ)
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
STATE = {0: "south", 1: "west", 2: "north", 3: "east"}                                    # netease:face_directional 的 direction 状态


def _javaBoardSide(direction):
    """JE 砧板的 FACING = context.getHorizontalDirection().getOpposite()，朝着放它的玩家 = direction 状态；弹向 FACING.getCounterClockWise()。"""
    return STEP[COUNTER[STATE[direction]]]


def _javaPanSide(direction):
    """JE 煎锅的 FACING = context.getHorizontalDirection()（玩家面朝的方向），锅柄朝着玩家 = direction 状态，所以 FACING 是它的反方向；弹向 FACING.getClockWise()。"""
    return STEP[CLOCKWISE[OPPOSITE[STATE[direction]]]]


def testTheBoardPopsWhatItCutToTheCounterClockwiseSideOfItsFacing():
    for direction in range(4):
        dx, dz = _javaBoardSide(direction)
        at, motion = Rules.boardPop(direction)
        assert at == (0.5 + dx * 0.2, 0.2, 0.5 + dz * 0.2), (direction, at)
        assert motion == (dx * 0.2, 0.0, dz * 0.2), (direction, motion)
    assert [Rules.boardPop(direction)[1][::2] for direction in range(4)] == [(0.2, 0.0), (0.0, 0.2), (-0.2, 0.0), (0.0, -0.2)],         "玩家站在南边朝北放下的板（direction 南）：切出来的往东，也就是玩家的右手边"


def testThePanPopsWhatItCookedUpAndToTheSideOfItsFacingClockwise():
    for direction in range(4):
        dx, dz = _javaPanSide(direction)
        at, motion = Rules.panPop(direction)
        assert at == (0.5, 0.3, 0.5), (direction, at)
        assert motion == (dx * 0.08, 0.25, dz * 0.08), (direction, motion)


def testTheBoardAndThePanThrowToTheSameHandSideForTheSamePlayerPosition():
    """同一位玩家站在锅 / 板的同一侧放下它们（两个方块的 direction 状态一样），切出来的和煎好的往同一边弹。"""
    for direction in range(4):
        assert _javaBoardSide(direction) == _javaPanSide(direction), direction


def testTheEngineGetsTheItemAtThePositionAndTheMotionAfterwards():
    fake.reset()
    entityId = Drops.PopItem(0, (1.5, 2.5, 3.5), {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}, (0.0, 0.1, 0.0))
    assert fake.spawned == [({"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}, 0, (1.5, 2.5, 3.5))]
    assert fake.motions == {entityId: (0.0, 0.1, 0.0)}


def testNoMotionIsSetWhenTheEngineCreatedNoItem():
    fake.reset()
    original = Drops.System.CreateEngineItemEntity
    Drops.System.CreateEngineItemEntity = classmethod(lambda cls, item, dimension, pos: None)
    try:
        assert Drops.PopItem(0, (1.5, 2.5, 3.5), {"newItemName": "minecraft:beef", "count": 1}, (0.0, 0.1, 0.0)) is None
    finally:
        Drops.System.CreateEngineItemEntity = original
    assert fake.motions == {}


def testPoppingFromTheBoardAndThePanReadsTheBlocksDirectionAndPlacesTheItemBesideItOrAboveIt():
    for direction in range(4):
        fake.reset()
        fake.blockAux[(0, (10, 64, 10))] = direction
        item = {"newItemName": "arris:cabbage_leaf", "newAuxValue": 0, "count": 2}
        boardId = Drops.PopFromBoard(0, (10, 64, 10), item)
        panId = Drops.PopFromPan(0, (10, 64, 10), item)
        (_i, _d, boardAt), (_j, _e, panAt) = fake.spawned
        dx, dz = _javaBoardSide(direction)
        assert boardAt == (10.5 + dx * 0.2, 64.2, 10.5 + dz * 0.2) and fake.motions[boardId] == (dx * 0.2, 0.0, dz * 0.2), direction
        assert panAt == (10.5, 64.3, 10.5) and fake.motions[panId] == (dx * 0.08, 0.25, dz * 0.08), direction


def testTheHolidayCreatorsAuxOfADirectionIsReadToo():
    """假日创造者实验玩法下 direction 1 / 2 / 3 的 aux 是 4 / 8 / 12：弹的方向照样对（读 aux 走 Placement.directionOfAux）。"""
    for direction, aux in ((1, 4), (2, 8), (3, 12)):
        fake.reset()
        fake.blockAux[(0, (10, 64, 10))] = aux
        Drops.PopFromBoard(0, (10, 64, 10), {"newItemName": "arris:cabbage_leaf", "newAuxValue": 0, "count": 1})
        dx, dz = _javaBoardSide(direction)
        assert list(fake.motions.values()) == [(dx * 0.2, 0.0, dz * 0.2)], direction


def testScatterItemSplitsBigStacksIntoChunksAndKeepsTheirOtherKeys():
    fake.reset()
    item = {"newItemName": "minecraft:bread", "newAuxValue": 0, "count": 50, "extraId": "marked"}
    Drops.ScatterItem(0, (10, 64, 10), item)
    assert sum(spawned["count"] for spawned, _dim, _pos in fake.spawned) == 50 and len(fake.spawned) >= 2
    assert all(spawned["extraId"] == "marked" and spawned["newItemName"] == "minecraft:bread" for spawned, _dim, _pos in fake.spawned)
    assert len(set(pos for _item, _dim, pos in fake.spawned)) == 1 and len(fake.motions) == len(fake.spawned)
    assert item["count"] == 50, "传进来的那件不被改"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
