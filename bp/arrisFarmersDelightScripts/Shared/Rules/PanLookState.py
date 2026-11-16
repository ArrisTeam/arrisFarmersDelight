# -*- coding: utf-8 -*-
"""PanLookState - 一口煎锅"看上去是什么样"的状态：解读服务端广播、方块实体数据里存的那份、两面熟度按速度外推（双端，纯逻辑）

对应 Hands-On Delight 里每个客户端都跑的那部分（SkilletLogic.publish + SkilletBehavior.refresh 读的状态）：JE 靠方块实体的更新包和站点数据，
这边是服务端 Server/PanLook.py 发给 32 格内的人的载荷（静态的另存在方块实体数据里，区块重载时补：cookingDict、heatEnable、panFrying）：
    item 锅里的东西（物品线格式，空是 {}）、batch 算多少件煎、byHand 手放的（两面分开煎）、heated 有没有热源、
    down / up 贴锅面和朝上面熟到哪（0..1，发的那一刻）、rate 每秒往前走多少（0 = 停着：没火、在等翻面、熟了、空锅）、
    both 两面一起走（蛋从下往上一次煎透）。
载荷来自网络，逐项查类型，不对的当作没有。熟度和 JE 的站点数据一样按 1/32 一档取整（Frying.syncStep）：看的人只看档，不看细的。
"""
from .HandsOn.Frying import syncStep

DEFAULT_PAN_KEY = "panFrying"      # 方块实体数据里存两面进度的键


def _item(raw):
    """物品字典 -> {"newItemName", "newAuxValue", "count"}；空的或不合法的是 None。"""
    if not isinstance(raw, dict):
        return None
    name, count = raw.get("newItemName"), raw.get("count")
    if not name or not isinstance(count, (int, float)) or isinstance(count, bool) or count <= 0:
        return None
    aux = raw.get("newAuxValue") or 0
    return {"newItemName": str(name), "newAuxValue": int(aux) if isinstance(aux, (int, float)) else 0, "count": int(count)}


def _number(value, default=0.0, low=0.0, high=1.0):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
        return max(low, min(high, float(value)))
    return default


class Look(object):
    """一口煎锅此刻的样子。"""

    __slots__ = ("item", "batch", "byHand", "heated", "down", "up", "rate", "both", "stamp")

    def __init__(self):
        self.item = None
        self.batch = 0
        self.byHand = self.heated = self.both = False
        self.down = self.up = self.rate = 0.0
        self.stamp = 0.0

    def key(self):
        """静态部分的指纹：变了才算"锅里的东西变了"（重摆、落进来）。"""
        item = self.item
        return ((item["newItemName"], item["newAuxValue"], item["count"]) if item else None, self.byHand, self.heated)


def decode(payload, now, previous=None):
    """广播来的载荷 -> Look。载荷里没有的键沿用 previous 的值。now 是本端的钟（秒）。"""
    look = Look()
    if previous is not None:
        for name in Look.__slots__:
            setattr(look, name, getattr(previous, name))
    if not isinstance(payload, dict):
        return look
    if "item" in payload:
        look.item = _item(payload["item"])
    if "batch" in payload:
        look.batch = int(_number(payload["batch"], 0.0, 0.0, 64.0))
    for name, key in (("byHand", "byHand"), ("heated", "heated"), ("both", "both")):
        if key in payload:
            setattr(look, name, payload[key] is True)
    if "down" in payload or "up" in payload or "rate" in payload:
        look.down = _number(payload.get("down"), look.down)
        look.up = _number(payload.get("up"), look.up)
        look.rate = _number(payload.get("rate"), look.rate, 0.0, 10.0)
        look.stamp = now
    if look.item is None:
        look.down = look.up = look.rate = 0.0
    return look


def progressAt(look, now):
    """按上次收到的熟度和速度外推到此刻，取成 1/32 一档：(贴锅面, 朝上面)。"""
    gone = look.rate * max(0.0, now - look.stamp)
    down = min(1.0, look.down + gone)
    up = min(1.0, look.up + gone) if look.both else look.up
    return syncStep(down), syncStep(up)


def fromBlockData(data):
    """区块晚加载的客户端：按方块实体里存的（已经解包的 dict）摆出这口锅，没有的键当空。"""
    look = Look()
    if not isinstance(data, dict):
        return look
    look.item = _item(data.get("cookingDict"))
    look.heated = data.get("heatEnable") is True
    frying = data.get(DEFAULT_PAN_KEY)
    if isinstance(frying, dict) and look.item is not None:
        look.byHand = frying.get("byHand") is True
        look.down = _number(frying.get("down"))
        look.up = _number(frying.get("up"))
        look.batch = int(_number(frying.get("batch"), 0.0, 0.0, 64.0))
    return look
