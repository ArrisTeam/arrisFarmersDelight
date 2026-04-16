# -*- coding: utf-8 -*-
from serverUtils.serverUtils import *

@Listen("ServerBlockUseEvent")
def OnServerSkilletBlockUse(args):
    blockName = args["blockName"]
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    x, y, z = blockPos
    if blockName == "arris:skillet":
        if SetPlayerUsedCD(playerId) is True:
            return
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if not blockEntityData:
            return
        carriedDict = compFactory.CreateItem(playerId).GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0, True)
        if carriedDict:
            if blockEntityData["displayEntityList"]:
                return
            if carriedDict["newItemName"] in CanCookedFoodDict:
                blockEntityData["cookingDict"] = carriedDict
                data = {"blockEntityData": blockEntityData, "blockPos": (x, y, z), "blockAuxValue": args["aux"], "dimensionId": dimensionId}
                SkilletDisplayEntity(carriedDict, playerId, data)
                gameType = compFactory.CreateGame(levelId).GetPlayerGameType(playerId)
                if gameType != 1:
                    compFactory.CreateItem(playerId).SetEntityItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, None, 0)
                downBlockName = compFactory.CreateBlockInfo(levelId).GetBlockNew((x, y - 1, z), dimensionId)[
                    "name"]
                blockEntityData["cookTimer"] = 7
                if downBlockName in CanProvideHeatBlockList:
                    ToAllPlayerPlaySound(dimensionId, (x, y, z), "ambient.skillet.addfood")
                else:
                    ToAllPlayerPlaySound(dimensionId, (x, y, z), "armor.equip_leather")
            else:
                if carriedDict["newItemName"] in ["arris:spatula", "arris:cutting_board", "arris:cooking_pot", "arris:skillet_item"]:
                    args["ret"] = True
                else:
                    compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "这个貌似不可以进行烹饪...")
        else:
            cookingDict = blockEntityData["cookingDict"]
            if cookingDict:
                compFactory.CreateItem(playerId).SetEntityItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, cookingDict, 0)
                ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
                blockEntityData["cookingDict"] = None
            displayEntityList = blockEntityData["displayEntityList"]
            if displayEntityList:
                for Id in displayEntityList:
                    DestroyEntity(Id)
                blockEntityData["displayEntityList"] = None
            blockEntityData["cookTimer"] = 7

@Listen("ServerItemUseOnEvent")
def OnServerSkilletItemUse(args):
    # 玩家在对方块使用物品之前服务端抛出的事件
    itemDict = args["itemDict"]
    itemName = itemDict["newItemName"]
    dimensionId = args["dimensionId"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    playerId = args["entityId"]
    blockName = args["blockName"]
    face = args["face"]
    if itemName == "arris:skillet_item" and blockName not in ["minecraft:frame", "minecraft:glow_frame", "arris:cutting_board"]:
        if SetPlayerUsedCD(playerId) is True:
            return
        pX, pY, pZ = compFactory.CreatePos(playerId).GetFootPos()
        aux = DetectionExperimentalHoliday()
        placePos = clickBlockFace(x, y, z)
        setPos = placePos[face]
        blockAux = aux.get(FromAngleGetBlockAux(x, z, pX, pZ), FromAngleGetBlockAux(x, z, pX, pZ))
        blockDict = {"name": itemChangeBlockDict[itemName]}
        placeBlock = compFactory.CreateBlockInfo(levelId).GetBlockNew(setPos, dimensionId)["name"]
        if placeBlock == "minecraft:air":
            SetNotCreateItem(playerId, itemDict)
            compFactory.CreateBlockInfo(levelId).SetBlockNew(setPos, blockDict, 0, dimensionId)
            blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(setPos, dimensionId)
            if blockStates:
                blockStates["direction"] = blockAux
                compFactory.CreateBlockState(levelId).SetBlockStates(setPos, blockStates, dimensionId)

@Listen("BlockNeighborChangedServerEvent")
def OnSkilletNeighborChanged(args):
    blockName = args["blockName"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimensionId"]
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if blockName == "arris:skillet" and neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]):
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if blockEntityData:
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
                blockEntityData["cookTimer"] = 7
            data = {"molang": blockEntityData["heatParticleEnable"], "blockPos": blockPos, "name": "variable.mod_heat"}
            Call("*", "SetEntityBlockMolang", data)

