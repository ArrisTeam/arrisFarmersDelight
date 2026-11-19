# -*- coding: utf-8 -*-
# runner: both
"""客户端按方块实体数据重画砧板上的东西（Client/BlockItems._itemsFromExData / _layoutOf，区块重新加载、玩家刚进服时走这条）。

实机量到的（3.10，2026-11-19）：服务端把方块实体数据的一个键清成 None 之后，客户端读到的不是 None、也不是没有这个键，而是引擎的"空"记号
{"__type__": 1, "__value__": 2}（一个值为 2 的字节）；服务端自己读是 None。所以客户端这边：物品要过 BlockDisplay.isItem 才当物品，
插着的标记（isItemCarved）只认存进去的 1 / 0——不然取回过东西的空板一重新加载就报错，清掉的标记读成"插着"。
蘑菇丛按它那件只用来显示的平面物品画。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import panclient as C

import fdtest

world = C.install()
Items = C.load("Client.BlockItems")
BD = C.load("Shared.Rules.BlockDisplay")
Station = C.load("Shared.Rules.BoardStation")
POS = (3, 64, 3)
CLEARED = {"__type__": 1, "__value__": 2}          # 服务端清成 None 的键在客户端的样子


def _byte(value):
    return {"__type__": 3, "__value__": value}


def _stack(name, count=1):
    return {"newItemName": {"__type__": 8, "__value__": name}, "newAuxValue": _byte(0), "count": _byte(count)}


def _board(exData):
    world.blocks[POS] = ("arris:cutting_board", 0)
    items = Items._itemsFromExData(BD.KIND_BOARD, exData)
    return items, Items._layoutOf(BD.KIND_BOARD, items, POS)


def testAKeyTheServerClearedIsNeitherAnItemNorACarvedFlag():
    items, placements = _board({"cuttingDict": CLEARED, "isItemCarved": CLEARED, "dishDone": CLEARED, "dishLayers": CLEARED})
    assert placements == [], "空板：什么都不画，也不出错"
    assert Station.CARVED not in items, "清掉的标记不是插着，是不知道"


def testTheFlagIsReadOnlyAsTheOneOrZeroThatWasStored():
    knife = _stack("arris:iron_knife")              # 假引擎不报物品类型：用刀表里的刀，老办法的推断才认得它
    items, carved = _board({"cuttingDict": knife, "isItemCarved": _byte(1)})
    assert items[Station.CARVED] is True and [placement.flat for placement in carved] == [False], "标记 1：插着，竖着画"
    items, lying = _board({"cuttingDict": knife, "isItemCarved": _byte(0)})
    assert items[Station.CARVED] is False and [placement.flat for placement in lying] == [True], "标记 0：躺着"
    items, old = _board({"cuttingDict": knife})
    assert Station.CARVED not in items and [placement.flat for placement in old] == [False], "老存档没有这个键：照老办法推断（刀是插着的）"
    items, odd = _board({"cuttingDict": knife, "isItemCarved": CLEARED})
    assert Station.CARVED not in items, "空记号不当标记"


def testAColonyIsLaidOutAsItsFlatLookItem():
    items, placements = _board({"cuttingDict": _stack("arris:red_mushroom_colony", 3)})
    assert [placement.item["newItemName"] for placement in placements] == ["arris:red_mushroom_colony_look"] * 2 and all(placement.flat for placement in placements)
    assert items["0"]["newItemName"] == "arris:red_mushroom_colony", "记着的还是真物品，只是画的时候换"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
