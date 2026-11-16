# -*- coding: utf-8 -*-
"""Skillet - 放置的煎锅：放入一叠食物、逐个煎熟弹出、取回（服务端）

煎锅物品放成方块（只有潜行才放）、方块里记着那一件煎锅、拆掉原样掉回在 Server/SkilletItem.py，放置本身在 Server/ItemToBlock.py（与派共用一份）。
锅里的东西只存在方块实体数据 cookingDict，画面由各客户端按广播自己渲染（Helpers/BlockItems.py），不再生成展示实体。
煎锅站点（场景交互前置在场时）手放的一批由 HandFrying.py 两面分开煎、等着颠锅；右键放进来的照这里一件一件煎。
"""
import time

from . import HandFrying, SkilletItem
from .EventRegistry import registerHandler
from .Helpers.BlockItems import DropLegacyDisplays, PublishSkillet
from .Helpers.Engine import compFactory, levelId, System, GetBlockEntityData, GetBlockName, GetCarriedItem, SetCarriedItem, \
    ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Heat import RefreshHeat
from .Helpers.Player import IsCreative, SetPlayerUsedCD
from ..Shared.Data.Cooking import CanCookedFoodDict, CanProvideHeatBlockList
from ..Shared.Rules.BlockDisplay import skilletLayers
from ..Shared.Rules.Ticks import Pacer

SKILLET = "arris:skillet"
# 每件食物煎 6 秒：计时从 7 倒数到 1
COOK_TIMER = 7
# 手里拿着这些物品点煎锅时拦截交互（不把它们当食物，也不在煎锅上放方块）
_BLOCKED_ITEMS = ("arris:spatula", "arris:cutting_board", "arris:cooking_pot", "arris:skillet_item")
# 每个煎锅每 TICK_STEP 秒处理一次（真实时间节拍，不受 /time set、doDaylightCycle false 影响），计时按步长累加
TICK_STEP = 0.25
_pacer = Pacer(TICK_STEP)


@registerHandler("ServerBlockUseEvent", match=SKILLET)
def OnServerSkilletBlockUse(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    x, y, z = blockPos
    if SetPlayerUsedCD(playerId) is True:
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    DropLegacyDisplays(blockEntityData)
    carriedDict = GetCarriedItem(playerId, True)
    if carriedDict:
        if blockEntityData["cookingDict"]:
            return
        if carriedDict["newItemName"] in CanCookedFoodDict:
            HandFrying.byFarmersDelight(dimensionId, blockPos)
            blockEntityData["cookingDict"] = carriedDict
            PublishSkillet(dimensionId, blockPos, carriedDict)
            if not IsCreative(playerId):
                SetCarriedItem(playerId, None)
            blockEntityData["cookTimer"] = COOK_TIMER
            downBlockName = GetBlockName((x, y - 1, z), dimensionId)
            sound = "ambient.skillet.addfood" if downBlockName in CanProvideHeatBlockList else "armor.equip_leather"
            ToAllPlayerPlaySound(dimensionId, blockPos, sound)
        elif carriedDict["newItemName"] in _BLOCKED_ITEMS:
            # ServerBlockUseEvent 的拦截字段是 cancel（ret 属于 ServerItemUseOnEvent）
            args["cancel"] = True
        else:
            ShowTip(playerId, "这东西可不能被烹饪……")
        return
    cookingDict = blockEntityData["cookingDict"]
    if cookingDict:
        HandFrying.byFarmersDelight(dimensionId, blockPos)
        SetCarriedItem(playerId, cookingDict)
        ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
        blockEntityData["cookingDict"] = None
        PublishSkillet(dimensionId, blockPos, None)
    blockEntityData["cookTimer"] = COOK_TIMER


def _refreshSkilletHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName):
    if not RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName):
        blockEntityData["cookTimer"] = COOK_TIMER


@registerHandler("BlockNeighborChangedServerEvent", match=SKILLET)
def OnSkilletNeighborChanged(args):
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos != (args["posX"], args["posY"] - 1, args["posZ"]):
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    blockEntityData = GetBlockEntityData(args["dimensionId"], blockPos)
    if blockEntityData:
        # 营火点燃 / 熄灭时名字不变，这里每次都重新读状态
        _refreshSkilletHeat(blockEntityData, blockPos, neighborPos, args["dimensionId"], args["toBlockName"])


@registerHandler("ServerPlaceBlockEntityEvent", match=SKILLET)
def OnServerSkilletCreate(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    ToAllPlayerPlaySound(dimensionId, blockPos, "dig.stone")
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if blockEntityData:
        SkilletItem.attachPending(blockEntityData, dimensionId, blockPos)
        belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
        blockEntityData["cookTimer"] = COOK_TIMER
        _refreshSkilletHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId))


@registerHandler("ServerBlockEntityTickEvent", match=SKILLET)
def OnSkilletTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    if not _pacer.due((dimensionId, blockPos), time.time()):
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData or blockEntityData["heatEnable"] is not True:
        return
    hand = HandFrying.peek(dimensionId, blockPos)
    if hand is not None and HandFrying.fry(hand, dimensionId, blockPos, blockEntityData, TICK_STEP):
        return
    cookingDict = blockEntityData["cookingDict"]
    if not cookingDict or cookingDict.get("newItemName") not in CanCookedFoodDict:
        return
    if blockEntityData["cookTimer"] is None:
        blockEntityData["cookTimer"] = COOK_TIMER
    blockEntityData["cookTimer"] -= TICK_STEP
    if blockEntityData["cookTimer"] > 1.0:
        return
    layersBefore = skilletLayers(cookingDict["count"])
    cookingDict["count"] -= 1
    blockEntityData["cookTimer"] = COOK_TIMER
    output = {"itemName": CanCookedFoodDict[cookingDict["newItemName"]], "auxValue": cookingDict.get("newAuxValue", 0), "count": 1}
    System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 0.3, args["posZ"] + 0.5))
    if cookingDict["count"] <= 0:
        blockEntityData["cookingDict"] = None
        PublishSkillet(dimensionId, blockPos, None)
    else:
        # 改了嵌套字典必须整体回写：只改取回来的字典，区块卸载后数量会恢复原样（刷熟食）
        blockEntityData["cookingDict"] = cookingDict
        if skilletLayers(cookingDict["count"]) != layersBefore:
            PublishSkillet(dimensionId, blockPos, cookingDict)


@registerHandler("BlockRemoveServerEvent", match=SKILLET)
def OnSkilletRemove(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    _pacer.forget((dimensionId, blockPos))
    HandFrying.forget(dimensionId, blockPos)
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if blockEntityData:
        DropLegacyDisplays(blockEntityData)
        cookingDict = blockEntityData["cookingDict"]
        if cookingDict:
            System.CreateEngineItemEntity(cookingDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
        PublishSkillet(dimensionId, blockPos, None)
    # 方块的战利品表是空的，煎锅自己在这里掉（连耐久、附魔一起；方块实体丢了也掉一把新的，不能凭空没了）
    SkilletItem.dropStored(blockEntityData, dimensionId, blockPos)
