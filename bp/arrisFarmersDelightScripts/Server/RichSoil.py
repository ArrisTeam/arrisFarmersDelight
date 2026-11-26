# -*- coding: utf-8 -*-
"""RichSoil - 沃土与沃土耕地：锄地、种原版作物、湿润 / 干燥、满湿时催熟上方作物、蘑菇变菌落（服务端）

概率与范围见 Shared/Rules/RichSoilRules.py（JE 的 RichSoilBlock / RichSoilFarmlandBlock）：
附近（水平 4 格、竖直 0 到 +1）有水或正下雨就湿润；湿润的沃土耕地和沃土每次随机刻 20% 给上方植物催熟一次（同骨粉）。
"""
import random

from .BoneMeal import BoostPlant
from .EventRegistry import registerHandler
from .FarmWorld import FarmWorld
from .Helpers import Deeds
from .Helpers.Engine import GetBlockName
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import GetItemType
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem, SetCarriedDurability
from .MushroomColony import PlaceColony
from ..Shared.Rules import ColonyRules, FarmEdits, RichSoilRules

RICH_SOIL = "arris:rich_soil"
FARMLAND = "arris:rich_soil_farmland"
FARMLAND_MOIST = "arris:rich_soil_farmland_moist"
# 沃土耕地上种原版作物：种子 → 对应的沃土作物方块
SEEDS = {
    "minecraft:wheat_seeds": "arris:rich_soil_wheat0",
    "minecraft:beetroot_seeds": "arris:rich_soil_beetroot0",
    "minecraft:potato": "arris:rich_soil_potatoes0",
    "minecraft:carrot": "arris:rich_soil_carrots0",
    "minecraft:torchflower_seeds": "arris:rich_soil_torchflower0",
}


def _setBlock(pos, name, dimensionId):
    FarmWorld(dimensionId).apply([FarmEdits.block(pos, name)])


def _hydrated(world, pos):
    """RichSoilFarmlandBlock：附近有水，或者头顶正下着雨。"""
    if world.rainingAt(pos):
        return True
    for cell in RichSoilRules.hydrationCells(pos):
        if world.hasWaterAt(cell):
            return True
    return False


def _tryBoost(world, pos):
    if random.random() < RichSoilRules.boostChance():
        BoostPlant(world, FarmEdits.above(pos))


@registerHandler("BlockRandomTickServerEvent", match=RICH_SOIL)
def OnRichSoilRandomTick(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    world = FarmWorld(args["dimensionId"])
    abovePos = FarmEdits.above(pos)
    colony = ColonyRules.MUSHROOM_TO_COLONY.get(world.nameAt(abovePos))
    if colony is not None:
        PlaceColony(world, abovePos, colony)
        return
    _tryBoost(world, pos)


@registerHandler("BlockRandomTickServerEvent", match=FARMLAND)
def OnDryFarmlandRandomTick(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    world = FarmWorld(args["dimensionId"])
    if _hydrated(world, pos):
        world.apply([FarmEdits.block(pos, FARMLAND_MOIST)])


@registerHandler("BlockRandomTickServerEvent", match=FARMLAND_MOIST)
def OnMoistFarmlandRandomTick(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    world = FarmWorld(args["dimensionId"])
    if _hydrated(world, pos):
        _tryBoost(world, pos)
    elif random.random() < RichSoilRules.dryChance():
        world.apply([FarmEdits.block(pos, FARMLAND)])


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
        Deeds.done(playerId, Deeds.PLACED_BLOCK, cropBlock)
