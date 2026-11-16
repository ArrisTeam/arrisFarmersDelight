# -*- coding: utf-8 -*-
# runner: both
"""砧板的声音在客户端：站点里的人（BoardEffects）和旁观的人（BoardWatch 的 OnBoardLook）按同一张声音表（Shared/Rules/BoardSounds）放，所以听到的一样；
旁观的人只处理本维度、方块位置合格、出声的几种事件，坏数据一律丢。假引擎和假视图见 boardclient.py。
"""
from __future__ import print_function

import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

KNIFE, AXE = "arris:iron_knife", "minecraft:iron_axe"
POS = list(C.STATION_POS)


def _open(board=None, layers=(), data=None, hand=None):
    behavior, view, api = C.station()
    view.state.board, view.state.layers = board, list(layers)
    view.data, view.hand = dict(data or {}), hand
    behavior.onOpen()
    return behavior, view


def _chopped(**extra):
    return dict({"at": 8.0, "at_x": 6.5, "spot": 0.5, "angle": 0.0, "tool": KNIFE, "item": "arris:cabbage", "yaw": 0, "stroke": "cut",
                 "block": False, "yields": ["arris:cabbage_leaf"]}, **extra)


def _look(event, **data):
    return dict(data, dimensionId=0, pos=list(POS), event=event)


def _names():
    return [sound[0] for sound in C.engine.played]


def testTheCookHearsTheKnifeAtPointEightThenTheLastStrokesThreeSounds():
    behavior, view = _open(C.item("arris:cabbage", 2), data={"plan": 1, "marks": 0, "style": "across", "spots": [0.5], "angles": [0.0], "stroke": "cut", "dish": ""})
    behavior.onEffect("chopped", _chopped())
    assert C.engine.played[-1][0] == "ambient.cutting_board.knife" and C.engine.played[-1][1] == 0.8 and 0.95 <= C.engine.played[-1][2] <= 1.10
    C.engine.played[:] = []
    behavior.onEffect("chopped", _chopped(done=True, count=2))
    assert [(sound[0], sound[1]) for sound in C.engine.played] == [("ambient.cutting_board.knife", 0.8), ("random.pop", 0.35)], "FD 的切声 + 飞给厨师的拿起声"
    assert C.engine.played[-1][2] == 1.3


def testEachToolHasItsOwnSoundForTheCook():
    behavior, view = _open(C.item("minecraft:oak_log", 1), data={"plan": 1, "marks": 0, "style": "across", "spots": [0.5], "angles": [0.0], "stroke": "strip", "dish": ""})
    behavior.onEffect("chopped", _chopped(tool=AXE, item="minecraft:oak_log", stroke="strip", block=True, yields=["minecraft:stripped_oak_log"]))
    assert C.engine.played[-1][:2] == ("use.wood", 0.8)
    behavior.onEffect("chopped", _chopped(tool="minecraft:iron_pickaxe", item="minecraft:stone", stroke="smash", block=True, yields=["minecraft:cobblestone"]))
    assert C.engine.played[-1][:2] == ("hit.stone", 0.6)
    behavior.onEffect("chopped", _chopped(tool="minecraft:shears", item="minecraft:leather_helmet", stroke="snip", yields=["minecraft:leather"]))
    assert C.engine.played[-1][:2] == ("mob.sheep.shear", 0.6)


def testPlacedGetsHigherWithTheLayerTakenHasOneSoundAndCarvedAndAssembledTheirOwn():
    behavior, view = _open()
    behavior.onEffect("placed", {"at": 3})
    assert C.engine.played[-1][:2] == ("dig.wood", 0.7) and abs(C.engine.played[-1][2] - 1.30) < 1.0e-9
    C.engine.played[:] = []
    behavior.onEffect("taken", {"stack": C.item("arris:tomato"), "at": 1, "carved": False})
    assert C.engine.played == [("random.pop", 0.3, 1.5)], "只有拿起声：不再叠上服务端的一声皮甲声"
    C.engine.played[:] = []
    behavior.onEffect("taken", {"stack": C.item("arris:iron_knife"), "at": -1, "carved": True})
    assert [sound[:2] for sound in C.engine.played] == [("hit.wood", 0.6), ("random.pop", 0.3)], "拔出插着的刀：拔出声 + 拿起声"
    C.engine.played[:] = []
    behavior.onEffect("carved", {})
    assert C.engine.played == [("dig.wood", 1.0, 0.8)]
    C.engine.played[:] = []
    behavior.onEffect("assembled", {"layers": [C.item("minecraft:bread"), C.item("arris:egg")], "finish": "sandwich", "block": False})
    assert C.engine.played == [("dig.wood", 0.8, 0.75), ("random.pop", 0.35, 1.4)]


def testARefusedStackKnocksOnce():
    behavior, view = _open(C.item("arris:cabbage", 2))
    behavior.onEffect("refused", {})
    assert C.engine.played == [("hit.wood", 0.4, 1.4)], "只有弹回的那一声（服务端不再另放）"


def testAnOnlookerHearsTheSameSoundsFromTheBoard():
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    C.BoardWatch.OnBoardLook(_look("chopped", **_chopped(done=True, count=2)))
    assert [(sound[0], sound[1]) for sound in C.engine.played] == [("ambient.cutting_board.knife", 0.8), ("random.pop", 0.35)]
    x, y, z = C.engine.playedAt[0]
    assert (x, z) == (POS[0] + 0.5, POS[2] + 0.5) and POS[1] < y < POS[1] + 1, "声音从板上传来"
    C.engine.played[:] = []
    C.BoardWatch.OnBoardLook(_look("placed", at=2))
    assert C.engine.played[-1][:2] == ("dig.wood", 0.7) and abs(C.engine.played[-1][2] - 1.25) < 1.0e-9
    C.engine.played[:] = []
    C.BoardWatch.OnBoardLook(_look("taken", carved=False, at=0))
    C.BoardWatch.OnBoardLook(_look("carved"))
    C.BoardWatch.OnBoardLook(_look("assembled", finish="sandwich", block=False))
    assert _names() == ["random.pop", "dig.wood", "dig.wood", "random.pop"]


def testAnOnlookerIgnoresWhatIsNotForThem():
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    good = _look("placed", at=1)
    for bad in (dict(good, dimensionId=1), dict(good, pos=[1, 2]), dict(good, pos=[1, 2, "3"]), dict(good, pos=[True, 2, 3]), dict(good, pos="x"),
                dict(good, event="refused"), dict(good, event="board_book"), dict(good, event=["placed"]), dict(good, event=None), "junk", None, 5, [good]):
        C.BoardWatch.OnBoardLook(bad)
    assert C.engine.played == [], "别的维度、坏位置、不出声的事件、坏数据：都不放"
    for junk in ({"tool": 5, "item": None, "yields": "x", "stroke": "nonsense"}, {}):
        C.BoardWatch.OnBoardLook(_look("chopped", **junk))
    assert len(C.engine.played) == 2 and _names() == ["ambient.cutting_board.knife"] * 2, "事件里的数据坏了：按刀声放，不抛"


def testTheBroadcastIsDeadUntilTheBoardStationIsRegisteredByTheBoot():
    C.engine.reset()
    C.BoardWatch._state["on"] = False
    C.BoardWatch.OnBoardLook(_look("placed", at=1))
    assert C.engine.played == [], "没装前置包（ClientBoot 没调 enable）：什么也不放"
    C.BoardWatch.enable(C.Geometry)
    C.BoardWatch.OnBoardLook(_look("placed", at=1))
    assert len(C.engine.played) == 1


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
