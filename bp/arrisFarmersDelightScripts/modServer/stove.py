# -*- coding: utf-8 -*-
from .serverUtils.serverUtils import *

@Listen("ServerPlaceBlockEntityEvent")
def OnServerStoveCreate(args):
    blockName = args["blockName"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
    if blockName in StoveList:
        blockEntityData["cookingIndex"] = 0
        displayEntityDict = {}
        for index in range(0, 6):
            blockEntityData[str(index)] = {"itemDict": None, "cookTimer": 7}
            displayEntityDict[str(index)] = None
        blockEntityData["displayEntityDict"] = displayEntityDict

@Listen("ServerItemUseOnEvent")
def OnServerStoveItemUse(args):
    # 玩家在对方块使用物品之前服务端抛出的事件
    itemDict = args["itemDict"]
    itemName = itemDict["newItemName"]
    dimensionId = args["dimensionId"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    playerId = args["entityId"]
    blockName = args["blockName"]
    if blockName in StoveList:
        if SetPlayerUsedCD(playerId) is True:
            return
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, (x, y, z))
        if blockEntityData:
            if blockEntityData["cookingIndex"] >= 6:
                blockEntityData["cookingIndex"] = 0
            upBlockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
            upBlockName = upBlockDict["name"]
            if upBlockName != "minecraft:air":
                compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "炉灶上方有方块阻挡...")
                return
            cookingIndex = blockEntityData["cookingIndex"]
            displayEntityDict = blockEntityData["displayEntityDict"]
            if displayEntityDict[str(cookingIndex)]:
                return
            if itemDict["newItemName"] in CanCookedFoodDict:
                index = blockEntityData["cookingIndex"]
                blockEntityData[str(index)] = {"itemDict": itemDict, "cookTimer": 7}
                SetNotCreateItem(playerId, itemDict)
                data = {"blockEntityData": blockEntityData, "blockPos": (x, y, z), "blockAuxValue": args["blockAuxValue"], "dimensionId": dimensionId}
                StoveDisplayEntity(itemDict, playerId, data)
                ToAllPlayerPlaySound(dimensionId, (x, y, z), "armor.equip_leather")
                blockEntityData["cookingIndex"] += 1
            else:
                if itemName in ["arris:cutting_board", "arris:cooking_pot", "arris:skillet_item"]:
                    return
                else:
                    compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "这个貌似不能烹饪...")

@Listen("ServerBlockEntityTickEvent")
def OnStoveTick(args):
    if args["blockName"] not in StoveList:
        return
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    if compFactory.CreateTime(levelId).GetTime() % 20 == 0:
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if not blockEntityData:
            return
        for index in range(0, 6):
            data = blockEntityData[str(index)]
            displayEntityDict = blockEntityData["displayEntityDict"]
            if data["itemDict"]:
                data["cookTimer"] -= 1
                blockEntityData[str(index)] = data
                if data["cookTimer"] <= 0:
                    output = {
                        "itemName": CanCookedFoodDict[data["itemDict"]["newItemName"]],
                        "auxValue": data["itemDict"]["newAuxValue"],
                        "count": 1,
                    }
                    blockEntityData[str(index)] = {"itemDict": None, "cookTimer": 7}
                    System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 1.3, args["posZ"] + 0.5))
                    entityId = displayEntityDict[str(index)]
                    DestroyEntity(entityId)
                    displayEntityDict[str(index)] = None
                    blockEntityData["displayEntityDict"] = displayEntityDict
            if blockEntityData["cookingIndex"] >= 6:
                blockEntityData["cookingIndex"] = 0

@Listen("BlockRemoveServerEvent")
def OnStoveRemove(args):
    # 方块在销毁时触发
    blockPos = (args["x"], args["y"], args["z"])
    blockName = args["fullName"]
    dimensionId = args["dimension"]
    if blockName in StoveList:
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        for index in range(0, 6):
            data = blockEntityData[str(index)]
            itemDict = data["itemDict"]
            if itemDict:
                System.CreateEngineItemEntity(itemDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
        displayEntityDict = blockEntityData["displayEntityDict"]
        if displayEntityDict:
            for i in displayEntityDict:
                entityId = displayEntityDict[str(i)]
                if not entityId:
                    continue
                DestroyEntity(entityId)
