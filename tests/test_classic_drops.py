# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的砧板 / 煎锅把东西弹出去、散出来（Server/CuttingBoard.py、Server/Skillet.py、Server/HandFrying.py，Server/Helpers/Drops.py 把位置和初速交给引擎）对 FD，用假引擎驱动：

- 砧板切出一件（CuttingBoardBlockEntity.processStoredItemUsingTool:89-92）：从板的 FACING 逆时针那一边、离中心 0.2、离底 0.2 弹出去，初速 stepX * 0.2、0、stepZ * 0.2；
- 煎锅煎好一件（SkilletBlockEntity.cookAndOutputItems:102-105）：锅心上 0.3，往 FACING 顺时针那一边初速 stepX * 0.08、往上 0.25、stepZ * 0.08（HoD 的 jumpOut 同）；
- 锅里的东西泡在水里浮出来（SkilletBlockEntity.cookingTick:55 的 ItemUtils.dropItems）、拆了板 / 煎锅（CuttingBoardBlock.onRemove、SkilletBlock.onRemove 的
  Containers.dropItemStack）：一叠从方块里随机一点掉出来（x、z 在 0.125 .. 0.875，y 在 0 .. 0.75），一次 10..30 个，各带一点随机的初速，不是都落在方块中心。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Board = fdtest.load("Server.CuttingBoard")
Skillet = fdtest.load("Server.Skillet")
BoardDish = fdtest.load("Server.Helpers.BoardDish")
HandFrying = fdtest.load("Server.HandFrying")

POS = (7, 64, 7)
SOUTH, WEST, NORTH, EAST = 0, 1, 2, 3                 # netease:face_directional 的 direction 状态 = 方块的 aux
TYPES = {"arris:iron_knife": "sword"}
LIMIT = 0.11485000171139836


def _install():
    """fakeengine 的物品信息一律是 food：板要问工具类型，这里按名字补。"""
    base = world._Item

    def _Item(target):
        methods = dict(base(target))
        methods["GetItemBasicInfo"] = lambda name, aux=0: {"itemType": TYPES.get(name, "food"), "maxDurability": 0, "maxStackSize": world.maxStack.get(name, 64)}
        return methods

    world._Item = _Item


_install()


class _EveryStep(object):
    """每次都放行的节拍器（测试不靠真实时间）。"""

    def due(self, key, now):
        return True

    def forget(self, key):
        pass


def _item(name, count=1, **extra):
    return dict({"newItemName": name, "newAuxValue": 0, "count": count}, **extra)


def _pops():
    """生成的掉落物：[(物品, 位置, 初速)]，按生成的先后（初速是 SetMotion 给的，没给的是 None）。"""
    ids = sorted(world.itemEntities, key=lambda entityId: int(entityId[len("item"):]))
    return [(item, pos, world.motions.get(entityId)) for (item, _dimension, pos), entityId in zip(world.spawned, ids)]


def _inside(pos):
    """JE 的 Containers.dropItemStack 的落点：x、z 离方块边至少半个掉落物宽（0.125 .. 0.875），y 在 0 .. 0.75。"""
    x, y, z = (pos[0] - POS[0], pos[1] - POS[1], pos[2] - POS[2])
    return 0.125 <= x <= 0.875 and 0.0 <= y <= 0.75 and 0.125 <= z <= 0.875


def _scattered(name, count):
    """生成的掉落物是 count 个 name 的一叠散出来的样子：分成 10..30 一块（最后一块可以少）、落点只有一个、不在方块中心、各带三角分布的初速。"""
    pops = [pop for pop in _pops() if pop[0].get("newItemName") == name]
    assert sum(item["count"] for item, _pos, _motion in pops) == count and len(pops) >= 2, pops
    assert all(1 <= item["count"] <= 30 for item, _pos, _motion in pops) and all(item["count"] >= 10 for item, _pos, _motion in pops[:-1])
    assert len(set(pos for _item, pos, _motion in pops)) == 1 and _inside(pops[0][1]), pops[0][1]
    assert pops[0][1] != (POS[0] + 0.5, POS[1] + 0.5, POS[2] + 0.5), "不是都落在方块中心"
    for _item, _pos, motion in pops:
        assert motion is not None and abs(motion[0]) <= LIMIT and abs(motion[1] - 0.2) <= LIMIT and abs(motion[2]) <= LIMIT, motion
    return pops


