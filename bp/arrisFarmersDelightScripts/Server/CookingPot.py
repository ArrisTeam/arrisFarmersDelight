# -*- coding: utf-8 -*-
"""CookingPot - 厨锅：放置、热源、烹饪 tick、配方书一键放入、破坏时掉落成品（服务端）

容器格：0-5 食材，6 容器（碗等），7 成品。煮好的成品先进方块实体数据里的预览槽 previewItemSlot，
容器格里有对应容器时再转到 7 号格。
"""
import copy

from ..QuModLibs.Server import AllowCall, InjectHttpPlayerId
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, ItemPosType, GetBlockEntityData, GetBlockName
from .Helpers.Heat import RefreshHeat
from ..Shared.Rules import CookingPot as CookingPotRules
from ..Shared.Rules.Ticks import isStaggeredTick

COOKING_POT = "arris:cooking_pot"
INPUT_SLOTS = 6
VESSEL_SLOT = 6
RESULT_SLOT = 7
# 一份菜的烹饪时长（秒）
COOK_SECONDS = 10.0
# tick 错峰：每个厨锅每 STRIDE 个 tick 才处理一次（约 5 Hz），计时步长按 STRIDE 补偿
TICK_STRIDE = 4
TICK_STEP = 0.05 * TICK_STRIDE
# 配方书"一键放入"时玩家离厨锅的最远距离（格）
MAX_REACH = 8.0


@registerHandler("ServerPlaceBlockEntityEvent", match=COOKING_POT)
def OnServerCookingPotCreate(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    blockEntityData["previewItemSlot"] = [{}]
    blockEntityData["timer"] = COOK_SECONDS
    belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
    RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId), delay=0.1)


@registerHandler("BlockNeighborChangedServerEvent", match=COOKING_POT)
def OnCookingPotNeighborChanged(args):
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos != (args["posX"], args["posY"] - 1, args["posZ"]):
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    blockEntityData = GetBlockEntityData(args["dimensionId"], blockPos)
    if not blockEntityData:
        return
    # 营火点燃 / 熄灭时名字不变，这里每次都重新读状态
    RefreshHeat(blockEntityData, blockPos, neighborPos, args["dimensionId"], args["toBlockName"])


def MoveFinishedMeals(blockEntityData, blockPos, dimensionId):
    """把预览槽里煮好的成品转到产出格；需要容器的成品同时消耗容器格里等量的容器。"""
    x, y, z = blockPos
    previewList = blockEntityData["previewItemSlot"] or [{}]
    previewItemSlot = previewList[0]
    if not previewItemSlot or not previewItemSlot.get("newItemName"):
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
    maxStackSize = itemComp.GetItemBasicInfo(resultItemName, resultAuxValue)["maxStackSize"]
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
    # 改了嵌套字典必须整体回写，否则区块卸载后恢复原值
    blockEntityData["previewItemSlot"] = [previewItemSlot] if previewItemSlot["count"] > 0 else [{}]
    System.CreateEngineEntityByTypeStr("minecraft:xp_orb", (x + 0.5, y + 1, z + 0.5), (0, 0), dimensionId)


@registerHandler("ServerBlockEntityTickEvent", match=COOKING_POT)
def OnCookingPotTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    if not isStaggeredTick(compFactory.CreateTime(levelId).GetTime(), blockPos, TICK_STRIDE):
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    itemComp = compFactory.CreateItem(levelId)
    inputItemSlot = [itemComp.GetContainerItem(blockPos, index, dimensionId) or {} for index in range(INPUT_SLOTS)]
    MoveFinishedMeals(blockEntityData, blockPos, dimensionId)
    if not any(inputItemSlot):
        blockEntityData["timer"] = COOK_SECONDS
        return
    resultItem, pushItemList = CookingPotRules.matchRecipe(inputItemSlot)
    if blockEntityData["timer"] is None:
        # /setblock、结构等方式放出的厨锅没有走放置事件，这里补默认值
        blockEntityData["timer"] = COOK_SECONDS
    if blockEntityData["heatEnable"] is None:
        belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
        RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId))
    if not (blockEntityData["heatEnable"] and resultItem):
        blockEntityData["timer"] = COOK_SECONDS
        return
    previewItemSlot = blockEntityData["previewItemSlot"] or [{}]
    maxStackSize = itemComp.GetItemBasicInfo(resultItem["newItemName"], resultItem["newAuxValue"])["maxStackSize"]
    if previewItemSlot[0] and previewItemSlot[0].get("count") >= maxStackSize:
        return
    if previewItemSlot[0] and resultItem["newItemName"] != previewItemSlot[0].get("newItemName"):
        return
    blockEntityData["timer"] -= TICK_STEP
    if blockEntityData["timer"] > TICK_STEP:
        return
    blockEntityData["timer"] = COOK_SECONDS
    for pushItem in pushItemList or []:
        output = {"newItemName": pushItem[0], "newAuxValue": pushItem[1], "count": 1}
        System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 1.0, args["posZ"] + 0.5))
    for index, itemDict in enumerate(inputItemSlot):
        if not itemDict:
            continue
        itemDict["count"] -= 1
        itemComp.SpawnItemToContainer(itemDict, index, blockPos, dimensionId)
    if not previewItemSlot[0]:
        blockEntityData["previewItemSlot"] = [resultItem]
    else:
        previewItemSlot[0]["count"] += resultItem["count"]
        blockEntityData["previewItemSlot"] = previewItemSlot


