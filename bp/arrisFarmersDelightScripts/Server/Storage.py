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
from ..Shared.Rules import Composter
from ..Shared.Rules.Ticks import probability

COMPOSTER = "minecraft:composter"
FILL = "composter_fill_level"

# 原版堆肥桶要登记后才会触发 ServerBlockUseEvent
compFactory.CreateBlockUseEventWhiteList(levelId).AddBlockItemListenForUseEvent(COMPOSTER + ":*")


@registerHandler("ServerBlockUseEvent", match=cabinetList)
def OnOpenCabinet(args):
    if SetPlayerUsedCD(args["playerId"]) is True:
        return
    ToAllPlayerPlaySound(args["dimensionId"], (args["x"], args["y"], args["z"]), "block.barrel.open")


@registerHandler("ServerBlockUseEvent", match=COMPOSTER)
def OnUseComposter(args):
    # JE ComposterBlock（基岩原版实测一样）：0 层第一件必成，7 层不收不扣，涨到 7 层后 1 秒变成可取的 8 层（规则在 Shared/Rules/Composter.py）
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates((x, y, z), dimensionId)
    level = blockStates[FILL]
    if not Composter.accepts(level):
        return
    handItemDict = GetCarriedItem(playerId)
    if not handItemDict:
        return
    item = (handItemDict["newItemName"], handItemDict["newAuxValue"])
    if item not in ComposterItemDict:
        return
    if SetPlayerUsedCD(playerId) is True:
        return                                         # 按住右键每刻重发：一下只放一件（JE 的右键间隔 4 刻）
    center = (x + 0.5, y, z + 0.5)
    ToAllPlayerPlaySound(dimensionId, center, "block.composter.fill")
    ToAllPlayerPlaySound(dimensionId, center, "item.bone_meal.use")
    ToAllPlayerGrowthParticle((x + 0.5, y + 0.8, z + 0.5))
    SetNotCreateItem(playerId, handItemDict)
    after = Composter.nextLevel(level, level > 0 and probability(ComposterItemDict[item]))
    if after > level:
        blockStates[FILL] = after
        ToAllPlayerPlaySound(dimensionId, center, "block.composter.fill_success")
        compFactory.CreateBlockState(levelId).SetBlockStates((x, y, z), blockStates, dimensionId)
        if after == Composter.READY:
            compFactory.CreateGame(levelId).AddTimer(Composter.READY_SECONDS, _ripen, (x, y, z), dimensionId)


def _ripen(pos, dimensionId):
    # 7 层过 1 秒变成可取的 8 层（引擎自己已经变了、或者被挖掉了就不管）
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId)
    if not blockStates or blockStates.get(FILL) != Composter.READY:
        return
    blockStates[FILL] = Composter.FULL
    compFactory.CreateBlockState(levelId).SetBlockStates(pos, blockStates, dimensionId)
    ToAllPlayerPlaySound(dimensionId, (pos[0] + 0.5, pos[1], pos[2] + 0.5), "block.composter.ready")

