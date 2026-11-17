# -*- coding: utf-8 -*-
"""StoveLook - 炉灶的世界外观广播：附近的人都看得见烤架上的东西、冒烟等翻、翻面落下取走的动作、烤好的汽和闪（服务端）

HoD 的炉灶场景是 idle_visible：32 格内每个客户端都按同步来的状态自己演全部动作（StoveLogic 在客户端也跑，只读），厨师关了站点、
没人开着站点，"该翻了"的烟和嗞嗞声照样在。基岩版的客户端拿不到站点状态，靠这条广播（和煎锅的 PanLook 同一个做法）：服务端把灶的样子发给
同维度 32 格内的玩家，新走进 32 格的人单发一份当前的样子、样子没变时每隔 REFRESH_SECONDS 秒再单发一份（Helpers/LookWatch：广播丢了——客户端还没
就绪、区块还没加载好——服务端当他收到了，等翻 / 烤好留在灶上这些状态又不再变，不补就永远看不到）；开站点的人开站那一刻单发一份（resend）；
客户端 Compat/Diegesis/StoveScenes 的 OnStoveLook 去演。
默认关着，前置包在场时由 Compat/Diegesis/ServerBoot 打开（enable），没装前置包什么都不发。负载（Call 到 OnStoveLook）：
    {"dimensionId", "pos": [x, y, z], "slots": 六个烤位，每个 {}（空）或 {"item": 物品线格式, "hand": 手放的（两面分开烤）,
     "down" / "up": 贴灶面 / 朝上面烤到哪（0..1，1/32 一档）}}
画面只看哪件东西、手放的吗、贴灶面熟没熟（冒烟等翻）、朝上面熟到哪（画熟的还是生的），所以只在这些变了时才发，不按速度往前推。
一次性的事件（placed / refused / turned / unturned / taken / grilled）走同一个端点，负载是 {"dimensionId", "pos", "event": 名字, ...}，发给附近所有人
（包括正在用站点的人：他的客户端按"自己刚翻过"去重）。
"""
from . import HandGrill
from .Helpers import LookWatch
from .Helpers.Engine import Call
from ..Shared.Rules import GrillStation
from ..Shared.Rules.HandsOn import Frying, Mth, StoveLook as Look

ENDPOINT = "OnStoveLook"
_enabled = [False]
_sent = {}                 # (维度, 坐标) -> {"sig": 上次发的签名, "audience": 已经收到当前样子的人}


def enable(on=True):
    _enabled[0] = bool(on)


def enabled():
    return _enabled[0]


def forget(dimensionId, blockPos):
    _sent.pop((dimensionId, tuple(blockPos)), None)


def wire(item):
    """物品的线格式（空是 {}）。"""
    if not item or (item.get("count") or 0) <= 0 or not item.get("newItemName"):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def build(dimensionId, blockPos, blockEntityData, hand):
    """灶现在的样子（上面说的负载）；hand 是 HandGrill 的手放状态，没有（没人手放过）就全是 FD 原样的。"""
    grill = hand.grill if hand is not None else None
    slots = []
    for place in range(GrillStation.PLACES):
        item = HandGrill.slotItem(blockEntityData, place)
        if item is None:
            slots.append({})
            continue
        slots.append({"item": wire(item), "hand": bool(grill and grill.byHand(place)),
                      "down": Frying.syncStep(grill.down(place)) if grill else 0.0,
                      "up": Frying.syncStep(grill.up(place)) if grill else 0.0})
    return {"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "slots": slots}


def _signature(payload):
    """画面看得出的东西：哪件东西、手放的吗、贴灶面熟没熟、朝上面在哪一档（Pieces 朝上那面每 1/12 才重画一次）。"""
    return tuple((slot["item"]["newItemName"], slot["item"]["newAuxValue"], slot["hand"], Mth.reached(slot["down"]), Look.look(slot["up"]))
                 if slot else None for slot in payload["slots"])


def tick(dimensionId, blockPos, blockEntityData, hand, now):
    """灶每个步（和每次动作）之后：样子变了就发给附近所有人；没变的时候，刚走进 32 格的人单发一份当前的样子。"""
    if not _enabled[0] or blockEntityData is None:
        return
    entry = _sent.setdefault((dimensionId, tuple(blockPos)), {"sig": None, "audience": LookWatch.Audience(LookWatch.REFRESH_SECONDS)})
    near = LookWatch.nearby(dimensionId, blockPos, now)
    if not near:
        entry["audience"].sent(near, now)             # 范围里没人：样子不用算，名单清空（谁回来都算新来的）
        return
    payload = build(dimensionId, blockPos, blockEntityData, hand)
    signature = _signature(payload)
    if signature != entry["sig"]:
        entry["sig"] = signature
        entry["audience"].sent(near, now)
        _send(near, payload)
    else:
        _send(entry["audience"].arrivals(near, now), payload)


def resend(dimensionId, blockPos, blockEntityData, hand, playerId):
    """这个人要开这座灶的站点：当前的样子单发给他一份（开站要用它摆命中盒、认哪几个烤位有东西，他的客户端可能还没收到过）。"""
    if _enabled[0] and blockEntityData is not None:
        _send([playerId], build(dimensionId, blockPos, blockEntityData, hand))


def _send(players, payload):
    for playerId in players:
        Call(playerId, ENDPOINT, payload)


def event(dimensionId, blockPos, name, data=None):
    """一次性的事件发给附近所有人。"""
    if not _enabled[0]:
        return
    payload = {"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "event": name}
    payload.update(data or {})
    _send(LookWatch.nearby(dimensionId, blockPos), payload)
