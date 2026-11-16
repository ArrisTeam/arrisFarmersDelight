# -*- coding: utf-8 -*-
"""PotLookState - 一口厨锅"看上去是什么样"的状态：解读服务端广播、算浮着哪几格、新放进了哪几格、进度外推（双端，纯逻辑）

对应 Hands-On Delight 里每个客户端都跑的那部分（PotLogic.refresh + PotBehavior.frame 读的状态）：JE 靠方块实体的更新包，
这边是服务端 Server/PotLook.py 发给 32 格内的人的载荷（静态部分另存在方块实体数据的 potLook 里，区块重载时补）：
    items 6 格料、served 产出格里装好的、meal 锅里煮好还没装的（count = 份数）、dish 这些料能做的菜、sunk 不浮的那几格、
    heated、stirring、spoon [x, z]（世界朝向，-1..1 = 勺尖偏移 / 2.3 像素）、progress 0..1、rate 每秒进度、cooking。
载荷来自网络，逐项查类型，不对的当作没有。
"""
SLOTS = 6
NO_SPOON = (0.0, 0.0)


def _item(raw):
    """物品字典 -> {"newItemName", "newAuxValue", "count"}；空的或不合法的是 None。"""
    if not isinstance(raw, dict):
        return None
    name, count = raw.get("newItemName"), raw.get("count")
    if not name or not isinstance(count, (int, float)) or isinstance(count, bool) or count <= 0:
        return None
    aux = raw.get("newAuxValue") or 0
    return {"newItemName": str(name), "newAuxValue": int(aux) if isinstance(aux, (int, float)) else 0, "count": int(count)}


def _number(value, default=0.0):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e6:
        return float(value)
    return default


class Look(object):
    """一口锅此刻的样子。"""

    __slots__ = ("items", "served", "meal", "dish", "sunk", "heated", "stirring", "spoon", "progress", "rate", "cooking", "stamp")

    def __init__(self):
        self.items = [None] * SLOTS
        self.served = self.meal = self.dish = None
        self.sunk = frozenset()
        self.heated = self.stirring = self.cooking = False
        self.spoon = NO_SPOON
        self.progress = self.rate = 0.0
        self.stamp = 0.0

    def staticKey(self):
        """静态部分的指纹：变了才重算汤色、重摆道具。"""
        def key(item):
            return (item["newItemName"], item["newAuxValue"], item["count"]) if item else None
        return (tuple(key(item) for item in self.items), key(self.served), key(self.meal), key(self.dish),
                tuple(sorted(self.sunk)), self.heated)


def decode(payload, now, previous=None):
    """广播来的载荷 -> Look。载荷里没有的键沿用 previous 的值（静态、动态可以分开发）。now 是本端的钟（秒）。"""
    look = Look()
    if previous is not None:
        for name in Look.__slots__:
            setattr(look, name, getattr(previous, name))
        look.items = list(previous.items)
    if not isinstance(payload, dict):
        return look
    if isinstance(payload.get("items"), (list, tuple)):
        items = [_item(raw) for raw in list(payload["items"])[:SLOTS]]
        look.items = items + [None] * (SLOTS - len(items))
    for name in ("served", "meal", "dish"):
        if name in payload:
            setattr(look, name, _item(payload[name]))
    if isinstance(payload.get("sunk"), (list, tuple)):
        look.sunk = frozenset(int(slot) for slot in payload["sunk"]
                              if isinstance(slot, (int, float)) and not isinstance(slot, bool) and 0 <= slot < SLOTS)
    for name in ("heated", "stirring", "cooking"):
        if name in payload:
            setattr(look, name, payload[name] is True)
    spoon = payload.get("spoon")
    if isinstance(spoon, (list, tuple)) and len(spoon) == 2:
        look.spoon = (max(-1.0, min(1.0, _number(spoon[0]))), max(-1.0, min(1.0, _number(spoon[1]))))
    if "progress" in payload or "rate" in payload:
        look.progress = max(0.0, min(1.0, _number(payload.get("progress"), look.progress)))
        look.rate = max(0.0, _number(payload.get("rate"), look.rate))
        look.stamp = now
    return look


def presentOf(look):
    """每格是不是有一件浮着的整料（有东西、不是倒进去化掉的那类）。"""
    return [look.items[slot] is not None and slot not in look.sunk for slot in range(SLOTS)]


def filledOf(look):
    """非空的食材格数（水位按它算，沉下去的也占一格）。"""
    return sum(1 for item in look.items if item is not None)


def hasFood(look):
    """锅里有没有东西：任何一格料，或煮好还没装的菜（PotLogic.hasFood：食材格加成品格；产出格里装好的不算）。
    场景有东西才自己放沸腾声、农夫乐事自己的那条才让位（CookingPotBlockMixin）；空锅烧着，农夫乐事自己的水沸声照响。"""
    return look.meal is not None or any(item is not None for item in look.items)


def servingsOf(look):
    return look.meal["count"] if look.meal else 0


def arrivedBetween(old, new):
    """从 old 到 new 新放进了东西的格子（按格号）：原来空着、现在有。old 为 None（刚看到这口锅）时一个都不算。"""
    if old is None:
        return []
    return [slot for slot in range(SLOTS) if old.items[slot] is None and new.items[slot] is not None]


def grewBetween(old, new):
    """从 old 到 new 个数涨了的下锅就沉的格子（同一种、数量多了：第二个蛋叠在第一个的格子里）。old 为 None 时一个都不算。
    会沉的才算（PotBehavior.refresh 的 sinks(now) && isSameItem && count 涨了）：浮着的料叠多了没有任何动作。"""
    if old is None:
        return []
    grown = []
    for slot in range(SLOTS):
        before, now = old.items[slot], new.items[slot]
        if before is not None and now is not None and slot in new.sunk and (before["newItemName"], before["newAuxValue"]) == (
                now["newItemName"], now["newAuxValue"]) and now["count"] > before["count"]:
            grown.append(slot)
    return grown


def emptiedBetween(old, new):
    """从 old 到 new 被拿空的格子。"""
    if old is None:
        return []
    return [slot for slot in range(SLOTS) if old.items[slot] is not None and new.items[slot] is None]


def progressAt(look, now):
    """按上次收到的进度和速度外推到此刻（服务端每 2 秒校一次）。"""
    return max(0.0, min(1.0, look.progress + look.rate * max(0.0, now - look.stamp)))


def foodOf(look):
    """JE 的 food 列表：有成品时只有成品，否则是各食材格加产出格里的东西。"""
    if look.meal:
        return [look.meal]
    return [item for item in look.items if item is not None] + ([look.served] if look.served else [])
