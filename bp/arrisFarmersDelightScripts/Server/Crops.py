# -*- coding: utf-8 -*-
"""Crops - 作物：随机刻生长、骨粉、采摘、种水稻、蘑菇菌落、杂草掉稻草（服务端）

沃土 / 沃土耕地见 Server/RichSoil.py，野生作物见 Server/WildCrops.py。
"""
import random

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, DestroyEntity, GetBlockName, GetCarriedItem, ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem
from .BoneMeal import ApplyBoneMeal
from ..Shared.Data.Farming import cropsDict
from ..Shared.Rules.Ticks import probability

# 这几种成熟作物右键采摘，不让手里的物品在它们上面生效
_HARVESTABLE = ("arris:cabbages_stage7", "arris:budding_tomatoes_stage6", "arris:tomatoes_vine_stage3")
_MUSHROOM_COLONIES = ("arris:red_mushroom_colony", "arris:brown_mushroom_colony")
_RICE_UPPER = ("arris:rice_upper_crop_stage0", "arris:rice_upper_crop_stage1", "arris:rice_upper_crop_stage2",
               "arris:rice_upper_crop_stage3")
_CROP_GROUND = ("minecraft:farmland", "arris:rich_soil_farmland_moist", "arris:rich_soil_farmland", "minecraft:grass_block")
# 稻米脚下：JE 的 minecraft:dirt 方块标签（FD 把沃土也加了进去）加上耕地（RiceBlock.mayPlaceOn）
_RICE_GROUND = ("minecraft:dirt", "minecraft:grass_block", "minecraft:podzol", "minecraft:coarse_dirt", "minecraft:mycelium",
                "minecraft:dirt_with_roots", "minecraft:moss_block", "minecraft:mud", "minecraft:muddy_mangrove_roots",
                "arris:rich_soil", "minecraft:farmland", "arris:rich_soil_farmland", "arris:rich_soil_farmland_moist")
_RICE_STAGES = ("arris:rice_stage0", "arris:rice_stage1", "arris:rice_stage2", "arris:rice_stage3")
_MUSHROOM_GROUND = ("arris:organic_compost_stage0", "arris:organic_compost_stage1", "arris:organic_compost_stage2",
                    "arris:organic_compost_stage3", "arris:rich_soil")
# 破坏时有概率掉稻草的方块
_STRAW_SOURCES = ("minecraft:fern", "minecraft:large_fern", "minecraft:short_grass", "minecraft:tall_grass",
                  "arris:sandy_shrub", "arris:rich_soil_wheat7", "arris:rice_upper_crop_stage3", "arris:rice_supporting")
STRAW_CHANCE = 30
SILK_TOUCH = 16


def _below(args):
    return (args["posX"], args["posY"] - 1, args["posZ"])


def _setBlock(pos, name, dimensionId, handling=0):
    if handling:
        compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, handling, dimensionId)
    else:
        compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, 0, dimensionId, False, False)


# ---------------- 方块变化 ----------------

@registerHandler("BlockNeighborChangedServerEvent", match=cropsDict)
def OnCropNeighborChanged(args):
    # 下方不再是耕地 / 草方块（稻米：泥土类 / 耕地，水下的草方块会退化成泥土）时作物掉落
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    ground = _RICE_GROUND if args["blockName"] in _RICE_STAGES else _CROP_GROUND
    if neighborPos == _below(args) and args["toBlockName"] not in ground:
        _setBlock((args["posX"], args["posY"], args["posZ"]), "minecraft:air", args["dimensionId"], handling=1)


