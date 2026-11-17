# -*- coding: utf-8 -*-
"""Items - 物品类型、刀具判断、叠不叠得起来（服务端）"""
from .Engine import compFactory, levelId
from ...Shared.Data.Cutting import knifeList
from ...Shared.Data.Food import platePackagedFoodDict
from ...Shared.Rules.HandsOn import ItemData

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


def GetMaxStack(itemDict):
    """这种物品一叠最多几个（引擎的 maxStackSize，问不到按 64）。"""
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(itemDict["newItemName"], itemDict.get("newAuxValue") or 0) or {}
    return max(1, info.get("maxStackSize") or 64)


def CanStack(a, b):
    """两件东西能叠在一起吗（JE 的 isSameItemSameTags）：名字、aux 一样，附魔、改名、userData 这些数据也一样（Shared/Rules/HandsOn/ItemData.same）。"""
    return a["newItemName"] == b["newItemName"] and (a.get("newAuxValue") or 0) == (b.get("newAuxValue") or 0) and ItemData.same(a, b)


def IsKnife(itemName):
    """配置里显式登记的刀（knifeList，下游可追加），或带 arris:knife 物品标签的物品。"""
    if itemName in knifeList:
        return True
    itemTags = compFactory.CreateItem(levelId).GetItemTags(itemName)
    return KNIFE_TAG in (itemTags or [])
