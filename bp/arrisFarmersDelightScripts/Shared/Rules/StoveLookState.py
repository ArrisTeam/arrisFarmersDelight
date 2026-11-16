# -*- coding: utf-8 -*-
"""StoveLookState - 一座炉灶"看上去是什么样"的状态：解读服务端广播、方块实体数据里存的那份（双端，纯逻辑）

对应 Hands-On Delight 里每个客户端都跑的那部分（StoveLogic.publish + StoveBehavior.refresh 读的状态）：JE 靠方块实体的更新包和站点数据，
这边是服务端 Server/StoveLook.py 发给 32 格内的人的载荷（静态的另存在方块实体数据里，区块重载时补："0".."5" 六个烤位、handGrill 手放的进度）：
    slots   六个烤位，每个是 {}（空）或 {"item": 物品线格式, "hand": 手放的（两面分开烤）, "down": 贴灶那面烤到哪, "up": 朝上那面烤到哪}（0..1，1/32 一档）
画面只关心：哪件东西、是不是手放的、贴灶那面熟没熟（冒不冒烟等翻）、朝上那面熟到哪（画熟的还是生的），所以只在这些变了时才广播，
不用像煎锅那样按速度往前推。载荷来自网络，逐项查类型，不对的当作没有。
"""
from .HandsOn import StoveLayout
from .HandsOn.Frying import syncStep

PLACES = StoveLayout.PLACES
INTS = (int, type(2 ** 64))      # py2 的 int / long（网络来的整数可能是 long）
SAVE_KEY = "handGrill"          # 方块实体数据里存手放进度的键（Server/HandGrill.SAVE_KEY）


def _item(raw):
    """物品字典 -> {"newItemName", "newAuxValue", "count"}；空的或不合法的是 None。"""
    if not isinstance(raw, dict):
        return None
    name, count = raw.get("newItemName"), raw.get("count")
    if not name or not isinstance(count, INTS + (float,)) or isinstance(count, bool) or count <= 0:
        return None
    aux = raw.get("newAuxValue") or 0
    return {"newItemName": str(name), "newAuxValue": int(aux) if isinstance(aux, INTS + (float,)) and not isinstance(aux, bool) else 0, "count": int(count)}


def _number(value, default=0.0):
    if isinstance(value, INTS + (float,)) and not isinstance(value, bool) and value == value:
        return max(0.0, min(1.0, float(value)))
    return default


class Look(object):
    """一座炉灶此刻的样子：六个烤位各自的东西、手放的吗、贴灶面和朝上面烤到哪。"""

    __slots__ = ("items", "hand", "down", "up")

    def __init__(self):
        self.items = [None] * PLACES
        self.hand = [False] * PLACES
        self.down = [0.0] * PLACES
        self.up = [0.0] * PLACES

    def data(self):
        """站点里 Pieces 读的 data（down / up / hand 三个长 6 的列表）。"""
        return {"down": list(self.down), "up": list(self.up), "hand": list(self.hand)}

    def getItem(self, ref):
        """ref 是 (槽组, 序号)，和站点状态同一个读法。"""
        place = ref[1] if isinstance(ref, (tuple, list)) and len(ref) == 2 else -1
        return self.items[place] if isinstance(place, INTS) and not isinstance(place, bool) and 0 <= place < PLACES else None


def decode(payload):
    """广播来的载荷 -> Look（整份换，没有"沿用上一份"：六个烤位每次都带齐）。"""
    look = Look()
    slots = payload.get("slots") if isinstance(payload, dict) else None
    if not isinstance(slots, list):
        return look
    for place in range(min(PLACES, len(slots))):
        slot = slots[place] if isinstance(slots[place], dict) else {}
        look.items[place] = _item(slot.get("item"))
        if look.items[place] is not None:
            look.hand[place] = slot.get("hand") is True
            look.down[place], look.up[place] = _number(slot.get("down")), _number(slot.get("up"))
    return look


def fromBlockData(data):
    """区块晚加载的客户端：按方块实体里存的（已经解包的 dict）摆出这座炉灶，没有的键当空。进度取 1/32 一档，和广播一样。"""
    look = Look()
    if not isinstance(data, dict):
        return look
    saved = data.get(SAVE_KEY) if isinstance(data.get(SAVE_KEY), dict) else {}
    for place in range(PLACES):
        slot = data.get(str(place))
        look.items[place] = _item(slot.get("itemDict")) if isinstance(slot, dict) else None
        if look.items[place] is None:
            continue
        look.hand[place] = _at(saved.get("byHand"), place) in (True, 1)
        look.down[place], look.up[place] = syncStep(_number(_at(saved.get("down"), place))), syncStep(_number(_at(saved.get("up"), place)))
    return look


def _index(value):
    return isinstance(value, INTS) and not isinstance(value, bool) and 0 <= value < PLACES


def _at(values, place):
    return values[place] if isinstance(values, list) and place < len(values) else None


def eventData(payload):
    """一次性事件的负载 -> 干净的 {"place", "places", "stack", "up"}：序号要在 0..5 里、栈按物品字典查、up 夹进 0..1，别的键不要。"""
    payload = payload if isinstance(payload, dict) else {}
    place = payload.get("place")
    places = payload.get("places")
    up = payload.get("up")
    return {"place": int(place) if _index(place) else None, "places": [int(at) for at in places if _index(at)] if isinstance(places, list) else [],
            "stack": _item(payload.get("stack")), "up": _number(up, None) if isinstance(up, INTS + (float,)) and not isinstance(up, bool) else None}
