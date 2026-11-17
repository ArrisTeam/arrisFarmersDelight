# -*- coding: utf-8 -*-
"""BoardFinish - 层凑成菜时先演哪套收尾、怎么演：十种收尾的动作表的入口（双端，纯规则）

对应 Hands-On Delight 的 client/BoardBehavior.java assembled 里的 switch（1546-1559）：压什么也不演，拌 / 卷 / 揉 / 一起切在 BoardFinishGroup，
串 / 摆 / 夹 / 成形 / 冻在 BoardFinishPlace，常量、每种演多久和 Plan 在 BoardFinishKit。客户端（Compat/Diegesis/BoardFinishPlay）把 plan 排出来的动作放到掉落物上，
旁观的人（BoardWatch）只放它的声音和粒子（Plan.effects），所以两边的时刻是同一份。
"""
import random

from . import Assembly
from .BoardFinishGroup import chop, knead, roll, toss
from .BoardFinishKit import Plan
from .BoardFinishPlace import arrange, freeze, sandwich, shape, skewer


def plan(finish, names, colorOf, rng=random.random):
    """这道菜做成时的收尾动作表。finish 是 Assembly.FINISH_* 之一（认不出的按压算：空表），names 是做成的各层的物品名（底座在前；
    旁观的人不知道名字，给一串空名字：只认冰、取最上面一层的颜色），colorOf(物品名) 是碎屑的颜色 0xRRGGBB（一起切时最上面一层的颜色，BoardFx.colorOf）。
    rng 给刀声音调里的那点随机。"""
    count = len(names)
    result = Plan(finish, count, rng)
    if count == 0:
        return result                                   # 没有层可演（JE 里 lastLayers 不会是空的）：只有等的时间
    if finish == Assembly.FINISH_TOSS:
        toss(result, count)
    elif finish == Assembly.FINISH_ROLL:
        roll(result, count)
    elif finish == Assembly.FINISH_SKEWER:
        skewer(result, count)
    elif finish == Assembly.FINISH_KNEAD:
        knead(result, count)
    elif finish == Assembly.FINISH_ARRANGE:
        arrange(result, count)
    elif finish == Assembly.FINISH_SANDWICH:
        sandwich(result, count)
    elif finish == Assembly.FINISH_SHAPE:
        shape(result, count)
    elif finish == Assembly.FINISH_FREEZE:
        freeze(result, count, names)
    elif finish == Assembly.FINISH_CHOP:
        chop(result, count, colorOf(names[-1]))
    return result
