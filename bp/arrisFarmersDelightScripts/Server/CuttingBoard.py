# -*- coding: utf-8 -*-
"""CuttingBoard - 砧板：放上一叠物品、用对的工具一件件切、空手取回（服务端）

照 JE：手里那一叠整叠放上去（同一种再放接着叠，叠满为止；创造模式手里留着），每切一下切一件、提示还剩几个；
工具不对提示换工具（判定和站点同一套：Shared/Rules/CuttingStation.fitsTool），带 chance 的产物按概率给。
板上的东西只存在方块实体数据 cuttingDict（带数量）；画面由各客户端按广播自己渲染（Helpers/BlockItems.py）。
"""
from .EventRegistry import registerHandler
from .Helpers import BoardDish
from .Helpers.BlockItems import DropLegacyDisplays, PublishBoard
from .Helpers.Engine import compFactory, levelId, System, GetBlockEntityData, GetCarriedItem, SetCarriedItem, ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import GetItemType, IsKnife
from .Helpers.Player import IsCreative, SetPlayerUsedCD, SetCarriedDurability
from ..Shared.Data.Cutting import CuttingBoardDict
from ..Shared.Rules import CuttingStation

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


def _kind(item):
    return (item["newItemName"], item.get("newAuxValue") or 0)


def _useWithItem(blockEntityData, carriedDict, blockPos, dimensionId, playerId):
    itemType = GetItemType(carriedDict)
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        if _kind(carriedDict) == _kind(cuttingDict):
            _place(blockEntityData, carriedDict, blockPos, dimensionId, playerId)     # 同一种：接着叠
            return
        result = CuttingBoardDict.get(_kind(cuttingDict))
        if not result:
            ShowTip(playerId, "这东西可不能切啊……")
        elif CuttingStation.fitsTool(carriedDict["newItemName"], itemType, result, IsKnife):
            _cutOne(blockEntityData, cuttingDict, result, carriedDict, blockPos, dimensionId, playerId)
        else:
            ShowTip(playerId, "或许得换个工具……")
        return
    if carriedDict["newItemName"] == "arris:skillet_item":
        return
    if itemType in _PLACEABLE_TYPES or _kind(carriedDict) in CuttingBoardDict:
        _place(blockEntityData, carriedDict, blockPos, dimensionId, playerId)
    else:
        ShowTip(playerId, "这东西可不能切啊……")


def _place(blockEntityData, carriedDict, blockPos, dimensionId, playerId):
    """手里那一叠放上板（板上已有同一种时叠上去，叠满为止）；创造模式手里的不少。"""
    board = blockEntityData["cuttingDict"]
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(carriedDict["newItemName"], _kind(carriedDict)[1]) or {}
    room = max(1, info.get("maxStackSize") or 64) - (board["count"] if board else 0)
    moved = min(carriedDict["count"], room)
    if moved <= 0:
        return
    stack = dict(board) if board else {"newItemName": carriedDict["newItemName"], "newAuxValue": _kind(carriedDict)[1]}
    stack["count"] = (board["count"] if board else 0) + moved
    blockEntityData["cuttingDict"] = stack
    if not IsCreative(playerId):
        left = dict(carriedDict)
        left["count"] -= moved
        SetCarriedItem(playerId, left if left["count"] > 0 else None)
    ToAllPlayerPlaySound(dimensionId, blockPos, "dig.wood")
    PublishBoard(dimensionId, blockPos, stack)


def _cutOne(blockEntityData, cuttingDict, result, carriedDict, blockPos, dimensionId, playerId):
    """切一件：产物掉在板上方（带 chance 的按概率），工具掉一点耐久，提示还剩几个。"""
    x, y, z = blockPos
    fortune = CuttingStation.fortuneOf(carriedDict)
    for name, aux, count in CuttingStation.resultsFor(result, 1, fortune=fortune):
        System.CreateEngineItemEntity({"newItemName": name, "newAuxValue": aux, "count": count}, dimensionId,
                                      (x + 0.5, y + 0.5, z + 0.5))
    ToAllPlayerPlaySound(dimensionId, blockPos, "ambient.cutting_board.knife")
    SetCarriedDurability(playerId, carriedDict, dimensionId, blockPos)
    left = (cuttingDict.get("count") or 1) - 1
    if left > 0:
        cuttingDict["count"] = left
        blockEntityData["cuttingDict"] = cuttingDict
        ShowTip(playerId, "还剩%d个……" % left)
    else:
        blockEntityData["cuttingDict"] = None
    PublishBoard(dimensionId, blockPos, blockEntityData["cuttingDict"])


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
