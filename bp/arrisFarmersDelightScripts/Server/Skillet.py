# -*- coding: utf-8 -*-
"""Skillet - 放置的煎锅：放入一叠食物、逐个煎熟弹出、取回（服务端）

煎锅物品放成方块的逻辑在 Server/ItemToBlock.py（与派共用一份）。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, DestroyEntity, GetBlockEntityData, GetBlockName, GetCarriedItem, \
    SetCarriedItem, ShowTip
from .Helpers.DisplayEntity import SkilletDisplayCount, SkilletDisplayEntity
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Heat import RefreshHeat
from .Helpers.Player import IsCreative, SetPlayerUsedCD
from ..Shared.Data.Cooking import CanCookedFoodDict, CanProvideHeatBlockList
from ..Shared.Rules.Ticks import isStaggeredTick

SKILLET = "arris:skillet"
# 每件食物煎 6 秒：计时从 7 倒数到 1，1 Hz 采样
COOK_TIMER = 7
# 手里拿着这些物品点煎锅时拦截交互（不把它们当食物，也不在煎锅上放方块）
_BLOCKED_ITEMS = ("arris:spatula", "arris:cutting_board", "arris:cooking_pot", "arris:skillet_item")


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
    carriedDict = GetCarriedItem(playerId, True)
    if carriedDict:
        if blockEntityData["displayEntityList"]:
            return
        if carriedDict["newItemName"] in CanCookedFoodDict:
            blockEntityData["cookingDict"] = carriedDict
            data = {"blockEntityData": blockEntityData, "blockPos": blockPos, "blockAuxValue": args["aux"], "dimensionId": dimensionId}
            SkilletDisplayEntity(carriedDict, playerId, data)
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
            ShowTip(playerId, "这个貌似不可以进行烹饪...")
        return
    cookingDict = blockEntityData["cookingDict"]
    if cookingDict:
        SetCarriedItem(playerId, cookingDict)
        ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
        blockEntityData["cookingDict"] = None
    displayEntityList = blockEntityData["displayEntityList"]
    if displayEntityList:
        for entityId in displayEntityList:
            DestroyEntity(entityId)
        blockEntityData["displayEntityList"] = None
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
        belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
        blockEntityData["cookTimer"] = COOK_TIMER
        _refreshSkilletHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId))


@registerHandler("ServerBlockEntityTickEvent", match=SKILLET)
def OnSkilletTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    # 1 Hz 采样 + 坐标相位错开：每个煎锅每秒仍然处理 1 次，但不同坐标落在不同 tick 上
    if not isStaggeredTick(compFactory.CreateTime(levelId).GetTime(), blockPos, 20):
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData or blockEntityData["heatEnable"] is not True:
        return
    cookingDict = blockEntityData["cookingDict"]
    if not cookingDict or cookingDict.get("newItemName") not in CanCookedFoodDict:
        return
    if blockEntityData["cookTimer"] is None:
        blockEntityData["cookTimer"] = COOK_TIMER
    blockEntityData["cookTimer"] -= 1.0
    if blockEntityData["cookTimer"] > 1.0:
        return
    cookingDict["count"] -= 1
    displayEntityList = list(blockEntityData["displayEntityList"] or [])
    # 数量变少后多出来的那几层展示实体删掉（从最上层开始）
    keep = SkilletDisplayCount(cookingDict["count"])
    while len(displayEntityList) > keep:
        DestroyEntity(displayEntityList.pop())
    blockEntityData["cookTimer"] = COOK_TIMER
    output = {"itemName": CanCookedFoodDict[cookingDict["newItemName"]], "auxValue": cookingDict.get("newAuxValue", 0), "count": 1}
    System.CreateEngineItemEntity(output, dimensionId, (args["posX"] + 0.5, args["posY"] + 0.3, args["posZ"] + 0.5))
    if cookingDict["count"] <= 0:
        for entityId in displayEntityList:
            DestroyEntity(entityId)
        blockEntityData["displayEntityList"] = None
        blockEntityData["cookingDict"] = None
    else:
        # 改了嵌套字典必须整体回写：只改取回来的字典，区块卸载后数量会恢复原样（刷熟食）
        blockEntityData["cookingDict"] = cookingDict
        blockEntityData["displayEntityList"] = displayEntityList


@registerHandler("BlockRemoveServerEvent", match=SKILLET)
def OnSkilletRemove(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    for entityId in blockEntityData["displayEntityList"] or []:
        DestroyEntity(entityId)
    cookingDict = blockEntityData["cookingDict"]
    if cookingDict:
        System.CreateEngineItemEntity(cookingDict, dimensionId, (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5))
