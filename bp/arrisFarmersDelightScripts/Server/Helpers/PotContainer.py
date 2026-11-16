# -*- coding: utf-8 -*-
"""PotContainer - 厨锅容器格与预览槽的读写：食材、出一份、加份数、装碗转出（服务端）

容器格：0-5 食材，6 容器（碗等），7 成品。煮好的成品先进方块实体数据里的预览槽 previewItemSlot，
容器格里有对应容器时再转到 7 号格（MoveFinishedMeals）。FD 原样的烹饪（Server/CookingPot.py）、
手工烹饪（Server/HandCooking.py）和厨锅站点（Compat/Diegesis/PotLogic.py）都经这里改锅里的东西。
"""
import random

from .Engine import compFactory, levelId, System
from ...Shared.Rules import CookingPot as CookingPotRules

INPUT_SLOTS = 6
VESSEL_SLOT = 6
RESULT_SLOT = 7


def maxStackOf(itemName, auxValue=0):
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(itemName, auxValue or 0)
    return (info or {}).get("maxStackSize") or 64


def inputs(dimensionId, blockPos):
    """6 个食材格（空格是 {}）。"""
    itemComp = compFactory.CreateItem(levelId)
    return [itemComp.GetContainerItem(blockPos, index, dimensionId) or {} for index in range(INPUT_SLOTS)]


def setInputs(dimensionId, blockPos, before, after):
    """把食材格从 before 改成 after，只写变了的格子。"""
    itemComp = compFactory.CreateItem(levelId)
    for index in range(INPUT_SLOTS):
        old, new = before[index] or {}, after[index] or {}
        if (old.get("newItemName"), old.get("newAuxValue"), old.get("count")) != \
                (new.get("newItemName"), new.get("newAuxValue"), new.get("count")):
            itemComp.SpawnItemToContainer(new if new.get("count", 0) > 0 else {}, index, blockPos, dimensionId)


def resultItem(dimensionId, blockPos):
    return compFactory.CreateItem(levelId).GetContainerItem(blockPos, RESULT_SLOT, dimensionId) or {}


def setResultItem(dimensionId, blockPos, item):
    compFactory.CreateItem(levelId).SpawnItemToContainer(item or {}, RESULT_SLOT, blockPos, dimensionId)


def preview(blockEntityData):
    """预览槽里煮好还没装碗的成品（{} 表示空）。"""
    previewList = blockEntityData["previewItemSlot"] or [{}]
    item = previewList[0] if previewList else {}
    return item if item and item.get("newItemName") and item.get("count", 0) > 0 else {}


def setPreview(blockEntityData, item):
    # 改了嵌套字典必须整体回写，否则区块卸载后恢复原值
    blockEntityData["previewItemSlot"] = [item] if item and item.get("count", 0) > 0 else [{}]


def addMeals(blockEntityData, meal, count):
    """预览槽加 count 份 meal（预览槽空着或已是同一道菜）。"""
    current = preview(blockEntityData)
    if current:
        current["count"] += count
        setPreview(blockEntityData, current)
    else:
        setPreview(blockEntityData, {"newItemName": meal["newItemName"], "newAuxValue": meal.get("newAuxValue", 0),
                                     "count": count})


def cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItemList, times=1):
    """煮出 times 份：每个非空食材格扣 times 件（slots 就地更新），吐出余料，预览槽加 times 份成品。"""
    x, y, z = blockPos
    for pushItem in pushItemList or []:
        output = {"newItemName": pushItem[0], "newAuxValue": pushItem[1], "count": times}
        System.CreateEngineItemEntity(output, dimensionId, (x + 0.5, y + 1.0, z + 0.5))
    itemComp = compFactory.CreateItem(levelId)
    for index, item in enumerate(slots):
        if not item:
            continue
        item["count"] -= times
        itemComp.SpawnItemToContainer(item if item["count"] > 0 else {}, index, blockPos, dimensionId)
        if item["count"] <= 0:
            slots[index] = {}
    addMeals(blockEntityData, meal, times * (meal.get("count") or 1))


def MoveFinishedMeals(blockEntityData, blockPos, dimensionId):
    """把预览槽里煮好的成品转到产出格；需要容器的成品同时消耗容器格里等量的容器。"""
    x, y, z = blockPos
    previewItemSlot = preview(blockEntityData)
    if not previewItemSlot:
        return
    resultItemName = previewItemSlot["newItemName"]
    resultAuxValue = previewItemSlot.get("newAuxValue", 0)
    recipeDict = CookingPotRules.findRecipeByResult(resultItemName)
    if recipeDict is None:
        return
    itemComp = compFactory.CreateItem(levelId)
    resultItemSlot = itemComp.GetContainerItem(blockPos, RESULT_SLOT, dimensionId)
    if resultItemSlot and resultItemSlot["newItemName"] != resultItemName:
        return
    resultCount = resultItemSlot["count"] if resultItemSlot else 0
    maxStackSize = maxStackOf(resultItemName, resultAuxValue)
    vessel = recipeDict.get("Vessel")
    vesselItemSlot = None
    if vessel:
        vesselItemSlot = itemComp.GetContainerItem(blockPos, VESSEL_SLOT, dimensionId)
        # 只比较物品名（与旧实现一致）
        if not vesselItemSlot or vesselItemSlot.get("newItemName") != vessel[0]:
            return
    amount = CookingPotRules.transferAmount(previewItemSlot["count"], resultCount, maxStackSize,
                                            vesselItemSlot["count"] if vesselItemSlot else None)
    if amount <= 0:
        return
    if vesselItemSlot:
        vesselItemSlot["count"] -= amount
        itemComp.SpawnItemToContainer(vesselItemSlot if vesselItemSlot["count"] > 0 else {}, VESSEL_SLOT, blockPos, dimensionId)
    resultDict = {"newItemName": resultItemName, "newAuxValue": resultAuxValue, "count": resultCount + amount, "enchantData": []}
    itemComp.SpawnItemToContainer(resultDict, RESULT_SLOT, blockPos, dimensionId)
    previewItemSlot["count"] -= amount
    setPreview(blockEntityData, previewItemSlot)
    dropExperience(resultItemName, amount, blockPos, dimensionId)


def dropExperience(resultItemName, count, blockPos, dimensionId):
    """盛出 count 个 resultItemName 给的经验（JE：每份按配方的 experience，零头按概率进一），锅上方一个经验球。"""
    x, y, z = blockPos
    value = CookingPotRules.experienceOrb(CookingPotRules.experienceOf(resultItemName), count, random.random())
    if value <= 0:
        return
    orbId = System.CreateEngineEntityByTypeStr("minecraft:xp_orb", (x + 0.5, y + 1, z + 0.5), (0, 0), dimensionId)
    if orbId:
        compFactory.CreateExp(orbId).SetOrbExperience(value)