@Listen("ServerPlaceBlockEntityEvent")
def OnServerSkilletCreate(args):
    blockName = args["blockName"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    if blockName == "arris:skillet":
        ToAllPlayerPlaySound(dimensionId, blockPos, "dig.stone")
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if blockEntityData:
            blockDict = compFactory.CreateBlockInfo(levelId).GetBlockNew((args["posX"], args["posY"] - 1, args["posZ"]), dimensionId)
            blockName = blockDict["name"]
            blockEntityData["cookTimer"] = 7
            if blockName in ["minecraft:campfire", "minecraft:fire", "minecraft:soul_fire", "minecraft:soul_campfire", "minecraft:lava", "minecraft:flowing_lava"]:
                blockEntityData["shelfEnable"] = 1.0
            else:
                blockEntityData["shelfEnable"] = 0.0
            data = {"molang": blockEntityData["shelfEnable"], "blockPos": blockPos, "name": "variable.mod_shelf"}
            Call("*", "SetEntityBlockMolang", data)

            if blockName in CanProvideHeatBlockList:
                blockEntityData["heatEnable"] = True
                blockEntityData["heatParticleEnable"] = 1.0
            else:
                blockEntityData["heatEnable"] = False
                blockEntityData["heatParticleEnable"] = 0.0
                blockEntityData["cookTimer"] = 7
            data = {"molang": blockEntityData["heatParticleEnable"], "blockPos": blockPos, "name": "variable.mod_heat"}
            Call("*", "SetEntityBlockMolang", data)

@Listen("ServerBlockEntityTickEvent")
def OnSkilletTick(args):
    if args["blockName"] != "arris:skillet":
        return
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    if compFactory.CreateTime(levelId).GetTime() % 20 == 0:
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        if not blockEntityData:
            return
        if blockEntityData["heatEnable"] is True:
            if not blockEntityData["cookingDict"]:
                return
            blockEntityData["cookTimer"] -= 1.0
            if blockEntityData["cookTimer"] <= 1.0:
                cookingDict = blockEntityData["cookingDict"]
                cookingDict["count"] -= 1
                count = cookingDict["count"]
                displayEntityList = blockEntityData["displayEntityList"]
                if count == 0: index = 0
                elif count == 1: index = 1
                elif 2 <= count <= 16: index = 2
                elif 17 <= count <= 32: index = 3
                elif 33 <= count <= 48: index = 4
                else: index = 0
                try:
                    entityId = displayEntityList[index]
                    DestroyEntity(entityId)
                except IndexError:
                    pass
                blockEntityData["cookTimer"] = 7
                output = {
                    "itemName": CanCookedFoodDict[cookingDict["newItemName"]],
                    "auxValue": cookingDict["newAuxValue"],
                    "count": 1,
                }
                System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 0.3, args["posZ"] + 0.5))
                if cookingDict["count"] <= 0:
                    blockEntityData["displayEntityList"] = None
                    blockEntityData["cookingDict"] = None

@Listen("BlockRemoveServerEvent")
def OnSkilletRemove(args):
    # 方块在销毁时触发
    blockPos = (args["x"], args["y"], args["z"])
    blockName = args["fullName"]
    dimensionId = args["dimension"]
    if blockName == "arris:skillet":
        blockEntityData = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)
        displayEntityList = blockEntityData["displayEntityList"]
        cookingDict = blockEntityData["cookingDict"]
        if displayEntityList:
            for Id in displayEntityList:
                DestroyEntity(Id)
        if cookingDict:
            System.CreateEngineItemEntity(cookingDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
