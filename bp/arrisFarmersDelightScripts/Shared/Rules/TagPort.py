# -*- coding: utf-8 -*-
"""TagPort - 把引擎的标签查询包成 ItemTags 用的"口"：返回值的形状、3.10 以前没有的接口、客户端进世界前标签不全（双端，纯规则）

两端的引擎口（Server/Helpers/Tags.py、Client/Tags.py）各建一个 EnginePort，交进来几个无参函数，分别返回引擎的物品组件
（CreateItem(levelId)）、方块组件（CreateBlock(levelId)）、方块信息组件（CreateBlockInfo(levelId)：GetBlockTags 只有服务端有，客户端给 None）、
配方组件（CreateRecipe(levelId)，Shared/Rules/Grilling 问营火配方用），外加一个时钟（无参，返回秒）。组件用到时才建。
用到的接口和返回值（官方文档 + 网易 3.10 实机，前置包工程 .planning/kaleidoscope/R4-netease-tags-engine.md §3、§6）：
- GetItemTags(物品名, aux) -> [标签名]：物品不存在是 None（服务端 3.2 起就有，客户端是后来加的）；
- LookupItemsByItemTag(标签) -> [{"itemName": 物品名}]：没人登记过的标签是 []（3.10 起，两端）；
- LookupBlocksByBlockTag(标签) -> [{"blockName": 方块名}]（3.10 起，两端；成员名引擎不校验）；
- GetBlockTags(方块名) -> [标签名]：方块不存在是 None（只有服务端，3.2 起）；
- GetRecipesByInput(物品名, "campfire", aux, 1) -> [配方]（两端；熔炉类配方的形状没有实机记录，原样交给 Grilling 去宽容地解析）。
组件或接口没有（getattr 探不到）、调用抛异常、返回读不懂的东西：都当"答不了"，返回 None，不往外抛——ItemTags 那时按静态词表答。

准备好没有（ready）：
- 有 LookupItemsByItemTag（3.10 起）：反查 Tags.READY_PROBE 那个标签，里面出现了那件原版物品才算好。客户端在 LoadClientAddonScriptsAfter 时
  原版物品的 GetItemTags 还是 None、反查漏掉原版成员和物品 JSON 里声明的成员，进世界的过程中才全（实机：0.86 秒时不全，2.4 秒时全了）；
  服务端从系统建好起就是全的，第一次探就过。
- 没有（3.10 以前，没有 netease_tags）：GetItemTags 答得了那件原版物品就算好——那时只有物品 JSON 里声明的标签，原版物品注册了就是全的。
- 探测限频：两次至少隔 every 秒（缺省 1 秒；没给时钟就每次都探）；探到一次算好之后一直算好，不再探。
"""
from ..Data import Tags

_TEXT = (type(""), type(u""))


def _strings(answer):
    """[标签名, ...] -> 元组（只留字符串）；不是列表返回 None。"""
    if not isinstance(answer, (list, tuple)):
        return None
    return tuple(name for name in answer if isinstance(name, _TEXT))


def _field(answer, key):
    """[{key: 名字}, ...] -> (名字, ...)（去重保序；直接给名字的列表也收）；不是列表返回 None。"""
    if not isinstance(answer, (list, tuple)):
        return None
    names, seen = [], set()
    for entry in answer:
        name = entry.get(key) if isinstance(entry, dict) else entry
        if isinstance(name, _TEXT) and name not in seen:
            seen.add(name)
            names.append(name)
    return tuple(names)


class EnginePort(object):
    """一端的引擎标签口。items / blocks / blockInfo / recipes：无参函数，返回引擎组件（没有的给 None）；clock：无参函数返回秒；
    every：探"准备好没有"的最小间隔。"""

    def __init__(self, items, blocks=None, blockInfo=None, clock=None, every=1.0, recipes=None):
        self._items = items
        self._blocks = blocks
        self._blockInfo = blockInfo
        self._recipes = recipes
        self._clock = clock
        self._every = every
        self._ready = False
        self._nextProbe = None
        self.probes = 0                 # 给游戏内自检看的：探过几次、第一次探和探到准备好是什么时候（时钟的读数，没给时钟是 None）
        self.firstProbeAt = None
        self.readyAt = None

    @staticmethod
    def _method(getter, name):
        """getter() 给的组件上的 name 方法；没有组件、没有这个方法（3.10 以前）、建组件抛异常都返回 None。"""
        if getter is None:
            return None
        try:
            return getattr(getter(), name, None)
        except Exception:  # noqa: BLE001 - 引擎口出什么错都当答不了，ItemTags 按静态词表答
            return None

    def _call(self, getter, name, *args):
        method = self._method(getter, name)
        if method is None:
            return None
        try:
            return method(*args)
        except Exception:  # noqa: BLE001 - 同上：参数不认、引擎内部出错，都当答不了
            return None

    def itemsOf(self, tag):
        """这个物品标签的全部成员（物品名的元组）；答不了 None。"""
        return _field(self._call(self._items, "LookupItemsByItemTag", tag), "itemName")

    def tagsOf(self, itemName, aux=0):
        """这件物品带的物品标签（标签名的元组）；答不了（物品不存在、没有这个接口）None。"""
        return _strings(self._call(self._items, "GetItemTags", itemName, aux))

    def blocksOf(self, tag):
        """这个方块标签的全部成员（方块名的元组）；答不了 None。"""
        return _field(self._call(self._blocks, "LookupBlocksByBlockTag", tag), "blockName")

    def blockTagsOf(self, blockName):
        """这个方块带的方块标签（标签名的元组）；答不了（客户端没有 GetBlockTags、方块不存在）None。"""
        return _strings(self._call(self._blockInfo, "GetBlockTags", blockName))

    def campfireRecipes(self, itemName, aux=0):
        """这件东西作原料的营火配方（GetRecipesByInput 给的列表原样交出去，Grilling 解析）；答不了 None。"""
        found = self._call(self._recipes, "GetRecipesByInput", itemName, "campfire", aux, 1)
        return found if isinstance(found, (list, tuple)) else None

    def ready(self):
        """引擎的标签全了没有（见模块说明）；限频地探，探到一次算好就一直算好。"""
        if self._ready:
            return True
        now = self._clock() if self._clock is not None else None
        if now is not None and self._nextProbe is not None and now < self._nextProbe:
            return False
        if now is not None:
            self._nextProbe = now + self._every
        self.probes += 1
        if self.probes == 1:
            self.firstProbeAt = now
        self._ready = self._probe()
        if self._ready:
            self.readyAt = now
        return self._ready

    def _probe(self):
        tag, item = Tags.READY_PROBE
        if self._method(self._items, "LookupItemsByItemTag") is not None:
            return item in (self.itemsOf(tag) or ())
        return self.tagsOf(item, 0) is not None
