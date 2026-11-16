# -*- coding: utf-8 -*-
"""BoardTools - 砧板站点用的工具与物品：找刀、扣耐久、按堆叠发产物（服务端）

从 BoardLogic.py 拆出来（它要放摆盘的入口，超了 250 行）。
"""
import copy

from ...Server.Helpers.Engine import compFactory, levelId, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Items import GetItemType, IsKnife
from ...Server.Helpers.Player import GiveOrDropItem
from ...Shared.Rules import CuttingStation as Rules


def findTool(playerId, recipe):
    """按主手、副手、背包的顺序找第一件合适的工具：((格子类型, 下标), 物品) 或 None。"""
    itemComp = compFactory.CreateItem(playerId)
    candidates = [((ItemPosType.CARRIED, 0), itemComp.GetPlayerItem(ItemPosType.CARRIED, 0, True)),
                  ((ItemPosType.OFFHAND, 0), itemComp.GetPlayerItem(ItemPosType.OFFHAND, 0, True))]
    for slot, item in enumerate(itemComp.GetPlayerAllItems(ItemPosType.INVENTORY, True) or []):
        candidates.append(((ItemPosType.INVENTORY, slot), item))
    return Rules.pickTool(candidates, recipe, IsKnife, GetItemType)


def wearTool(playerId, dimensionId, pos, where, toolItem, uses):
    """每切一件磨损一次；用坏了播放破碎声并清掉那一格（创造模式与不会损坏的工具由调用方排除）。"""
    tool = copy.deepcopy(toolItem)
    tool["durability"] -= uses
    broken = tool["durability"] <= 0
    if broken:
        ToAllPlayerPlaySound(dimensionId, pos, "random.break")
    posType, slot = where
    itemComp = compFactory.CreateItem(playerId)
    if posType == ItemPosType.INVENTORY:
        if broken:
            itemComp.SetInvItemNum(slot, 0)
        else:
            itemComp.SetPlayerAllItems({(posType, slot): tool})
    else:
        itemComp.SetEntityItem(posType, None if broken else tool, 0)


def give(playerId, dimensionId, name, aux, count):
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, aux) or {}
    for size in Rules.stacks(count, info.get("maxStackSize") or 64):
        GiveOrDropItem(playerId, {"newItemName": name, "newAuxValue": aux, "count": size}, dimensionId)
