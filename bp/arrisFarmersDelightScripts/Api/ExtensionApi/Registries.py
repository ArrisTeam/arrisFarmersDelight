# -*- coding: utf-8 -*-
"""Registries - 门面上配方以外的登记口（刀、热源方块、炉灶方块、可堆肥的物品）和标签的只读查询 ext.tags（双端，不碰引擎）

刀、热源优先用标签：把自己的刀登记进 common:knife、热源方块登记进 farmersdelight:heat_sources（docs/TAGS.md），
这几个登记口是给没法用标签的情况。登记就是往旧接口的那几张表里追加（knifeList、CanProvideHeatBlockList、StoveList、ComposterItemDict），
表同步照旧发给客户端（堆肥表只有服务端读，不同步）；已经在表里的不重复加，照样返回 ok。只在服务端（客户端返回 server_only，不抛）。
热源带状态条件（registerHeatSource 的 states）时写的是状态条件表 HeatSourceStateDict，不进名单（见那个方法）。
炉灶只登记点着的那个方块（会烤东西、给热）：熄灭的孪生方块和点火 / 灭火的换方块是另一回事，以后再开。
返回 {"ok", "error", "id"}（"id" 是登记的名字；states 写错时另带 "message"）。
"""
from ...Shared.Data import Tags as Vocabulary
from ...Shared.Data.Cooking import CanProvideHeatBlockList, HeatSourceStateDict, StoveList
from ...Shared.Data.Cutting import knifeList
from ...Shared.Data.Farming import ComposterItemDict
from ...Shared.Rules import BoardStation, HeatStates, ItemTags
from ...Shared.Rules.TableWire import INT_TYPES, isInt

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2
except NameError:
    _TEXT = (str,)


def _answer(ok, error, name):
    return {"ok": ok, "error": error, "id": name}


def _name(value):
    """"ns:name" 的物品 / 方块名（py2 的 unicode 换成 str）；写法不对是 None。"""
    if isinstance(value, _TEXT) and not isinstance(value, str):
        value = value.encode("utf-8")
    if not isinstance(value, str) or value.count(":") != 1 or " " in value or value.startswith("#") or not all(value.split(":")):
        return None
    return value


class Registries(object):
    """一端的配方以外的登记口（ext.registerKnife……）。"""

    def __init__(self, side):
        self._side = side

    def _append(self, name, container):
        if self._side != "server":
            return _answer(False, "server_only", name)
        found = _name(name)
        if found is None:
            return _answer(False, "invalid_name", name)
        if found not in container:
            container.append(found)
        return _answer(True, None, found)

    def registerKnife(self, itemName):
        """这件物品算刀（砧板上切东西、刀杀生物多掉东西、刀切蛋糕……）：追加进 knifeList（所有刀切配方的工具表就是它）。"""
        answer = self._append(itemName, knifeList)
        if answer["ok"]:
            BoardStation.invalidate()
        return answer

    def registerHeatSource(self, blockName, states=None):
        """这个方块给厨锅、煎锅加热。
        不给 states：不看方块状态（要看点燃状态的方块用标签 farmersdelight:heat_sources），追加进 CanProvideHeatBlockList（旧接口的名单）。
        给了 states（{状态名: 条件}，条件写一个值、一组值或 {"min": n, "max": n}，Shared/Rules/HeatStates）：只写进状态条件表
        HeatSourceStateDict（同一个方块再登记就换成新的条件），不进名单——名单是旧接口"不看状态的热源"，读它的下游会以为一直热；
        条件表里的方块满足条件就是热源，不用再进名单或标签，已经在名单、标签里的写了条件也按条件判（锅下面、手持煎锅身边都判）。
        客户端按服务端照条件算好的 aux 判（Server/HeatAux，下一次表同步时算好、一起发过去）。"""
        if states is None:
            return self._append(blockName, CanProvideHeatBlockList)
        if self._side != "server":
            return _answer(False, "server_only", blockName)
        found = _name(blockName)
        if found is None:
            return _answer(False, "invalid_name", blockName)
        conditions, problem = HeatStates.normalize(states)
        if conditions is None:
            answer = _answer(False, "invalid_states", found)
            answer["message"] = problem
            return answer
        HeatSourceStateDict[found] = conditions
        return _answer(True, None, found)

    def registerStove(self, blockName):
        """这个方块是点着的炉灶（会烤上面的东西、站上去烫脚、炉灶站点认它）：追加进 StoveList。方块要像农夫乐事的炉灶一样带方块实体（六个烤位存在里面）。"""
        return self._append(blockName, StoveList)

    def registerCompostable(self, itemName, chance, aux=0):
        """这件物品能放进原版堆肥桶，chance 是让桶升一层的概率（百分数，大于 0、不超过 100）：写进 ComposterItemDict。"""
        if self._side != "server":
            return _answer(False, "server_only", itemName)
        found = _name(itemName)
        if found is None or not isInt(aux) or aux < 0:
            return _answer(False, "invalid_name", itemName)
        if isinstance(chance, bool) or not isinstance(chance, INT_TYPES + (float,)) or not 0 < chance <= 100:
            return _answer(False, "invalid_chance", found)
        ComposterItemDict[(found, aux)] = chance
        return _answer(True, None, found)


class TagView(object):
    """ext.tags：标签查询的只读包装（Shared/Rules/ItemTags），外加词表里每个标签的名字常量（ext.tags.RAW_BEEF == "common:raw_beef"……）。
    引擎没准备好（远端客户端进世界之前）时按农夫乐事的静态词表答；generation() 变了说明答案可能变了。"""

    def __init__(self):
        for key, value in vars(Vocabulary).items():
            if key.isupper() and isinstance(value, str):
                setattr(self, key, value)

    def has(self, itemName, tag):
        return ItemTags.has(itemName, tag)

    def itemsOf(self, tag):
        return ItemTags.itemsOf(tag)

    def tagsOf(self, itemName, aux=0):
        return ItemTags.tagsOf(itemName, aux)

    def blockHas(self, blockName, tag):
        return ItemTags.blockHas(blockName, tag)

    def blocksOf(self, tag):
        return ItemTags.blocksOf(tag)

    def generation(self):
        return ItemTags.generation()

    def names(self):
        """词表里的物品标签名（农夫乐事登记的，加上没有成员、只在文档里的那几个），排好序。"""
        return sorted(set(Vocabulary.ITEM_TAGS) | set(Vocabulary.VANILLA_TAGS) | set(Vocabulary.WITHOUT_MEMBERS))
