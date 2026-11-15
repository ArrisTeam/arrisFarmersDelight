# -*- coding: utf-8 -*-
"""Items - 网易物品字典的取值小工具（双端）

物品是引擎给的字典 {"newItemName": 名字, "newAuxValue": aux, "count": 数量}，空槽是 None 或 {}。
配方里的物品身份是 (名字, aux) 元组。规则内核只收数量和元组，这里把字典拆成它们。
"""


def isEmpty(item):
    return not item or item.get("count", 0) <= 0


def countOf(item):
    return 0 if isEmpty(item) else item.get("count", 0)


def keyOf(item):
    """物品身份 (名字, aux)；空槽是 None。"""
    if isEmpty(item):
        return None
    return (item["newItemName"], item.get("newAuxValue", 0))


def countsOf(items):
    """各槽的数量（空槽 0）：PotMatch.servingsLeft / Assembly.rounds 要的就是它。"""
    return [countOf(item) for item in items]


def keysOf(items):
    """各槽的物品身份（空槽 None）。"""
    return [keyOf(item) for item in items]


def make(name, aux=0, count=1):
    """造一个物品字典（测试和占位用）。"""
    return {"newItemName": name, "newAuxValue": aux, "count": count}
