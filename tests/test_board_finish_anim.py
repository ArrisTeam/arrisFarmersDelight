# -*- coding: utf-8 -*-
# runner: both
"""做成一道菜之前的十种收尾动画在砧板站点里的画法（Compat/Diegesis/BoardFinishPlay + BoardDrawEvents.assembled + BoardThing，旁观的人在 BoardWatch，假引擎见 boardclient.py）：
每一种都演到底、不留掉落物，演多久、声音粒子什么时候来都是 JE 的（BoardBehavior.assembled / pop，1521-1652），演的时候层真的在翻、立、滚；
收尾里又来的状态照旧最后才画（Draw.late）；沉完的层下一回再摆东西不会还是缩着的。
"""
from __future__ import print_function

import math

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")
Finish = fdtest.load("Shared.Rules.HandsOn.BoardFinish")
Kit = fdtest.load("Shared.Rules.HandsOn.BoardFinishKit")
Icon = fdtest.load("Shared.Rules.HandsOn.BoardIcon")
Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
Sounds = fdtest.load("Shared.Rules.BoardSounds")
ItemPose = fdtest.load("Shared.Rules.ItemPose")
Mix = fdtest.load("Shared.Rules.SoundMix")
PropMath = dgtest.load("Client.PropMath")
CHANGED = type("Changes", (), {"hasSlot": lambda self, ref: True})()
DT = 1.0 / 60.0
TOMATO = "arris:tomato"
POP = [Sounds.ASSEMBLED[0], Sounds.ASSEMBLED[1]]
# 每种收尾一道有代表性的菜：(收尾, 成品, 底座在前的各层)
DISHES = (
    (Assembly.FINISH_PRESS, "arris:apple_pie_item", ["arris:pie_crust", "minecraft:apple", "minecraft:sugar"]),
    (Assembly.FINISH_TOSS, "arris:mixed_salad", ["minecraft:bowl", "arris:cabbage", "minecraft:beetroot", TOMATO]),
    (Assembly.FINISH_ROLL, "arris:kelp_roll", ["minecraft:dried_kelp", "arris:cooked_rice", "minecraft:carrot", "arris:cooked_rice"]),
    (Assembly.FINISH_SKEWER, "arris:barbecue_stick", ["minecraft:stick", "arris:onion", TOMATO, "minecraft:cooked_chicken"]),
    (Assembly.FINISH_KNEAD, "arris:sweet_berry_cookie", ["minecraft:wheat", "minecraft:wheat", "minecraft:sweet_berries"]),
    (Assembly.FINISH_ARRANGE, "arris:steak_and_potatoes", ["minecraft:bowl", "arris:cooked_rice", "minecraft:cooked_beef", "minecraft:baked_potato", "arris:onion"]),
    (Assembly.FINISH_SANDWICH, "arris:egg_sandwich", ["minecraft:bread", "arris:fried_egg", "arris:fried_egg"]),
    (Assembly.FINISH_SHAPE, "arris:salmon_roll", ["arris:cooked_rice", "arris:salmon_slice", "arris:salmon_slice"]),
    (Assembly.FINISH_FREEZE, "arris:melon_popsicle", ["minecraft:stick"] + ["minecraft:melon_slice"] * 4 + ["minecraft:ice"] * 2),
    (Assembly.FINISH_CHOP, "arris:sandwich_cut", ["minecraft:bread", TOMATO, "arris:cabbage"]),
)


def _open(layers=()):
    behavior, view, api = C.station()
    view.state.board, view.state.layers = None, [C.item(name) for name in layers]
    view.data, view.hand = {}, None
    behavior.onOpen()
    C.engine.played[:] = []
    C.engine.particles[:] = []
    view.dust[:] = []
    return behavior, view


def _frames(behavior, seconds):
    for _ in range(int(round(seconds / DT))):
        behavior.frame(DT)


