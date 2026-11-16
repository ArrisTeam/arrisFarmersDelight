# -*- coding: utf-8 -*-
"""MushroomColony - 蘑菇菌落：在沃土上随机刻生长，沃土把放着的蘑菇变成菌落（服务端）

年龄 / 状态的对应与概率见 Shared/Rules/ColonyRules.py（JE 年龄 0-3，每次随机刻 25%，只在沃土上长）。
掉落（年龄 0-3 掉 2/3/4/5 个蘑菇，剪刀剪满龄的菌落掉菌落本身）写在 loot_tables/arris_*_mushroom_colony*.json 里。
"""
import random

from .EventRegistry import registerHandler
from .FarmWorld import FarmWorld
from ..Shared.Rules import ColonyRules, FarmEdits


def PlaceColony(world, pos, colonyName):
    """在 pos 放一个新菌落：JE 的菌落年龄 0，对应贴图正好是 stage0 的 growth 2。"""
    world.apply([FarmEdits.block(pos, colonyName),
                 FarmEdits.states(pos, {ColonyRules.GROWTH_STATE: ColonyRules.GROWTH_OF_AGE[0]})])


@registerHandler("BlockRandomTickServerEvent", match=ColonyRules.COLONY_BLOCKS)
def OnMushroomColonyRandomTick(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    world = FarmWorld(args["dimensionId"])
    if world.nameAt(FarmEdits.below(pos)) not in ColonyRules.GROWABLE_ON:
        return
    growth = ColonyRules.tickGrowth(world.growthAt(pos), random)
    if growth is not None:
        world.apply([FarmEdits.states(pos, {ColonyRules.GROWTH_STATE: growth})])
