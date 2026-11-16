# -*- coding: utf-8 -*-
"""Items - 物品类型与刀具判断（服务端）"""
from .Engine import compFactory, levelId
from ...Shared.Data.Cutting import knifeList
from ...Shared.Data.Food import platePackagedFoodDict

KNIFE_TAG = "arris:knife"


def GetItemType(itemDict):
    """物品类型（"food" / "block" / "sword" ...）；盘装食物方块对应的物品按食物算；空物品、引擎不认识的物品
    （拆掉的附属包留在背包里的）返回 None——砧板空手借刀要对整个背包逐件问，不能因为一件不认识的就抛。"""
    if not itemDict:
        return None
    itemName = itemDict["newItemName"]
    if itemName in platePackagedFoodDict:
        return "food"
    return (compFactory.CreateItem(levelId).GetItemBasicInfo(itemName) or {}).get("itemType")


def IsKnife(itemName):
    """配置里显式登记的刀（knifeList，下游可追加），或带 arris:knife 物品标签的物品。"""
    if itemName in knifeList:
        return True
    itemTags = compFactory.CreateItem(levelId).GetItemTags(itemName)
    return KNIFE_TAG in (itemTags or [])