@AllowCall
@InjectHttpPlayerId
def CookingPotAddFood(playerId, args):
    # 配方书"放入食材"：把背包里指定下标的物品各取 1 个放进厨锅前几格。
    # 安全：playerId 由服务端注入；维度取玩家自己的；厨锅位置要真的是厨锅且在交互距离内；
    # 背包下标逐个校验，客户端只能决定"拿自己背包里的哪几格"
    if not playerId or not isinstance(args, dict):
        return
    blockPos = args.get("blockPos")
    indexList = args.get("indexList")
    if not isinstance(blockPos, (list, tuple)) or len(blockPos) != 3 or not isinstance(indexList, (list, tuple)):
        return
    blockPos = (int(blockPos[0]), int(blockPos[1]), int(blockPos[2]))
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    if GetBlockName(blockPos, dimensionId) != COOKING_POT:
        return
    playerPos = compFactory.CreatePos(playerId).GetFootPos()
    if playerPos is None:
        return
    dx, dy, dz = blockPos[0] + 0.5 - playerPos[0], blockPos[1] + 0.5 - playerPos[1], blockPos[2] + 0.5 - playerPos[2]
    if dx * dx + dy * dy + dz * dz > MAX_REACH * MAX_REACH:
        return
    _addFood(playerId, blockPos, dimensionId, indexList)


def _addFood(playerId, blockPos, dimensionId, indexList):
    itemComp = compFactory.CreateItem(levelId)
    inputItemSlot = [itemComp.GetContainerItem(blockPos, index, dimensionId) or {} for index in range(INPUT_SLOTS)]
    inventoryType = ItemPosType.INVENTORY
    playerAllItemList = compFactory.CreateItem(playerId).GetPlayerAllItems(inventoryType, True)
    changedInventory = {}
    changedSlots = set()
    for slotIndex, invIndex in enumerate(indexList[:INPUT_SLOTS]):
        if not isinstance(invIndex, int) or not 0 <= invIndex < len(playerAllItemList):
            break
        inventoryDict = playerAllItemList[invIndex]
        if not inventoryDict or inventoryDict.get("count", 0) <= 0:
            break
        slotItem = inputItemSlot[slotIndex]
        if not slotItem:
            slotItem = copy.deepcopy(inventoryDict)
            slotItem["count"] = 1
        elif (slotItem["newItemName"] == inventoryDict["newItemName"]
              and slotItem.get("newAuxValue", 0) == inventoryDict.get("newAuxValue", 0)):
            maxStackSize = itemComp.GetItemBasicInfo(slotItem["newItemName"], slotItem.get("newAuxValue", 0))["maxStackSize"]
            if slotItem["count"] >= maxStackSize:
                break
            slotItem["count"] += 1
        else:
            break
        inputItemSlot[slotIndex] = slotItem
        changedSlots.add(slotIndex)
        inventoryDict["count"] -= 1
        playerAllItemList[invIndex] = inventoryDict if inventoryDict["count"] > 0 else None
        changedInventory[(inventoryType, invIndex)] = playerAllItemList[invIndex]
    if not changedSlots:
        return
    compFactory.CreateItem(playerId).SetPlayerAllItems(changedInventory)
    for slotIndex in changedSlots:
        itemComp.SpawnItemToContainer(inputItemSlot[slotIndex], slotIndex, blockPos, dimensionId)


@registerHandler("BlockRemoveServerEvent", match=COOKING_POT)
def OnCookingPotRemove(args):
    # 厨锅被破坏：预览槽里煮好还没装碗的成品存在方块实体数据里，不掉出来就会凭空消失
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    previewList = blockEntityData["previewItemSlot"] or [{}]
    previewItemSlot = previewList[0]
    if previewItemSlot and previewItemSlot.get("newItemName") and previewItemSlot.get("count", 0) > 0:
        dropDict = {"newItemName": previewItemSlot["newItemName"], "newAuxValue": previewItemSlot.get("newAuxValue", 0),
                    "count": previewItemSlot["count"]}
        System.CreateEngineItemEntity(dropDict, dimensionId, (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5))
        blockEntityData["previewItemSlot"] = [{}]
