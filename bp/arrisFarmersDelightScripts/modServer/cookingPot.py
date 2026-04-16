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

    blockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((args["posX"], args["posY"] - 1, args["posZ"]), dimensionId)
    blockName = blockDict["name"]
    if blockName in ["minecraft:fire", "minecraft:campfire", "minecraft:soul_fire", "minecraft:soul_campfire", "minecraft:lava", "minecraft:flowing_lava"]:
        blockEntityData["shelfEnable"] = 1.0
    else:
        blockEntityData["shelfEnable"] = 0.0
    data = {"molang": blockEntityData["shelfEnable"], "blockPos": blockPos, "name": "variable.mod_shelf"}
    compFactory.CreateGame(levelId).AddTimer(0.1, Call, "*", "SetEntityBlockMolang", data)

    if blockName in CanProvideHeatBlockList:
        blockEntityData["heatEnable"] = True
        blockEntityData["heatParticleEnable"] = 1.0
    else:
        blockEntityData["heatEnable"] = False
        blockEntityData["heatParticleEnable"] = 0.0
    data = {"molang": blockEntityData["heatParticleEnable"], "blockPos": blockPos, "name": "variable.mod_heat"}
    compFactory.CreateGame(levelId).AddTimer(0.1, Call, "*", "SetEntityBlockMolang", data)

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
    neighborName = args["toBlockName"]
    if neighborName in ["minecraft:campfire", "minecraft:fire", "minecraft:soul_fire", "minecraft:soul_campfire", "minecraft:lava", "minecraft:flowing_lava"]:
        blockEntityData["shelfEnable"] = 1.0
    else:
        blockEntityData["shelfEnable"] = 0.0
    data = {"molang": blockEntityData["shelfEnable"], "blockPos": blockPos, "name": "variable.mod_shelf"}
    Call("*", "SetEntityBlockMolang", data)

    if neighborName in CanProvideHeatBlockList:
        blockEntityData["heatEnable"] = True
        blockEntityData["heatParticleEnable"] = 1.0
    else:
        blockEntityData["heatEnable"] = False
        blockEntityData["heatParticleEnable"] = 0.0
    data = {"molang": blockEntityData["heatParticleEnable"], "blockPos": blockPos, "name": "variable.mod_heat"}
    Call("*", "SetEntityBlockMolang", data)

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

    if blockEntityData["heatEnable"] and resultItem:
        previewItemSlot = blockEntityData["previewItemSlot"]
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

@AllowCall
def CookingPotAddFood(args):
    itemsDictMap = dict()
    playerId = args["playerId"]
    blockPos = args["blockPos"]
    dimensionId = args["dimensionId"]
    inputList = args["inputList"]
    indexList = args["indexList"]

    inputItemSlot = []
    for index in range(7):
        itemDict = compFactory.CreateItem(levelId).GetContainerItem(blockPos, index, dimensionId)
        if not itemDict:
            itemDict = {}
        inputItemSlot.append(itemDict)
    playerAllItemList = compFactory.CreateItem(playerId).GetPlayerAllItems(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, True)
    for index in range(len(inputList)):
        if not inputItemSlot[index]:
            itemDict = copy.deepcopy(playerAllItemList[indexList[index]])
            itemDict["count"] = 1
            inputItemSlot[index] = itemDict
            inventoryDict = playerAllItemList[indexList[index]]
            inventoryDict["count"] -= 1
            if inventoryDict["count"] <= 0:
                compFactory.CreateItem(playerId).SetInvItemNum(indexList[index], 0)
                playerAllItemList[indexList[index]] = None
            else:
                playerAllItemList[indexList[index]] = inventoryDict
        else:
            if inputItemSlot[index] and playerAllItemList[indexList[index]] and inputItemSlot[index]["newItemName"] == playerAllItemList[indexList[index]]["newItemName"]:
                inputItemSlot[index]["count"] += 1
                inventoryDict = playerAllItemList[indexList[index]]
                inventoryDict["count"] -= 1
                if inventoryDict["count"] <= 0:
                    compFactory.CreateItem(playerId).SetInvItemNum(indexList[index], 0)
                    playerAllItemList[indexList[index]] = None
                else:
                    playerAllItemList[indexList[index]] = inventoryDict
            else:
                break
    for i in range(0, len(playerAllItemList)):
        itemsDictMap[(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, i)] = playerAllItemList[i]
    if itemsDictMap:
        compFactory.CreateItem(playerId).SetPlayerAllItems(itemsDictMap)

    for index, itemDict in enumerate(inputItemSlot):
        if not itemDict:
            continue
        compFactory.CreateItem(levelId).SpawnItemToContainer(itemDict, index, blockPos, dimensionId)
