# -*- coding: utf-8 -*-
"""BoneMeal - 骨粉对本模组植物的效果，沃土催熟也走这里（服务端）

效果本身照 JE 的 BonemealableBlock 写在 Shared/Rules/BoneMealRules.py（纯规则、离线测试）；
这里只负责读世界、把修改落地、放特效、扣骨粉。
"""
import random

from .FarmWorld import FarmWorld
from .Helpers.Fx import ToAllPlayerPlaySound, ToAllPlayerGrowthParticle
from .Helpers.Player import SetNotCreateItem
from ..Shared.Data.Farming import UNAFFECTED_BY_RICH_SOIL
from ..Shared.Rules import BoneMealRules


def _boneMealEffect(dimensionId, pos):
    ToAllPlayerPlaySound(dimensionId, pos, "item.bone_meal.use")
    ToAllPlayerGrowthParticle(pos)


def ApplyBoneMeal(playerId, itemDict, blockName, blockPos, dimensionId):
    """对本模组植物使用骨粉。JE 认的合法目标才用掉骨粉（效果没出来也算用掉，比如野生作物 20% 不长）；返回是否用掉。"""
    world = FarmWorld(dimensionId)
    valid, edits = BoneMealRules.boneMeal(world, blockName, blockPos, random)
    if not valid:
        return False
    world.apply(edits)
    x, y, z = blockPos
    _boneMealEffect(dimensionId, (x + 0.5, y + 0.5, z + 0.5))
    SetNotCreateItem(playerId, itemDict)
    return True


def BoostPlant(world, plantPos):
    """沃土 / 沃土耕地催熟 plantPos 的植物（RichSoilBlock.boostPlant）：不受影响的、不是合法目标的不动；返回是否催熟了。"""
    name = world.nameAt(plantPos)
    if name in UNAFFECTED_BY_RICH_SOIL:
        return False
    valid, edits = BoneMealRules.boneMeal(world, name, plantPos, random)
    if not valid:
        return False
    world.apply(edits)
    x, y, z = plantPos
    _boneMealEffect(world.dimensionId, (x + 0.5, y + 0.5, z + 0.5))
    return True
