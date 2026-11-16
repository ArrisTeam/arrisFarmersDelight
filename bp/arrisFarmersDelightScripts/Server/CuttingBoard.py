# -*- coding: utf-8 -*-
"""CuttingBoard - 砧板：放上一件物品、用对的工具切、空手取回（服务端）

板上的东西只存在方块实体数据 cuttingDict（带数量：站点模式能放一叠，这里一次切一件）；
画面由各客户端按广播自己渲染（Helpers/BlockItems.py），不再生成展示实体。
"""
from .EventRegistry import registerHandler
from .Helpers import BoardDish
from .Helpers.BlockItems import DropLegacyDisplays, PublishBoard
from .Helpers.Engine import compFactory, levelId, System, GetBlockEntityData, GetCarriedItem, SetCarriedItem, ShowTip
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
    DropLegacyDisplays(blockEntityData)
    if BoardDish.giveBack(playerId, dimensionId, blockPos, blockEntityData):
        return                           # 站点摆到一半的菜：经典玩法右键先全还给玩家
    carriedDict = GetCarriedItem(playerId, True)
    if carriedDict:
        _useWithItem(blockEntityData, carriedDict, blockPos, dimensionId, playerId)
        return
    # 空手：取回砧板上的物品
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        SetCarriedItem(playerId, cuttingDict)
        ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
        blockEntityData["cuttingDict"] = None
        PublishBoard(dimensionId, blockPos, None)


def _useWithItem(blockEntityData, carriedDict, blockPos, dimensionId, playerId):
    x, y, z = blockPos
    itemType = GetItemType(carriedDict)
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        # 砧板上有东西：拿着对的工具就切一件
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
            else:
                blockEntityData["cuttingDict"] = None
            PublishBoard(dimensionId, blockPos, blockEntityData["cuttingDict"])
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
        PublishBoard(dimensionId, blockPos, carriedDict)
    else:
        ShowTip(playerId, "这东西可不能切啊……")


@registerHandler("BlockRemoveServerEvent", match=CUTTING_BOARD)
def OnCuttingBoardRemove(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    DropLegacyDisplays(blockEntityData)
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        System.CreateEngineItemEntity(cuttingDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
    BoardDish.spill(dimensionId, blockPos, blockEntityData)
    PublishBoard(dimensionId, blockPos, None)
