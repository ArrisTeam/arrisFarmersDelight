# -*- coding: utf-8 -*-
"""BoardEmit - 砧板站点发一次性的表现（服务端）：开着站点的人走前置包的 effect，附近没开站点的人走本包的广播（Server/BoardLook）

声音不再由服务端对所有人放一个固定的：两边的客户端按同一张声音表（Shared/Rules/BoardSounds）自己放，音量、音调照 JE，
刀声按工具、材质分，最后一刀有收尾声。两边的人各收一份：站点里的人收 effect，旁观的人（32 格内、没开着这个站点）收 BoardLook 的广播，不重复。
"""
from ...Server import BoardLook


def emit(logic, name, data=None):
    """站点的一个表现事件：发给开着站点的人（effect），再发给附近旁观的人（广播，只有出声 / 出碎屑的几种）。"""
    station = logic.station
    station.effect(name, data)
    BoardLook.event(station.dimensionId, station.pos, name, data, skip=list(station.users), actor=logic.actor)
