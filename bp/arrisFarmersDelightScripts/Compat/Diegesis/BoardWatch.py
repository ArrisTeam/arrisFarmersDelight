# -*- coding: utf-8 -*-
"""BoardWatch - 旁观砧板的人：听得到切菜声、放东西的声音、手倒液体 / 磕蛋的声音、做成一道菜的收尾声，看得到碎屑和做成的面粉 / 霜 / 闪光（客户端）

装了场景交互前置、砧板站点登记成功才启用（BoardClientLink 这一步调 enable）。服务端 Server/BoardLook 把站点的表现事件（chopped / placed / taken / carved / assembled / refused）
发给同维度 32 格内、没开着这个站点的人（开着的人收站点自己的 effect，两边不重复）；这里按和站点里一样的声音表（Shared/Rules/BoardSounds）放，
所以刀声按工具和材质分、最后一刀有收尾声、放第几层音调高几分，旁观的人和站点里的人听到的一样；碎屑也是（BoardFx.chopPuffs：起点和初速是操作者那边的站点
像素，按他的朝向转到世界）。动画不演：旁观的人看到的板是 Client/BlockItems 摆的；放下的一层要是液体（桶、瓶）或蛋，站点里的手倒、磕时出的声音
（倒桶 / 倒瓶、磕蛋、蛋落到食物上）旁观的人也按同一时刻听到：placed 效果带着放的是什么（item），Sounds.handSounds 给出各声的延迟，这里用计时器补上。
做成一道菜（assembled）也是：层怎么动旁观的人看不到，可收尾的声音和粒子（拌的皮革声、卷揉压的布步声、冰棒的霜……）和最后一刻（pop）做成的两声、面粉 / 霜、闪光
都按站点里同一份动作表（Shared/Rules/HandsOn/BoardFinish）的时刻放；收尾演多久要层数，assembled 效果带着 count。
"""
from . import BoardFx, PotFx
from ...Client.Engine import compFactory, levelId
from ...QuModLibs.Client import AllowCall
from ...Shared.Rules import BoardSounds as Sounds
from ...Shared.Rules.BoardStation import MOST_LAYERS
from ...Shared.Rules.HandsOn import BoardFinish as Finish
from ...Shared.Rules.HandsOn import BoardFinishKit as Kit
from ...Shared.Rules.HandsOn import BoardScene as Scene

OBSERVED = frozenset(("chopped", "placed", "taken", "carved", "assembled", "refused"))     # 和服务端 Server/BoardLook.OBSERVED 同一份
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


def _later(delay, func, *args):
    """delay 秒之后做 func(*args)；不用等就现在做。"""
    if delay > 0.0:
        compFactory.CreateGame(levelId).AddTimer(float(delay), func, *args)
    else:
        func(*args)


def _layers(payload):
    """做成的层数（assembled 效果带着）：不是 0..MOST_LAYERS 的整数（坏数据）按 0 算。"""
    count = payload.get("count")
    return count if isinstance(count, int) and not isinstance(count, bool) and 0 <= count <= MOST_LAYERS else 0


def _effect(block, geometry, center, cue):
    """收尾里的一声 / 一阵粒子（站点里的人从 BoardFinishPlay 放同一份）：旁观的人没有站点视图，站点像素按 yaw 0 换到世界，起点是板面中心 center 加上偏移。"""
    _at, op, _target, args = cue
    if op == Kit.SOUND:
        BoardFx.play(args, soundAt(block))
    elif geometry is None:
        return
    elif op == Kit.DUST:
        puff, color = args
        (x, y, z), velocity, spread, count = puff
        BoardFx.puffAt(geometry, 0, block, ((center[0] + x, y, center[1] + z), velocity, spread, count), color)
    elif op == Kit.GLINT:
        (x, y, z), color, count = args
        PotFx.particle(BoardFx.GLINT, geometry.stationPointToWorld(0, center[0] + x, y, center[1] + z, *block), color=color, count=count)


def _popped(block, finish, geometry, center):
    """收尾演完、菜弹出来的那一刻（JE 的 pop）：做成的两声、面粉 / 霜、一点闪光。"""
    for sound in Sounds.soundsOf("assembled"):
        BoardFx.play(sound, soundAt(block))
    if geometry is not None:
        BoardFx.finishPuff(geometry, 0, block, center[0], center[1], finish)
        BoardFx.glintInWorld(geometry.stationPointToWorld(0, center[0], Scene.TOP + 1.0, center[1], *block))


def _assembled(block, payload, geometry):
    """做成一道菜：收尾的声音和粒子在各自的时刻，pop 在收尾演完那一刻（Plan.seconds）；旁观的人这时层原来就摆着，不用等层落定。"""
    finish = payload.get("finish")
    plan = Finish.plan(finish, [""] * _layers(payload), BoardFx.colorOf)
    mx, _, mz = geometry.worldPointToStation(0, *(tuple(BoardFx.centerOf(block)) + tuple(block))) if geometry is not None else (0.0, 0.0, 0.0)
    for cue in plan.effects():
        _later(cue[0], _effect, block, geometry, (mx, mz), cue)
    _later(plan.seconds, _popped, block, finish, geometry, (mx, mz))


@AllowCall
def OnBoardLook(payload):
    # 服务端发给 32 格内的旁观者；别的维度的、坏数据的直接丢
    if not _state["on"] or not isinstance(payload, dict) or payload.get("dimensionId") != _currentDimension():
        return
    block, name = _blockOf(payload), payload.get("event")
    if block is None or not isinstance(name, (str, type(u""))) or name not in OBSERVED:
        return
    for sound in ([] if name == "assembled" else Sounds.soundsOf(name, payload)):         # 做成的声音等收尾演完（_popped）
        BoardFx.play(sound, soundAt(block))
    if name == "placed":
        for delay, sound in Sounds.handSounds(payload):
            compFactory.CreateGame(levelId).AddTimer(float(delay), BoardFx.play, sound, soundAt(block))
    geometry = _state["geometry"]
    if name == "assembled":
        _assembled(block, payload, geometry)
    elif geometry is not None and name == "chopped":
        BoardFx.chopPuffs(geometry, block, payload)
