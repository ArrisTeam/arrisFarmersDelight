# -*- coding: utf-8 -*-
"""ItemToBlock - 煎锅物品、整块的派对方块使用时放成方块（服务端）

以前煎锅的放置逻辑有两份（这里和 skillet.py 各一份），只靠共用的交互冷却互斥；现在只留这一份。
原版南瓜派（minecraft:pumpkin_pie）也走这里，照 JE 的 PlacePumpkinPieMixin：对方块使用要么放成方块、要么放不下，
都不会落到"吃"；只有配置要求潜行（缺省不要求）而玩家没潜行时才交给原版去吃。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetBlockName
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Placement import DetectionExperimentalHoliday
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem
from ..Shared.Data import Food
from ..Shared.Data.Food import itemChangeBlockDict, pieList
from ..Shared.Rules.Placement import auxFromAngle, placePositions, placesPumpkinPie

# 点在这些方块上时不放置（展示框要放物品，砧板要把物品摆上去）
_SKIP_BLOCKS = ("minecraft:frame", "minecraft:glow_frame", "arris:cutting_board")


def _itemName(args):
    return args["itemDict"]["newItemName"]


# 优先级 98：排在野生作物检查（99）之后、作物 / 水稻 / 骨粉（50）之前，与旧版顺序一致
@registerHandler("ServerItemUseOnEvent", match=itemChangeBlockDict, keyOf=_itemName, priority=98)
def OnPlaceItemAsBlock(args):
    if args["blockName"] in _SKIP_BLOCKS:
        return
    itemDict = args["itemDict"]
    itemName = itemDict["newItemName"]
    playerId = args["entityId"]
    if itemName == Food.PUMPKIN_PIE:
        if not placesPumpkinPie(compFactory.CreatePlayer(playerId).isSneaking(), Food.PUMPKIN_PIE_SNEAK_TO_PLACE):
            return
        args["ret"] = True       # 按住右键每刻重发：冷却内、放不下的时候也要取消，不然会开始吃
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    setPos = placePositions(x, y, z)[args["face"]]
    pX, pY, pZ = compFactory.CreatePos(playerId).GetFootPos()
    facing = auxFromAngle(x, z, pX, pZ)
    blockAux = DetectionExperimentalHoliday().get(facing, facing)
    if GetBlockName(setPos, dimensionId) != "minecraft:air":
        return
    blockName = itemChangeBlockDict[itemName]
    SetNotCreateItem(playerId, itemDict)
    compFactory.CreateBlockInfo(levelId).SetBlockNew(setPos, {"name": blockName}, 0, dimensionId)
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(setPos, dimensionId)
    if blockStates:
        blockStates["direction"] = blockAux
        compFactory.CreateBlockState(levelId).SetBlockStates(setPos, blockStates, dimensionId)
    blockEntityData = GetBlockEntityData(dimensionId, setPos)
    if blockEntityData and blockName in pieList:
        ToAllPlayerPlaySound(dimensionId, setPos, "dig.cloth")
        blockEntityData["blockStatus"] = 0.0
        blockEntityData["setMolang"] = False
