# -*- coding: utf-8 -*-
"""ItemToBlock - 煎锅物品、整块的派对方块使用时放成方块（服务端）

以前煎锅的放置逻辑有两份（这里和 skillet.py 各一份），只靠共用的交互冷却互斥；现在只留这一份。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetBlockName
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Placement import DetectionExperimentalHoliday
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem
from ..Shared.Data.Food import itemChangeBlockDict, pieList
from ..Shared.Rules.Placement import auxFromAngle, placePositions

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
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    playerId = args["entityId"]
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
