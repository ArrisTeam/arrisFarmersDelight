# -*- coding: utf-8 -*-
"""ItemTags - 按标签认物品 / 方块：问引擎的标签，问不了时按农夫乐事自己的词表答（双端，纯规则）

以后所有"按标签认"的地方（是不是刀、是不是热源、厨锅的格子收不收……）都问这里，不直接调引擎：
- 引擎口两端各装一个：服务端 Server/Helpers/Tags.py、客户端 Client/Tags.py，导入时 setPort（口是 Shared/Rules/TagPort.EnginePort）。
  单机时两端在同一个进程、共用这一份模块状态，所以按端各存一个；两个都在就用服务端的（服务端从系统建好起标签就是全的）。
- 没有口（离线测试、Strata 沙箱）或者口还没准备好（客户端进世界之前，见 TagPort）时，按 Shared/Data/Tags 的静态表作答，
  就是农夫乐事单独在场时的答案；这时的答案不缓存，口准备好之后换成引擎的。
- 口准备好之后：静态表 ∪ 引擎的答案。引擎的答案本来就含农夫乐事登记的那些，并上静态表是保底：引擎那边万一没挂上，农夫乐事自己的东西照样认，
  也就是装了引擎口只会多认别的模组的东西，不会比单独在场时少认。答案按标签 / 物品名缓存（标签加载完就不变了，查询本身也便宜）。
  某一样口答不了（3.10 以前没有反查接口：itemsOf / blocksOf 答 None）时那一样只有静态表的，按物品问（GetItemTags）照旧问引擎。
- generation()：答案可能变了就加一——装上 / 卸下口、口从没准备好变成准备好、refresh()。按标签建了索引的地方拿它判断要不要重建。
- 口的调用抛异常或者返回读不懂的东西：当它没答，用静态表，不往外抛。
口（鸭子类型）：ready() -> 真假；itemsOf(标签) / blocksOf(标签) -> 名字的序列；tagsOf(物品名, aux) / blockTagsOf(方块名) -> 标签名的序列；答不了返回 None。
"""
from ..Data import Tags

SIDES = ("server", "client")          # 两个口都在时用前面那个
_EMPTY = frozenset()
_TEXT = (type(""), type(u""))
_ports = {}                           # 端 -> 口
_state = {"generation": 0, "ready": False}
_cache = {}                           # (种类, 键) -> 答案：只在口准备好时写，换代时清空


def _staticItems():
    found = {}
    for table in (Tags.ITEM_TAGS, Tags.VANILLA_TAGS):
        for tag, members in table.items():
            found[tag] = found.get(tag, ()) + tuple(name for name in members if name not in found.get(tag, ()))
    return found


def _reverse(table):
    """{标签: 成员} -> {成员: frozenset(标签)}"""
    found = {}
    for tag, members in table.items():
        for name in members:
            found[name] = found.get(name, _EMPTY) | frozenset((tag,))
    return found


_STATIC_ITEMS = _staticItems()                                          # 标签 -> 物品名元组（表里的顺序）
_STATIC_ITEM_SETS = dict((tag, frozenset(members)) for tag, members in _STATIC_ITEMS.items())
_STATIC_TAGS_OF = _reverse(_STATIC_ITEMS)                                # 物品名 -> 标签
_STATIC_BLOCKS = dict((tag, frozenset(members)) for tag, members in Tags.BLOCK_TAGS.items())
_STATIC_BLOCK_TAGS_OF = _reverse(Tags.BLOCK_TAGS)                        # 方块名 -> 标签


def setPort(side, port):
    """装上一端的引擎口（port 为 None 是卸下）。side："server" / "client"。"""
    if side not in SIDES:
        raise ValueError("side 只能是 %s，给的是 %r" % ("、".join(SIDES), side))
    if port is None:
        _ports.pop(side, None)
    else:
        _ports[side] = port
    _state["ready"] = False
    _bump()


def _bump():
    _state["generation"] += 1
    _cache.clear()


def _ask(port, name, *args):
    """port.name(*args)；口没有这个方法、调用抛异常都返回 None。"""
    try:
        return getattr(port, name)(*args)
    except Exception:  # noqa: BLE001 - 口出什么错都当没答，按静态表答
        return None


