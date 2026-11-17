# -*- coding: utf-8 -*-
"""CuttingBoard - 砧板：放上一叠物品、用对的工具一件件切、空手取回（服务端）

照 JE（FD 的 CuttingBoardBlock.use）：板空着时手里什么都能整叠放上去（同一种再放接着叠，叠满为止；创造模式手里留着），每切一下切一件、提示还剩几个；
板上有东西、放不上去的（别的东西、同一种但叠满了或数据不一样）就当是拿工具来切：工具不对提示换工具（判定和站点同一套：Shared/Rules/CuttingStation.fitsTool），
带 chance 的产物按概率给，从板的侧面带着初速弹出去（CuttingBoardBlockEntity:89-92，Helpers/Drops.PopFromBoard）。空手取回，创造模式取回的东西不给玩家（:68）。
放上去、取回、切一件各响 FD 自己的那一声（Shared/Rules/BoardSounds 的 FD_PLACE / FD_TAKE / processed），切一件还飞出 5 颗这件东西的碎屑（Client/Endpoints.PlayCrumbs）。
拆了板：板上的东西从方块里随机一点掉出来（CuttingBoardBlock.onRemove 的 Containers.dropItemStack，Helpers/Drops.ScatterItem），摆着的菜的每一层也是（HoD 的 CuttingBoardBlockMixin）。
下面撑不住（空气 / 液体，Shared/Rules/BoardSupport）：放不下，已经放着的在下面变成这样时当场被拆（JE 的 canSurvive + updateShape）。
板上的东西只存在方块实体数据 cuttingDict（带数量，整件存：附魔、耐久、改名等数据一起，Shared/Rules/HandsOn/ItemData.py）；
画面由各客户端按广播自己渲染（Helpers/BlockItems.py）。
"""
from .EventRegistry import registerHandler
from .Helpers import BoardDish
from .Helpers.BlockItems import DropLegacyDisplays, PublishBoard
from .Helpers.Drops import PopFromBoard, ScatterItem
from .Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetCarriedItem, SetCarriedItem, ShowTip
from .Helpers.Fx import ToAllPlayerCrumbs, ToAllPlayerPlaySound
from .Helpers.Items import CanStack, GetItemType, GetMaxStack, IsKnife
from .Helpers.Player import IsCreative, SetPlayerUsedCD, SetCarriedDurability
from ..Shared.Data.Cutting import CuttingBoardDict
from ..Shared.Rules import BoardSounds, BoardSupport, CuttingStation
from ..Shared.Rules.HandsOn import ItemData

CUTTING_BOARD = "arris:cutting_board"


@registerHandler("BlockNeighborChangedServerEvent", match=CUTTING_BOARD)
def OnCuttingBoardNeighborChanged(args):
    # 下方方块撑不住了（变成空气 / 液体，JE 的 updateShape + canSurvive）：像被挖掉一样拆下来，掉板自己，板上的东西从方块里散落（BlockRemoveServerEvent）
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]) and not BoardSupport.survives(args["toBlockName"]):
        blockPos = (args["posX"], args["posY"], args["posZ"])
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": BoardSupport.AIR}, 1, args["dimensionId"])


@registerHandler("ServerEntityTryPlaceBlockEvent", match=CUTTING_BOARD)
def OnTryPlaceCuttingBoard(args):
    # JE 的 canSurvive：下面撑不住（空气 / 液体：贴着墙侧面放、悬空）就放不下，物品留在手里
    below = compFactory.CreateBlockInfo(levelId).GetBlockNew((args["x"], args["y"] - 1, args["z"]), args["dimensionId"])
    if not BoardSupport.survives(below["name"] if below else None):
        args["cancel"] = True


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
    # 空手：取回砧板上的东西
    cuttingDict = blockEntityData["cuttingDict"]
    if cuttingDict:
        if not IsCreative(playerId):                       # JE CuttingBoardBlock.java:68：创造模式取回的东西不给玩家
            SetCarriedItem(playerId, ItemData.restored(cuttingDict))
        ToAllPlayerPlaySound(dimensionId, _center(blockPos), *BoardSounds.FD_TAKE)
        blockEntityData["cuttingDict"] = None
        PublishBoard(dimensionId, blockPos, None)


