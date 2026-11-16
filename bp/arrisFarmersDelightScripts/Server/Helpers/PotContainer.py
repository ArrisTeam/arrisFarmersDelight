# -*- coding: utf-8 -*-
"""PotContainer - 厨锅容器格与预览槽的读写：食材、出一份、加份数、装碗转出、记煮了几份给经验（服务端）

容器格：0-5 食材，6 容器（碗等），7 成品。煮好的成品先进方块实体数据里的预览槽 previewItemSlot，
容器格里有对应容器时再转到 7 号格（MoveFinishedMeals）。FD 原样的烹饪（Server/CookingPot.py）、
手工烹饪（Server/HandCooking.py）和厨锅站点（Compat/Diegesis/PotLogic.py）都经这里改锅里的东西。
煮了几份记在方块实体数据 potUsed（{成品名: 份数}，随锅存档，FD 的 usedRecipeTracker）：盛出时按它给经验（awardExperience）。
"""
import random

from .Engine import compFactory, levelId, System
from ...Shared.Rules import CookingPot as CookingPotRules

INPUT_SLOTS = 6
VESSEL_SLOT = 6
RESULT_SLOT = 7
USED_KEY = "potUsed"


_maxStacks = {}      # (物品名, aux) -> 堆叠上限：运行中不会变，锅每步都要问


def maxStackOf(itemName, auxValue=0):
    key = (itemName, auxValue or 0)
    if key not in _maxStacks:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(itemName, key[1])
        _maxStacks[key] = (info or {}).get("maxStackSize") or 64
    return _maxStacks[key]


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


def spill(dimensionId, blockPos, item):
    """用料剩下的空容器掉在锅上方（FD 的 ejectIngredientRemainder：厨师不在场、没人接时）。"""
    x, y, z = blockPos
    System.CreateEngineItemEntity(item, dimensionId, (x + 0.5, y + 1.0, z + 0.5))


def cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItemList, times=1, sink=None):
    """煮出 times 份：每个非空食材格扣 times 件（slots 就地更新），吐出余料，预览槽加 times 份成品，记下煮了 times 份。
    sink(物品) 返回真表示余料有人接了（厨师在工位时交给他）；没人接就 spill 掉在锅上方。"""
    for pushItem in pushItemList or []:
        output = {"newItemName": pushItem[0], "newAuxValue": pushItem[1], "count": times}
        if sink is None or not sink(output):
            spill(dimensionId, blockPos, output)
    itemComp = compFactory.CreateItem(levelId)
    for index, item in enumerate(slots):
        if not item:
            continue
        item["count"] -= times
        itemComp.SpawnItemToContainer(item if item["count"] > 0 else {}, index, blockPos, dimensionId)
        if item["count"] <= 0:
            slots[index] = {}
    addMeals(blockEntityData, meal, times * (meal.get("count") or 1))
    addUsed(blockEntityData, meal["newItemName"], times)


def addUsed(blockEntityData, resultName, times):
    """记下这道菜又煮了 times 份（FD 的 usedRecipeTracker；整体回写才会存档）。"""
    used = dict(blockEntityData[USED_KEY] or {})
    used[resultName] = used.get(resultName, 0) + times
    blockEntityData[USED_KEY] = used


def spawnOrb(value, where, dimensionId):
    """在 where 放一个 value 点经验的经验球。"""
    if value <= 0:
        return
    orbId = System.CreateEngineEntityByTypeStr("minecraft:xp_orb", where, (0, 0), dimensionId)
    if orbId:
        compFactory.CreateExp(orbId).SetOrbExperience(value)


def awardExperience(blockEntityData, where, dimensionId):
    """把记着的份数换成经验球放在 where，记着的清零（FD 的 awardUsedRecipes）：每道菜按"煮了几份 x 一份的经验"，
    整数部分照给、零头按概率进一。煮了几份是按煮出来的算的，星星多送的份数不算。返回给了多少经验。"""
    used = blockEntityData[USED_KEY]
    if not used:
        return 0
    blockEntityData[USED_KEY] = None
    total = 0
    for name, times in used.items():
        total += CookingPotRules.experienceOrb(CookingPotRules.servingExperienceOf(name), times, random.random())
    spawnOrb(total, where, dimensionId)
    return total


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
    awardExperience(blockEntityData, (x + 0.5, y + 1, z + 0.5), dimensionId)