# ---------------------------------------------------------------- 砧板

def _board(direction=SOUTH, stack=None, hand=None):
    world.reset()
    world.motions.clear()
    data = skilletkit.EngineData()
    if stack is not None:
        data["cuttingDict"] = dict(stack)
    world.setBlock(POS[0], POS[1], POS[2], "arris:cutting_board", data=data, aux=direction)
    world.addPlayer("p1", hand=dict(hand) if hand else None)
    return data


def _cut():
    world.runTimers()
    Board.OnServerCuttingBoardBlockUse({"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False})


def testACutPopsOutOfTheSideOfTheBoardNotStraightUp():
    # 玩家站在南边朝北放下板：direction 南，切出来的往东（板的 FACING 南的逆时针）；另三个朝向依次转
    expected = {SOUTH: (1, 0), WEST: (0, 1), NORTH: (-1, 0), EAST: (0, -1)}
    for direction, (dx, dz) in expected.items():
        _board(direction, stack=_item("arris:cabbage", 2), hand=_item("arris:iron_knife"))
        _cut()
        (item, pos, motion), = _pops()
        assert item["newItemName"] == "arris:cabbage_leaf" and item["count"] == 2, direction
        assert pos == (POS[0] + 0.5 + dx * 0.2, POS[1] + 0.2, POS[2] + 0.5 + dz * 0.2), (direction, pos)
        assert motion == (dx * 0.2, 0.0, dz * 0.2), (direction, motion)


def testEveryKindOfProductOfOneCutLeavesTheSameWay():
    _board(EAST, stack=_item("arris:cabbage", 3), hand=_item("arris:iron_knife"))
    _cut()
    _cut()
    pops = _pops()
    assert len(pops) == 2 and len(set((pos, motion) for _item, pos, motion in pops)) == 1, "两件各弹一回，位置和初速都一样（JE 的 spawnItemEntity 没有随机）"
    assert pops[0][2] == (0.0, 0.0, -0.2) and pops[0][1] == (POS[0] + 0.5, POS[1] + 0.2, POS[2] + 0.5 - 0.2), "朝东的板：往北"


def testBreakingTheBoardScattersWhatIsOnItInsideTheBlock():
    _board(SOUTH, stack=_item("minecraft:stick", 50))
    Board.OnCuttingBoardRemove({"x": POS[0], "y": POS[1], "z": POS[2], "dimension": 0, "fullName": "arris:cutting_board"})
    _scattered("minecraft:stick", 50)


def testBreakingABoardAlsoScattersTheDishBeingBuiltOnIt():
    """HoD 的 CuttingBoardBlockMixin：拆板时摆着的菜（层）也 Containers.dropContents，每叠各自随机一点。"""
    data = _board(SOUTH)
    data["dishLayers"] = [BoardDish.stack(_item("minecraft:bread", 1)), BoardDish.stack(_item("minecraft:carrot", 40))]
    Board.OnCuttingBoardRemove({"x": POS[0], "y": POS[1], "z": POS[2], "dimension": 0, "fullName": "arris:cutting_board"})
    assert [pop[0]["newItemName"] for pop in _pops() if pop[0]["count"] == 1] == ["minecraft:bread"]
    _scattered("minecraft:carrot", 40)
    assert all(_inside(pos) and pos != (POS[0] + 0.5, POS[1] + 0.5, POS[2] + 0.5) for _item, pos, _motion in _pops())
    assert data["dishLayers"] is None, "掉出来的不再留在板上"


def testBreakingABoardWithOneItemDropsItInsideTheBlockToo():
    _board(SOUTH, stack=_item("minecraft:stick", 1))
    Board.OnCuttingBoardRemove({"x": POS[0], "y": POS[1], "z": POS[2], "dimension": 0, "fullName": "arris:cutting_board"})
    (item, pos, motion), = _pops()
    assert item["newItemName"] == "minecraft:stick" and item["count"] == 1 and _inside(pos) and motion is not None


# ---------------------------------------------------------------- 煎锅

def _pan(direction=SOUTH, stack=None, heated=True, water=False):
    world.reset()
    world.motions.clear()
    HandFrying._hands.clear()
    Skillet._pacer = _EveryStep()
    data = skilletkit.EngineData(heatEnable=heated)
    if stack is not None:
        data["cookingDict"] = dict(stack)
    world.setBlock(POS[0], POS[1], POS[2], "arris:skillet", data=data, aux=direction)
    world.setBlock(POS[0], POS[1] - 1, POS[2], "minecraft:campfire")
    if water:
        world.water.add((0,) + POS)
    world.addPlayer("p1")
    return data


def _tick():
    Skillet.OnSkilletTick({"dimension": 0, "posX": POS[0], "posY": POS[1], "posZ": POS[2], "blockName": "arris:skillet"})


def _cookOne(limit=400):
    for _ in range(limit):
        _tick()
        if world.spawned:
            return
    raise AssertionError("没煎好")


def testACookedPieceJumpsOutOfThePanWithFarmersDelightsSpeed():
    # 玩家站在南边朝北放下煎锅：direction 南（锅柄朝南），煎好的往东（FD 的 FACING 北的顺时针）；另三个朝向依次转
    expected = {SOUTH: (1, 0), WEST: (0, 1), NORTH: (-1, 0), EAST: (0, -1)}
    for direction, (dx, dz) in expected.items():
        _pan(direction, stack=_item("minecraft:beef", 2))
        _cookOne()
        (item, pos, motion), = _pops()
        assert item["itemName"] == "minecraft:cooked_beef" and item["count"] == 1, direction
        assert pos == (POS[0] + 0.5, POS[1] + 0.3, POS[2] + 0.5), (direction, pos)
        assert motion == (dx * 0.08, 0.25, dz * 0.08), (direction, motion)


def testAStationsFinishedBatchWithNobodyAroundJumpsOutTheSameWay():
    """HoD 的 jumpOut：站点里没人时煎好的一批从锅里往侧面弹出去，和 FD 的煎锅一样。"""
    for direction, (dx, dz) in {SOUTH: (1, 0), WEST: (0, 1), NORTH: (-1, 0), EAST: (0, -1)}.items():
        _pan(direction)
        hand = HandFrying.PanHand()
        assert HandFrying._handOut(hand, 0, POS, _item("minecraft:cooked_beef", 3)) is False
        (item, pos, motion), = _pops()
        assert item["count"] == 3 and pos == (POS[0] + 0.5, POS[1] + 0.3, POS[2] + 0.5) and motion == (dx * 0.08, 0.25, dz * 0.08), direction


def testItemsFloatingOutOfAPanInWaterScatterInsideTheBlock():
    data = _pan(stack=_item("minecraft:beef", 50), water=True)
    _tick()
    assert data["cookingDict"] is None
    _scattered("minecraft:beef", 50)


def testBreakingAPanScattersItsFoodInsideTheBlock():
    _pan(stack=_item("minecraft:beef", 40))
    Skillet.OnSkilletRemove({"x": POS[0], "y": POS[1], "z": POS[2], "dimension": 0})
    _scattered("minecraft:beef", 40)


def testBreakingAnEmptyPanDropsNoFoodAndOnePieceStaysInsideTheBlock():
    _pan(stack=_item("minecraft:beef", 1))
    Skillet.OnSkilletRemove({"x": POS[0], "y": POS[1], "z": POS[2], "dimension": 0})
    foods = [pop for pop in _pops() if pop[0].get("newItemName") == "minecraft:beef"]
    assert len(foods) == 1 and foods[0][0]["count"] == 1 and _inside(foods[0][1]) and foods[0][2] is not None


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
