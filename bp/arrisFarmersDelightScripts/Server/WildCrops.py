# -*- coding: utf-8 -*-
"""WildCrops - 野生作物：只能种在指定地面上、地面没了就掉落、上方积雪清掉（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetBlockName
from ..Shared.Data.Farming import WildCropDict
from ..Shared.Rules.Placement import placePositions


def _itemName(args):
    return args["itemDict"]["newItemName"]


@registerHandler("BlockNeighborChangedServerEvent", match=WildCropDict)
def OnWildCropNeighborChanged(args):
    blockName = args["blockName"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimensionId"]
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    neighborName = args["toBlockName"]
    if neighborPos == (args["posX"], args["posY"] - 1, args["posZ"]) and neighborName not in WildCropDict[blockName]:
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)
    if neighborName == "minecraft:snow_layer" and neighborPos == (args["posX"], args["posY"] + 1, args["posZ"]):
        # 上方积了一层雪时把雪清掉
        compFactory.CreateBlockInfo(levelId).SetBlockNew(neighborPos, {"name": "minecraft:air"}, 0, dimensionId, False, False)


# 优先级 99：排在物品放置（98）之前（与旧版同一函数里的顺序一致）
@registerHandler("ServerItemUseOnEvent", match=WildCropDict, keyOf=_itemName, priority=99)
def OnPlaceWildCrop(args):
    # 拿着野生作物对方块使用：放置位置的下方不是允许的地面就取消
    itemName = _itemName(args)
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    pos = placePositions(x, y, z)[args["face"]]
    groundName = GetBlockName((pos[0], pos[1] - 1, pos[2]), dimensionId)
    if groundName not in WildCropDict[itemName]:
        args["ret"] = True
    if itemName == "arris:wild_rice":
        # 野生稻米要求上方是空气（两格高）
        if GetBlockName((pos[0], pos[1] + 1, pos[2]), dimensionId) != "minecraft:air":
            args["ret"] = True
