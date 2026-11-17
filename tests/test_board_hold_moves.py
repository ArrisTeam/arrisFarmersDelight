# -*- coding: utf-8 -*-
# runner: both
"""砧板站点的触屏长按（Compat/Diegesis/BoardHold.py）：手上拿着一叠按在板口，只有整叠真的比一个放得多时才给"放一个"（服务端的 BoardPlace.place 算：放的是一层时一层最多和
第 0 层一样多、板上同种的叠到上限，这些时候点一下整叠和右键一个收的一样多，"放一个"和点一下是同一件事，选了也没有区别）。评审的 s4。
"""
from __future__ import print_function

import test_board_view as T

import fdtest

C = T.C
HoldMenu = fdtest.load("Compat.Diegesis.HoldMenu")
BoardPlace = fdtest.load("Shared.Rules.HandsOn.BoardPlace")


def moved(behavior, hand, one):
    return BoardPlace.place(hand, behavior.board(), behavior.layers(), one, True, behavior.env).moved


def testNoPutOneWhereALayerTakesJustOneEitherWay():
    """第 0 层只有 1 个，上面一层最多和它一样多：整叠和一个都只收 1 个。"""
    layers = [C.item("minecraft:bread", 1)]
    hand = C.item("arris:beef_patty", 5)
    behavior, view = T._open(layers=layers, hand=hand)
    assert moved(behavior, hand, False) == moved(behavior, hand, True) == 1, "前提：服务端两种点法收的一样多"
    assert T._hold(behavior, "mouth") is None, "放一个和点一下是同一件事：不给菜单"
    behavior.onPointer(C.Event("down", "mouth", button=0))
    behavior.onPointer(C.Event("down", "mouth", button=1))
    assert view.sent == [("place", {"one": False}), ("place", {"one": True})]


def testPutOneWhereTheWholeStackWouldPlaceMoreThanOne():
    """第 0 层有 3 个：上面一层整叠最多放 3 个、右键放 1 个——不一样，给。"""
    layers = [C.item("minecraft:bread", 3)]
    hand = C.item("arris:beef_patty", 5)
    behavior, view = T._open(layers=layers, hand=hand)
    assert moved(behavior, hand, False) == 3 and moved(behavior, hand, True) == 1
    assert T._hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]}


def testNoPutOneWhenTheBoardsStackIsAtTheCapSoTheWholeStackAndOneAreTheSame():
    board, data = T._across(63)
    hand = C.item("arris:cabbage", 5)
    behavior, view = T._open(board, data=data, hand=hand)
    assert moved(behavior, hand, False) == moved(behavior, hand, True) == 1, "板上 63 个、上限 64：整叠也只收 1 个"
    assert T._hold(behavior, "mouth") is None
    board, data = T._across(60)
    behavior, view = T._open(board, data=data, hand=hand)
    assert moved(behavior, hand, False) == 4 and moved(behavior, hand, True) == 1
    assert T._hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]}, "板上 60 个：整叠收 4 个，一个收 1 个，不一样"


def testTheEmptyBoardAndTheOldCasesAreUnchanged():
    behavior, view = T._open(hand=C.item("arris:cabbage", 3))
    assert T._hold(behavior, "mouth") == {"menu": [HoldMenu.PUT_ONE]}
    view.hand = C.item("arris:cabbage", 1)
    assert T._hold(behavior, "mouth") is None, "只有一个"
    view.hand = C.item("minecraft:dirt", 3)
    assert T._hold(behavior, "mouth") is None, "板不收的东西：整叠和一个都是 0"


def main():
    return fdtest.run(globals())


if __name__ == "__main__":
    raise SystemExit(main())
