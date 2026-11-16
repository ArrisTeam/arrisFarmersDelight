# -*- coding: utf-8 -*-
# runner: both
"""篮子吸掉落物的服务端接线（Server/Basket.py）用假引擎驱动（tests/fakeengine.py）。

规则本身（收集区、塞的次序、冷却长度）在 test_basket_rules.py；这里管接线：
事件那条路与轮询那条路都吸、红石锁住、满了不吸、吸一半把剩下的放回原处、两个篮子叠着只给一个、冷却、定时器只开一个。
"""
from __future__ import print_function

import sys

import fakeengine
import fdtest

world = fakeengine.install()
engineModule = sys.modules[fakeengine.ENGINE_MODULE]
world.loaded = {}               # GetEngineActor 的返回：实体 id -> {"dimensionId", "identifier"}
world.containers = {}           # (维度, 坐标) -> 27 格
world.powered = set()           # 被红石充能的 (维度, 坐标)
world.repeating = []            # AddRepeatedTimer 登记的 (秒, 函数)
engineModule.GetLoadedEntities = lambda: dict(world.loaded)

_baseItem, _baseGame = world._Item, world._Game


def _item(target):
    methods = _baseItem(target)

    def container(pos, dim):
        return world.containers.setdefault((dim, tuple(pos)), [None] * 27)

    def setSlot(itemDict, index, pos, dim):
        container(pos, dim)[index] = dict(itemDict) if itemDict and itemDict.get("count", 0) > 0 else None
        return True

    methods.update({
        "GetContainerItem": lambda pos, index, dim, getUserData=False: container(pos, dim)[index],
        "SpawnItemToContainer": setSlot,
        "GetDroppedItem": lambda entityId, getUserData=False: world.itemEntities.get(entityId),
        "GetItemBasicInfo": lambda name, aux=0: {"maxStackSize": 16 if name == "minecraft:egg" else 64},
    })
    return methods


def _game(target):
    methods = _baseGame(target)
    methods["AddRepeatedTimer"] = lambda seconds, func: world.repeating.append((seconds, func)) or ("timer", len(world.repeating))
    return methods


world._Item, world._Game = _item, _game
world._RedStone = lambda target: {"GetBlockPoweredState": lambda pos, dim: 2 if (dim, tuple(pos)) in world.powered else 0}

Registry = fdtest.load("Server.EventRegistry")
Basket = fdtest.load("Server.Basket")
Rules = fdtest.load("Shared.Rules.Basket")

BASKET = (10, 64, 10)
ONION = {"newItemName": "arris:onion", "newAuxValue": 0, "count": 5}


class _Clock(object):
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


clock = _Clock()
Basket.time = clock


def _setUp():
    Registry.clearAll()
    Registry.registerHandler("OnEntityInsideBlockServerEvent", match=Basket.basketList)(Basket.OnEntityInsideBasket)
    Registry.registerHandler("ClientLoadAddonsFinishServerEvent")(Basket.OnBasketPlayerJoin)
    for table in (world.entities, world.blocks, world.itemEntities, world.containers, world.loaded):
        table.clear()
    world.spawned[:] = []
    world.destroyed[:] = []
    world.repeating[:] = []
    world.powered.clear()
    del Basket._timer[:]
    Basket._gate = Rules.Gate()
    clock.now += 100.0
    world.setBlock(BASKET[0], BASKET[1], BASKET[2], "arris:basket")


def _drop(entityId, itemDict, foot=(10.5, 64.125, 10.5), listed=True):
    """放一个掉落物实体；listed 表示它出现在 GetEngineActor 里（轮询看得到）。"""
    world.addEntity(entityId, "minecraft:item", pos=foot)
    world.itemEntities[entityId] = dict(itemDict)
    if listed:
        world.loaded[entityId] = {"dimensionId": 0, "identifier": "minecraft:item"}


def _inside(entityId, pos=BASKET, blockName="arris:basket"):
    Registry.dispatch("OnEntityInsideBlockServerEvent",
                      {"entityId": entityId, "blockX": pos[0], "blockY": pos[1], "blockZ": pos[2], "blockName": blockName,
                       "cancel": False}, blockName)


def _slots(pos=BASKET):
    return world.containers.get((0, tuple(pos)), [None] * 27)


# ---- 事件那条路：掉落物进了篮子这一格 ----

def testItemInsideTheBasketGoesIntoSlotZeroAndTheEntityIsRemoved():
    _setUp()
    _drop("i1", ONION)
    _inside("i1")
    assert _slots()[0] == ONION and world.destroyed == ["i1"]


def testUserDataSurvivesTheTrip():
    _setUp()
    named = dict(ONION, userData={"display": {"Name": "x"}}, enchantData=[(1, 2)])
    _drop("i1", named)
    _inside("i1")
    assert _slots()[0]["userData"] == {"display": {"Name": "x"}} and _slots()[0]["enchantData"] == [(1, 2)]


def testSameKindIsMergedBeforeAnythingElse():
    _setUp()
    world.containers[(0, BASKET)] = [dict(ONION, count=62)] + [None] * 26
    _drop("i1", ONION)
    _inside("i1")
    assert _slots()[0]["count"] == 64 and _slots()[1]["count"] == 3 and world.destroyed == ["i1"]


def testOtherEntitiesAreIgnored():
    _setUp()
    world.addEntity("cow", "minecraft:cow", pos=(10.5, 64.0, 10.5))
    _inside("cow")
    assert _slots() == [None] * 27 and world.destroyed == []


def testWoodenBasketWorksTheSame():
    _setUp()
    world.setBlock(BASKET[0], BASKET[1], BASKET[2], "arris:wooden_basket")
    _drop("i1", ONION)
    Registry.dispatch("OnEntityInsideBlockServerEvent",
                      {"entityId": "i1", "blockX": 10, "blockY": 64, "blockZ": 10, "blockName": "arris:wooden_basket"},
                      "arris:wooden_basket")
    assert _slots()[0] == ONION


