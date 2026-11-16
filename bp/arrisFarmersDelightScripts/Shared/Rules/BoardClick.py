# -*- coding: utf-8 -*-
"""BoardClick - 点砧板这一下算什么：手上拿着东西点、空手点（双端，纯规则）

对应 Hands-On Delight：client/BoardBehavior.java 的 onItemClick（1294-1326，手上拿着一叠点板）和 onEvent（1222-1254，空手点板面）。
只决定"这一下是什么动作"，不碰引擎；表现（BoardView.py）按结果发 place / carve / chop / take / assemble、敲一声或交还给内核。
返回 (动作, 参数)：
    CARVE            Shift 点空板，光标上的工具插进去
    PUT_AWAY         右键手上的工具：放回背包（内核的 PUT_AWAY，表现不接这一下）
    CHOP             落刀：光标栈上切得了板上东西的工具 / 空手借背包里的刀（要光标在食物上才算，由调用方判断）
    ASSEMBLE         层凑成了一道菜：点一下做成
    TAKE             取回
    KNOCK            敲一声（工具点在没有可切的东西上），什么也不发
    PLACE, one       放上去，one 为真是右键只放一个
    NOTHING          这一下什么也不是
"""
from .BoardStation import keyOf

CARVE, PUT_AWAY, CHOP, ASSEMBLE, TAKE, KNOCK, PLACE, NOTHING = "carve", "put_away", "chop", "assemble", "take", "knock", "place", "nothing"


def withStack(env, hand, button, shift, board, layers, ready, cutsBoard):
    """手上拿着 hand 点板（onItemClick）。board 是板上的东西（或 None）、layers 是摆盘的层、ready 是层已经凑成一道菜了、
    cutsBoard 是手上这件正好切得了板上的东西（BoardBehavior.tool 对光标栈的那一支）。"""
    if shift and env.canStick(hand) and keyOf(board) is None and not layers:
        return (CARVE,)
    tool = env.isTool(hand, board)
    if button == 1 and tool:
        return (PUT_AWAY,)
    if cutsBoard and not layers:
        return (CHOP,)
    if tool and button == 0 and ready and layers:
        return (ASSEMBLE,)                       # 刀落在一叠凑成菜的层上：一起切的菜用它，别的菜就当手做完
    if tool:
        return (KNOCK,)
    return (PLACE, button == 1)


def bareHand(button, board, layers, ready, toolBorrowed, carved):
    """空手点板面（onEvent）。toolBorrowed：背包里有刀可借（切得了板上的东西）；carved：板上是插着的工具。"""
    if carved:
        return (TAKE,)
    if layers:
        return (ASSEMBLE,) if ready and button == 0 else (TAKE,)
    if keyOf(board) is not None:
        return (CHOP,) if button == 0 and toolBorrowed else (TAKE,)
    return (NOTHING,)
