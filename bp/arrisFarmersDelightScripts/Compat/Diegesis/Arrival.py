# -*- coding: utf-8 -*-
"""Arrival - 这一次进站点是右键使用方块进来的，还是从相邻的站点走过来的（双端，纯逻辑）

JE 的 StationView.openedByUse："手上拿着的东西是给这个站点的"只在使用方块进来时成立——煎锅、炉灶、砧板开站那一下把主手的东西放上去
（SkilletBehavior.onOpen:197-204、StoveBehavior.onOpen:110-113、BoardBehavior:365）都先看它。从砧板按 A / D（或停在屏幕边）走到旁边的煎锅，
主手里的生肉不该自己进锅。
前置包给的：服务端 station.openedByUse(playerId)，客户端 view.openedByUse（一个值）。老版本的前置包没有这两样：一律当使用进来的，和从前一样。
"""


def byUse(owner, playerId=None):
    """owner：服务端传站点（再给 playerId），客户端传视图。"""
    asked = getattr(owner, "openedByUse", True)
    return bool(asked(playerId)) if callable(asked) else bool(asked)
