# -*- coding: utf-8 -*-
from serverUtils.serverUtils import *

@Listen("ServerBlockUseEvent")
def OnServerPlatePackagedBlockUse(args):
    blockName = args["blockName"]
    x = args["x"]
    y = args["y"]
    z = args["z"]
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    if blockName in platePackagedFoodDict:
        if SetPlayerUsedCD(playerId) is True:
            return
        handItemDict = compFactory.CreateItem(playerId).GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.CARRIED, 0)
        if handItemDict is None:
            handItemDict = {}
        itemName = handItemDict.get("newItemName")
        packagedFoodDict = platePackagedFoodDict[blockName]
        name = packagedFoodDict.get("target")
        item = packagedFoodDict.get("item")
        aux = DetectionExperimentalHoliday()
        blockAux = aux.get(args["aux"], args["aux"])
        if name is not None:
            itemDict = {
                "itemName": item,
                "count": 1
            }
            if blockName[0:28] == "arris:rice_roll_medley_block":
                compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": name}, 0, dimensionId)
                blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
                if blockStates:
                    blockStates["direction"] = blockAux
                    compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, blockStates, dimensionId)
                ToAllPlayerPlaySound(dimensionId, (x, y, z), "armor.equip_leather")
                compFactory.CreateItem(playerId).SpawnItemToPlayerInv(itemDict, playerId)
            elif itemName == "minecraft:bowl":
                compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": name}, 0, dimensionId)
                blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
                if blockStates:
                    blockStates["direction"] = blockAux
                    compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, blockStates, dimensionId)
                ToAllPlayerPlaySound(dimensionId, (x, y, z), "armor.equip_leather")
                SetNotCreateItem(playerId, handItemDict)
                compFactory.CreateItem(playerId).SpawnItemToPlayerInv(itemDict, playerId)
            else:
                compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "你需要一个碗来食用它")
        else:
            compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)
