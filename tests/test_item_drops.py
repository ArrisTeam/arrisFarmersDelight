# -*- coding: utf-8 -*-
# runner: both
"""东西从方块里掉出来 / 弹出去（Shared/Rules/ItemDrops.py 的位置和初速，Server/Helpers/Drops.py 把它们交给引擎）对 JE：
Containers.dropItemStack（ItemUtils.dropItems 对炉灶的每个烤位调它）：x、z 在 0.125 .. 0.875，y 在 0 .. 0.75，一次掉 10..30 个，初速三角分布（横向 0、竖直 0.2，偏差 0.11485）；
FD 的 ItemUtils.spawnItemEntity 烤好弹出：横向高斯乘 0.01、往上 0.1。
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
