# -*- coding: utf-8 -*-
"""Heat - 厨锅 / 煎锅下方的热源与支架判断（服务端）

热源照 FD 的 HeatableBlockEntity.isHeated（java:15-36，厨锅和煎锅共用）：正下方一格是热源（标签 heat_sources：岩浆块、熔岩炼药锅、炉灶、熔岩、营火、火；
带 LIT 状态的要点着才算）就热；正下方是传热方块（标签 heat_conductors：漏斗）时，改看再下面一格是不是热源，所以漏斗下面的火也烧得热上面的锅。
"这一格算不算热源"的规则在 Shared/Rules/HeatSources.heats（这里只读方块名和方块状态交给它，lit=True：JE 在这里看 LIT）：
写了状态条件的方块按条件判（Shared/Data/Cooking.HeatSourceStateDict；熔岩炼药锅在基岩版是 cauldron 的状态 cauldron_liquid = lava，
3.10 实机：SetBlockNew("minecraft:lava_cauldron") 返回 True，放出来的是盛水、0 级的 minecraft:cauldron）；名单 CanProvideHeatBlockList 里的照旧
（营火的 LIT 是 extinguished 取反；炉灶的 LIT 是两个方块：点着的 arris:stove 在名单里，熄着的孪生方块不在）；
不在名单里的再看方块标签 farmersdelight:heat_sources：有点燃状态的要点着（lit 为真 / extinguished 为假），没有的就算。
手持煎锅身边的那 27 格也问同一条规则（IsNearHeat，lit=False：JE 的 isPlayerNearHeatSource 不看 LIT，写了的状态条件照判）。
支架（托盘）只认正下方那一格：CookingPotBlock.getTrayState / SkilletBlock 只看 pos.below() 是不是 tray_heat_sources（熔岩、营火、火），
所以漏斗再下面有火也不画托盘，和 JE 一样；传热的那一格变了没有邻居事件，由 Server/HeatConduct.py 隔一会儿去看。
托盘看的是 ShelfBlockSet ∪ 方块标签 farmersdelight:tray_heat_sources（名单原样留着，不在名单里的再看标签）。
厨锅还有第三种支架：吊把手（HANDLE，Server/PotSupport.py），挂着时不论下面是什么都不画托盘；热不热和它无关（isHeated 不看支架）。
"""
from .Engine import compFactory, levelId, GetBlockEntityData, GetBlockName
from .Fx import ToAllPlayerBlockMolang
from ...Shared.Data import Tags
from ...Shared.Rules import HeatSources, ItemTags, PotSupport

# 厨锅 / 煎锅放在这些方块上时显示支架模型
ShelfBlockSet = frozenset(["minecraft:fire", "minecraft:campfire", "minecraft:soul_fire", "minecraft:soul_campfire",
                           "minecraft:lava", "minecraft:flowing_lava"])


def _states(blockPos, dimensionId):
    """方块状态字典，读不到是空字典（基岩版只有服务端读得到方块状态）。"""
    return compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId) or {}


def IsHeatSource(blockPos, dimensionId, blockName=None):
    """锅 / 煎锅正下方的这一格能不能给它热（HeatSources.heats，看点燃状态）：写了状态条件的按条件（盛着熔岩的炼药锅……），
    名单 CanProvideHeatBlockList 里的（下游可追加）营火还要是点燃的，不在名单里的看方块标签 farmersdelight:heat_sources。"""
    if blockName is None:
        blockName = GetBlockName(blockPos, dimensionId)
    return HeatSources.heats(blockName, lambda: _states(blockPos, dimensionId), lit=True)


def IsNearHeat(blockPos, dimensionId):
    """手持煎锅身边 3x3x3 里的这一格算不算热源（Server/SkilletHand；HeatSources.heats，不看点燃状态，写了的状态条件照判）。"""
    return HeatSources.heats(GetBlockName(blockPos, dimensionId), lambda: _states(blockPos, dimensionId), lit=False)


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