def _made(behavior, view, finish, dish, layers, count=1):
    """板上摆着这几层（先走一会儿让它们落定）：状态变成层清空、菜躺在板上，随后 assembled 效果到。"""
    _frames(behavior, 1.0)
    C.engine.played[:] = []
    view.state.layers, view.state.board = [], C.item(dish, count)
    behavior.onState(CHANGED)
    behavior.onEffect("assembled", {"layers": [C.item(name) for name in layers], "finish": finish, "block": False})


def _live(view):
    return sorted(prop.item["newItemName"] for prop in view.props.live())


def _timeline(behavior, view, seconds, watch=None):
    """逐帧走 seconds 秒：返回 [(时刻, 响的声音)]（assembled 效果到的那一刻已经响了的算 0 秒）；watch(时刻) 每帧调一次。"""
    heard, seen = [(0.0, sound) for sound in C.engine.played], len(C.engine.played)
    for step in range(int(round(seconds / DT))):
        behavior.frame(DT)
        if watch is not None:
            watch((step + 1) * DT)
        for sound in C.engine.played[seen:]:
            heard.append(((step + 1) * DT, sound))
        seen = len(C.engine.played)
    return heard


def _engine(sound):
    """JE 的 (声音名, 音量, 音调) -> 引擎收到的：定义里自带音量音调的（刀声 1.5）BoardFx.play 先除掉（SoundMix）。"""
    return (sound[0],) + tuple(Mix.engineArgs(*sound))


def _same(a, b, eps=1.0e-6):
    return all(abs(x - y) < eps for x, y in zip(a, b)) and len(a) == len(b)


def _matrixClose(a, b, eps=1.0e-6):
    return all(abs(x - y) < eps for row, other in zip(a, b) for x, y in zip(row, other))


# ---------------------------------------------------------------- 每一种都演到底

def testEveryFinishRunsToTheEndAndLeavesOnlyTheDishAndTheTimeIsJavas():
    for finish, dish, layers in DISHES:
        behavior, view = _open(layers)
        _made(behavior, view, finish, dish, layers)
        draw, count = behavior.draw, len(layers)
        assert abs(draw.melting - Kit.sinking(finish, count)) < 1.0e-9, (finish, "melting = 收尾 + 沉 0.28 + 一刻（层都摆着：不用等落）")
        elapsed = 0.0
        while draw.melting > 0.0 and elapsed < 5.0:
            behavior.frame(DT)
            elapsed += DT
        assert Kit.finishing(finish, count) + Kit.MELT_TIME - 1.0e-9 <= elapsed <= Kit.finishing(finish, count) + Kit.MELT_TIME + 3 * DT, (finish, elapsed)
        assert _live(view) == [dish], (finish, _live(view), "层沉完、盖子收起来：只剩菜")
        assert draw.late is None and draw.melting == 0.0 and all(not thing.mover.visible for thing in draw.layers)
        behavior.onClose()


def testTheSoundsOfEveryFinishComeWhenJavaPlaysThemAndThePopWaitsForTheFinish():
    for finish, dish, layers in DISHES:
        behavior, view = _open(layers)
        _made(behavior, view, finish, dish, layers)
        plan = Finish.plan(finish, layers, C.BoardFx.colorOf)
        heard = _timeline(behavior, view, plan.seconds + Kit.MELT_TIME + 0.2)
        want = sorted([(cue[0], cue[3]) for cue in plan.effects() if cue[1] == Kit.SOUND] + [(plan.seconds, POP[0]), (plan.seconds, POP[1])], key=lambda item: item[0])
        assert len(heard) == len(want), (finish, heard, want)
        for (at, sound), (when, expected) in zip(heard, want):
            assert sound[:2] == _engine(expected)[:2] and (finish == Assembly.FINISH_CHOP or abs(sound[2] - _engine(expected)[2]) < 1.0e-9), (finish, sound, expected)
            assert when - 1.0e-9 <= at <= when + 2.5 * DT, (finish, "声音在 JE 放的时刻（最多晚一两帧）", sound, at, when)
        pops = [at for at, sound in heard if sound[:2] == (POP[0][0], POP[0][1]) and sound[2] == POP[0][2]]
        assert len(pops) == 1 and pops[0] >= plan.seconds - 1.0e-9, (finish, "做成的两声等收尾演完")
        behavior.onClose()


