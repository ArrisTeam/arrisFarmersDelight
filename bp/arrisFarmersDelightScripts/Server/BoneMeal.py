# -*- coding: utf-8 -*-
"""BoneMeal - 对本模组作物使用骨粉、湿润沃土耕地的额外生长（服务端）"""
import random

from .Helpers.Engine import compFactory, levelId, GetBlockName
from .Helpers.Fx import ToAllPlayerPlaySound, ToAllPlayerGrowthParticle
from .Helpers.Player import SetNotCreateItem
from ..Shared.Data.Farming import cropsDict
from ..Shared.Rules import CropGrowth


def _setBlock(pos, name, dimensionId):
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, 0, dimensionId, False, False)


def _boneMealEffect(dimensionId, pos):
    ToAllPlayerPlaySound(dimensionId, pos, "item.bone_meal.use")
    ToAllPlayerGrowthParticle(pos)


def ApplyBoneMeal(playerId, itemDict, blockName, blockPos, dimensionId):
    """对本模组作物使用骨粉。只有真的长了才扣骨粉；返回是否生效。"""
    x, y, z = blockPos
    if blockName in ("arris:budding_tomatoes_stage6", "arris:tomatoes_vine_stage3"):
        # 成熟的番茄：上方有绳子时沿绳子长出一节藤
        if GetBlockName((x, y + 1, z), dimensionId) != "arris:rope":
            return False
        _setBlock((x, y + 1, z), "arris:tomatoes_vine_stage0", dimensionId)
        _boneMealEffect(dimensionId, (x + 0.5, y + 1, z + 0.5))
        SetNotCreateItem(playerId, itemDict)
        return True
    if blockName == "arris:rice_stage3":
        # 成熟的稻苗：上方是空气时长出稻穗，与随机刻长穗的结果一致（下半变为 rice_supporting）
        if GetBlockName((x, y + 1, z), dimensionId) != "minecraft:air":
            return False
        _setBlock((x, y, z), "arris:rice_supporting", dimensionId)
        _setBlock((x, y + 1, z), "arris:rice_upper_crop_stage0", dimensionId)
        _boneMealEffect(dimensionId, (x + 0.5, y + 1, z + 0.5))
        SetNotCreateItem(playerId, itemDict)
        return True
    blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
    growth = blockStates.get("arris:growth") if blockStates else None
    if growth is not None and growth < 7:
        blockStates["arris:growth"] = min(7, growth + random.randint(2, 4))
        compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, blockStates, dimensionId)
        _boneMealEffect(dimensionId, (x + 0.5, y + 0.5, z + 0.5))
        SetNotCreateItem(playerId, itemDict)
        return True
    if blockName in cropsDict:
        return CropAccelerateTheRipening({"blockName": blockName, "playerId": playerId, "itemDict": itemDict,
                                          "dimensionId": dimensionId, "blockPos": blockPos})
    return False


def CropAccelerateTheRipening(data, mode=None):
    """作物催熟：骨粉一次长 2-3 级，湿润沃土耕地每次随机刻额外长 1 级（阶段表见 Shared/Rules/CropGrowth）。

    已成熟或不认识的方块不处理、不扣骨粉；返回是否长了。
    """
    x, y, z = data["blockPos"]
    steps = 1 if mode == "rich_soil_farmland" else random.randint(2, 3)
    newName = CropGrowth.grownName(data["blockName"], steps)
    if newName is None:
        return False
    _setBlock((x, y, z), newName, data["dimensionId"])
    _boneMealEffect(data["dimensionId"], (x + 0.5, y, z + 0.5))
    if data["playerId"]:
        SetNotCreateItem(data["playerId"], data["itemDict"])
    return True
