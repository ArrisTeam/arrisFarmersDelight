# -*- coding: utf-8 -*-
"""Heat - 厨锅 / 煎锅下方的热源与支架判断（服务端）

热源照 FD 的 HeatableBlockEntity.isHeated（java:15-36，厨锅和煎锅共用）：正下方一格是热源（标签 heat_sources：岩浆块、熔岩炼药锅、炉灶、熔岩、营火、火；
带 LIT 状态的要点着才算）就热；正下方是传热方块（标签 heat_conductors：漏斗）时，改看再下面一格是不是热源，所以漏斗下面的火也烧得热上面的锅。
基岩版里的对应：熔岩炼药锅没有自己的方块，是 cauldron 的状态 cauldron_liquid = lava（3.10 实机：SetBlockNew("minecraft:lava_cauldron")
返回 True，放出来的是盛水、0 级的 minecraft:cauldron；标签表达不了，按状态认，HoldsLava）；营火的 LIT 是 extinguished 取反；
炉灶的 LIT 是两个方块（点着的 arris:stove 在 CanProvideHeatBlockList 里，熄着的孪生方块不在）。
不在名单里的方块再看方块标签 farmersdelight:heat_sources（Shared/Rules/HeatSources）：有点燃状态的要点着（lit 为真 / extinguished 为假），没有的就算。
支架（托盘）只认正下方那一格：CookingPotBlock.getTrayState / SkilletBlock 只看 pos.below() 是不是 tray_heat_sources（熔岩、营火、火），
所以漏斗再下面有火也不画托盘，和 JE 一样；传热的那一格变了没有邻居事件，由 Server/HeatConduct.py 隔一会儿去看。
托盘看的是 ShelfBlockSet ∪ 方块标签 farmersdelight:tray_heat_sources（名单原样留着，不在名单里的再看标签）。
厨锅还有第三种支架：吊把手（HANDLE，Server/PotSupport.py），挂着时不论下面是什么都不画托盘；热不热和它无关（isHeated 不看支架）。
"""
from .Engine import compFactory, levelId, GetBlockEntityData, GetBlockName
from .Fx import ToAllPlayerBlockMolang
from ...Shared.Data import Tags
from ...Shared.Data.Cooking import CanProvideHeatBlockList
from ...Shared.Rules import HeatSources, ItemTags, PotSupport

# 厨锅 / 煎锅放在这些方块上时显示支架模型
ShelfBlockSet = frozenset(["minecraft:fire", "minecraft:campfire", "minecraft:soul_fire", "minecraft:soul_campfire",
                           "minecraft:lava", "minecraft:flowing_lava"])

# 营火类方块熄灭时名字不变，只是 extinguished 状态为 True
_CAMPFIRE_BLOCKS = frozenset(["minecraft:campfire", "minecraft:soul_campfire"])


def _states(blockPos, dimensionId):
    """方块状态字典，读不到是空字典（基岩版只有服务端读得到方块状态）。"""
    return compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId) or {}


def HoldsLava(blockPos, dimensionId):
    """这一格是不是熔岩炼药锅（JE 的 lava_cauldron）：读方块状态，cauldron_liquid 为 lava 而且锅里有东西（HeatSources.holdsLava）。
    锅 / 煎锅下面的热源（IsHeatSource）和手持煎锅身边的热源（Server/SkilletHand）都用它。"""
    return HeatSources.holdsLava(_states(blockPos, dimensionId))


def IsHeatSource(blockPos, dimensionId, blockName=None):
    """该位置的方块能否提供热量：在 CanProvideHeatBlockList 里（下游可追加），营火还要是点燃的；盛着熔岩的炼药锅也是；
    不在名单里的看方块标签（HeatSources.sourceByTag：带 farmersdelight:heat_sources，有点燃状态的还要点着）。"""
    if blockName is None:
        blockName = GetBlockName(blockPos, dimensionId)
    if blockName in CanProvideHeatBlockList:
        return blockName not in _CAMPFIRE_BLOCKS or _states(blockPos, dimensionId).get("extinguished") is not True
    if blockName == HeatSources.CAULDRON:
        return HoldsLava(blockPos, dimensionId)
    return HeatSources.sourceByTag(blockName, lambda: _states(blockPos, dimensionId))


def IsHeated(belowPos, dimensionId, belowName=None):
    """HeatableBlockEntity.isHeated：belowPos 是锅 / 煎锅正下方那一格；它是热源就热，它是传热方块（漏斗，或带 farmersdelight:heat_conductors
    的，HeatSources.conducts）就看再下面一格是不是热源。"""
    if belowName is None:
        belowName = GetBlockName(belowPos, dimensionId)
    if IsHeatSource(belowPos, dimensionId, belowName):
        return True
    return HeatSources.conducts(belowName) and IsHeatSource((belowPos[0], belowPos[1] - 1, belowPos[2]), dimensionId)


def SupportOf(blockEntityData):
    """厨锅现在的支架（PotSupport.NONE / TRAY / HANDLE），从方块实体数据里的两个旗读（世界外观广播 Server/PotLook 用）。"""
    return PotSupport.kindOf(blockEntityData["handleEnable"] == 1.0, blockEntityData["shelfEnable"] == 1.0)


def RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName, delay=0.0):
    """按下方方块刷新"支架""加热"两个状态，并同步给客户端的方块实体 molang；返回是否有热源。

    厨锅挂着吊把手（handleEnable，Server/PotSupport 存的）时下面是什么都不画托盘（FD 的 updateShape：HANDLE 不动），也把这个旗一并同步；
    煎锅和没有这个键的厨锅（/setblock 放的）没有吊把手。
    delay > 0 时延后发送（方块刚放下时客户端的方块实体还没建好）：到点时现读方块实体数据再发——排着的这一会儿里支架又变了
    （刚放下就潜行切了吊把手）的话，发的得是现在的值；原来发的是排队时的值，会把刚切好的吊把手冲掉。
    """
    handle = blockEntityData["handleEnable"]
    onTray = ItemTags.blockListed(belowName, ShelfBlockSet, Tags.TRAY_HEAT_SOURCES)
    blockEntityData["shelfEnable"] = 1.0 if onTray and handle != 1.0 else 0.0
    heat = IsHeated(belowPos, dimensionId, belowName)
    blockEntityData["heatEnable"] = heat
    blockEntityData["heatParticleEnable"] = 1.0 if heat else 0.0
    if delay > 0:
        compFactory.CreateGame(levelId).AddTimer(delay, PushSupport, dimensionId, blockPos)
    else:
        _push(blockEntityData, blockPos)
    return heat


def PushSupport(dimensionId, blockPos):
    """把这个方块现在的支架、加热状态发给各客户端的方块实体模型（延后的那一份到点时调：现读，方块已经不在了就不发）。"""
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if blockEntityData:
        _push(blockEntityData, blockPos)


def _push(blockEntityData, blockPos):
    pairs = [("variable.mod_shelf", blockEntityData["shelfEnable"]), ("variable.mod_heat", blockEntityData["heatParticleEnable"])]
    if blockEntityData["handleEnable"] is not None:
        pairs.append(("variable.mod_handle", blockEntityData["handleEnable"]))
    for name, value in pairs:
        ToAllPlayerBlockMolang(blockPos, name, value)
