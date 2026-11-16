# -*- coding: utf-8 -*-
"""ItemData - 板上的东西带着的数据（附魔、耐久、改名、extraId、userData）：存不存得住、怎么写进方块实体数据、怎么读回来、两件算不算同一种（双端，纯规则）

JE 里板上的东西是整件的 ItemStack：附魔、名字、NBT 原样跟着，取回时原样还（BoardLogic.place 的 split / copyWithCount），
isSameItemSameTags 才叠在一起。基岩的物品字典 {"newItemName", "newAuxValue", "count", ...} 多出来的这几个键
    durability / enchantData / modEnchantData / customTips / extraId / userData
和煎锅（SkilletRules.storeItem / restoreItem）一样存进方块实体数据：方块实体数据只收 str 键、同类元素的列表、非 unicode 的字符串，
所以元组换成列表、py2 的 unicode 换成 str；读回来时附魔列表换回 (类型, 等级) 元组再交给引擎。
存不住的（键不是 str、列表里类型混着、非有限小数、嵌套太深、太大、引擎对象之类）storable 说"否"，板就不收（和 carve 的守卫一个意思），
绝不悄悄丢数据。showInHand 这类只管怎么显示的键不算物品的数据，不存。
"""
import copy

KEYS = ("durability", "enchantData", "modEnchantData", "customTips", "extraId", "userData")
ENCHANTS = ("enchantData", "modEnchantData")
MAX_DEPTH = 16                      # 嵌套层数上限（同前置包 Wire.MAX_DEPTH：方块实体数据递归读写，不能被一个很深的结构拖垮）
MAX_NODES = 1024                    # 一件东西的数据最多这么多个节点：板是一格方块，装不下一本写满字的书
_TEXT = type(u"")
_INTS = (int, type(2 ** 64))
_INF = float("inf")
_LIMIT = 2 ** 63


def _plain(value):
    """元组换成列表，py2 的 unicode 换成 str（键和值都转），其余原样。"""
    if isinstance(value, dict):
        return dict((_plain(key), _plain(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, _TEXT) and _TEXT is not str:
        return value.encode("utf-8")
    return value


def _blank(key, value):
    """没设置的数据：None、空串、空列表 / 字典；耐久 0 是"不会坏的物品"（引擎读出来是 0）。"""
    if value is None:
        return True
    if key == "durability":
        return not value
    return isinstance(value, (list, tuple, dict, str, _TEXT)) and len(value) == 0


def dataOf(item):
    """物品上有的数据：{键: 规范化的值（列表、str）}，没有的键不列。空物品是 {}。"""
    found = {}
    for key in KEYS:
        value = item.get(key) if item else None
        if not _blank(key, value):
            found[key] = _plain(value)
    return found


def _kind(value):
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, _INTS):
        return "int"
    if isinstance(value, float):
        return "float"
    if type(value) is str:
        return "str"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    return "other"


def _problem(value, depth=0, nodes=None):
    """第一处存不进方块实体数据的地方的描述；都能存是 None。规则同前置包的 Wire.wireProblem，再加整数范围和节点数上限。"""
    nodes = nodes if nodes is not None else [0]
    nodes[0] += 1
    if nodes[0] > MAX_NODES:
        return "数据太大（超过 %d 个节点）" % MAX_NODES
    kind = _kind(value)
    if kind in ("none", "bool", "str"):
        return None
    if kind == "int":
        return None if -_LIMIT <= value < _LIMIT else "整数超出 64 位"
    if kind == "float":
        return "非有限小数" if value != value or value in (_INF, -_INF) else None
    if kind in ("dict", "list") and depth >= MAX_DEPTH:
        return "嵌套超过 %d 层" % MAX_DEPTH
    if kind == "dict":
        for key, item in value.items():
            if _kind(key) != "str":
                return "键 %r 不是 str" % (key,)
            problem = _problem(item, depth + 1, nodes)
            if problem is not None:
                return problem
        return None
    if kind == "list":
        kinds = set(_kind(item) for item in value)
        if len(kinds) > 1:
            return "列表元素类型不一致 %s" % sorted(kinds)
        for item in value:
            problem = _problem(item, depth + 1, nodes)
            if problem is not None:
                return problem
        return None
    return "不允许的类型"


def storable(item):
    """这件东西的数据（dataOf）都存得进方块实体数据吗。没有数据的当然存得住。"""
    for value in dataOf(item).values():
        if _problem(value) is not None:
            return False
    return True


def _normal(key, value):
    """比较用：附魔按内容比、不看顺序，也不分元组和列表。"""
    if key in ENCHANTS:
        return sorted((tuple(entry) if isinstance(entry, list) else (entry,) for entry in value), key=repr)
    return value


def same(a, b):
    """两件东西的数据一样吗（JE 的 isSameItemSameTags 里"tags"那一半；名字和 aux 另外比）。"""
    left, right = dataOf(a), dataOf(b)
    if set(left) != set(right):
        return False
    return all(_normal(key, left[key]) == _normal(key, right[key]) for key in left)


def copyOf(item, count=None):
    """板上、手里用的一份：名字、aux、数量加上全部数据（深拷贝，附魔的元组还是元组）；count 给了就改数量。"""
    out = {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0,
           "count": int(item.get("count") or 1) if count is None else int(count)}
    for key in KEYS:
        value = item.get(key)
        if not _blank(key, value):
            out[key] = copy.deepcopy(value)
    return out


def light(item, count=None):
    """只给客户端看的一份（弹回 / 拿走的动画用）：名字、aux、数量，带耐久的工具再加耐久；不带别的数据，事件载荷里不放元组。"""
    out = {"newItemName": _plain(item["newItemName"]), "newAuxValue": item.get("newAuxValue") or 0,
           "count": int(item.get("count") or 1) if count is None else int(count)}
    if item.get("durability"):
        out["durability"] = item["durability"]
    return out


def stored(item, count=None):
    """要写进方块实体数据的一份：名字（str）、aux、数量加上规范化的数据（附魔是列表的列表）。"""
    out = {"newItemName": _plain(item["newItemName"]), "newAuxValue": int(item.get("newAuxValue") or 0),
           "count": int(item.get("count") or 1) if count is None else int(count)}
    out.update(dataOf(item))
    return out


def restored(item):
    """从方块实体数据读出来的一份换回物品字典（附魔换回 (类型, 等级) 元组，引擎要这个）；读出来的可能是引擎对象，所以一律先规范化。"""
    out = {"newItemName": _plain(item["newItemName"]), "newAuxValue": int(item.get("newAuxValue") or 0), "count": int(item.get("count") or 0)}
    for key, value in dataOf(item).items():
        out[key] = [tuple(entry) if isinstance(entry, list) else entry for entry in value] if key in ENCHANTS else value
    return out
