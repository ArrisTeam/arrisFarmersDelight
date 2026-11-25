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


def _fill(pos, dimensionId):
    """堆肥桶的方块状态和层数（读不到层数是 None）。"""
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId)
    return blockStates, (blockStates or {}).get(FILL)


def _claims(level, itemDict):
    """这一下归不归堆肥桶：手里是能堆肥的、桶没到 8 层（7 层也归：不收、不扣，但也不让别的处理把东西放下）。
    JE ComposterBlock.use：不潜行时方块的 use 先于物品；8 层是取骨粉，交给原版。"""
    return bool(itemDict) and (itemDict["newItemName"], itemDict["newAuxValue"]) in ComposterItemDict and         level is not None and level < Composter.FULL


def _compost(playerId, itemDict, pos, dimensionId, blockStates):
    # 0 层第一件必成，1~6 层按概率涨一层、成不成都扣一件，7 层不收不扣，涨到 7 层后 1 秒变成可取的 8 层（Shared/Rules/Composter.py）
    level = blockStates[FILL]
    if not Composter.accepts(level) or SetPlayerUsedCD(playerId) is True:
        return                                         # 按住右键每刻重发：一下只放一件（JE 的右键间隔 4 刻）；同一下的另一个事件也在这里挡住
    x, y, z = pos
    center = (x + 0.5, y, z + 0.5)
    ToAllPlayerPlaySound(dimensionId, center, "block.composter.fill")
    ToAllPlayerPlaySound(dimensionId, center, "item.bone_meal.use")
    ToAllPlayerGrowthParticle((x + 0.5, y + 0.8, z + 0.5))
    SetNotCreateItem(playerId, itemDict)
    item = (itemDict["newItemName"], itemDict["newAuxValue"])
    after = Composter.nextLevel(level, level > 0 and probability(ComposterItemDict[item]))
    if after > level:
        blockStates[FILL] = after
        ToAllPlayerPlaySound(dimensionId, center, "block.composter.fill_success")
        compFactory.CreateBlockState(levelId).SetBlockStates(pos, blockStates, dimensionId)
        if after == Composter.READY:
            compFactory.CreateGame(levelId).AddTimer(Composter.READY_SECONDS, _ripen, pos, dimensionId)


# 优先级 100：排在野生作物（99）、物品放成方块（98，派）、种水稻（50）之前，见 Server/ModServer.py 的优先级表——
# 派、菌落、填馅南瓜这些能堆肥又能放成方块的东西点堆肥桶，不潜行时归堆肥（JE：方块的 use 在先），不放成方块
@registerHandler("ServerItemUseOnEvent", match=COMPOSTER, priority=100)
def OnUseItemOnComposter(args):
    playerId = args["entityId"]
    if compFactory.CreatePlayer(playerId).isSneaking() is True:
        return                                         # 潜行：JE 不调方块的 use，照常放方块
    pos = (args["x"], args["y"], args["z"])
    blockStates, level = _fill(pos, args["dimensionId"])
    if not _claims(level, args["itemDict"]):
        return
    args["ret"] = True
    _compost(playerId, args["itemDict"], pos, args["dimensionId"], blockStates)
    return True


@registerHandler("ServerBlockUseEvent", match=COMPOSTER)
def OnUseComposter(args):
    playerId = args["playerId"]
    pos = (args["x"], args["y"], args["z"])
    blockStates, level = _fill(pos, args["dimensionId"])
    handItemDict = GetCarriedItem(playerId)
    if not _claims(level, handItemDict):
        return
    args["cancel"] = True                              # 这一下归堆肥（7 层也是：不收，也不放下）
    _compost(playerId, handItemDict, pos, args["dimensionId"], blockStates)


def _ripen(pos, dimensionId):
    # 7 层过 1 秒变成可取的 8 层（引擎自己已经变了、或者被挖掉了就不管）
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dimensionId)
    if not blockStates or blockStates.get(FILL) != Composter.READY:
        return
    blockStates[FILL] = Composter.FULL
    compFactory.CreateBlockState(levelId).SetBlockStates(pos, blockStates, dimensionId)
    ToAllPlayerPlaySound(dimensionId, (pos[0] + 0.5, pos[1], pos[2] + 0.5), "block.composter.ready")

