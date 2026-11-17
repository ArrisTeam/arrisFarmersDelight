# -*- coding: utf-8 -*-
"""Heat - 厨锅 / 煎锅下方的热源与支架判断（服务端）

热源照 FD 的 HeatableBlockEntity.isHeated（java:15-36，厨锅和煎锅共用）：正下方一格是热源（标签 heat_sources：岩浆块、熔岩炼药锅、炉灶、熔岩、营火、火；
带 LIT 状态的要点着才算）就热；正下方是传热方块（标签 heat_conductors：漏斗）时，改看再下面一格是不是热源，所以漏斗下面的火也烧得热上面的锅。
基岩版里的对应：熔岩炼药锅没有自己的方块（引擎里没有 lava_cauldron），是 cauldron 的状态 cauldron_liquid = lava；营火的 LIT 是 extinguished 取反；
炉灶的 LIT 是两个方块（点着的 arris:stove 在 CanProvideHeatBlockList 里，熄着的孪生方块不在）。
支架（托盘）只认正下方那一格：CookingPotBlock.getTrayState / SkilletBlock 只看 pos.below() 是不是 tray_heat_sources（熔岩、营火、火），
所以漏斗再下面有火也不画托盘，和 JE 一样；传热的那一格变了没有邻居事件，由 Server/HeatConduct.py 隔一会儿去看。
"""
from .Engine import compFactory, levelId, GetBlockName
from .Fx import ToAllPlayerBlockMolang
from ...Shared.Data.Cooking import CanProvideHeatBlockList, HeatConductorList

# 厨锅 / 煎锅放在这些方块上时显示支架模型
ShelfBlockSet = frozenset(["minecraft:fire", "minecraft:campfire", "minecraft:soul_fire", "minecraft:soul_campfire",
                           "minecraft:lava", "minecraft:flowing_lava"])

# 营火类方块熄灭时名字不变，只是 extinguished 状态为 True
_CAMPFIRE_BLOCKS = frozenset(["minecraft:campfire", "minecraft:soul_campfire"])
_CAULDRON = "minecraft:cauldron"


def _states(blockPos, dimensionId):
    """方块状态字典，读不到是空字典（基岩版只有服务端读得到方块状态）。"""
    return compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId) or {}


def _holdsLava(blockPos, dimensionId):
    """熔岩炼药锅（JE 的 lava_cauldron）：基岩版是 cauldron 的 cauldron_liquid 状态为 lava，而且锅里有东西（fill_level > 0，倒空了的不算）。"""
    states = _states(blockPos, dimensionId)
    return states.get("cauldron_liquid") == "lava" and (states.get("fill_level") or 0) > 0


def IsHeatSource(blockPos, dimensionId, blockName=None):
    """该位置的方块能否提供热量：在 CanProvideHeatBlockList 里（下游可追加），营火还要是点燃的；盛着熔岩的炼药锅也是。"""
    if blockName is None:
        blockName = GetBlockName(blockPos, dimensionId)
    if blockName in CanProvideHeatBlockList:
        return blockName not in _CAMPFIRE_BLOCKS or _states(blockPos, dimensionId).get("extinguished") is not True
    return blockName == _CAULDRON and _holdsLava(blockPos, dimensionId)


def IsHeated(belowPos, dimensionId, belowName=None):
    """HeatableBlockEntity.isHeated：belowPos 是锅 / 煎锅正下方那一格；它是热源就热，它是传热方块（漏斗）就看再下面一格是不是热源。"""
    if belowName is None:
        belowName = GetBlockName(belowPos, dimensionId)
    if IsHeatSource(belowPos, dimensionId, belowName):
        return True
    return belowName in HeatConductorList and IsHeatSource((belowPos[0], belowPos[1] - 1, belowPos[2]), dimensionId)


def RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName, delay=0.0):
    """按下方方块刷新"支架""加热"两个状态，并同步给客户端的方块实体 molang；返回是否有热源。

    delay > 0 时延后发送（方块刚放下时客户端的方块实体还没建好）。
    """
    blockEntityData["shelfEnable"] = 1.0 if belowName in ShelfBlockSet else 0.0
    heat = IsHeated(belowPos, dimensionId, belowName)
    blockEntityData["heatEnable"] = heat
    blockEntityData["heatParticleEnable"] = 1.0 if heat else 0.0
    pairs = (("variable.mod_shelf", blockEntityData["shelfEnable"]), ("variable.mod_heat", blockEntityData["heatParticleEnable"]))
    for name, value in pairs:
        if delay > 0:
            compFactory.CreateGame(levelId).AddTimer(delay, ToAllPlayerBlockMolang, blockPos, name, value)
        else:
            ToAllPlayerBlockMolang(blockPos, name, value)
    return heat
