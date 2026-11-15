# -*- coding: utf-8 -*-
"""Items - 物品类型与刀具判断（服务端）"""
from .Engine import compFactory, levelId
from ...Shared.Data.Cutting import knifeList
from ...Shared.Data.Food import platePackagedFoodDict

KNIFE_TAG = "arris:knife"


def GetItemType(itemDict):
    """物品类型（"food" / "block" / "sword" ...）；盘装食物方块对应的物品按食物算；空物品返回 None。"""
    if not itemDict:
        return None
    itemName = itemDict["newItemName"]
    if itemName in platePackagedFoodDict:
        return "food"
    return compFactory.CreateItem(levelId).GetItemBasicInfo(itemName)["itemType"]


def IsKnife(itemName):
    """配置里显式登记的刀（knifeList，下游可追加），或带 arris:knife 物品标签的物品。"""
    if itemName in knifeList:
        return True
    itemTags = compFactory.CreateItem(levelId).GetItemTags(itemName)
    return KNIFE_TAG in (itemTags or [])
