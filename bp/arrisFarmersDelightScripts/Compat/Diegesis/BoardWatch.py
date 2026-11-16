# -*- coding: utf-8 -*-
"""BoardWatch - 旁观砧板的人：听得到切菜声、放东西的声音，看得到碎屑（客户端）

装了场景交互前置、砧板站点登记成功才启用（ClientBoot 调 enable）。服务端 Server/BoardLook 把站点的表现事件（chopped / placed / taken / carved / assembled）
发给同维度 32 格内、没开着这个站点的人（开着的人收站点自己的 effect，两边不重复）；这里按和站点里一样的声音表（Shared/Rules/BoardSounds）放，
所以刀声按工具和材质分、最后一刀有收尾声、放第几层音调高几分，旁观的人和站点里的人听到的一样；碎屑也是（BoardFx.chopPuffs：起点和初速是操作者那边的站点
像素，按他的朝向转到世界）。动画不演：旁观的人看到的板是 Client/BlockItems 摆的。
"""
from . import BoardFx
from ...Client.Engine import compFactory, levelId
from ...QuModLibs.Client import AllowCall
from ...Shared.Rules import BoardDust as Dust
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.HandsOn import Assembly

OBSERVED = frozenset(("chopped", "placed", "taken", "carved", "assembled"))     # 和服务端 Server/BoardLook.OBSERVED 同一份
_state = {"on": False, "geometry": None}


def enable(geometry=None):
    """前置包在场、砧板站点登记了：从现在起听得到旁边的砧板。geometry 是前置包的 Geometry（碎屑要换算站点坐标，没有就不飞碎屑）。"""
    _state["on"] = True
    _state["geometry"] = geometry


def enabled():
    return _state["on"]


def _currentDimension():
    return compFactory.CreateGame(levelId).GetCurrentDimension()


def _blockOf(payload):
    """负载里的方块位置（三个整数），不合格是 None。"""
    pos = payload.get("pos")
    if not isinstance(pos, (list, tuple)) or len(pos) != 3 or not all(isinstance(v, int) and not isinstance(v, bool) for v in pos):
        return None
    return tuple(pos)


def soundAt(block):
    """板面上方一点：旁观的人听到声音从板上传来。"""
    return (block[0] + 0.5, block[1] + 0.1, block[2] + 0.5)


@AllowCall
def OnBoardLook(payload):
    # 服务端发给 32 格内的旁观者；别的维度的、坏数据的直接丢
    if not _state["on"] or not isinstance(payload, dict) or payload.get("dimensionId") != _currentDimension():
        return
    block, name = _blockOf(payload), payload.get("event")
    if block is None or not isinstance(name, (str, type(u""))) or name not in OBSERVED:
        return
    for sound in Sounds.soundsOf(name, payload):
        BoardFx.play(sound, soundAt(block))
    geometry = _state["geometry"]
    if geometry is None:
        return
    if name == "chopped":
        BoardFx.chopPuffs(geometry, block, payload)
    elif name == "assembled":
        mx, _, mz = geometry.worldPointToStation(0, *(tuple(BoardFx.centerOf(block)) + tuple(block)))
        frost = payload.get("finish") == Assembly.FINISH_FREEZE
        BoardFx.puffAt(geometry, 0, block, Dust.flourPuff(mx, mz, frost), BoardFx.FROST if frost else BoardFx.FLOUR)
