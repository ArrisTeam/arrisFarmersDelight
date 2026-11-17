# -*- coding: utf-8 -*-
# runner: both
"""砧板站点客户端的几个收尾细节（Compat/Diegesis/BoardEffects + BoardDraw + BoardDrawEvents + BoardThing + BoardCutter，假引擎见 boardclient.py）：
方块类切到底（削皮：削出来的去皮原木升起；别的：在方块中心炸开，方块不往上飘）、铲一铲方块缩 14%、层凑成一道等点的菜时各层落定、
工具点到活上活抖一下（削皮、剪刀不抖）。对应 HoD 的 blockDone（1459-1475）、drawWear（516-544）、refresh 末尾的 settle（490-506）、impact（1045-1047）。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
AXE, PICKAXE, SHOVEL = "minecraft:iron_axe", "minecraft:iron_pickaxe", "minecraft:iron_shovel"
CHANGED = type("Changes", (), {"hasSlot": lambda self, ref: True})()
SAME = type("Changes", (), {"hasSlot": lambda self, ref: False})()


def _open(board=None, layers=(), data=None, hand=None):
    behavior, view, api = C.station()
    view.state.board, view.state.layers = board, list(layers)
    view.data, view.hand = dict(data or {}), hand
    behavior.onOpen()
    return behavior, view


def _data(stroke, plan=1, marks=0, dish=""):
    return {"plan": plan, "marks": marks, "style": "across", "spots": [0.5, 0.2, 0.8][:plan], "angles": [0.0, 0.0, 0.0][:plan], "stroke": stroke, "dish": dish}


def _frames(behavior, count=40, dt=1.0 / 60.0):
    for _ in range(count):
        behavior.frame(dt)


def _live(view, name):
    return [prop for prop in view.props.live() if prop.item["newItemName"] == name]


def _lastStroke(behavior, view, stroke, tool, item, yields, block=True):
    """最后一刀：状态里板上的东西已经没了，再收到服务端的 chopped（done）。"""
    view.state.board = None
    behavior.onState(CHANGED)
    behavior.onEffect("chopped", {"at": 8.0, "at_x": 6.5, "tool": tool, "item": item, "yaw": 0, "stroke": stroke, "block": block, "yields": yields, "count": 1, "done": True})


def testABarkStripRisesTheStrippedLogAndTheBlockDoesNotFloatAway():
    behavior, view = _open(C.item("minecraft:oak_log", 1), data=_data("strip"))
    _frames(behavior, 2)
    assert len(_live(view, "minecraft:oak_log")) == 1
    _lastStroke(behavior, view, "strip", AXE, "minecraft:oak_log", ["minecraft:stripped_oak_log", "arris:tree_bark"])
    _frames(behavior, 2)
    assert not _live(view, "minecraft:oak_log"), "方块自己不往上飘"
    log = _live(view, "minecraft:stripped_oak_log")
    assert len(log) == 1 and not log[0].flat and log[0].roll == 0.0, "削出来的去皮原木，立着、不转"
    low = _bottomOf(view, "minecraft:stripped_oak_log")
    _frames(behavior, 8)
    assert _bottomOf(view, "minecraft:stripped_oak_log") > low + 0.8, "往上升"
    _frames(behavior, 20)
    assert not _live(view, "minecraft:stripped_oak_log"), "升 3 像素、缩没"
    assert len(C.engine.particles) == 1, "削皮切出东西的：只有这一刀的碎屑，不炸开"


def testAStoneWorkedToTheEndBurstsAtItsMiddleAndNothingFloatsUp():
    behavior, view = _open(C.item("minecraft:stone", 1), data=_data("smash"))
    _frames(behavior, 2)
    _lastStroke(behavior, view, "smash", PICKAXE, "minecraft:stone", ["minecraft:cobblestone"])
    _frames(behavior, 5)
    assert not view.props.live(), "方块炸开：没有东西往上飘，也没有升起来的"
    assert [p["vars"]["variable.count"] for p in C.engine.particles] == [10.0, 18.0], "这一刀 10 颗，再在方块中心炸 18 颗"


def testAFlatFoodStillFloatsAwayOnTheLastStroke():
    behavior, view = _open(C.item("arris:cabbage", 2), data=_data("cut"))
    _frames(behavior, 2)
    _lastStroke(behavior, view, "cut", "arris:iron_knife", "arris:cabbage", ["arris:cabbage_leaf"], block=False)
    _frames(behavior, 4)
    assert len(_live(view, "arris:cabbage")) == 1 and len(C.engine.particles) == 1, "食物往上飘着缩没，只有这一刀的碎屑"
    _frames(behavior, 20)
    assert not _live(view, "arris:cabbage")


def _scaleOf(view, name):
    return _live(view, name)[0].scale


def _bottomOf(view, name):
    """方块那个立方体的底面：道具的轴心在"中心"下方半个贴图边长，引擎把立方体画在轴心上方 CUBE_LIFT。"""
    prop = _live(view, name)[0]
    pivot = prop.center[1] - prop.scale * Scene.SPRITE_SPAN / 2.0
    return pivot + Scene.CUBE_LIFT - prop.scale * Scene.CUBE_SPAN / 2.0


def testAShovelShrinksTheBlockFourteenPercentPerShovelfulAndItStaysOnTheBoard():
    data = _data("dig", plan=3)
    behavior, view = _open(C.item("minecraft:gravel", 1), data=data)
    _frames(behavior, 2)
    full, floor = _scaleOf(view, "minecraft:gravel"), _bottomOf(view, "minecraft:gravel")
    assert abs(full - Scene.itemScale(True)) < 1e-9
    view.data["marks"] = 1
    behavior.onState(SAME)
    _frames(behavior, 12)
    assert abs(_scaleOf(view, "minecraft:gravel") - full * 0.86) < 1e-9, "一铲：缩 14%"
    assert abs(_bottomOf(view, "minecraft:gravel") - floor) < 1e-9, "缩小了还躺在板上（底边不动）"
    view.data["marks"] = 2
    behavior.onState(SAME)
    _frames(behavior, 12)
    assert abs(_scaleOf(view, "minecraft:gravel") - full * 0.72) < 1e-9
    behavior.cutter.pending.add(behavior.cutter.clock)                      # 自己落的一铲还没等到回话：也算（JE 的 pendingChops）
    behavior.redraw()
    _frames(behavior, 12)
    assert abs(_scaleOf(view, "minecraft:gravel") - full * 0.58) < 1e-9
    view.state.board = C.item("minecraft:cobblestone", 1)
    view.data["marks"] = 0                                                   # 换了一块：服务端重布刀口
    behavior.onState(CHANGED)
    _frames(behavior, 2)
    assert abs(_scaleOf(view, "minecraft:cobblestone") - full) < 1e-9, "换了一块：从头算"


def testNoOtherToolWearsABlockDown():
    behavior, view = _open(C.item("minecraft:stone", 1), data=_data("smash", plan=3))
    _frames(behavior, 2)
    full = _scaleOf(view, "minecraft:stone")
    view.data["marks"] = 2
    behavior.onState(SAME)
    _frames(behavior, 12)
    assert abs(_scaleOf(view, "minecraft:stone") - full) < 1e-9, "镐是换裂纹（这里不画），不缩"
    behavior, view = _open(C.item("arris:cabbage", 2), data=_data("dig", plan=3, marks=2))
    _frames(behavior, 2)
    assert abs(_scaleOf(view, "arris:cabbage") - Scene.itemScale(False)) < 1e-9, "不是方块的东西不缩"


def _settled(behavior):
    return [thing for thing in behavior.draw.layers[:2] if thing.mover.moving]


def testTheLayersHopAndSoundWhenTheyAddUpToADishWaitingForTheCook():
    layers = [C.item("minecraft:bread", 1), C.item("arris:tomato", 1)]
    behavior, view = _open(layers=layers, data=_data("cut", dish=""))
    _frames(behavior, 30)
    C.engine.played[:] = []
    view.data["dish"] = "arris:some_dish"
    behavior.onState(SAME)
    assert C.engine.played == [("dig.wood", 0.5, 0.8)], "落定的一声"
    _frames(behavior, 3)
    assert len(_settled(behavior)) == 2, "各层在原位弹一下"
    rest = behavior.draw.layers[0].mover.pos[1]
    _frames(behavior, 20)
    assert not _settled(behavior) and abs(behavior.draw.layers[0].mover.pos[1] - rest) < 0.5
    behavior.onState(SAME)
    assert len(C.engine.played) == 1, "一直是凑成的：不再响"
    view.data["dish"] = ""
    behavior.onState(SAME)
    view.data["dish"] = "arris:some_dish"
    behavior.onState(SAME)
    assert len(C.engine.played) == 2, "拆了再凑成：再来一次"


def testAnEmptyBoardOrLayersThatAddUpToNothingMakeNoSound():
    behavior, view = _open(layers=[C.item("minecraft:bread", 1)], data=_data("cut", dish=""))
    _frames(behavior, 30)
    assert C.engine.played == []
    view.state.layers = [C.item("minecraft:bread", 1), C.item("arris:tomato", 1)]
    behavior.onState(SAME)
    assert C.engine.played == [], "加了一层、还没凑成"


def testAToolStrokeShakesTheFoodAtImpactButBarkAndSnipDoNot():
    behavior, view = _open(C.item("minecraft:oak_log", 3), data=_data("chop"), hand=C.item(AXE))
    behavior.draw.item.rng = lambda: 1.0
    _frames(behavior, 3)
    rest = _live(view, "minecraft:oak_log")[0].center
    behavior.cutter._impact()
    behavior.frame(1.0 / 60.0)
    shaken = _live(view, "minecraft:oak_log")[0].center
    assert all(shaken[i] > rest[i] + 0.1 for i in range(3)) and all(shaken[i] < rest[i] + 0.25 for i in range(3)), "三个方向都偏一点，幅度 0.25 以内"
    _frames(behavior, 12)
    assert all(abs(a - b) < 1e-9 for a, b in zip(_live(view, "minecraft:oak_log")[0].center, rest)), "抖完回到原位"
    assert behavior.draw.item.shaking is None
    for stroke in ("strip", "snip"):
        view.data["stroke"] = stroke
        behavior.cutter._impact()
        assert behavior.draw.item.shaking is None, "削皮、剪刀不抖：%s" % stroke
    view.data["stroke"] = "smash"
    behavior.cutter._impact()
    assert behavior.draw.item.shaking is not None, "别的工具都抖"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