@registerHandler("BlockNeighborChangedServerEvent", match="arris:rice_supporting")
def OnRiceSupportingNeighborChanged(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    neighborName = args["toBlockName"]
    if neighborPos == _below(args):
        if neighborName not in _RICE_GROUND:
            _setBlock(blockPos, "minecraft:air", args["dimensionId"], handling=1)
    elif neighborPos == (args["posX"], args["posY"] + 1, args["posZ"]):
        # 稻穗没了：下半回到成熟的稻苗
        if neighborName not in _RICE_UPPER:
            _setBlock(blockPos, "arris:rice_stage3", args["dimensionId"])


@registerHandler("BlockNeighborChangedServerEvent", match=_MUSHROOM_COLONIES)
def OnMushroomColonyNeighborChanged(args):
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos == _below(args):
        _setBlock((args["posX"], args["posY"], args["posZ"]), "minecraft:air", args["dimensionId"], handling=1)


# ---------------- 随机刻生长 ----------------

@registerHandler("BlockRandomTickServerEvent", match=cropsDict)
def OnCropRandomTick(args):
    # 光照 9-15 时长一级；成熟的番茄沿上方的绳子长藤，成熟的稻苗长出稻穗
    if not 9 <= args["brightness"] <= 15:
        return
    blockName = args["fullName"]
    x, y, z = args["posX"], args["posY"], args["posZ"]
    dimensionId = args["dimensionId"]
    if blockName in ("arris:budding_tomatoes_stage6", "arris:tomatoes_vine_stage3"):
        if GetBlockName((x, y + 1, z), dimensionId) == "arris:rope":
            _setBlock((x, y + 1, z), "arris:tomatoes_vine_stage0", dimensionId)
    elif blockName == "arris:rice_stage3":
        if GetBlockName((x, y + 1, z), dimensionId) == "minecraft:air":
            _setBlock((x, y, z), "arris:rice_supporting", dimensionId)
            _setBlock((x, y + 1, z), "arris:rice_upper_crop_stage0", dimensionId)
    elif cropsDict[blockName]:
        # 成熟阶段（以及沃土）在 cropsDict 里映射到空字符串，不再往下长
        _setBlock((x, y, z), cropsDict[blockName], dimensionId)


@registerHandler("BlockRandomTickServerEvent", match=_MUSHROOM_COLONIES)
def OnMushroomColonyRandomTick(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(pos, args["dimensionId"])
    growth = blockStates.get("arris:growth") if blockStates else None
    if growth is not None and growth < 7:
        blockStates["arris:growth"] += 1
        compFactory.CreateBlockState(levelId).SetBlockStates(pos, blockStates, args["dimensionId"])


# ---------------- 对方块使用物品 ----------------

# 优先级 100：在其它 ServerItemUseOnEvent 处理之前取消物品使用（右键是采摘）
@registerHandler("ServerItemUseOnEvent", match=_HARVESTABLE, priority=100)
def OnUseItemOnHarvestable(args):
    args["ret"] = True


# 优先级 50：排在物品放置（98）之后、炉灶（10）之前，与旧版模块加载顺序一致（见 Server/ModServer.py）
@registerHandler("ServerItemUseOnEvent", priority=50)
def OnServerItemUse(args):
    itemDict = args["itemDict"]
    itemName = itemDict["newItemName"]
    dimensionId = args["dimensionId"]
    x, y, z = args["x"], args["y"], args["z"]
    playerId = args["entityId"]
    blockName = args["blockName"]
    face = args["face"]
    if itemName == "arris:rice":
        if SetPlayerUsedCD(playerId) is True:
            return
        _plantRice(playerId, itemDict, blockName, face, (x, y, z), dimensionId)
    elif itemName == "minecraft:bone_meal":
        if SetPlayerUsedCD(playerId) is True:
            return
        ApplyBoneMeal(playerId, itemDict, blockName, (x, y, z), dimensionId)
    elif face == 1 and blockName in _MUSHROOM_GROUND and itemName in ("minecraft:brown_mushroom", "minecraft:red_mushroom"):
        # 蘑菇放在有机肥 / 沃土上长成蘑菇菌落
        if SetPlayerUsedCD(playerId) is True:
            return
        SetNotCreateItem(playerId, itemDict)
        ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 0.5, z + 0.5), "dig.grass")
        colony = "arris:brown_mushroom_colony" if itemName == "minecraft:brown_mushroom" else "arris:red_mushroom_colony"
        _setBlock((x, y + 1, z), colony, dimensionId)


