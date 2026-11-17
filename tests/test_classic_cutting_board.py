# -*- coding: utf-8 -*-
# runner: both
"""经典玩法的砧板（Server/CuttingBoard.py，没装场景交互前置 / 站点关了 / 潜行右键时走的）对 FD 的 CuttingBoardBlock.use 和 CuttingBoardBlockEntity，用假引擎驱动。

JE：板空着、没插工具时 canAddItem 对任何东西都成立（ItemStackHandler 什么都收），所以什么都能摆上去；板上有东西、放不上去的（别的东西、同一种但叠满了或数据不一样）
走 processStoredItemUsingTool：板上的东西没有切法提示 invalid_item，手里的工具不对提示 invalid_tool，对了切一件、提示 remaining_items；
空手取回：创造模式取回的东西不给玩家（java:68 的 if (!player.isCreative())）。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Board = fdtest.load("Server.CuttingBoard")

POS = (7, 64, 7)
TYPES = {"arris:iron_knife": "sword", "minecraft:iron_sword": "sword", "minecraft:iron_axe": "axe", "minecraft:cobblestone": "block"}
INVALID_ITEM, INVALID_TOOL, NOT_STORABLE = "这东西可不能切啊……", "或许得换个工具……", "这东西放不上砧板……"


def _item(name, count=1, **extra):
    return dict({"newItemName": name, "newAuxValue": 0, "count": count}, **extra)


def _install():
    """fakeengine 的物品信息一律是 food：板要问工具类型、方块类型，这里按名字补。"""
    base = world._Item

    def _Item(target):
        methods = dict(base(target))
        methods["GetItemBasicInfo"] = lambda name, aux=0: {"itemType": TYPES.get(name, "food"), "maxDurability": 0, "maxStackSize": world.maxStack.get(name, 64)}
        return methods

    world._Item = _Item


_install()


def _setUp(hand=None, creative=False, board=None):
    world.reset()
    data = skilletkit.EngineData()
    if board is not None:
        data["cuttingDict"] = dict(board)
    world.setBlock(POS[0], POS[1], POS[2], "arris:cutting_board", data=data)
    world.addPlayer("p1", hand=dict(hand) if hand else None, creative=creative)
    return data


def _use():
    world.runTimers()                         # 交互冷却的计时器（0.2 秒）：每次点击之间先过掉
    args = {"x": POS[0], "y": POS[1], "z": POS[2], "dimensionId": 0, "playerId": "p1", "cancel": False}
    Board.OnServerCuttingBoardBlockUse(args)
    return args


def _tips():
    return [text for target, endpoint, text in world.calls if endpoint == "ShowTip"]


def _hand():
    return world.players["p1"]["hand"]


# ---------------------------------------------------------------- 板空着：什么都能放

def testAnEmptyBoardTakesAnythingNotOnlyWhatCanBeCut():
    for name in ("minecraft:stick", "minecraft:bread", "minecraft:iron_sword", "minecraft:cobblestone", "arris:cabbage"):
        data = _setUp(hand=_item(name, 3))
        _use()
        assert data["cuttingDict"]["newItemName"] == name and data["cuttingDict"]["count"] == 3, name
        assert _hand() is None and _tips() == [], name


def testTheWholeStackGoesOntoTheBoardAndOnlyTheMaxStackFits():
    world.maxStack["minecraft:ender_pearl"] = 16
    data = _setUp(hand=_item("minecraft:ender_pearl", 20))
    _use()
    assert data["cuttingDict"]["count"] == 16 and _hand()["count"] == 4, "叠不过物品的最大堆叠，多的留在手里"
    data = _setUp(hand=_item("minecraft:stick", 10), board=_item("minecraft:stick", 60))
    _use()
    assert data["cuttingDict"]["count"] == 64 and _hand()["count"] == 6, "同一种接着叠，叠满为止"


def testCreativeKeepsTheStackInTheHandWhenPlacing():
    data = _setUp(hand=_item("minecraft:stick", 5), creative=True)
    _use()
    assert data["cuttingDict"]["count"] == 5 and _hand()["count"] == 5


def testWhatTheEngineCannotStoreWithTheItemIsRefusedWithATip():
    data = _setUp(hand=_item("minecraft:stick", 1, userData={"mixed": [1, "x"]}))
    _use()
    assert data["cuttingDict"] is None and _hand() is not None and _tips() == [NOT_STORABLE]


def testTheSkilletItemIsLeftToItsOwnPlacement():
    data = _setUp(hand=_item("arris:skillet_item", 1))
    _use()
    assert data["cuttingDict"] is None and _hand() is not None and _tips() == []


# ---------------------------------------------------------------- 板上有东西、放不上去：当作拿工具来切（processStoredItemUsingTool）

def testAFullStackOfWhatCanBeCutAsksForAnotherTool():
    data = _setUp(hand=_item("arris:cabbage", 1), board=_item("arris:cabbage", 64))
    _use()
    assert _tips() == [INVALID_TOOL] and data["cuttingDict"]["count"] == 64 and _hand()["count"] == 1, "叠满了的同一种：当作拿它去切自己，不是工具"


def testAFullStackOfWhatHasNoRecipeSaysItCannotBeCut():
    data = _setUp(hand=_item("minecraft:stick", 1), board=_item("minecraft:stick", 64))
    _use()
    assert _tips() == [INVALID_ITEM] and data["cuttingDict"]["count"] == 64


def testTheSameThingWithOtherDataDoesNotMergeAndGoesTheToolWay():
    data = _setUp(hand=_item("arris:cabbage", 1), board=_item("arris:cabbage", 3, extraId="marked"))
    _use()
    assert _tips() == [INVALID_TOOL] and data["cuttingDict"]["count"] == 3 and _hand()["count"] == 1, "JE 的 isSameItemSameTags 不叠，走切的那一支"


def testTheWrongToolAndTheThingNoRecipeTakesGetTheirTips():
    data = _setUp(hand=_item("minecraft:iron_axe", 1), board=_item("arris:cabbage", 2))
    _use()
    assert _tips() == [INVALID_TOOL] and data["cuttingDict"]["count"] == 2 and world.spawned == []
    data = _setUp(hand=_item("arris:iron_knife", 1), board=_item("minecraft:stick", 2))
    _use()
    assert _tips() == [INVALID_ITEM] and data["cuttingDict"]["count"] == 2 and world.spawned == []


def testTheRightToolCutsOneAndSaysHowManyAreLeft():
    data = _setUp(hand=_item("arris:iron_knife", 1), board=_item("arris:cabbage", 2))
    _use()
    assert world.spawnedNames() == [("arris:cabbage_leaf", 2)] and data["cuttingDict"]["count"] == 1 and _tips() == ["还剩1个……"]
    _use()
    assert world.spawnedNames() == [("arris:cabbage_leaf", 2)] * 2 and data["cuttingDict"] is None


# ---------------------------------------------------------------- 空手取回

def testAnEmptyHandTakesTheStackBackAndCreativeDoesNotGetIt():
    data = _setUp(board=_item("arris:cabbage", 5))
    _use()
    assert data["cuttingDict"] is None and _hand()["newItemName"] == "arris:cabbage" and _hand()["count"] == 5
    data = _setUp(board=_item("arris:cabbage", 5), creative=True)
    _use()
    assert data["cuttingDict"] is None and _hand() is None, "JE CuttingBoardBlock.java:68：创造模式取回的东西不给玩家"
    data = _setUp(creative=True)
    _use()
    assert data["cuttingDict"] is None and _hand() is None, "空板空手：什么也没有"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
