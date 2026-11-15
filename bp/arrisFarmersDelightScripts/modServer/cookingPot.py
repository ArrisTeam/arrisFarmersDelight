# -*- coding: utf-8 -*-
from serverUtils.serverUtils import *
import copy, time

@Listen("ServerPlaceBlockEntityEvent")
def OnServerCookingPotCreate(args):
    blockName = args["blockName"]
    if blockName != "arris:cooking_pot":
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return

    blockEntityData["previewItemSlot"] = [{}]
    blockEntityData["timer"] = 10.0

    belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
    blockName = compFactory.CreateBlockInfo(levelId).GetBlockNew(belowPos, dimensionId)["name"]
    UpdateCookingPotHeat(blockEntityData, blockPos, belowPos, dimensionId, blockName, delay=0.1)

def UpdateCookingPotHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName, delay=0.0):
    # 根据下方方块刷新"架子"和"加热"两个状态，并同步给客户端的方块实体 molang
    if belowName in ShelfBlockSet:
        blockEntityData["shelfEnable"] = 1.0
    else:
        blockEntityData["shelfEnable"] = 0.0
    heat = IsHeatSource(belowPos, dimensionId, belowName)
    blockEntityData["heatEnable"] = heat
    blockEntityData["heatParticleEnable"] = 1.0 if heat else 0.0
    for name, value in (("variable.mod_shelf", blockEntityData["shelfEnable"]), ("variable.mod_heat", blockEntityData["heatParticleEnable"])):
        data = {"molang": value, "blockPos": blockPos, "name": name}
        if delay > 0:
            compFactory.CreateGame(levelId).AddTimer(delay, Call, "*", "SetEntityBlockMolang", data)
        else:
            Call("*", "SetEntityBlockMolang", data)
    return heat

@Listen("BlockNeighborChangedServerEvent")
def OnCookingPotNeighborChanged(args):
    blockName = args["blockName"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimensionId"]
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if blockName != "arris:cooking_pot" or neighborPos != (args["posX"], args["posY"] - 1, args["posZ"]):
        return
    blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    # 营火点燃 / 熄灭时名字不变，这里每次都重新读状态
    UpdateCookingPotHeat(blockEntityData, blockPos, neighborPos, dimensionId, args["toBlockName"])

@Listen("ServerBlockEntityTickEvent")
def OnCookingPotTick(args):
    if args["blockName"] != "arris:cooking_pot":
        return
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    # 坐标加盐错峰：N 个厨锅分散到 COOKING_POT_TICK_STRIDE 个不同 tick 上，瞬时工作量降为 1/STRIDE
    tickCount = compFactory.CreateTime(levelId).GetTime()
    if (tickCount + PosHash(blockPos)) % COOKING_POT_TICK_STRIDE != 0:
        return
    blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    inputItemSlot = []
    num = 0
    for index in range(6):
        itemDict = compFactory.CreateItem(levelId).GetContainerItem(blockPos, index, dimensionId)
        if not itemDict:
            itemDict = {}
            num += 1
        inputItemSlot.append(itemDict)
    CheckCookingPotVessel(blockEntityData, blockPos, dimensionId)
    if num >= 6:
        blockEntityData["timer"] = 10.0
        return
    resultItem, pushItemList = CheckCookingPotRecipe(inputItemSlot)

    if blockEntityData["timer"] is None:
        # /setblock、结构等方式放出的厨锅没有走放置事件，这里补默认值
        blockEntityData["timer"] = 10.0
    if blockEntityData["heatEnable"] is None:
        belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
        belowName = compFactory.CreateBlockInfo(levelId).GetBlockNew(belowPos, dimensionId)["name"]
        UpdateCookingPotHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName)
    if blockEntityData["heatEnable"] and resultItem:
        previewItemSlot = blockEntityData["previewItemSlot"] or [{}]
        itemName = resultItem["newItemName"]
        auxValue = resultItem["newAuxValue"]
        basicInfo = compFactory.CreateItem(levelId).GetItemBasicInfo(itemName, auxValue)
        maxStackSize = basicInfo["maxStackSize"]

        if previewItemSlot[0] and previewItemSlot[0].get("count") >= maxStackSize:
            return
        if not previewItemSlot[0] or resultItem["newItemName"] == previewItemSlot[0].get("newItemName"):
            # 错峰后本 handler 每 STRIDE tick 才跑一次，步长需按 STRIDE 倍补偿以保持总烹饪时长 10s
            blockEntityData["timer"] -= 0.05 * COOKING_POT_TICK_STRIDE
            if blockEntityData["timer"] <= 0.05 * COOKING_POT_TICK_STRIDE:
                blockEntityData["timer"] = 10.0

                if pushItemList:
                    for pushItem in pushItemList:
                        output = {"newItemName": pushItem[0], "newAuxValue": pushItem[1], "count": 1}
                        System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 1.0, args["posZ"] + 0.5))

                for index, itemDict in enumerate(inputItemSlot):
                    if not itemDict:
                        continue
                    itemDict["count"] -= 1
                    compFactory.CreateItem(levelId).SpawnItemToContainer(itemDict, index, blockPos, dimensionId)

                if not previewItemSlot[0]:
                    blockEntityData["previewItemSlot"] = [resultItem]
                else:
                    if not resultItem:
                        return
                    count = previewItemSlot[0]["count"] + resultItem["count"]
                    previewItemSlot[0]["count"] = count
                    blockEntityData["previewItemSlot"] = previewItemSlot
    else:
        blockEntityData["timer"] = 10.0

# 厨锅 6 个输入格；配方书"一键放入"时玩家离厨锅的最远距离（格）
COOKING_POT_INPUT_SLOTS = 6
COOKING_POT_MAX_REACH = 8.0

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
    if compFactory.CreateBlockInfo(levelId).GetBlockNew(blockPos, dimensionId)["name"] != "arris:cooking_pot":
        return
    playerPos = compFactory.CreatePos(playerId).GetFootPos()
    if playerPos is None:
        return
    dx, dy, dz = blockPos[0] + 0.5 - playerPos[0], blockPos[1] + 0.5 - playerPos[1], blockPos[2] + 0.5 - playerPos[2]
    if dx * dx + dy * dy + dz * dz > COOKING_POT_MAX_REACH * COOKING_POT_MAX_REACH:
        return

    itemComp = compFactory.CreateItem(levelId)
    inputItemSlot = []
    for index in range(COOKING_POT_INPUT_SLOTS):
        inputItemSlot.append(itemComp.GetContainerItem(blockPos, index, dimensionId) or {})
    inventoryType = serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
    playerAllItemList = compFactory.CreateItem(playerId).GetPlayerAllItems(inventoryType, True)
    changedInventory = {}
    changedSlots = set()
    for slotIndex, invIndex in enumerate(indexList[:COOKING_POT_INPUT_SLOTS]):
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

@Listen("BlockRemoveServerEvent")
def OnCookingPotRemove(args):
    # 厨锅被破坏：预览槽里煮好还没装碗的成品存在方块实体数据里，不掉出来就会凭空消失
    if args["fullName"] != "arris:cooking_pot":
        return
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    previewList = blockEntityData["previewItemSlot"] or [{}]
    previewItemSlot = previewList[0]
    if previewItemSlot and previewItemSlot.get("newItemName") and previewItemSlot.get("count", 0) > 0:
        dropDict = {"newItemName": previewItemSlot["newItemName"], "newAuxValue": previewItemSlot.get("newAuxValue", 0), "count": previewItemSlot["count"]}
        System.CreateEngineItemEntity(dropDict, dimensionId, (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5))
        blockEntityData["previewItemSlot"] = [{}]