# ---- 冷却、红石、满了 ----

def testOnlyOneWholeItemPerEightTicks():
    _setUp()
    _drop("i1", ONION)
    _drop("i2", dict(ONION, count=2))
    _inside("i1")
    _inside("i2")                                   # 同一时刻：冷却中
    assert world.destroyed == ["i1"] and _slots()[0]["count"] == 5
    clock.now += 0.39
    _inside("i2")
    assert world.destroyed == ["i1"]
    clock.now += 0.02                               # 过了 0.4 秒
    _inside("i2")
    assert world.destroyed == ["i1", "i2"] and _slots()[0]["count"] == 7


def testRedstonePowerLocksTheBasket():
    _setUp()
    world.powered.add((0, BASKET))
    _drop("i1", ONION)
    _inside("i1")
    assert world.destroyed == [] and _slots() == [None] * 27
    world.powered.clear()
    clock.now += 0.1
    _inside("i1")
    assert world.destroyed == []                    # 重试间隔里：不会每刻都去读 27 格
    clock.now += 0.11
    _inside("i1")
    assert world.destroyed == ["i1"] and _slots()[0] == ONION


def testFullBasketTakesNothing():
    _setUp()
    world.containers[(0, BASKET)] = [dict(ONION, count=64) for _ in range(27)]
    _drop("i1", ONION)
    _inside("i1")
    assert world.destroyed == [] and world.spawned == []


def testPartlyFittingStackLeavesTheRestWhereItLay():
    _setUp()
    slots = [{"newItemName": "arris:rice", "newAuxValue": 0, "count": 64} for _ in range(27)]
    slots[7] = dict(ONION, count=54)                # 只有这一格还有 10 个的余地
    world.containers[(0, BASKET)] = slots
    _drop("i1", dict(ONION, count=25), foot=(10.4, 64.3, 10.6))
    _inside("i1")
    assert _slots()[7]["count"] == 64
    assert world.destroyed == ["i1"]
    assert world.spawned == [(dict(ONION, count=15), 0, (10.4, 64.3, 10.6))]     # 剩下 15 个在原处重新放一个


# ---- 轮询那条路：篮子上面那一格里的掉落物 ----

def test_pollTakesItemsFromTheBlockAboveToo():
    _setUp()
    _drop("i1", ONION, foot=(10.5, 65.2, 10.5))     # 上面那一格里，事件那条路看不到它
    Basket.poll()
    assert world.destroyed == ["i1"] and _slots()[0] == ONION


def test_pollIgnoresItemsOutsideTheCollectionArea():
    _setUp()
    _drop("beside", ONION, foot=(12.5, 64.2, 10.5))         # 隔了一格
    _drop("high", ONION, foot=(10.5, 66.4, 10.5))           # 离收集区上沿还有 0.4
    _drop("below", ONION, foot=(10.5, 63.2, 10.5))          # 篮子底下那格
    Basket.poll()
    assert world.destroyed == [] and _slots() == [None] * 27


def test_pollOnlyLooksAtLoadedItemEntities():
    _setUp()
    _drop("i1", ONION, foot=(10.5, 65.2, 10.5), listed=False)
    world.loaded["cow"] = {"dimensionId": 0, "identifier": "minecraft:cow"}
    world.addEntity("cow", "minecraft:cow", pos=(10.5, 65.2, 10.5))
    Basket.poll()
    assert world.destroyed == []


def test_pollGivesAnItemToOnlyOneOfTwoStackedBaskets():
    _setUp()
    world.setBlock(10, 65, 10, "arris:wooden_basket")        # 叠在上面的另一个篮子
    _drop("i1", ONION, foot=(10.5, 65.2, 10.5))              # 在上面那个篮子的身体里，也在下面那个篮子的收集区里
    Basket.poll()
    assert world.destroyed == ["i1"]
    inLower, inUpper = _slots(BASKET) != [None] * 27, _slots((10, 65, 10)) != [None] * 27
    assert inLower != inUpper                                # 只在其中一个里
    assert inUpper                                           # 自己那一格的篮子先吸（排在最前）


def test_pollTakesOneWholeItemPerBasketPerCooldown():
    _setUp()
    _drop("i1", ONION, foot=(10.5, 65.2, 10.5))
    _drop("i2", ONION, foot=(10.5, 65.4, 10.5))
    Basket.poll()
    assert len(world.destroyed) == 1 and _slots()[0]["count"] == 5
    clock.now += 0.4
    Basket.poll()
    assert len(world.destroyed) == 2 and _slots()[0]["count"] == 10


def test_pollSkipsLockedAndFullBaskets():
    _setUp()
    world.powered.add((0, BASKET))
    _drop("i1", ONION, foot=(10.5, 65.2, 10.5))
    Basket.poll()
    assert world.destroyed == []


# ---- 定时器 ----

def testTimerStartsOnceWhenAPlayerJoinsOrAnItemFallsIn():
    _setUp()
    Registry.dispatch("ClientLoadAddonsFinishServerEvent", {"playerId": "p1"})
    Registry.dispatch("ClientLoadAddonsFinishServerEvent", {"playerId": "p2"})
    assert len(world.repeating) == 1 and world.repeating[0][0] == Basket.POLL == 0.25
    _drop("i1", ONION)
    _inside("i1")
    assert len(world.repeating) == 1


def testLiveBasketListIsSharedWithTheData():
    Blocks = fdtest.load("Shared.Data.Blocks")
    assert Basket.basketList is Blocks.basketList
    assert Blocks.basketList == ["arris:basket", "arris:wooden_basket"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