def _names(answer):
    """口答的名字序列 -> 元组（只留字符串）；答不了 / 读不懂返回 None。"""
    if not isinstance(answer, (list, tuple, set, frozenset)):
        return None
    return tuple(name for name in answer if isinstance(name, _TEXT))


def _sync():
    """现在能用的口（没有、没准备好返回 None）；口从没准备好变成准备好（或者反过来）时换代。"""
    port = None
    for side in SIDES:
        port = _ports.get(side)
        if port is not None:
            break
    ok = port is not None and bool(_ask(port, "ready"))
    if ok != _state["ready"]:
        _state["ready"] = ok
        _bump()
    return port if ok else None


def ready():
    """现在有没有能用的引擎口（没有时全部按静态词表答）。"""
    return _sync() is not None


def generation():
    """答案的代数：装上 / 卸下口、口变成准备好、refresh() 时加一。"""
    _sync()
    return _state["generation"]


def refresh():
    """丢掉缓存（下次查询重新问引擎），换代。"""
    _bump()


def _itemsOf(port, tag):
    static = _STATIC_ITEMS.get(tag, ())
    if port is None:
        return static
    key = ("items", tag)
    if key not in _cache:
        found = _names(_ask(port, "itemsOf", tag)) or ()
        _cache[key] = static + tuple(name for name in _unique(found) if name not in _STATIC_ITEM_SETS.get(tag, _EMPTY))
    return _cache[key]


def _unique(names):
    seen = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            yield name


def _itemSet(port, tag):
    if port is None:
        return _STATIC_ITEM_SETS.get(tag, _EMPTY)
    key = ("itemset", tag)
    if key not in _cache:
        _cache[key] = frozenset(_itemsOf(port, tag))
    return _cache[key]


def _tagsOf(port, itemName, aux):
    static = _STATIC_TAGS_OF.get(itemName, _EMPTY)
    if port is None or not itemName:
        return static
    key = ("tags", itemName, aux or 0)
    if key not in _cache:
        _cache[key] = static | frozenset(_names(_ask(port, "tagsOf", itemName, aux or 0)) or ())
    return _cache[key]


def _blocksOf(port, tag):
    static = _STATIC_BLOCKS.get(tag, _EMPTY)
    if port is None:
        return static
    key = ("blocks", tag)
    if key not in _cache:
        _cache[key] = static | frozenset(_names(_ask(port, "blocksOf", tag)) or ())
    return _cache[key]


def _blockTagsOf(port, blockName):
    static = _STATIC_BLOCK_TAGS_OF.get(blockName, _EMPTY)
    if port is None or not blockName:
        return static
    key = ("blocktags", blockName)
    if key not in _cache:
        _cache[key] = static | frozenset(_names(_ask(port, "blockTagsOf", blockName)) or ())
    return _cache[key]


def itemsOf(tag):
    """这个物品标签现在的全部成员（物品名的元组）：静态表的在前（表里的顺序），引擎多出来的（别的模组登记的）接在后面。"""
    return _itemsOf(_sync(), tag)


def tagsOf(itemName, aux=0):
    """这件物品现在带的全部物品标签（frozenset）。口准备好时含引擎给的一切（原版的 minecraft:is_food、物品 JSON 里声明的……）。"""
    return _tagsOf(_sync(), itemName, aux)


def has(itemName, tag):
    """这件物品带不带这个物品标签：按物品问（GetItemTags）、按标签反查（LookupItemsByItemTag），任一个说带就是带。"""
    if not itemName:
        return False
    port = _sync()
    return tag in _tagsOf(port, itemName, 0) or itemName in _itemSet(port, tag)


def blocksOf(tag):
    """这个方块标签现在的全部成员（方块名的 frozenset）。"""
    return _blocksOf(_sync(), tag)


def blockTagsOf(blockName):
    """这个方块现在带的方块标签（frozenset）。引擎的 GetBlockTags 只有服务端有：客户端只有静态表的，判断用 blockHas（它还按标签反查）。"""
    return _blockTagsOf(_sync(), blockName)


def blockHas(blockName, tag):
    """这个方块带不带这个方块标签：按标签反查（LookupBlocksByBlockTag，两端）或按方块问（GetBlockTags，服务端）任一个说带就是带。"""
    if not blockName:
        return False
    port = _sync()
    return blockName in _blocksOf(port, tag) or tag in _blockTagsOf(port, blockName)