def testNothingOfThePopIsDoneBeforeTheFinishEnds():
    """pop 的东西（层往里沉、菜弹出来、面粉 / 霜、闪光、做成的两声）都等收尾演完：收尾期间菜还没出来、层没开始缩。"""
    for finish, dish, layers in DISHES:
        if Kit.finishing(finish, len(layers)) <= 0.0:
            continue
        behavior, view = _open(layers)
        _made(behavior, view, finish, dish, layers)
        draw, finishing = behavior.draw, Kit.finishing(finish, len(layers))
        _frames(behavior, finishing - 3 * DT)
        assert draw.item.prop is None and not draw.item.mover.visible, (finish, "菜还没弹出来")
        assert POP[0] not in C.engine.played and not [p for p in C.engine.particles if p["vars"].get("variable.count") == 12.0], finish
        assert not [entry for entry in view.dust if entry[2:] == (0xFFE9A0, 5)], finish
        for thing in draw.layers[:len(layers)]:
            assert thing.mover.scale > 0.1 or finish in (Assembly.FINISH_FREEZE, Assembly.FINISH_SKEWER, Assembly.FINISH_ARRANGE, Assembly.FINISH_SHAPE), (finish, "层还没开始沉")
        _frames(behavior, 6 * DT)
        assert draw.item.mover.visible and POP[0] in C.engine.played, (finish, "收尾演完：菜弹出来、做成的声音")
        behavior.onClose()


# ---------------------------------------------------------------- 层真的在动

def testTheLayersAreReallyMovedByTheFinishAndHalfwayThroughSomethingHasLeftItsPlace():
    for finish, dish, layers in DISHES:
        if finish == Assembly.FINISH_PRESS:
            continue                                            # 压什么也不演（动作表是空的，test_board_finish_plan）
        behavior, view = _open(layers)
        _made(behavior, view, finish, dish, layers)
        home = [prop.center for prop in view.props.live()]
        _frames(behavior, Kit.finishing(finish, len(layers)) * 0.5 + 0.001)
        moved = [prop for prop in view.props.live() if all(not _same(prop.center, h, 1.0e-3) for h in home)]
        if finish == Assembly.FINISH_SANDWICH:
            assert len([p for p in view.props.live() if p.item["newItemName"] == "minecraft:bread"]) == 2, "夹：盖子是面包的又一份"
        else:
            assert moved, (finish, "有层离开了原位")
        behavior.onClose()


def testTossTheBowlTiltsBackTwelveDegreesAndTheContentsTumble():
    layers = DISHES[1][2]
    behavior, view = _open(layers)
    _made(behavior, view, DISHES[1][0], DISHES[1][1], layers)
    draw = behavior.draw
    lowest, tumbled, highest = [0.0], [0.0], [0.0]

    def watch(_at):
        lowest[0] = min(lowest[0], draw.layers[0].mover.rotation[0] if draw.layers[0].mover.rotation else 0.0)
        for thing in draw.layers[1:4]:
            tumbled[0] = max(tumbled[0], abs(thing.mover.rotation[0]) if thing.mover.rotation else 0.0)
            highest[0] = max(highest[0], thing.mover.pos[1])
    _timeline(behavior, view, 0.6, watch)
    assert abs(lowest[0] + 12.0) < 0.5, "碗后仰到 -12 度"
    assert 35.0 < tumbled[0] <= 40.0 + 1.0e-6, "料翻滚 40 度"
    assert highest[0] > 4.0, "料飞起来 4 像素以上（加弧高 0.6 的倍数）"


