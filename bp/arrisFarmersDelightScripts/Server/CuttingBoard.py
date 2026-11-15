# -*- coding: utf-8 -*-
"""CuttingBoard - 砧板：放上一件物品、用对的工具一击切完、空手取回（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, DestroyEntity, GetBlockEntityData, GetCarriedItem, \
    SetCarriedItem, ShowTip
from .Helpers.DisplayEntity import CuttingBoardDisplayEntity
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import GetItemType, IsKnife
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem, SetCarriedDurability
from ..Shared.Data.Cutting import CuttingBoardDict

CUTTING_BOARD = "arris:cutting_board"
# 这些类型的物品可以单纯摆在砧板上（不切）
_PLACEABLE_TYPES = ("sword", "axe", "hoe", "shovel", "pickaxe")


@registerHandler("BlockNeighborChangedServerEvent", match=CUTTING_BOARD)
def OnCuttingBoardNeighborChanged(args):
    # 下方方块变成空气时砧板掉落（放在别的方块上的物品）
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]) and args["toBlockName"] == "minecraft:air":
        blockPos = (args["posX"], args["posY"], args["posZ"])
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, args["dimensionId"])


# 优先级 100：在其它 ServerItemUseOnEvent 处理之前取消物品使用（不在砧板上放方块、不吃掉手里的食物）
@registerHandler("ServerItemUseOnEvent", match=CUTTING_BOARD, priority=100)
def OnServerCuttingBoardItemUse(args):
    args["ret"] = True


@registerHandler("ServerBlockUseEvent", match=CUTTING_BOARD)
def OnServerCuttingBoardBlockUse(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    carriedDict = GetCarriedItem(playerId, True)
    if carriedDict:
        _useWithItem(args, blockEntityData, carriedDict, blockPos, dimensionId, playerId)
        return
    # 空手：取回砧板上的物品
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        SetCarriedItem(playerId, cuttingDict)
        ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
        blockEntityData["cuttingDict"] = None
    displayEntityId = blockEntityData["displayEntityId"]
    if displayEntityId:
        DestroyEntity(displayEntityId)
        blockEntityData["displayEntityId"] = None


def _useWithItem(args, blockEntityData, carriedDict, blockPos, dimensionId, playerId):
    x, y, z = blockPos
    itemType = GetItemType(carriedDict)
    displayEntityId = blockEntityData["displayEntityId"]
    cuttingDict = blockEntityData["cuttingDict"]
    if displayEntityId and cuttingDict:
        # 砧板上有东西：拿着对的工具就切
        result = CuttingBoardDict.get((cuttingDict["newItemName"], cuttingDict["newAuxValue"]))
        if not result:
            return
        itemName = carriedDict["newItemName"]
        isToolType = "item_type" in result and itemType == result.get("item_type")
        if itemName in result["tool"] or isToolType or IsKnife(itemName):
            for resultDict in result["itemList"]:
                System.CreateEngineItemEntity(resultDict, dimensionId, (x + 0.5, y + 0.5, z + 0.5))
            ToAllPlayerPlaySound(dimensionId, blockPos, "ambient.cutting_board.knife")
            SetCarriedDurability(playerId, carriedDict, dimensionId, blockPos)
            # 站点模式能在板上放一叠：经典玩法一次切一件，切完最后一件才清空
            left = (cuttingDict.get("count") or 1) - 1
            if left > 0:
                cuttingDict["count"] = left
                blockEntityData["cuttingDict"] = cuttingDict
                return
            DestroyEntity(displayEntityId)
            blockEntityData["cuttingDict"] = None
            blockEntityData["displayEntityId"] = None
        return
    # 砧板是空的：放上一件
    itemName = carriedDict["newItemName"]
    if itemName == "arris:skillet_item":
        return
    if itemType in _PLACEABLE_TYPES or (itemName, carriedDict["newAuxValue"]) in CuttingBoardDict:
        ToAllPlayerPlaySound(dimensionId, blockPos, "dig.wood")
        SetNotCreateItem(playerId, carriedDict)
        carriedDict["count"] = 1
        blockEntityData["cuttingDict"] = carriedDict
        data = {"blockEntityData": blockEntityData, "blockPos": blockPos, "blockAuxValue": args["aux"], "dimensionId": dimensionId}
        CuttingBoardDisplayEntity(carriedDict, playerId, data)
    else:
        ShowTip(playerId, "该物品无法放置在砧板上...")


@registerHandler("BlockRemoveServerEvent", match=CUTTING_BOARD)
def OnCuttingBoardRemove(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    displayEntityId = blockEntityData["displayEntityId"]
    if displayEntityId:
        DestroyEntity(displayEntityId)
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        System.CreateEngineItemEntity(cuttingDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
