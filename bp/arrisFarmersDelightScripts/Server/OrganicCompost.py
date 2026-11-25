# -*- coding: utf-8 -*-
"""OrganicCompost - 有机肥的随机刻：按周围的催化剂、天空和水堆沤成沃土（服务端）

概率与阶段换算在 Shared/Rules/CompostRules.py（OrganicCompostBlock.randomTick）。
JE 取 3×3×3 里每格上方的天空光，最大值 > 12 算露天；这里没有直接读天空光的接口，
改成看这 9 列里有没有一列最高的非空气方块不高过有机肥上方一格（上面只有一棵植物也算露天）。
催化剂是名单 COMPOST_ACTIVATORS ∪ 方块标签 farmersdelight:compost_activators（名单原样留着，不在名单里的再看标签）。
"""
import random

from .EventRegistry import registerHandler
from .FarmWorld import FarmWorld
from ..Shared.Data import Tags
from ..Shared.Data.Farming import COMPOST_ACTIVATORS
from ..Shared.Rules import CompostRules, FarmEdits, ItemTags


def _skyOpen(world, x, y, z):
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            top = world.topHeightAt(x + dx, z + dz)
            if top is None or top <= y + 1:
                return True
    return False


@registerHandler("BlockRandomTickServerEvent", match=CompostRules.COMPOST_STAGES)
def OnOrganicCompostRandomTick(args):
    blockName = args["fullName"]
    x, y, z = args["posX"], args["posY"], args["posZ"]
    world = FarmWorld(args["dimensionId"])
    activators = 0
    hasWater = False
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                cell = (x + dx, y + dy, z + dz)
                if ItemTags.blockListed(world.nameAt(cell), COMPOST_ACTIVATORS, Tags.COMPOST_ACTIVATORS):
                    activators += 1
                if not hasWater and world.hasWaterAt(cell):
                    hasWater = True
    chance = CompostRules.stageChance(activators, _skyOpen(world, x, y, z), hasWater)
    if random.random() < chance:
        world.apply([FarmEdits.block((x, y, z), CompostRules.nextBlock(blockName))])
