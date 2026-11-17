# -*- coding: utf-8 -*-
"""PotLook - 厨锅的世界外观广播：附近的玩家看得到汤里的料、勺子在转、锅在煮（服务端）

站点开着的人看站点里的画面；周围没开站点的人看到的是方块——HoD 里"附近的玩家看得见汤在滚、勺子在转、料落进锅里"，
这里靠这条广播：服务端把锅的样子发给同维度 32 格内的玩家（客户端的 OnPotLook 去画）。默认关着，前置包在场时由
Compat/Diegesis/ServerBoot 打开（enable），没装前置包什么都不发。负载（Call 到 OnPotLook）：
    {"dimensionId", "pos": [x, y, z], "items": [6 件料的线格式或 {}], "served": 产出格, "meal": 煮好待盛的菜, "dish": 现在这些料能做的菜,
     "sunk": [沉着的格号], "heated": 有没有热源, "stirring": 锅算不算被搅着, "spoon": [x, z]（世界朝向，-1..1，同 spoon_x / spoon_z），
     "progress": 0..1, "rate": 进度每秒走多少（0 = 停着）, "cooking": 加热着、被搅着、有料可做、没有菜等着盛}
静态的部分（items / served / meal / dish / sunk / heated）变了就写进方块实体数据 potLook（区块晚加载的客户端从它恢复），
锅的 5 Hz 步里查；写进去的是同一份，只是空的几项（served / meal / dish 是 {}、sunk 是 []）不写，读的人缺键当空
（引擎文档只说列表各项要同类型，空列表和空字典放不放得下没说，不碰）。
勺子每个被接受的搅拌发一次（每口锅每秒最多 8 次）；进度在走时每 2 秒补一次，客户端按 rate 往前推。
样子没变的时候，刚走进 32 格的人单发一份当前的样子：别人做菜时他在 32 格外（区块却加载着），客户端的场景停在老样子上，走近了也没有下一次
变化来纠正（煮好等着盛的锅不再变）；发出去的那一份也可能丢（客户端还没就绪），所以过几秒再补，间隔逐次加倍（Helpers/LookWatch.Audience）。
一次性的事件（盛出 scooped、整批出锅 served）走同一个端点，负载是 {"dimensionId", "pos", "event": 名字, ...}，只发给没开站点的旁观者
（开站点的人从站点的表现事件里拿到；站点每刻用 attend 告诉这里现在有谁在用它）。
"""
from .Helpers import LookWatch, PotContainer
from ..QuModLibs.Server import MultiClientsCall
from ..Shared.Rules import PotStation
from ..Shared.Rules.HandsOn import PotCooking

ENDPOINT = "OnPotLook"
RANGE = LookWatch.RANGE    # 32 格，与前置包的 WATCH_RANGE 一致（两个包互不导入）
LOOK_KEY = "potLook"       # 方块实体数据里静态部分的镜像
STROKE_INTERVAL = 0.125    # 搅拌时每口锅最多每秒发 8 次
MOVING_INTERVAL = 2.0      # 进度在走时每 2 秒补一次
_enabled = [False]
_sent = {}                 # (维度, 坐标) -> {"static": 签名, "at": 上次发的时刻, "stroke": 上次搅拌发的时刻, "stirring", "moving",
                           #                  "served": 上次见到的出锅批数, "users": 正在用站点的人, "audience": 收到当前样子的人}


def enable(on=True):
    _enabled[0] = bool(on)


def enabled():
    return _enabled[0]


def forget(dimensionId, blockPos):
    _sent.pop((dimensionId, tuple(blockPos)), None)


def attend(dimensionId, blockPos, users):
    """站点每刻告诉这里：现在有这些玩家在用这口锅的站点（一次性事件不发给他们，他们从站点的表现事件里拿）。"""
    if _enabled[0]:
        _entry(dimensionId, blockPos)["users"] = list(users)