def testSkewerThePiecesStandAcrossTheStickFaceTowardsTheHandleAndAreSmaller():
    finish, dish, layers = DISHES[3]
    behavior, view = _open(layers)
    _made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    _frames(behavior, 0.4)                                     # 三片都滑完了（最后一片 0.2 + 0.18 = 0.38），还没开始推（0.48）
    stick = Icon.iconOf("minecraft:stick").axis(10.0)
    stand = math.degrees(math.atan2(stick.dirX, stick.dirZ))
    for index in (1, 2, 3):
        prop = draw.layers[index].prop
        assert prop is not None and prop.flat and prop.matrix is not None
        assert _matrixClose(prop.matrix, ItemPose.lyingMatrix(stand, -60.0, 0.0)), index
        assert abs(prop.scale - 0.7 * Scene.scaleOf(Scene.LAYER_SIZE)) < 1.0e-9, "缩到 0.7"
    normal = [row[2] * -1.0 for row in draw.layers[1].prop.matrix]            # 贴图正面的朝向（本地 -z 在站点里的样子）
    assert normal[2] < -0.5 and normal[0] > 0.5 * abs(normal[2]) * 0.7, "脸朝镜头这一边（-z）、朝柄（+x，屏幕左边）"
    _frames(behavior, 0.3)
    xs = [draw.layers[i].mover.pos[0] for i in (1, 2, 3)]
    assert xs[0] > xs[1] > xs[2], "先上去的推得最远，最后一片留在尖上（尖在屏幕右上，x 更小）"


def testRollTheLayersTiltAboutTheirLengthAsTheyRoll():
    finish, dish, layers = DISHES[2]
    behavior, view = _open(layers)
    _made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    seen = []
    _timeline(behavior, view, 0.7, lambda at: seen.append(draw.layers[1].mover.rotation[0] if draw.layers[1].mover.rotation else 0.0))
    assert max(seen) > 20.0 and min(seen) < -12.0 and abs(seen[-1]) < 1.0e-3, "来回滚：+25 度、-17 度……最后回正"


def testSandwichTheLidIsAnotherLoafThatLiftsClosesAndMeltsAndThenItIsGone():
    finish, dish, layers = DISHES[6]
    behavior, view = _open(layers)
    _made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    heights = {}
    _timeline(behavior, view, 0.9, lambda at: heights.__setitem__(round(at, 3), [p.center[1] for p in view.props.live() if p.item["newItemName"] == "minecraft:bread"]))
    first = heights[round(DT, 3)]
    assert len(first) == 2, "底座和盖子"
    lift = max(max(values) for values in heights.values() if len(values) == 2)
    over = len(layers) * Motion.LAYER_STEP
    assert abs(lift - (Scene.TOP + over + 3.0 + Scene.FLAT_LIFT)) < 0.02, "盖子抬到 over + 3"
    closed = heights[round(0.32, 3)] if round(0.32, 3) in heights else heights[min(heights, key=lambda k: abs(k - 0.32))]
    assert abs(max(closed) - (Scene.TOP + over + Scene.FLAT_LIFT)) < 0.1, "0.32 秒合上（盖在馅上面一层的高度）"
    _frames(behavior, 0.4)
    assert _live(view) == [dish] and not draw.ghosts[0].mover.visible and all(thing.prop is None for thing in draw.ghosts), "融完盖子收起来"


