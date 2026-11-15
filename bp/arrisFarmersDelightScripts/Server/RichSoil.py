# -*- coding: utf-8 -*-
"""RichSoil - 沃土与沃土耕地：锄地、种原版作物、湿润 / 干燥、湿润时给上方作物加速（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetBlockName
from .Helpers.Fx import ToAllPlayerPlaySound, ToAllPlayerGrowthParticle
from .Helpers.Items import GetItemType
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem, SetCarriedDurability
from .Crops import CropAccelerateTheRipening
from ..Shared.Data.Farming import cropsDict

RICH_SOIL = "arris:rich_soil"
FARMLAND = "arris:rich_soil_farmland"
FARMLAND_MOIST = "arris:rich_soil_farmland_moist"
# 水平方向这么远以内有水就湿润（与原版耕地一致：4 格）
WATER_RANGE = 4
_WATER = ("minecraft:water", "minecraft:flowing_water")
# 沃土耕地上种原版作物：种子 → 对应的沃土作物方块
SEEDS = {
    "minecraft:wheat_seeds": "arris:rich_soil_wheat0",
    "minecraft:beetroot_seeds": "arris:rich_soil_beetroot0",
    "minecraft:potato": "arris:rich_soil_potatoes0",
    "minecraft:carrot": "arris:rich_soil_carrots0",
    "minecraft:torchflower_seeds": "arris:rich_soil_torchflower0",
}


def _setBlock(pos, name, dimensionId):
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, 0, dimensionId, False, False)


def _hasWaterNearby(x, y, z, dimensionId):
    comp = compFactory.CreateBlockInfo(levelId)
    for dx in range(-WATER_RANGE, WATER_RANGE + 1):
        for dz in range(-WATER_RANGE, WATER_RANGE + 1):
            if dx == 0 and dz == 0:
                continue
            blockDict = comp.GetLiquidBlock((x + dx, y, z + dz), dimensionId)
            if blockDict and blockDict["name"] in _WATER:
                return True
    return False


@registerHandler("BlockRandomTickServerEvent", match=FARMLAND)
def OnDryFarmlandRandomTick(args):
    x, y, z = args["posX"], args["posY"], args["posZ"]
    if _hasWaterNearby(x, y, z, args["dimensionId"]):
        _setBlock((x, y, z), FARMLAND_MOIST, args["dimensionId"])


@registerHandler("BlockRandomTickServerEvent", match=FARMLAND_MOIST)
def OnMoistFarmlandRandomTick(args):
    x, y, z = args["posX"], args["posY"], args["posZ"]
    dimensionId = args["dimensionId"]
    if not _hasWaterNearby(x, y, z, dimensionId):
        _setBlock((x, y, z), FARMLAND, dimensionId)
    # 湿润时给上方作物额外长一级
    upPos = (x, y + 1, z)
    upName = GetBlockName(upPos, dimensionId)
    if upName in cropsDict:
        CropAccelerateTheRipening({"blockName": upName, "playerId": None, "itemDict": None,
                                   "dimensionId": dimensionId, "blockPos": upPos}, "rich_soil_farmland")
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(upPos, dimensionId)
    if blockStates:
        growth = blockStates.get("arris:growth")
        if growth and growth < 7:
            blockStates["arris:growth"] += 1
            compFactory.CreateBlockState(levelId).SetBlockStates(upPos, blockStates, dimensionId)
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1.5, z + 0.5), "item.bone_meal.use")
            ToAllPlayerGrowthParticle((x + 0.5, y + 1.5, z + 0.5))


@registerHandler("ItemUseOnAfterServerEvent", match=RICH_SOIL)
def OnHoeRichSoil(args):
    playerId = args["entityId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    itemDict = args["itemDict"]
    if GetItemType(itemDict) == "hoe":
        pos = (args["x"], args["y"], args["z"])
        SetCarriedDurability(playerId, itemDict, args["dimensionId"], pos)
        _setBlock(pos, FARMLAND, args["dimensionId"])
        ToAllPlayerPlaySound(args["dimensionId"], pos, "use.gravel")


@registerHandler("ItemUseOnAfterServerEvent", match=(FARMLAND, FARMLAND_MOIST))
def OnPlantOnRichFarmland(args):
    playerId = args["entityId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    itemDict = args["itemDict"]
    if args["face"] != 1 or GetBlockName((x, y + 1, z), dimensionId) != "minecraft:air":
        return
    cropBlock = SEEDS.get(itemDict["newItemName"])
    if cropBlock:
        _setBlock((x, y + 1, z), cropBlock, dimensionId)
        ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "dig.grass")
        SetNotCreateItem(playerId, itemDict)