def _wire(item):
    if not item or (item.get("count") or 0) <= 0 or not item.get("newItemName"):
        return {}
    return {"newItemName": PotContainer.plain(item["newItemName"]), "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def _signature(wire):
    return (wire.get("newItemName"), wire.get("newAuxValue"), wire.get("count")) if wire else None


def _rate(hand):
    """进度每秒走多少：被搅着的整批 = 批量速度 / 一份总时长，FD 原样 = 1 / 总时长，不煮 = 0。"""
    if not (hand.heated and hand.dish) or hand.total <= 0.0:
        return 0.0
    if hand.mode == PotCooking.STIRRED:
        return PotCooking.batchSpeed(hand.batch) / hand.total
    return 1.0 / hand.total if hand.mode == PotCooking.FD_WAY else 0.0


def build(dimensionId, blockPos, items, served, meal, hand, now):
    """锅现在的样子（上面说的负载）：items 是 6 个食材格，served 产出格，meal 预览槽里煮好的菜，hand 是这口锅的 PotHand。"""
    stirring = hand.clock.isStirred(now)
    wires = [_wire(item) for item in items]
    return {
        "dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])],
        "items": wires, "served": _wire(served), "meal": _wire(meal), "dish": _wire(hand.dish),
        "sunk": PotStation.sunkSlots(items), "heated": bool(hand.heated),
        "stirring": stirring, "spoon": [round(hand.spoonAt[0], 3), round(hand.spoonAt[1], 3)] if stirring else [0.0, 0.0],
        "progress": round(hand.clock.progress(hand.total, hand.batch), 3), "rate": round(_rate(hand), 5),
        "cooking": bool(hand.heated and stirring and hand.dish and not meal),
    }


def _static(payload):
    """静态的部分（变了才写方块实体数据、才算"静态变了"）。"""
    return dict((key, payload[key]) for key in ("items", "served", "meal", "dish", "sunk", "heated"))


def _mirror(static):
    """写进方块实体数据的样子：静态部分里空的几项不写（读的人缺键当空）；items 一直是 6 项（空格是 {}，和 previewItemSlot 一样的写法）。"""
    mirror = {"items": static["items"], "heated": static["heated"]}
    for key in ("served", "meal", "dish"):
        if static[key]:
            mirror[key] = static[key]
    if static["sunk"]:
        mirror["sunk"] = static["sunk"]
    return mirror


def _signatureOf(static):
    return (tuple(_signature(w) for w in static["items"]), _signature(static["served"]), _signature(static["meal"]),
            _signature(static["dish"]), tuple(static["sunk"]), static["heated"])


def _nearby(dimensionId, blockPos, now=None):
    """同维度、离方块 RANGE 格内的玩家（给了 now 就用 LookWatch 半秒内的快照）。"""
    return LookWatch.nearby(dimensionId, blockPos, now)


def _entry(dimensionId, blockPos):
    entry = _sent.get((dimensionId, tuple(blockPos)))
    if entry is None:
        entry = _sent[(dimensionId, tuple(blockPos))] = {
            "static": None, "at": -1.0e12, "stroke": -1.0e12, "stirring": None, "moving": False, "served": None, "users": [],
            "audience": LookWatch.Audience(LookWatch.REFRESH_SECONDS, LookWatch.REFRESH_MOST)}
    return entry


def _send(payload, entry, now):
    entry["at"], entry["stirring"], entry["moving"] = now, payload["stirring"], payload["rate"] > 0.0
    players = _nearby(payload["dimensionId"], payload["pos"], now)
    entry["audience"].sent(players, now)
    if players:
        MultiClientsCall(players, ENDPOINT, payload)


def tick(dimensionId, blockPos, blockEntityData, hand, slots, now):
    """锅的 5 Hz 步之后：静态的部分变了就写方块实体数据并广播；被搅着的状态变了、进度停了或开始走也发；进度在走时每 2 秒补一次；
    都没有的时候，刚走进 32 格的人、隔够了的人单发一份当前的样子。slots 是这一步刚读的 6 个食材格。"""
    if not _enabled[0] or blockEntityData is None:
        return
    entry = _entry(dimensionId, blockPos)
    payload = build(dimensionId, blockPos, slots, PotContainer.resultItem(dimensionId, blockPos), PotContainer.preview(blockEntityData),
                    hand, now)
    static = _static(payload)
    signature = _signatureOf(static)
    changed = signature != entry["static"]
    moving = payload["rate"] > 0.0
    if entry["served"] is not None and hand.served != entry["served"]:
        event(dimensionId, blockPos, "served", {"grade": hand.clock.grade, "bonus": hand.clock.bonus}, entry["users"])
    entry["served"] = hand.served
    if changed:
        entry["static"] = signature
        blockEntityData[LOOK_KEY] = _mirror(static)
    if changed or payload["stirring"] != entry["stirring"] or moving != entry["moving"] or \
            (moving and now - entry["at"] >= MOVING_INTERVAL):
        _send(payload, entry, now)
    else:
        late = entry["audience"].arrivals(_nearby(dimensionId, blockPos, now), now)
        if late:
            MultiClientsCall(late, ENDPOINT, payload)


def stroke(dimensionId, blockPos, blockEntityData, hand, now):
    """一次被接受的搅拌：把勺尖发出去（每口锅每秒最多 8 次）。"""
    if not _enabled[0] or blockEntityData is None:
        return
    entry = _entry(dimensionId, blockPos)
    if now - entry["stroke"] < STROKE_INTERVAL:
        return
    entry["stroke"] = now
    _send(build(dimensionId, blockPos, PotContainer.inputs(dimensionId, blockPos), PotContainer.resultItem(dimensionId, blockPos),
                PotContainer.preview(blockEntityData), hand, now), entry, now)


def event(dimensionId, blockPos, name, data=None, skip=()):
    """一次性的事件（scooped / served）发给附近没开站点的玩家（skip 里的人不发）。"""
    if not _enabled[0]:
        return
    payload = {"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "event": name}
    payload.update(data or {})
    players = [playerId for playerId in _nearby(dimensionId, blockPos) if playerId not in skip]
    if players:
        MultiClientsCall(players, ENDPOINT, payload)