def testFreezeTheFruitGathersAtTheTipAndTheIceVanishes():
    finish, dish, layers = DISHES[8]
    behavior, view = _open(layers)
    _made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    _frames(behavior, 0.45)
    ices = [draw.layers[i] for i in (5, 6)]
    assert all(thing.prop is None for thing in ices), "冰缩没了（0.35 秒）"
    assert abs(draw.layers[1].mover.scale - 0.75) < 1.0e-9, "水果缩到 0.75"
    stick = Icon.iconOf("minecraft:stick").axis(10.0)
    tip = stick.at(0.28)
    assert draw.layers[1].mover.pos[0] < Motion.layerJitter(0)[0] + tip[0] + 1.0 and draw.layers[1].mover.pos[2] > 0.0, "聚在签子尖那头（屏幕右上）"
    dust = [p for p in C.engine.particles if p["id"] == "arris:board_dust"]
    assert [int(p["vars"]["variable.count"]) for p in dust] == [10], "聚好那一刻 10 颗霜"
    assert [entry[2:] for entry in view.dust] == [(0xE8F4FF, 4)], "霜色的闪光 4 颗"
    assert Sounds.GLASS_BREAK in [sound[0] for sound in C.engine.played]


def testTheLayersSinkFromWhereTheFinishLeftThemNotFromWhereTheyFirstLay():
    """pop 把各层从各自的 rest（收尾演完躺的地方：拌换了次序、卷合拢成一根、串排在签子上……）往板中间沉（x、z 缩到 0.4，高缩到 0.08）。"""
    for finish, dish, layers in DISHES:
        if finish in (Assembly.FINISH_PRESS, Assembly.FINISH_SANDWICH, Assembly.FINISH_CHOP):
            continue                                                  # 这三种 rest 就是各层本来躺的地方
        behavior, view = _open(layers)
        _made(behavior, view, finish, dish, layers)
        draw = behavior.draw
        plan = Finish.plan(finish, layers, C.BoardFx.colorOf)
        _frames(behavior, plan.seconds + Kit.MELT_TIME - 2 * DT)
        for index in range(len(layers)):
            x, y, z = plan.rest[index]
            assert _same(draw.layers[index].mover.pos, (x * 0.4, y * 0.08, z * 0.4), 0.06), (finish, index, draw.layers[index].mover.pos)
            assert abs(draw.layers[index].mover.scale - 0.1) < 0.02
        behavior.onClose()


def testTheRestingTurnIsTheStartOfTheFirstRotationSoThereIsNoJumpWhenTheFinishBegins():
    """层摆着时画的朝向是 Ry(-turn)（和原来按 along 摆的一样）；收尾第一次转它的时候从这个朝向起，第一帧看不出跳。"""
    for finish, dish, layers in DISHES:
        if finish not in (Assembly.FINISH_TOSS, Assembly.FINISH_ROLL, Assembly.FINISH_KNEAD, Assembly.FINISH_SKEWER, Assembly.FINISH_ARRANGE, Assembly.FINISH_SHAPE):
            continue
        behavior, view = _open(layers)
        _frames(behavior, 1.0)
        before = [prop.matrix for prop in view.props.live()]
        view.state.layers, view.state.board = [], C.item(dish)
        behavior.onState(CHANGED)
        behavior.onEffect("assembled", {"layers": [C.item(name) for name in layers], "finish": finish, "block": False})
        behavior.frame(DT)
        draw = behavior.draw
        for index in range(1, len(layers)):
            prop = draw.layers[index].prop
            if prop is not None:
                assert _matrixClose(prop.matrix, before[index], 0.05), (finish, index, "第一帧：只比摆着的转了一点点")
        behavior.onClose()


def testAThingRotatedByAFinishIsTurnedBackWhenItIsPutDown():
    behavior, view = _open(["minecraft:bread"])
    thing = behavior.draw.layers[0]
    thing.rotateTo(10.0, 20.0, 30.0)
    assert thing.mover.rotation == (10.0, 20.0, 30.0)
    thing.put(0.0, 0.0, 0.0)
    assert thing.mover.rotation is None and thing.mover.scale == 1.0
    thing.rotateTo(5.0, 0.0, 0.0, 0.2)
    assert thing.mover.rotation == (0.0, -thing.turn, 0.0), "没转过的从摆着的样子起：Ry(-turn)"


