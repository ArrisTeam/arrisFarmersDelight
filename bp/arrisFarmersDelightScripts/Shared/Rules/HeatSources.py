# -*- coding: utf-8 -*-
"""HeatSources - 热源方块：名单（CanProvideHeatBlockList）∪ 方块标签 farmersdelight:heat_sources，以及"点着没有"的规则（双端，纯规则）

JE：方块标签 farmersdelight:heat_sources（HeatableBlockEntity.isHeated：在标签里就热，方块带 LIT 状态的要点着才算）。这边原来只有一张方块名单
（Shared/Data/Cooking.CanProvideHeatBlockList，联动契约，下游追加名字），营火另看 extinguished（Server/Helpers/Heat.IsHeatSource）。现在并上同一个标签，
规则照 JE：方块有"点没点着"这类状态（名字是 lit、以 :lit 结尾，或者 extinguished）的看状态（isLit），没有这类状态的（火、熔岩、岩浆块、
点着的炉灶……）在标签里就算热。别的模组"一个方块 + lit 状态"的炉灶、营火式的方块登记进同一个标签就行。
标签经 Shared/Rules/ItemTags 问（反查 LookupBlocksByBlockTag 两端都有；按方块问的 GetBlockTags 只有服务端）。
- 锅 / 煎锅下面的热源（服务端，读得到方块状态）：名单里的照旧；不在名单里的问 sourceByTag。
- 手持煎锅"身边有没有热源"（JE 的 isPlayerNearHeatSource 只看方块标签、不看点没点着；服务端 SkilletHand、客户端 Input 同一条规则）：
  名单 ∪ 标签，不看状态（nearHeat / NEAR）——和名单里的营火现在的算法一样（营火在名单里，熄了也算）。
- 传热方块（conducts：JE 的 farmersdelight:heat_conductors）：名单 HeatConductorList ∪ 这个方块标签；锅 / 煎锅下面是它时看再下面一格。
托盘（Server/Helpers/Heat.ShelfBlockSet ∪ farmersdelight:tray_heat_sources）在 Heat.py 里并。
"""
from ..Data import Tags
from ..Data.Cooking import CanProvideHeatBlockList, HeatConductorList
from . import ItemTags

_TRUE = (True, 1, "true", "True")
_FALSE = (False, 0, "false", "False")


def _litKey(key):
    return key == "lit" or str(key).endswith(":lit")


def isLit(states):
    """方块状态算不算点着：有名字是 lit 或以 :lit 结尾的状态且为真，或者有 extinguished 状态且为假；都没有（或读不到状态）就不算。"""
    states = states if isinstance(states, dict) else {}
    for key, value in states.items():
        if _litKey(key) and value in _TRUE:
            return True
    return "extinguished" in states and states["extinguished"] in _FALSE


def hasLitState(states):
    """方块有没有"点没点着"这类状态（JE 的 hasProperty(LIT)）：名字是 lit、以 :lit 结尾，或者 extinguished。"""
    states = states if isinstance(states, dict) else {}
    return any(_litKey(key) or key == "extinguished" for key in states)


def sourceByTag(blockName, states):
    """不在名单里的方块按标签算不算热源（JE 的 isHeated）：带 farmersdelight:heat_sources 才算；有点燃状态的要点着，没有的就算热。
    states 是无参函数（带标签时才读）。"""
    if not blockName or not ItemTags.blockHas(blockName, Tags.HEAT_SOURCES):
        return False
    current = states()
    return isLit(current) if hasLitState(current) else True


def nearHeat(blockName):
    """手持煎锅身边的热源方块：名单里的，或带热源标签的（不看点没点着）。"""
    if not blockName:
        return False
    return blockName in CanProvideHeatBlockList or ItemTags.blockHas(blockName, Tags.HEAT_SOURCES)


def conducts(blockName):
    """把热传给上面一格的方块（HeatableBlockEntity.isHeated 的 heat_conductors）：名单里的，或带 farmersdelight:heat_conductors 的。"""
    return ItemTags.blockListed(blockName, HeatConductorList, Tags.HEAT_CONDUCTORS)


class _Near(object):
    """给 SkilletRules.nearHeat 当 heatNames：'方块名 in NEAR' 就是 nearHeat(方块名)。"""

    def __contains__(self, blockName):
        return nearHeat(blockName)


NEAR = _Near()
