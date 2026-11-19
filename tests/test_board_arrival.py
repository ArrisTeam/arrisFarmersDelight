# -*- coding: utf-8 -*-
# runner: both
"""书里点一道菜时各层从玩家那边飞来（Compat/Diegesis/BoardDraw + BoardDrawEvents + BoardEffects，假引擎见 boardclient.py）：
一次放好几层的，从屏幕下沿（玩家那边）一层隔一层飞来、落定；手放的一层从光标上方落下；放好就做成的（书里点的菜）板上没摆过的层先飞来、都落了才沉进去、
做成的声音和面粉等落完；板上原来就摆着的层在原位。对应 HoD 的 refresh 里的 together / landFromPlayer（446-484、603-608）和 assembled 里的 arrive（1583-1617）。
这里的菜都按"压"（什么收尾也不演）做成：只看层怎么来、什么时候沉；十种收尾本身在 test_board_finish_anim.py。
"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
SAME = type("Changes", (), {"hasSlot": lambda self, ref: False})()
BREAD, TOMATO, CABBAGE, EGG = "minecraft:bread", "arris:tomato", "arris:cabbage", "arris:egg"


def _open(board=None, layers=(), data=None):
    behavior, view, api = C.station()
    view.state.board, view.state.layers = board, list(layers)
    view.data, view.hand = dict(data or {}), None
    behavior.onOpen()
    C.engine.played[:] = []
    C.engine.particles[:] = []
    return behavior, view


def _frames(behavior, seconds, dt=1.0 / 60.0):
    for _ in range(int(round(seconds / dt))):
        behavior.frame(dt)


def _layer(behavior, index):
    return behavior.draw.layers[index]


def _home(index):
    pose = Scene.layerPose(index)
    return (pose["x"], pose["y"], pose["z"])


def _near(a, b, eps=1.0e-6):
    return all(abs(x - y) < eps for x, y in zip(a, b))


def _lay(behavior, view, layers):
    view.state.layers = list(layers)
    behavior.onState(SAME)


def testThePlayersPlaceInTheScreenIsBelowTheMiddleOfTheBoardTowardsTheCook():
    behavior, view = _open()
    x, z = behavior.draw.fromPlayer()
    assert abs(x) < 1.0e-6 and z < -3.0, "屏幕下沿正中那点投到板面上，比屏幕正中那点更靠玩家（站点里 -z）"
    assert behavior.draw.fromPlayer(Scene.TOP + 20.0)[1] != z, "投到的平面越高偏移不同"


def testSeveralLayersLaidAtOnceFlyInFromThePlayerOneAfterTheOther():
    behavior, view = _open()
    offset = behavior.draw.fromPlayer()
    _lay(behavior, view, [C.item(BREAD), C.item(TOMATO), C.item(CABBAGE)])
    first = _layer(behavior, 0).mover
    home = _home(0)
    assert first.visible and _near(first.pos, (home[0] + offset[0], home[1] + Motion.DROP_HEIGHT, home[2] + offset[1])), "第一层一开始就在玩家那边的上空"
    assert not _layer(behavior, 1).mover.visible and not _layer(behavior, 2).mover.visible, "后面的先藏着"
    _frames(behavior, 0.1)
    assert not _layer(behavior, 1).mover.visible, "隔 0.16 秒一层"
    _frames(behavior, 0.08)
    assert _layer(behavior, 1).mover.visible and not _layer(behavior, 2).mover.visible
    _frames(behavior, 0.16)
    assert _layer(behavior, 2).mover.visible
    mid = _layer(behavior, 0).mover
    _frames(behavior, 0.0)
    assert mid.pos[1] < home[1] + Motion.DROP_HEIGHT, "第一层已经在往下落"
    _frames(behavior, 1.0)
    for index in range(3):
        assert _near(_layer(behavior, index).mover.pos, _home(index), 1.0e-4), index
    assert len([prop for prop in view.props.live()]) == 3


def testALayerLaidByHandStillLandsFromAboveTheCursor():
    behavior, view = _open(layers=[C.item(BREAD)])
    _frames(behavior, 1.0)
    _lay(behavior, view, [C.item(BREAD), C.item(TOMATO)])
    mover = _layer(behavior, 1).mover
    home = _home(1)
    assert mover.visible and abs(mover.pos[0] - home[0]) < 1.0e-6 and abs(mover.pos[1] - (home[1] + Motion.DROP_HEIGHT)) < 1.0e-6, "没有光标射线：正上方"
    assert abs(mover.pos[2] - home[2]) < 1.0e-6, "手放的一层不从玩家那边飞来"
    assert behavior.draw.landUntil == 0.0


def testTheSettleOfAWholeDishWaitsForTheLastLayerToLand():
    behavior, view = _open()
    view.data["dish"] = "arris:some_dish"
    _lay(behavior, view, [C.item(BREAD), C.item(TOMATO), C.item(CABBAGE)])
    assert abs(behavior.draw.landUntil - (2 * Motion.LAYER_STAGGER + Motion.PLAYER_LAND_TIME)) < 1.0e-9
    assert C.engine.played == [], "还在飞：落定的一声等它们落完"
    _frames(behavior, 0.6)
    assert C.engine.played == []
    _frames(behavior, 0.1)
    assert C.engine.played == [("dig.wood", 0.5, 0.8)], "最后一层落完（0.64 秒）才响"


def testADishPickedInTheBookFliesInBeforeItMeltsAndItsSoundsWaitForTheLanding():
    behavior, view = _open()
    behavior.draw.quiet = False
    view.state.board = C.item("arris:egg_sandwich", 1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())              # 状态先到：层是空的、菜已经躺在板上
    made = [C.item(BREAD), C.item(EGG), C.item("arris:tomato")]
    behavior.onEffect("assembled", {"layers": made, "finish": "press", "block": False})
    arrive = 2 * Motion.LAYER_STAGGER + Motion.PLAYER_LAND_TIME + Motion.SETTLE_TIME
    assert C.engine.played == [] and not C.engine.particles, "各层还没落：做成的声音、面粉都等着"
    assert _layer(behavior, 0).mover.visible and not _layer(behavior, 1).mover.visible, "没摆过的层一层隔一层飞来"
    assert behavior.draw.melting > arrive
    _frames(behavior, 0.2)
    assert _layer(behavior, 1).mover.visible and _layer(behavior, 0).mover.scale == 1.0, "还没开始沉"
    _frames(behavior, arrive - 0.2 - 0.02)
    assert C.engine.played == [] and _layer(behavior, 2).mover.scale == 1.0
    _frames(behavior, 0.04)
    assert C.engine.played == [("dig.wood", 0.8, 0.75), ("random.pop", 0.35, 1.4)], "各层落完：做成的两声"
    assert C.engine.particles, "面粉"
    _frames(behavior, 0.1)
    assert _layer(behavior, 0).mover.scale < 1.0, "开始沉"
    dish = behavior.draw.item.mover
    assert [prop for prop in view.props.live() if prop.item["newItemName"] == "arris:egg_sandwich"] and 0.3 < dish.scale < 1.0 and dish.pos[1] > 0.0,         "菜同一刻弹出来（JE 的 pop：层往里沉和菜长出来一起开始），不是等层沉完"
    _frames(behavior, 1.0)
    assert [prop.item["newItemName"] for prop in view.props.live()] == ["arris:egg_sandwich"], "菜弹出来，层都没了"
    assert behavior.draw.melting == 0.0


def _made(behavior, view, dish="arris:egg_sandwich", count=1, made=(BREAD, EGG), before=(BREAD, EGG)):
    """板上摆着 before 这几层；状态变成"层清空、菜在板上"，随后 assembled 效果到。"""
    view.state.layers = []
    view.state.board = C.item(dish, count)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.onEffect("assembled", {"layers": [C.item(name) for name in made], "finish": "press", "block": False})


def _shown(view):
    return sorted(prop.item["newItemName"] for prop in view.props.live())


def testALayerLaidWhileTheLayersSinkIsDrawnOnceTheyAreGone():
    """层往菜里沉的这一会儿里服务端又来了状态（菜被拿走、板上又放了一层）：原来整个丢掉，那一层一直不画，要等下一次状态变化。
    JE 每刻都 refresh，层那一半等 melting 走完再照当时的状态画。"""
    for wait in (0.05, 0.2):
        behavior, view = _open(layers=[C.item(BREAD), C.item(EGG)])
        _frames(behavior, 1.0)
        _made(behavior, view)
        _frames(behavior, wait)
        view.state.board, view.state.layers = None, [C.item(TOMATO)]       # 菜拿走了，又放了一层番茄
        behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
        assert behavior.draw.melting > 0.0, "还在沉：层这时是动画的"
        _frames(behavior, 2.0)
        assert _shown(view) == [TOMATO], (wait, _shown(view))
        assert behavior.draw.shown == {"board": None, "layers": [(TOMATO, 0)]} and behavior.draw.late is None, behavior.draw.shown
        assert _near(_layer(behavior, 0).mover.pos, _home(0)), "落在第一层的位置"


def testADishTakenWhileTheLayersSinkDoesNotPopUpAfterwards():
    """层还没落完（书里点的菜：各层要飞一秒多）菜就被拿走了：到弹出来那一刻照最新的状态，板上不画一道已经不在的菜。"""
    behavior, view = _open()
    behavior.draw.quiet = False
    view.state.board = C.item("arris:egg_sandwich", 1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.onEffect("assembled", {"layers": [C.item(BREAD), C.item(EGG), C.item(TOMATO)], "finish": "press", "block": False})
    _frames(behavior, 0.5)                                                # 各层还在飞
    view.state.board = None
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    _frames(behavior, 3.0)
    assert _shown(view) == [] and behavior.draw.shown["board"] is None and behavior.draw.item.prop is None, _shown(view)


def testTheSheetUnderAStackOfDishesWaitsUntilTheLayersHaveSunk():
    """一次做成好几个的（曲奇 8 块）：底下垫的那一张不和正在沉的层抢位置，层沉完才露出来（JE 的 pop：after(MELT_TIME) 才 pile.setVisible）。"""
    behavior, view = _open(layers=[C.item(BREAD), C.item(EGG)])
    _frames(behavior, 1.0)
    _made(behavior, view, dish="arris:sweet_berry_cookie", count=8)
    draw = behavior.draw
    assert not draw.pile.mover.visible, "层还在：垫的那一张先收着"
    _frames(behavior, Motion.MELT_TIME - 0.05)
    assert not draw.pile.mover.visible and draw.item.mover.visible
    _frames(behavior, 0.2)
    assert draw.pile.mover.visible and draw.melting == 0.0
    assert _shown(view) == ["arris:sweet_berry_cookie"] * 2, _shown(view)


def testLayersThatLayOnTheBoardStayAndOnlyTheLastOneComesFromThePlayer():
    behavior, view = _open(layers=[C.item(BREAD), C.item(EGG)])
    _frames(behavior, 1.0)
    view.state.layers = []
    view.state.board = C.item("arris:egg_sandwich", 1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    _frames(behavior, 0.1)
    made = [C.item(BREAD), C.item(EGG), C.item("arris:tomato")]
    behavior.onEffect("assembled", {"layers": made, "finish": "press", "block": False})
    assert _near(_layer(behavior, 0).mover.pos, _home(0)) and _near(_layer(behavior, 1).mover.pos, _home(1)), "原来摆着的两层在原位"
    third = _layer(behavior, 2).mover
    assert third.visible and third.pos[1] > _home(2)[1] + 2.0, "最后放的那层从玩家那边飞来"
    arrive = Motion.PLAYER_LAND_TIME + Motion.SETTLE_TIME
    _frames(behavior, arrive - 0.03)
    assert C.engine.played == []
    _frames(behavior, 0.06)
    assert len(C.engine.played) == 2


def testLayersClearedLongAgoAreNotTakenForTheOnesThatLay():
    behavior, view = _open(layers=[C.item(BREAD)])
    _frames(behavior, 0.5)
    view.state.layers = []
    behavior.onState(SAME)
    _frames(behavior, 2.0)                                              # 一直空着（比如取空了）
    view.state.board = C.item("arris:egg_sandwich", 1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.onEffect("assembled", {"layers": [C.item(BREAD), C.item(EGG)], "finish": "press", "block": False})
    assert not _layer(behavior, 1).mover.visible and _layer(behavior, 0).mover.visible and _layer(behavior, 0).mover.pos[1] > _home(0)[1] + 2.0, \
        "老早清空的层不算原来摆着的：全从玩家那边飞来"


def testALayerLaidAfterADishHasMeltedIsNotLeftShrunk():
    """JE 的 tick 在层沉完时 scaleTo(1, 0) 再收起来：这一格下一回再摆东西是原来的大小（原来只收起来，缩着的 0.1 一直留着：下一道菜的第一层是个小点）。"""
    behavior, view = _open(layers=[C.item(BREAD), C.item(EGG)])
    _frames(behavior, 1.0)
    _made(behavior, view)
    _frames(behavior, 2.0)
    assert behavior.draw.melting == 0.0 and [_layer(behavior, index).mover.scale for index in range(2)] == [1.0, 1.0], "沉完收起来的层缩放还原了"
    view.state.board, view.state.layers = None, [C.item(CABBAGE)]
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    _frames(behavior, 1.0)
    cabbage = [prop for prop in view.props.live() if prop.item["newItemName"] == CABBAGE]
    assert len(cabbage) == 1 and abs(cabbage[0].scale - Scene.scaleOf(10.0)) < 1.0e-9, "第 0 层画 10 像素，不是缩着的"


def testWithoutAnythingNewToLandTheDishMeltsAtOnceAndMakesItsSoundsAtOnce():
    behavior, view = _open(layers=[C.item(BREAD), C.item(EGG)])
    _frames(behavior, 1.0)
    view.state.layers = []
    view.state.board = C.item("arris:egg_sandwich", 1)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: True})())
    behavior.onEffect("assembled", {"layers": [C.item(BREAD), C.item(EGG)], "finish": "press", "block": False})
    assert len(C.engine.played) == 2 and C.engine.particles, "层都摆着：马上做成，声音和面粉不等"
    assert abs(behavior.draw.melting - (Motion.MELT_TIME + 0.05)) < 1.0e-9


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