def testTheStateIsHeldBackUntilTheLayersAreGoneEvenWhenFramesAreVeryLong():
    """落在帧上的步骤最多晚一两帧：帧很长（掉帧）时倒数先走完的话，层还在沉的时候来的状态就当场画了。倒数只由收尾和沉完（done）去结束。"""
    finish, dish, layers = DISHES[1]
    behavior, view = _open(layers)
    _made(behavior, view, finish, dish, layers)
    draw = behavior.draw
    for _ in range(4):
        behavior.frame(0.25)                                         # 1 秒：倒数（0.54 + 0.28 + 0.05 = 0.87）走完了，done 要到下一帧才跑
    assert draw.melting > 0.0, "done 还没跑：还在沉"
    view.state.board, view.state.layers = None, [C.item(TOMATO)]
    behavior.onState(CHANGED)
    assert draw.late is not None and draw.shown["layers"] != [(TOMATO, 0)], "状态先记着"
    behavior.frame(0.25)
    assert draw.melting == 0.0 and draw.late is None
    _frames(behavior, 1.0)
    assert draw.shown["layers"] == [(TOMATO, 0)] and _live(view) == [TOMATO]


# ---------------------------------------------------------------- 书里点的菜、状态来得晚

def testADishFromTheBookFliesInFirstAndOnlyThenPlaysItsFinish():
    finish, dish, layers = DISHES[3]
    behavior, view = _open()
    draw = behavior.draw
    behavior.draw.quiet = False
    view.state.board = C.item(dish)
    behavior.onState(CHANGED)
    behavior.onEffect("assembled", {"layers": [C.item(name) for name in layers], "finish": finish, "block": False})
    arrive = 3 * Motion.LAYER_STAGGER + Motion.PLAYER_LAND_TIME + Motion.SETTLE_TIME
    assert abs(draw.melting - (arrive + Kit.sinking(finish, 4))) < 1.0e-9, "等层飞完 + 收尾 + 沉 + 一刻"
    _frames(behavior, arrive - 0.05)
    assert all(thing.mover.rotation is None and thing.mover.scale == 1.0 for thing in draw.layers[:4]), "层还在飞：收尾没开始"
    _frames(behavior, 0.1 + 0.1)
    assert draw.layers[1].mover.rotation is not None, "落定了：收尾开始（片滑向签子尖）"
    _frames(behavior, 2.0)
    assert _live(view) == [dish]


def testAStateThatComesWhileTheFinishPlaysIsDrawnOnceTheLayersAreGone():
    for finish, dish, layers in DISHES:
        behavior, view = _open(layers)
        _made(behavior, view, finish, dish, layers)
        _frames(behavior, 0.1)
        view.state.board, view.state.layers = None, [C.item(TOMATO)]
        behavior.onState(CHANGED)
        draw = behavior.draw
        assert draw.melting > 0.0 and draw.late is not None, finish
        _frames(behavior, 2.5)
        assert _live(view) == [TOMATO], (finish, _live(view))
        assert draw.shown["layers"] == [(TOMATO, 0)] and draw.late is None
        tomato = draw.layers[0]
        assert tomato.mover.scale == 1.0 and tomato.mover.rotation is None and abs(tomato.prop.scale - Scene.scaleOf(10.0)) < 1.0e-9, (finish, "放回的第一层不是缩着的、转着的")
        behavior.onClose()


# ---------------------------------------------------------------- 平躺的东西按姿态矩阵摆

def _worldAxes(yaw):
    origin = C.Geometry.stationPointToWorld(yaw, 0.0, 0.0, 0.0)
    return [tuple(a - b for a, b in zip(C.Geometry.stationPointToWorld(yaw, *point), origin)) for point in ((16.0, 0.0, 0.0), (0.0, 16.0, 0.0), (0.0, 0.0, 16.0))]


