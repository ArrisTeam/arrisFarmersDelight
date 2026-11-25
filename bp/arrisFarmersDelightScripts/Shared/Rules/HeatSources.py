# -*- coding: utf-8 -*-
"""HeatSources - 热源方块：名单（CanProvideHeatBlockList）∪ 两个方块标签，以及"点着没有"的规则（双端，纯规则）

JE：方块标签 farmersdelight:heat_sources（HeatableBlockEntity.isHeated：带 LIT 状态的要点着才算）。这边原来只有一张方块名单
（Shared/Data/Cooking.CanProvideHeatBlockList，联动契约，下游追加名字），营火另看 extinguished（Server/Helpers/Heat.IsHeatSource）。现在并上：
- common:heat_source：方块名本身就说明在发热的（火、熔岩、岩浆块、点着的炉灶……），在标签里就算；
- common:heat_source_lit：要看方块状态点没点着的（营火、别的模组"一个方块 + lit 状态"的炉灶），点着（isLit）才算。
标签经 Shared/Rules/ItemTags 问（反查 LookupBlocksByBlockTag 两端都有；按方块问的 GetBlockTags 只有服务端）。
- 锅 / 煎锅下面的热源（服务端，读得到方块状态）：名单里的照旧；不在名单里的问 sourceByTag。
- 手持煎锅"身边有没有热源"（JE 的 isPlayerNearHeatSource 只看方块标签、不看点没点着；服务端 SkilletHand、客户端 Input 同一条规则）：
  名单 ∪ 两个标签，不看状态（nearHeat / NEAR）——和名单里的营火现在的算法一样（营火在名单里，熄了也算）。
托盘（Server/Helpers/Heat.ShelfBlockSet）和传热方块（HeatConductorList）不归这里。
"""
from ..Data import Tags
from ..Data.Cooking import CanProvideHeatBlockList
from . import ItemTags

_TRUE = (True, 1, "true", "True")
_FALSE = (False, 0, "false", "False")


def isLit(states):
    """方块状态算不算点着：有名字是 lit 或以 :lit 结尾的状态且为真，或者有 extinguished 状态且为假；都没有（或读不到状态）就不算。"""
    states = states if isinstance(states, dict) else {}
    for key, value in states.items():
        if (key == "lit" or str(key).endswith(":lit")) and value in _TRUE:
            return True
    return "extinguished" in states and states["extinguished"] in _FALSE


def sourceByTag(blockName, states):
    """不在名单里的方块按标签算不算热源：common:heat_source 直接算；common:heat_source_lit 要点着。states 是无参函数（要看状态时才读）。"""
    if not blockName:
        return False
    if ItemTags.blockHas(blockName, Tags.HEAT_SOURCE):
        return True
    return ItemTags.blockHas(blockName, Tags.HEAT_SOURCE_LIT) and isLit(states())


def nearHeat(blockName):
    """手持煎锅身边的热源方块：名单里的，或带两个热源标签之一的（不看点没点着）。"""
    if not blockName:
        return False
    return blockName in CanProvideHeatBlockList or ItemTags.blockHas(blockName, Tags.HEAT_SOURCE) \
        or ItemTags.blockHas(blockName, Tags.HEAT_SOURCE_LIT)


class _Near(object):
    """给 SkilletRules.nearHeat 当 heatNames：'方块名 in NEAR' 就是 nearHeat(方块名)。"""

    def __contains__(self, blockName):
        return nearHeat(blockName)


NEAR = _Near()
