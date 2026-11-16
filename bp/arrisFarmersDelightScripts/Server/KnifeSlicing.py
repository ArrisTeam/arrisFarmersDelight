# -*- coding: utf-8 -*-
"""KnifeSlicing - 刀切蛋糕、用刀拆派和蛋糕掉切片、用刀拆南瓜掉南瓜片（服务端）

照 JE：
- 手里拿刀右键蛋糕（含插蜡烛的）切下一片，不吃、不耗刀（KnifeItem.onCakeInteraction）；
- 用刀破坏派 / 蛋糕，掉剩下口数的切片（PastrySlicingModifier：slicing_*.json），插蜡烛的蛋糕额外掉 7 片；
- 用刀破坏南瓜（没有精准采集）掉 4 片南瓜片，不掉南瓜（scavenging_pumpkin.json）。
手里拿刀右键派切下一片在 FoodBlocks.py。创造模式破坏方块本来就不掉东西，这里也不补。
"""
import time

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, DestroyEntity, GetBlockEntityData, GetCarriedItem
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import IsKnife
from .Helpers.Player import IsCreative, SetPlayerUsedCD
from ..Shared.Data import Slicing as Data
from ..Shared.Rules import Slicing as Rules
from ..Shared.Rules.MobLoot import SILK_TOUCH, enchantLevel

CAKES = (Data.CAKE,) + Data.CANDLE_CAKES
SLICEABLE = frozenset(CAKES + tuple(Data.pieSliceItems))
AIR = {"name": "minecraft:air"}

# 原版蛋糕要登记后才会触发 ServerBlockUseEvent（用刀右键要抢在"吃蛋糕"之前取消）
for _cake in CAKES:
    compFactory.CreateBlockUseEventWhiteList(levelId).AddBlockItemListenForUseEvent(_cake + ":*")

_tickets = Rules.SliceTickets()


def _knifeInHand(playerId):
    handItemDict = GetCarriedItem(playerId, True)
    if handItemDict and IsKnife(handItemDict["newItemName"]):
        return handItemDict
    return None


def _spawn(dimensionId, blockPos, itemName, count):
    itemDict = {"newItemName": itemName, "newAuxValue": 0, "count": count}
    System.CreateEngineItemEntity(itemDict, dimensionId, (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5))


def _cakeBites(blockPos, dimensionId, aux):
    # 蛋糕已吃口数：优先读方块状态 bite_counter，读不到退回 aux（蛋糕的 aux 就是口数）
    states = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
    if states and "bite_counter" in states:
        return states["bite_counter"]
    return aux or 0


@registerHandler("ServerBlockUseEvent", match=CAKES)
def OnKnifeOnCake(args):
    playerId = args["playerId"]
    if _knifeInHand(playerId) is None:
        return
    args["cancel"] = True          # 手里拿着刀不吃蛋糕
    if SetPlayerUsedCD(playerId) is True:
        return
    blockName = args["blockName"]
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    blockInfo = compFactory.CreateBlockInfo(levelId)
    if blockName == Data.CAKE:
        nextBites = Rules.cakeAfterCut(_cakeBites(blockPos, dimensionId, args.get("aux")))
        if nextBites is None:
            blockInfo.SetBlockNew(blockPos, AIR, 0, dimensionId)
        else:
            compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, {"bite_counter": nextBites}, dimensionId)
    else:
        # 插蜡烛的蛋糕：变成只少了一片的蛋糕，蜡烛掉出来（JE：换成 BITES = 1 的蛋糕再 dropResources）
        blockInfo.SetBlockNew(blockPos, {"name": Data.CAKE}, 0, dimensionId)
        compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, {"bite_counter": 1}, dimensionId)
        _spawn(dimensionId, blockPos, Rules.candleOf(blockName), 1)
    _spawn(dimensionId, blockPos, Data.CAKE_SLICE, 1)
    ToAllPlayerPlaySound(dimensionId, blockPos, Data.SLICE_SOUND)


def _slicesLeft(blockName, blockPos, dimensionId, aux):
    if blockName in Data.pieSliceItems:
        blockEntityData = GetBlockEntityData(dimensionId, blockPos)
        return Rules.pieSlicesLeft(blockEntityData["blockStatus"] if blockEntityData else None)
    if blockName == Data.CAKE:
        return Rules.cakeSlicesLeft(_cakeBites(blockPos, dimensionId, aux))
    return Data.CAKE_BITES         # 插蜡烛的蛋糕：额外 7 片


# 引擎先发"即将破坏"（方块还在，读得到口数），破坏完成才发"已被破坏"；切片等后一个事件到了再掉，破坏被取消就不白掉
@registerHandler("ServerPlayerTryDestroyBlockEvent", match=SLICEABLE)
def OnTryBreakSliceable(args):
    playerId = args["playerId"]
    if IsCreative(playerId) or _knifeInHand(playerId) is None:
        return
    blockName = args["fullName"]
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    drops = Rules.sliceDrops(blockName, _slicesLeft(blockName, blockPos, dimensionId, args.get("auxData")))
    _tickets.put((dimensionId,) + blockPos, drops, playerId, time.time())


@registerHandler("DestroyBlockEvent", match=SLICEABLE)
def OnBrokeSliceable(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    for itemName, count in _tickets.take((dimensionId,) + blockPos, args["playerId"], time.time()):
        _spawn(dimensionId, blockPos, itemName, count)


@registerHandler("DestroyBlockEvent", match=Data.PUMPKIN)
def OnBrokePumpkin(args):
    # 用刀破坏南瓜（没有精准采集）：南瓜换成 4 片南瓜片。只在真的拿掉了掉出来的南瓜时才补片，免得两样都有
    playerId = args["playerId"]
    handItemDict = None if IsCreative(playerId) else _knifeInHand(playerId)
    if handItemDict is None or enchantLevel(handItemDict, SILK_TOUCH) > 0:
        return
    itemComp = compFactory.CreateItem(levelId)
    removed = False
    for entityId in args["dropEntityIds"] or []:
        dropped = itemComp.GetDroppedItem(entityId)
        if dropped and dropped["newItemName"] == Data.PUMPKIN:
            DestroyEntity(entityId)
            removed = True
    if removed:
        _spawn(args["dimensionId"], (args["x"], args["y"], args["z"]), Data.PUMPKIN_SLICE, Data.PUMPKIN_SLICES)
