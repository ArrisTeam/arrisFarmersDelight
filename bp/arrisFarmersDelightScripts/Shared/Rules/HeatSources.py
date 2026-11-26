# -*- coding: utf-8 -*-
"""HeatSources - 一格方块算不算热源：名单（CanProvideHeatBlockList）、方块标签 farmersdelight:heat_sources、状态条件表（HeatSourceStateDict），
以及"点着没有"的规则（双端，纯规则）

"这一格算不算热源"都走这里：服务端锅 / 煎锅下面（Server/Helpers/Heat.IsHeatSource）、手持煎锅身边（Heat.IsNearHeat，Server/SkilletHand），
客户端手持煎锅身边（Client/Input）。规则：
1. 方块在状态条件表里（Shared/Data/Cooking.HeatSourceStateDict，怎么判见 HeatStates）：只按条件判，处处都判——锅 / 煎锅下面、手持煎锅身边都一样
   （JE 的手持煎锅不看 LIT，可熔岩炼药锅在 JE 是另一个方块，这边是炼药锅的状态，所以写明的条件要判）；状态读不到、缺这个状态都算不满足；
   名单、标签里的方块写了条件也按条件判；条件表里的方块不用再进名单或标签。
   JE 标签里的熔岩炼药锅就是表里的一条：基岩版没有 minecraft:lava_cauldron 这个方块（3.10 实机：SetBlockNew 它放出来的是盛水、0 级的
   minecraft:cauldron），是炼药锅的状态 cauldron_liquid = lava，舀空了的不算。
2. 没写条件的：名单里的照旧（锅下面时营火看 extinguished，别的就算热）；不在名单里的看标签：带 farmersdelight:heat_sources 的，
   JE 查 LIT 的地方（锅 / 煎锅下面，lit=True）方块有点燃状态（lit、*:lit、extinguished）的要点着、没有的就算热；JE 不查的地方
   （手持煎锅身边，lit=False）不看。
客户端读不到方块状态（GetBlock 只给名字和 aux）：写了条件的方块查"满足条件的 aux"（HeatSourceAuxDict，heatsByAux），表里没有这个方块的当不热；
没写条件的照 2（手持煎锅身边本来就不看点燃状态）。
传热方块（conducts：JE 的 farmersdelight:heat_conductors）：名单 HeatConductorList ∪ 这个方块标签；锅 / 煎锅下面是它时看再下面一格。
托盘（Server/Helpers/Heat.ShelfBlockSet ∪ farmersdelight:tray_heat_sources）在 Heat.py 里并。
标签经 Shared/Rules/ItemTags 问（反查 LookupBlocksByBlockTag 两端都有；按方块问的 GetBlockTags 只有服务端）。
"""
from ..Data import Tags
from ..Data.Cooking import CanProvideHeatBlockList, HeatConductorList, HeatSourceAuxDict, HeatSourceStateDict
from . import HeatStates, ItemTags
from .TableWire import isInt

_TRUE = (True, 1, "true", "True")
_FALSE = (False, 0, "false", "False")
# 名单里锅 / 煎锅下面要看 extinguished 的两个（熄了名字不变）
CAMPFIRES = frozenset(["minecraft:campfire", "minecraft:soul_campfire"])


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


def _read(states):
    current = states()
    return current if isinstance(current, dict) else {}


def heats(blockName, states, lit=True):
    """这一格的方块算不算热源（服务端）。states：无参函数，要看状态时才读（读不到给 None / {} 都行）；
    lit：JE 查点燃状态的地方（锅 / 煎锅下面）为真，手持煎锅身边为假。"""
    if not blockName:
        return False
    conditions = HeatSourceStateDict.get(blockName)
    if conditions is not None:
        return HeatStates.matches(states(), conditions)
    if blockName in CanProvideHeatBlockList:
        return not lit or blockName not in CAMPFIRES or _read(states).get("extinguished") is not True
    if not ItemTags.blockHas(blockName, Tags.HEAT_SOURCES):
        return False
    if not lit:
        return True
    current = _read(states)
    return isLit(current) if hasLitState(current) else True


def heatsByAux(blockName, aux):
    """客户端手持煎锅身边的这一格算不算热源：只有方块名和 aux（GetBlock）。写了条件的查 HeatSourceAuxDict（这个方块不在里面就当不热），
    没写的照 heats 的名单 / 标签规则，不看点燃状态。"""
    if not blockName:
        return False
    if blockName in HeatSourceStateDict:
        return isInt(aux) and aux in (HeatSourceAuxDict.get(blockName) or ())
    return heats(blockName, lambda: None, lit=False)


def conducts(blockName):
    """把热传给上面一格的方块（HeatableBlockEntity.isHeated 的 heat_conductors）：名单里的，或带 farmersdelight:heat_conductors 的。"""
    return ItemTags.blockListed(blockName, HeatConductorList, Tags.HEAT_CONDUCTORS)
