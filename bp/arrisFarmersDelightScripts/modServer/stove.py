# -*- coding: utf-8 -*-
from .serverUtils.serverUtils import *

STOVE_SLOTS = 6

def InitStoveData(blockEntityData):
    # 炉灶 6 个烤位的默认数据；/setblock、结构放出的炉灶没走放置事件，用到时补上
    blockEntityData["cookingIndex"] = 0
    displayEntityDict = {}
    for index in range(0, STOVE_SLOTS):
        blockEntityData[str(index)] = {"itemDict": None, "cookTimer": 7}
        displayEntityDict[str(index)] = None
    blockEntityData["displayEntityDict"] = displayEntityDict

def EnsureStoveData(blockEntityData):
    if blockEntityData["displayEntityDict"] is None:
        InitStoveData(blockEntityData)

@Listen("ServerPlaceBlockEntityEvent")
def OnServerStoveCreate(args):
    blockName = args["blockName"]
    if blockName not in StoveList:
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    InitStoveData(blockEntityData)

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
            EnsureStoveData(blockEntityData)
            upBlockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y + 1, z), dimensionId)
            upBlockName = upBlockDict["name"]
            if upBlockName != "minecraft:air":
                compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "炉灶上方有方块阻挡...")
                return
            # 从 cookingIndex 开始找第一个空烤位（旧实现只看 cookingIndex 那一格，占着就放不进去）
            displayEntityDict = blockEntityData["displayEntityDict"]
            start = blockEntityData["cookingIndex"] or 0
            freeIndex = None
            for offset in range(STOVE_SLOTS):
                index = (start + offset) % STOVE_SLOTS
                slotData = blockEntityData[str(index)]
                if not displayEntityDict.get(str(index)) and not (slotData and slotData.get("itemDict")):
                    freeIndex = index
                    break
            if freeIndex is None:
                return
            if itemDict["newItemName"] in CanCookedFoodDict:
                blockEntityData["cookingIndex"] = freeIndex
                blockEntityData[str(freeIndex)] = {"itemDict": itemDict, "cookTimer": 7}
                SetNotCreateItem(playerId, itemDict)
                data = {"blockEntityData": blockEntityData, "blockPos": (x, y, z), "blockAuxValue": args["blockAuxValue"], "dimensionId": dimensionId}
                StoveDisplayEntity(itemDict, playerId, data)
                ToAllPlayerPlaySound(dimensionId, (x, y, z), "armor.equip_leather")
                blockEntityData["cookingIndex"] = (freeIndex + 1) % STOVE_SLOTS
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
    # 1Hz 采样 + 坐标相位错开：每个炉灶每秒仍然 tick 1 次，但不同坐标落在不同 tick 上
    if (compFactory.CreateTime(levelId).GetTime() + PosHash(blockPos)) % 20 == 0:
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if not blockEntityData:
            return
        EnsureStoveData(blockEntityData)
        for index in range(0, STOVE_SLOTS):
            data = blockEntityData[str(index)]
            displayEntityDict = blockEntityData["displayEntityDict"]
            if data and data.get("itemDict"):
                data["cookTimer"] = (data.get("cookTimer") or 7) - 1
                blockEntityData[str(index)] = data
                if data["cookTimer"] <= 0:
                    rawDict = data["itemDict"]
                    cookedName = CanCookedFoodDict.get(rawDict["newItemName"])
                    if cookedName:
                        output = {"itemName": cookedName, "auxValue": rawDict.get("newAuxValue", 0), "count": 1}
                    else:
                        # 配方被附属包移除了：原样退回生食，别让它卡在烤位上
                        output = rawDict
                    blockEntityData[str(index)] = {"itemDict": None, "cookTimer": 7}
                    System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 1.3, args["posZ"] + 0.5))
                    entityId = displayEntityDict.get(str(index))
                    if entityId:
                        DestroyEntity(entityId)
                    displayEntityDict[str(index)] = None
                    blockEntityData["displayEntityDict"] = displayEntityDict
        if (blockEntityData["cookingIndex"] or 0) >= STOVE_SLOTS:
            blockEntityData["cookingIndex"] = 0

@Listen("BlockRemoveServerEvent")
def OnStoveRemove(args):
    # 方块在销毁时触发
    blockPos = (args["x"], args["y"], args["z"])
    blockName = args["fullName"]
    dimensionId = args["dimension"]
    if blockName in StoveList:
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if not blockEntityData:
            return
        for index in range(0, STOVE_SLOTS):
            data = blockEntityData[str(index)]
            itemDict = data.get("itemDict") if data else None
            if itemDict:
                System.CreateEngineItemEntity(itemDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
        displayEntityDict = blockEntityData["displayEntityDict"]
        if displayEntityDict:
            for i in displayEntityDict:
                entityId = displayEntityDict[str(i)]
                if not entityId:
                    continue
                DestroyEntity(entityId)