def testAnUntouchedFlatThingIsDrawnByTheMatrixExactlyAsTheAlongPathDrewIt():
    """平躺的东西现在一律按姿态矩阵摆（才能翻、立、滚）：没转过的和原来按 along = (cos turn, sin turn) 摆的是同一个朝向，四个站点朝向都一样（用前置包真的 PropMath）。"""
    for yaw in (0, 90, 180, 270):
        axes = _worldAxes(yaw)
        for turn in (0.0, -1.1, 14.3, 11.0, -7.7, 17.0):
            along = (math.cos(math.radians(turn)), math.sin(math.radians(turn)))
            a = C.Geometry.stationPointToWorld(yaw, 0.0, 0.0, 0.0)
            b = C.Geometry.stationPointToWorld(yaw, along[0], 0.0, along[1])
            before = PropMath.flatMatrix(b[0] - a[0], b[2] - a[2])
            after = PropMath.toWorld(axes, ItemPose.lyingMatrix(-turn))
            assert _matrixClose(before, after, 1.0e-9), (yaw, turn)
            assert all(abs(x - y) < 1.0e-6 for x, y in zip(PropMath.engineEuler(before), PropMath.engineEuler(after))), (yaw, turn, "引擎收到的三个角也一样")


def testTheStationDrawsARestingLayerThroughTheMatrix():
    behavior, view = _open(["minecraft:bread", TOMATO, "arris:cabbage"])
    _frames(behavior, 1.0)
    for index, prop in enumerate(view.props.live()):
        assert prop.flat and _matrixClose(prop.matrix, ItemPose.lyingMatrix(-Scene.layerPose(index)["turn"])), index


# ---------------------------------------------------------------- 旁观的人

def testAnOnlookerHearsTheFinishAndThePopAtTheSameMomentsTheCookDoes():
    C.BoardWatch.enable(C.Geometry)
    for finish, _dish, layers in DISHES:
        count = len(layers)
        plan = Finish.plan(finish, [""] * count, C.BoardFx.colorOf)
        C.engine.reset()
        C.BoardWatch.OnBoardLook({"dimensionId": 0, "pos": list(C.STATION_POS), "event": "assembled", "finish": finish, "block": False, "count": count})
        immediate = [sound[:2] for sound in C.engine.played]
        engine = lambda sound: _engine(sound)[:2]
        timers = C.engine.run_timers()
        waiting = [(round(seconds, 6), args[3][3][:2]) for seconds, func, args in timers if func.__name__ == "_effect" and args[3][1] == Kit.SOUND]
        pops = [round(seconds, 6) for seconds, func, _args in timers if func.__name__ == "_popped"]
        want = [(round(cue[0], 6), cue[3][:2]) for cue in plan.effects() if cue[1] == Kit.SOUND]
        assert waiting == [item for item in want if item[0] > 0.0], (finish, waiting, want)
        assert immediate[:len([1 for item in want if item[0] <= 0.0])] == [engine(cue[3]) for cue in plan.effects() if cue[1] == Kit.SOUND and cue[0] <= 0.0], (finish, "不用等的当场响")
        if plan.seconds > 0.0:
            assert pops == [round(plan.seconds, 6)], (finish, pops, "做成的两声、面粉、闪光等收尾演完")
            assert POP[0][:2] not in immediate
            C.engine.reset()
        else:
            assert pops == [] and immediate[-2:] == [engine(POP[0]), engine(POP[1])], (finish, "压：做成的两声当场响")


def testAnOnlookerWithoutTheLayerCountOrWithBadDataStillHearsThePopAfterTheFinishAndDoesNotRaise():
    C.BoardWatch.enable(C.Geometry)
    for bad in (None, -1, 10, "3", True, 2.5, [3]):
        C.engine.reset()
        C.BoardWatch.OnBoardLook({"dimensionId": 0, "pos": list(C.STATION_POS), "event": "assembled", "finish": "toss", "block": False, "count": bad})
        C.engine.run_timers()
        assert [sound[:2] for sound in C.engine.played][-2:] == [(POP[0][0], POP[0][1]), (POP[1][0], POP[1][1])], bad


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