def _center(blockPos):
    return (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5)


def _kind(item):
    return (item["newItemName"], item.get("newAuxValue") or 0)


def _stacksOnto(board, carriedDict):
    """手里的能叠到板上这一叠上吗（ItemStackHandler.insertItem）：同一种、数据也一样、没叠满。"""
    return CanStack(board, carriedDict) and board["count"] < GetMaxStack(carriedDict)


def _useWithItem(blockEntityData, carriedDict, blockPos, dimensionId, playerId):
    if carriedDict["newItemName"] == "arris:skillet_item":
        return                           # 煎锅物品潜行才放成方块（Server/SkilletItem.py），这一下不当东西摆上板
    board = blockEntityData["cuttingDict"]
    if not board or _stacksOnto(board, carriedDict):
        _place(blockEntityData, carriedDict, blockPos, dimensionId, playerId)      # FD 的 canAddItem：板空着，或是同一种还有空位
    else:
        _process(blockEntityData, board, carriedDict, blockPos, dimensionId, playerId)


def _place(blockEntityData, carriedDict, blockPos, dimensionId, playerId):
    """手里那一叠放上板（板上已有同一种时叠上去，叠满为止）；创造模式手里的不少。数据（附魔、改名……）存不进方块实体数据的不放，不然取回时会丢数据。"""
    if not ItemData.storable(carriedDict):
        ShowTip(playerId, "这东西放不上砧板……")
        return
    board = blockEntityData["cuttingDict"]
    have = board["count"] if board else 0
    moved = min(carriedDict["count"], GetMaxStack(carriedDict) - have)
    stack = dict(board) if board else ItemData.stored(carriedDict)
    stack["count"] = have + moved
    blockEntityData["cuttingDict"] = stack
    if not IsCreative(playerId):
        left = dict(carriedDict)
        left["count"] -= moved
        SetCarriedItem(playerId, left if left["count"] > 0 else None)
    ToAllPlayerPlaySound(dimensionId, _center(blockPos), *BoardSounds.FD_PLACE)
    PublishBoard(dimensionId, blockPos, stack)


def _process(blockEntityData, board, carriedDict, blockPos, dimensionId, playerId):
    """JE 的 processStoredItemUsingTool：板上的东西没有切法提示不能切，手里的工具不对提示换工具，对了切一件。"""
    result = CuttingBoardDict.get(_kind(board))
    if not result:
        ShowTip(playerId, "这东西可不能切啊……")
    elif CuttingStation.fitsTool(carriedDict["newItemName"], GetItemType(carriedDict), result, IsKnife):
        _cutOne(blockEntityData, board, result, carriedDict, blockPos, dimensionId, playerId)
    else:
        ShowTip(playerId, "或许得换个工具……")


def _cutOne(blockEntityData, cuttingDict, result, carriedDict, blockPos, dimensionId, playerId):
    """切一件：产物从板的侧面弹出去（带 chance 的按概率；FD 的 spawnItemEntity，朝板的朝向逆时针那一边），飞碎屑、响切声，工具掉一点耐久，提示还剩几个。"""
    fortune = CuttingStation.fortuneOf(carriedDict)
    for name, aux, count in CuttingStation.resultsFor(result, 1, fortune=fortune):
        PopFromBoard(dimensionId, blockPos, {"newItemName": name, "newAuxValue": aux, "count": count})
    ToAllPlayerCrumbs(dimensionId, blockPos, cuttingDict["newItemName"])
    yields = [entry["itemName"] for entry in result["itemList"]]
    ToAllPlayerPlaySound(dimensionId, _center(blockPos), *BoardSounds.processed(
        carriedDict["newItemName"], cuttingDict["newItemName"], yields, CuttingStation.strokeOf(result), GetItemType(cuttingDict) == "block"))
    if not CuttingStation.ignoresWear(carriedDict):          # "耐久"附魔免掉的这一下不磨（JE 的 hurtAndBreak）
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
        ScatterItem(dimensionId, blockPos, ItemData.restored(cuttingDict))              # FD 的 Containers.dropItemStack：从方块里随机一点掉出来
    BoardDish.spill(dimensionId, blockPos, blockEntityData)
    PublishBoard(dimensionId, blockPos, None)
