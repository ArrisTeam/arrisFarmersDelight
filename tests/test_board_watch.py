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
    assert C.engine.played == [], "板上没摆过这两层（书里点的菜）：先飞来，做成的声音等它们落完（test_board_arrival 细查）"
    for _ in range(60):
        behavior.frame(1.0 / 60.0)
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


def _later():
    """排着的计时器（手倒 / 磕的声音，旁观的人补）：按时刻先后跑掉，返回 [(秒, 声音)]。"""
    return [(seconds, args[0]) for seconds, _func, args in C.engine.run_timers()]


def testAnOnlookerHearsTheHandPourAndCrackAtTheSameMomentsTheCookDoes():
    """放下的一层是液体或蛋：站点里的手倒 / 磕时出声，旁观的人没有手的动画，placed 带着放的什么，按同一时刻补上同一个声音。"""
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    C.BoardWatch.OnBoardLook(_look("placed", at=1, item="minecraft:milk_bucket"))
    assert len(C.engine.played) == 1 and C.engine.played[0][:2] == ("dig.wood", 0.7) and abs(C.engine.played[0][2] - 1.2) < 1.0e-9, "放下那一声当场响"
    assert _later() == [(0.5, ("bucket.empty_water", 0.45, 1.0))], "液体开始流（0.3 + 0.2 秒）：倒桶"
    assert C.engine.played[-1] == ("bucket.empty_water", 0.45, 1.0) and C.engine.playedAt[-1] == C.BoardWatch.soundAt(tuple(POS)), "声音从板上传来"
    C.BoardWatch.OnBoardLook(_look("placed", at=3, item="arris:milk_bottle"))
    assert [sound for _at, sound in _later()] == [("bottle.empty", 0.45, 1.0)]
    C.BoardWatch.OnBoardLook(_look("placed", at=2, item="minecraft:egg"))
    later = _later()
    assert [round(at, 6) for at, _sound in later] == [0.36, 0.9] and [sound for _at, sound in later] == [("block.turtle_egg.crack", 0.35, 1.5), ("dig.wood", 0.4, 1.4)],         "磕在板沿 0.36 秒、蛋液落到食物上 0.9 秒"


def testAnOnlookerHearsNothingFromAHandForTheBaseOrOrdinaryOrBadLayers():
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    cases = ({"at": 0, "item": "minecraft:milk_bucket"}, {"at": 1, "item": "minecraft:bread"}, {"at": 1}, {"item": "minecraft:egg"},
             {"at": "1", "item": "minecraft:egg"}, {"at": 1, "item": ["minecraft:egg"]}, {"at": True, "item": "minecraft:egg"}, {})
    for data in cases:
        C.BoardWatch.OnBoardLook(_look("placed", **data))
    assert len(C.engine.played) == len(cases) and _later() == [], "放下那一声照响；底座是容器照旧落下、别的东西没有手、坏数据不抛：什么也不补"
    C.engine.reset()
    C.BoardWatch.OnBoardLook(_look("taken", at=1, item="minecraft:egg", carved=False))
    assert _later() == [], "只有放下才有手"


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
