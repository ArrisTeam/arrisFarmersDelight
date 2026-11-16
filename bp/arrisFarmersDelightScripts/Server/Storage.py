# -*- coding: utf-8 -*-
"""Storage - 橱柜开门声、堆肥桶接受本模组物品（服务端）

橱柜与篮子是 netease:block_chest，界面与存储都由引擎负责；篮子吸掉落物在 Basket.py（这里导入它来登记处理函数）。
"""
from . import Basket  # noqa: F401 - 导入即登记
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetCarriedItem
from .Helpers.Fx import ToAllPlayerPlaySound, ToAllPlayerGrowthParticle
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem
from ..Shared.Data.Blocks import cabinetList
from ..Shared.Data.Farming import ComposterItemDict
from ..Shared.Rules.Ticks import probability

COMPOSTER = "minecraft:composter"
COMPOSTER_FULL = 8

# 原版堆肥桶要登记后才会触发 ServerBlockUseEvent
compFactory.CreateBlockUseEventWhiteList(levelId).AddBlockItemListenForUseEvent(COMPOSTER + ":*")


@registerHandler("ServerBlockUseEvent", match=cabinetList)
def OnOpenCabinet(args):
    if SetPlayerUsedCD(args["playerId"]) is True:
        return
    ToAllPlayerPlaySound(args["dimensionId"], (args["x"], args["y"], args["z"]), "block.barrel.open")


@registerHandler("ServerBlockUseEvent", match=COMPOSTER)
def OnUseComposter(args):
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates((x, y, z), dimensionId)
    if blockStates["composter_fill_level"] >= COMPOSTER_FULL:
        return
    handItemDict = GetCarriedItem(playerId)
    if not handItemDict:
        return
    item = (handItemDict["newItemName"], handItemDict["newAuxValue"])
    if item not in ComposterItemDict:
        return
    center = (x + 0.5, y, z + 0.5)
    ToAllPlayerPlaySound(dimensionId, center, "block.composter.fill")
    ToAllPlayerPlaySound(dimensionId, center, "item.bone_meal.use")
    ToAllPlayerGrowthParticle((x + 0.5, y + 0.8, z + 0.5))
    SetNotCreateItem(playerId, handItemDict)
    if probability(ComposterItemDict[item]):
        blockStates["composter_fill_level"] += 1
        ToAllPlayerPlaySound(dimensionId, center, "block.composter.fill_success")
        compFactory.CreateBlockState(levelId).SetBlockStates((x, y, z), blockStates, dimensionId)

