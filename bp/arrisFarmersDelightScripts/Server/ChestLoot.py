# -*- coding: utf-8 -*-
"""ChestLoot - 战利品箱第一次被打开时，追加农夫乐事的物品（服务端）

照 JE 的 AddLootTableModifier：对 14 张原版箱子的战利品表，在原版掷出的东西之外再额外掷一次 FD 自己的表
（Shared/Data/ChestLoot.py）。原版的战利品表文件一个字不动：引擎在 OnContainerFillLoottableServerEvent 里把掷好的物品交给脚本，
置 dirty 并交回完整物品列表（引擎用交回的列表整体替换），所以这里在原列表后面接上追加的物品。
"""
from .EventRegistry import registerHandler
from ..Shared.Data.ChestLoot import CHEST_LOOT
from ..Shared.Rules.ChestLoot import rollTable, tableKey


def _tableKey(args):
    return tableKey(args["loottable"])


@registerHandler("OnContainerFillLoottableServerEvent", match=CHEST_LOOT, keyOf=_tableKey)
def OnChestFilled(args):
    extraItems = rollTable(_tableKey(args))
    if extraItems:
        itemList = args["itemList"]
        itemList.extend(extraItems)
        args["itemList"] = itemList
        args["dirty"] = True
