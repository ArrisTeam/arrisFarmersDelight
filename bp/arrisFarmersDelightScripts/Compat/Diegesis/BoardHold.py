# -*- coding: utf-8 -*-
"""BoardHold - 砧板站点的触屏长按（前置包的表现钩子 onHold，条目和返回值的写法见 HoldMenu.py）：手指按在板上按住不动，有什么右键 / Shift 点击的变体可给（客户端）

按 BoardClick 问（BoardView._withStack / _bareHand 点一下怎么办就怎么问），只给"和点一下不一样"的变体：
- 手上拿着一叠点板（板口 mouth）：点一下放整叠、右键放一个——手上不止一个、点一下确实是放（不是切、做成、敲一声）、而且整叠真的比一个放得多（服务端的 BoardPlace.place：
  放的是一层时一层最多和第 0 层一样多、板上同种的叠到上限，这些时候整叠和一个收的一样多，"放一个"和点一下是同一件事），才有"放一个"
  （前置包有数量档时不给：那个按钮的"单个"档点一下就是它，HoldMenu.tapMode）；
  拿着能插进空板的工具时 Shift 点板是插进去（CARVE），点一下只会敲一声——有"插在板上"；
- 空手点板面（surface）：点一下切（借背包里的刀）或做成一道菜，右键是取回——点一下不是取回、右键是，才有"取回"；点一下本来就是取回（插着的工具、层没凑成）、板空着，都没有。
别处是 None：按下立刻生效。
"""
from . import HoldMenu
from ...Shared.Rules import BoardClick as Click
from ...Shared.Rules.HandsOn import BoardPlace


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
    if tap == (Click.PLACE, False) and ask(1, False) == (Click.PLACE, True) and hand["count"] > 1 and not HoldMenu.tapMode(owner.view) \
            and _movesMore(env, hand, board, layers):
        entries.append(HoldMenu.PUT_ONE)
    return HoldMenu.menu(*entries) if entries else None


def _movesMore(env, hand, board, layers):
    """点一下整叠比右键一个收得多吗（服务端的 place 算出来的）：不比一个多的时候，"放一个"和点一下是同一件事，不给这个菜单；收不下（0 个）更不给。"""
    return BoardPlace.place(hand, board, layers, False, True, env).moved > BoardPlace.place(hand, board, layers, True, True, env).moved


def _bareHand(owner):
    board, layers = owner.board(), owner.layers()
    borrowed = owner.toolOf()[1]
    carved = board is not None and owner.env.isCarving(board)

    def ask(button):
        return Click.bareHand(button, board, layers, owner.ready(), borrowed, carved)[0]

    return HoldMenu.menu(HoldMenu.TAKE_BACK) if ask(0) != Click.TAKE and ask(1) == Click.TAKE else None
