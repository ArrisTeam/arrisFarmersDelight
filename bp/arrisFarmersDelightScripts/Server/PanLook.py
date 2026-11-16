# -*- coding: utf-8 -*-
"""PanLook - 煎锅的世界外观广播：附近的人都看得见锅里的东西、油在冒、锅被颠、东西煎好了（服务端）

HoD 的煎锅场景是 idle_visible：32 格内每个客户端都按同步来的状态自己演全部动作（SkilletLogic 在客户端也跑，只读）。基岩版的客户端拿不到
站点状态，靠这条广播：服务端把锅的样子发给同维度 32 格内的玩家（客户端 Compat/Diegesis/PanScenes 的 OnPanLook 去演）。默认关着，
前置包在场时由 Compat/Diegesis/ServerBoot 打开（enable），没装前置包什么都不发。新走进 32 格的人单发一份当前的样子（Helpers/LookWatch：
等翻面、煎好留在锅里这些不再变的状态，不补的话走近的人永远看到旧的）。负载（Call 到 OnPanLook）：
    {"dimensionId", "pos": [x, y, z], "item": 锅里的东西（物品线格式，空是 {}）, "batch": 算多少件煎, "byHand": 手放的（两面分开煎）,
     "heated": 有没有热源, "down" / "up": 贴锅面 / 朝上面熟到哪（0..1）, "rate": 每秒往前走多少（0 = 停着）, "both": 两面一起走（蛋）}
状态变了（东西、批量、手放、热源、开始 / 停止走、颠了一下）马上发；在走的时候每 KEYFRAME_SECONDS 秒补一次，客户端按 rate 往前推。
一次性的事件（placed / tossed / untossed / taken / fried）走同一个端点，负载是 {"dimensionId", "pos", "event": 名字, ...}，发给附近所有人
（包括正在用站点的人：他的客户端按"自己刚颠过"去重）。锅的计时和这里一样用真实时间，不受 /time 影响。
"""
from .Helpers import LookWatch
from .Helpers.Engine import Call
from ..Shared.Rules import PanStation, SkilletRules

ENDPOINT = "OnPanLook"
RANGE = LookWatch.RANGE
KEYFRAME_SECONDS = 1.0     # 熟度在走时多久补发一次
STORED_KEY = "skilletItem"
_enabled = [False]
_sent = {}                 # (维度, 坐标) -> {"sig": 上次发的签名, "at": 上次发的时刻, "audience": 已经收到当前样子的人}


def enable(on=True):
    _enabled[0] = bool(on)


def enabled():
    return _enabled[0]


def forget(dimensionId, blockPos):
    _sent.pop((dimensionId, tuple(blockPos)), None)


def _wire(item):
    if not item or (item.get("count") or 0) <= 0 or not item.get("newItemName"):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def fireAspectOf(blockEntityData):
    """方块里那件煎锅的火焰附加等级（没存过是 0；和 SkilletItem.fireAspectOf 同一个读法，这里不导入它）。"""
    return SkilletRules.fireAspectLevel(blockEntityData[STORED_KEY]) if blockEntityData else 0


def rateOf(item, frying, heated, fireAspect):
    """熟度每秒走多少：热着、手放的、食物还没熟透、贴锅面没在等翻面才走；蛋从下往上一次煎透（两面一起，速度减半）。"""
    if not item or not heated or not frying.byHand or PanStation.friedOf(item["newItemName"]) is None or frying.isDone() or frying.waits():
        return 0.0
    batch = frying.batch or max(1, min(item.get("count") or 1, PanStation.BATCH))
    return (0.5 if PanStation.isOneSided(item["newItemName"]) else 1.0) / PanStation.sideSeconds(batch, fireAspect)


def build(dimensionId, blockPos, blockEntityData, hand):
    """锅现在的样子（上面说的负载）。"""
    item = blockEntityData["cookingDict"]
    frying = hand.frying
    heated = blockEntityData["heatEnable"] is True
    rate = rateOf(item, frying, heated, fireAspectOf(blockEntityData))
    return {"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "item": _wire(item),
            "batch": int(frying.batch), "byHand": bool(frying.byHand), "heated": bool(heated),
            "down": round(frying.down, 4), "up": round(frying.up, 4), "rate": round(rate, 5),
            "both": bool(item and PanStation.isOneSided(item["newItemName"]))}


def _signature(payload, hand):
    item = payload["item"]
    return ((item.get("newItemName"), item.get("newAuxValue"), item.get("count")) if item else None, payload["batch"], payload["byHand"],
            payload["heated"], payload["rate"] > 0.0, hand.tosses)


def nearby(dimensionId, blockPos, now=None):
    """同维度、离方块 RANGE 格内的玩家（给了 now 就用 LookWatch 的快照）。"""
    return LookWatch.nearby(dimensionId, blockPos, now)


def tick(dimensionId, blockPos, blockEntityData, hand, now):
    """锅每个步（和每次动作）之后：状态变了就发给附近所有人；熟度在走时每 KEYFRAME_SECONDS 秒补一次；
    没变的时候，刚走进 32 格的人单发一份当前的样子（他们错过了上一次广播）。"""
    if not _enabled[0] or blockEntityData is None:
        return
    entry = _sent.setdefault((dimensionId, tuple(blockPos)), {"sig": None, "at": -1.0e12, "audience": LookWatch.Audience()})
    payload = build(dimensionId, blockPos, blockEntityData, hand)
    signature = _signature(payload, hand)
    near = nearby(dimensionId, blockPos, now)
    if signature != entry["sig"] or (payload["rate"] > 0.0 and now - entry["at"] >= KEYFRAME_SECONDS):
        entry["sig"], entry["at"] = signature, now
        entry["audience"].sent(near)
        _send(near, payload)
    else:
        _send(entry["audience"].arrivals(near), payload)


def _send(players, payload):
    for playerId in players:
        Call(playerId, ENDPOINT, payload)


def event(dimensionId, blockPos, name, data=None):
    """一次性的事件发给附近所有人。"""
    if not _enabled[0]:
        return
    payload = {"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "event": name}
    payload.update(data or {})
    _send(nearby(dimensionId, blockPos), payload)
