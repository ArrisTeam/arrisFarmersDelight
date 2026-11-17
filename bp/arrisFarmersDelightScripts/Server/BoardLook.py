# -*- coding: utf-8 -*-
"""BoardLook - 砧板的世界外观广播：附近没开着站点的人也听得到切菜声、放东西的声音、看得到碎屑（服务端）

HoD 的站点效果（chopped / placed / taken / carved / assembled / refused）对所有看得见这块板的人都演（声音、碎屑；动画只有本人看得到）；
基岩版前置包的 station.effect 只发给开着站点的人，旁观的人什么也听不到，原来靠服务端对所有人放一个不分工具的刀声顶着。
这条广播补上：服务端把同一批效果发给同维度 32 格内、没开着这个站点的玩家（开着的人收站点自己的 effect，两边不重复），
客户端 Compat/Diegesis/BoardWatch 的 OnBoardLook 按和站点里一样的声音表（Shared/Rules/BoardSounds）放声音、飞碎屑；动画不演——
旁观的人看到的板由 Client/BlockItems 摆。默认关着，前置包在场、砧板站点登记了时由 Compat/Diegesis/BoardServerLink 这一步打开（enable），没装什么都不发。
负载（Call 到 OnBoardLook）：{"dimensionId", "pos": [x, y, z], "event": 效果名, ...效果的数据}，数据里只有动画才用的大块（stack、layers）不带（assembled 带做成了几层 count）。
refused 按玩家限速：被拒的动作每秒能来 40 个（前置包按玩家的令牌桶上限），不限的话改过的客户端发一串非法的 chop 就能把被拒的敲击声当喇叭，每个都给 32 格内每个人发一次广播；
同一个人被拒的敲击声，旁观的人 REFUSED_GAP 秒内至多听一声（站点里的人收的 effect 不在这里，不限）。
"""
import time

from .Helpers.Engine import Call
from .PanLook import nearby

ENDPOINT = "OnBoardLook"
OBSERVED = frozenset(("chopped", "placed", "taken", "carved", "assembled", "refused"))     # 旁观的人只关心出声、出碎屑的这几种（refused：被拒的敲击声，JE 里人人听得到）
_ANIMATION_ONLY = ("stack", "layers")
REFUSED_GAP = 0.3          # 秒：同一个人被拒的敲击声，旁观的人这么久之内至多听一声（真实时间，不受 /time 影响）
_enabled = [False]
_refusedAt = {}            # 玩家 id -> 上一次把他被拒的敲击声广播给旁观的人的时刻


def enable(on=True):
    _enabled[0] = bool(on)


def enabled():
    return _enabled[0]


def payloadOf(dimensionId, blockPos, name, data=None):
    """发出去的负载：效果数据去掉动画专用的大块，再带上维度、方块位置、效果名；assembled 多带做成了几层（count）：层不带，可收尾演多久（旁观的人按它放收尾的声音）要层数。"""
    payload = dict((key, value) for key, value in (data or {}).items() if key not in _ANIMATION_ONLY)
    payload.update({"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "event": name})
    if name == "assembled":
        payload["count"] = len((data or {}).get("layers") or [])
    return payload


def _mayHearRefusal(actor):
    """这个人被拒的敲击声，这一次旁观的人该不该听到：离他上一次被听到不到 REFUSED_GAP 秒就不发。时钟倒着走（换了世界、测试）当作隔够了。"""
    now = time.time()
    last = _refusedAt.get(actor)
    if last is not None and 0.0 <= now - last < REFUSED_GAP:
        return False
    _refusedAt[actor] = now
    if len(_refusedAt) > 64:                   # 玩家来来去去：只留这一阵里被听到过的
        for key in [key for key, at in _refusedAt.items() if not 0.0 <= now - at < REFUSED_GAP]:
            del _refusedAt[key]
    return True


def event(dimensionId, blockPos, name, data=None, skip=(), actor=None):
    """一个效果发给附近没开着站点的人。skip：开着站点的人（他们收站点自己的 effect）。关着、不是旁观的人关心的效果什么也不发。
    actor：这个效果是谁的动作引出来的（refused 按他限速，没有就算一个人）。"""
    if not _enabled[0] or name not in OBSERVED:
        return
    if name == "refused" and not _mayHearRefusal(actor):
        return
    payload = payloadOf(dimensionId, blockPos, name, data)
    for playerId in nearby(dimensionId, blockPos):
        if playerId not in skip:
            Call(playerId, ENDPOINT, payload)
