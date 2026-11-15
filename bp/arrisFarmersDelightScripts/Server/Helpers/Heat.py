# -*- coding: utf-8 -*-
"""Heat - 厨锅 / 煎锅下方的热源与支架判断（服务端）"""
from .Engine import compFactory, levelId, GetBlockName
from .Fx import ToAllPlayerBlockMolang
from ...Shared.Data.Cooking import CanProvideHeatBlockList

# 厨锅 / 煎锅放在这些方块上时显示支架模型
ShelfBlockSet = frozenset(["minecraft:fire", "minecraft:campfire", "minecraft:soul_fire", "minecraft:soul_campfire",
                           "minecraft:lava", "minecraft:flowing_lava"])

# 营火类方块熄灭时名字不变，只是 extinguished 状态为 True
_CAMPFIRE_BLOCKS = frozenset(["minecraft:campfire", "minecraft:soul_campfire"])


def IsHeatSource(blockPos, dimensionId, blockName=None):
    """该位置的方块能否提供热量：在 CanProvideHeatBlockList 里（下游可追加），营火还要是点燃的。"""
    if blockName is None:
        blockName = GetBlockName(blockPos, dimensionId)
    if blockName not in CanProvideHeatBlockList:
        return False
    if blockName in _CAMPFIRE_BLOCKS:
        states = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
        if states and states.get("extinguished") is True:
            return False
    return True


def RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName, delay=0.0):
    """按下方方块刷新"支架""加热"两个状态，并同步给客户端的方块实体 molang；返回是否有热源。

    delay > 0 时延后发送（方块刚放下时客户端的方块实体还没建好）。
    """
    blockEntityData["shelfEnable"] = 1.0 if belowName in ShelfBlockSet else 0.0
    heat = IsHeatSource(belowPos, dimensionId, belowName)
    blockEntityData["heatEnable"] = heat
    blockEntityData["heatParticleEnable"] = 1.0 if heat else 0.0
    pairs = (("variable.mod_shelf", blockEntityData["shelfEnable"]), ("variable.mod_heat", blockEntityData["heatParticleEnable"]))
    for name, value in pairs:
        if delay > 0:
            compFactory.CreateGame(levelId).AddTimer(delay, ToAllPlayerBlockMolang, blockPos, name, value)
        else:
            ToAllPlayerBlockMolang(blockPos, name, value)
    return heat