def _plantRice(playerId, itemDict, blockName, face, pos, dimensionId):
    x, y, z = pos
    if blockName not in _RICE_GROUND or face != 1:
        return                           # 和 JE 的 RiceItem 一样：不是泥土类 / 耕地的顶面就不提示
    if GetBlockName((x, y + 1, z), dimensionId) != "minecraft:water":
        ShowTip(playerId, "这株作物很难在水洼外生存。")
        return
    SetNotCreateItem(playerId, itemDict)
    ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 1, z + 0.5), "dig.grass")
    _setBlock((x, y + 1, z), "arris:rice_stage0", dimensionId)


# ---------------- 采摘 ----------------

@registerHandler("ServerBlockUseEvent", match=("arris:budding_tomatoes_stage6", "arris:tomatoes_vine_stage3"))
def OnTomatoUse(args):
    x, y, z = args["x"], args["y"], args["z"]
    blockName = args["blockName"]
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    carriedDict = GetCarriedItem(playerId) or {}
    if carriedDict.get("newItemName") == "minecraft:bone_meal":
        # 和 ServerItemUseOnEvent 那条路径共用：谁先触发谁处理（冷却挡住另一条）
        ApplyBoneMeal(playerId, carriedDict, blockName, (x, y, z), dimensionId)
    else:
        dropPos = (x + 0.5, y, z + 0.5)
        System.CreateEngineItemEntity({"itemName": "arris:tomato", "count": random.randint(1, 2)}, dimensionId, dropPos)
        ToAllPlayerPlaySound(dimensionId, dropPos, "block.sweet_berry_bush.pick")
        nextName = "arris:budding_tomatoes_stage3" if blockName == "arris:budding_tomatoes_stage6" else "arris:tomatoes_vine_stage0"
        _setBlock((x, y, z), nextName, dimensionId)
    # ServerBlockUseEvent 的拦截字段是 cancel（ret 属于 ServerItemUseOnEvent）
    args["cancel"] = True


@registerHandler("ServerBlockUseEvent", match="arris:cabbages_stage7")
def OnCabbageUse(args):
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    if SetPlayerUsedCD(args["playerId"]) is True:
        return
    dropPos = (x + 0.5, y, z + 0.5)
    System.CreateEngineItemEntity({"itemName": "arris:cabbage_leaf", "count": random.randint(1, 2)}, dimensionId, dropPos)
    ToAllPlayerPlaySound(dimensionId, dropPos, "block.sweet_berry_bush.pick")
    _setBlock((x, y, z), "arris:cabbages_stage3", dimensionId)
    args["cancel"] = True


@registerHandler("ServerBlockUseEvent", match="arris:rice_stage3")
def OnRiceUse(args):
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    carriedDict = GetCarriedItem(playerId)
    if carriedDict and carriedDict.get("newItemName") == "minecraft:bone_meal":
        ApplyBoneMeal(playerId, carriedDict, args["blockName"], (args["x"], args["y"], args["z"]), args["dimensionId"])


# ---------------- 破坏 ----------------

@registerHandler("DestroyBlockEvent", match=_STRAW_SOURCES)
def OnDestroyStrawSource(args):
    # 生存模式下破坏杂草 / 成熟麦子 / 稻穗有概率掉稻草
    playerId = args["playerId"]
    if compFactory.CreateGame(levelId).GetPlayerGameType(playerId) == 1:
        return
    if probability(STRAW_CHANCE):
        pos = (args["x"] + 0.5, args["y"], args["z"] + 0.5)
        System.CreateEngineItemEntity({"itemName": "arris:straw", "count": 1, "auxValue": 0}, args["dimensionId"], pos)


@registerHandler("DestroyBlockEvent", match=_MUSHROOM_COLONIES)
def OnDestroyMushroomColony(args):
    # 精准采集挖蘑菇菌落不掉落
    handItemDict = GetCarriedItem(args["playerId"], True)
    if handItemDict is None:
        return
    for enchant in handItemDict.get("enchantData") or []:
        if enchant[0] == SILK_TOUCH:
            for entityId in args["dropEntityIds"]:
                DestroyEntity(entityId)
            return
