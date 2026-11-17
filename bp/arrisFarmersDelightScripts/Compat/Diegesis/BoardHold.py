# -*- coding: utf-8 -*-
"""BoardHold - 砧板站点的触屏长按（前置包的表现钩子 onHold，条目和返回值的写法见 HoldMenu.py）：手指按在板上按住不动，有什么右键 / Shift 点击的变体可给（客户端）

按 BoardClick 问（BoardView._withStack / _bareHand 点一下怎么办就怎么问），只给"和点一下不一样"的变体：
- 手上拿着一叠点板（板口 mouth）：点一下放整叠、右键放一个——手上不止一个、点一下确实是放（不是切、做成、敲一声）、板收得下（BoardGlow.placeable），才有"放一个"；
  拿着能插进空板的工具时 Shift 点板是插进去（CARVE），点一下只会敲一声——有"插在板上"；
- 空手点板面（surface）：点一下切（借背包里的刀）或做成一道菜，右键是取回——点一下不是取回、右键是，才有"取回"；点一下本来就是取回（插着的工具、层没凑成）、板空着，都没有。
别处是 None：按下立刻生效。
"""
from . import HoldMenu
from .BoardGlow import placeable
from ...Shared.Rules import BoardClick as Click


def onHold(owner, event):
    """BoardViewMixin.onHold：owner 是表现，event 是和按下收到的同一种拾取事件。"""
    if owner.draw is None:
        return None
    key = event.hit.node.key if event.hit is not None else None
    if owner.view.hand is not None:
        return _withStack(owner) if key == "mouth" else None
    return _bareHand(owner) if key == "surface" else None


def _withStack(owner):
    env, hand, board, layers = owner.env, owner.view.hand, owner.board(), owner.layers()
    cuts = board is not None and not layers and env.cutsWith(board, hand)

    def ask(button, quick):
        return Click.withStack(env, hand, button, quick, board, layers, owner.ready(), cuts)

    tap = ask(0, False)
    entries = []
    if ask(0, True) == (Click.CARVE,):                 # 只有 Shift 点才会是插（BoardClick.withStack），点一下不会
        entries.append(HoldMenu.CARVE)
    if tap == (Click.PLACE, False) and ask(1, False) == (Click.PLACE, True) and hand["count"] > 1 and placeable(env, hand, board, layers):
        entries.append(HoldMenu.PUT_ONE)
    return HoldMenu.menu(*entries) if entries else None


def _bareHand(owner):
    board, layers = owner.board(), owner.layers()
    borrowed = owner.toolOf()[1]
    carved = board is not None and owner.env.isCarving(board)

    def ask(button):
        return Click.bareHand(button, board, layers, owner.ready(), borrowed, carved)[0]

    return HoldMenu.menu(HoldMenu.TAKE_BACK) if ask(0) != Click.TAKE and ask(1) == Click.TAKE else None
