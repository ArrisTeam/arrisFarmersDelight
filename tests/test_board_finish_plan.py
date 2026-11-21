# -*- coding: utf-8 -*-
# runner: both
"""做成一道菜之前的十种收尾动画的动作表（Shared/Rules/HandsOn/BoardFinish*.py）：常量和每种演多久照 HoD 的 BoardBehavior.assembled（1521-1562），
每一种的位置、转角、缩放、声音、粒子逐条照 toss / roll / skewer / knead / arrange / sandwich / shape / freeze / chopTogether（1657-1961）。
JE 的 moveTo(x, y - index * LAYER_STEP, z) 是从层自己的高度算起，这里的位置是离板面的高，所以期望值里的高度是 index * LAYER_STEP 加上 JE 的偏移。
"""
from __future__ import print_function

import io
import json
import math

import fdtest

Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")
Finish = fdtest.load("Shared.Rules.HandsOn.BoardFinish")
Kit = fdtest.load("Shared.Rules.HandsOn.BoardFinishKit")
Icon = fdtest.load("Shared.Rules.HandsOn.BoardIcon")
Motion = fdtest.load("Shared.Rules.HandsOn.BoardMotion")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
Sounds = fdtest.load("Shared.Rules.BoardSounds")

KINDS = (Assembly.FINISH_PRESS, Assembly.FINISH_TOSS, Assembly.FINISH_ROLL, Assembly.FINISH_SKEWER, Assembly.FINISH_KNEAD, Assembly.FINISH_ARRANGE,
         Assembly.FINISH_SANDWICH, Assembly.FINISH_SHAPE, Assembly.FINISH_FREEZE, Assembly.FINISH_CHOP)
STEP = Motion.LAYER_STEP
COLOR = 0x336699
VANILLA = fdtest.vanilla("sounds", "sound_definitions.json")      # 本机最新的原版资源包里的（tools/vanilla_pack.py）；没有游戏目录是 None


def _names(count, base="minecraft:bread"):
    return [base] + ["arris:tomato"] * (count - 1)


def _plan(finish, count, **kwargs):
    return Finish.plan(finish, _names(count, kwargs.pop("base", "minecraft:bread")), lambda name: COLOR, **kwargs)


def _close(a, b, eps=1.0e-9):
    return all(abs(x - y) < eps for x, y in zip(a, b)) and len(a) == len(b)


def _sounds(plan):
    return [(round(cue[0], 9), cue[3]) for cue in plan.effects() if cue[1] == Kit.SOUND]


def _cues(plan, op, target=None):
    return [cue for cue in plan.ordered() if cue[1] == op and (target is None or cue[2] == target)]


def _replay(plan, until, dt=1.0 / 1200.0):
    """把动作表放到一个个 Mover 上走 until 秒（层从摆好的位置起）；返回 {目标: Mover}。"""
    movers = dict((i, Motion.Mover(*Scene_pose(i))) for i in range(plan.count))
    movers[Kit.LID] = Motion.Mover(0.0, 0.0, 0.0)
    cues = [cue for cue in plan.ordered() if cue[2] is not None]
    index, clock = 0, 0.0
    while clock <= until + 1.0e-9:
        while index < len(cues) and cues[index][0] <= clock + 1.0e-9:
            _at, op, target, args = cues[index]
            index += 1
            mover = movers[target]
            if op == Kit.MOVE:
                mover.move(args[0][0], args[0][1], args[0][2], args[1], args[2])
            elif op == Kit.ROTATE:
                mover.rotateTo(args[0][0], args[0][1], args[0][2], args[1])
            elif op == Kit.SCALE:
                mover.scaleTo(args[0], args[1])
        for mover in movers.values():
            mover.update(dt)
        clock += dt
    return movers


def Scene_pose(index):
    pose = Scene.layerPose(index)
    return (pose["x"], pose["y"], pose["z"])


# ---------------------------------------------------------------- 常量和时长

def testTheConstantsAreJavas():
    """BoardBehavior.java 类头的常量（95-163）。"""
    assert (Kit.MELT_TIME, Kit.LAYER_STEP) == (0.28, 0.65)
    assert (Kit.TOSS_HEIGHT, Kit.TOSS_TIME, Kit.TOSS_REST, Kit.TOSS_JERK, Kit.TOSS_JERK_TIME, Kit.TOSS_TILT, Kit.TOSS_TUMBLE) == (4.0, 0.42, 0.12, 0.9, 0.16, 12.0, 40.0)
    assert (Kit.ROLL_GATHER, Kit.ROLLS, Kit.ROLL_STROKE, Kit.ROLL_TRAVEL, Kit.ROLL_TURN) == (0.12, 3, 0.14, 1.6, 25.0)
    assert (Kit.SKEWER_SLIDE, Kit.SKEWER_STAGGER, Kit.SKEWER_PUSH, Kit.SKEWER_FIRST, Kit.SKEWER_LAST, Kit.SKEWER_STAND, Kit.SKEWER_SCALE) == \
        (0.18, 0.1, 0.16, 0.12, 0.62, -60.0, 0.7)
    assert (Kit.ARRANGE_SLIDE, Kit.ARRANGE_STAGGER, Kit.ARRANGE_RING, Kit.ARRANGE_SCALE) == (0.18, 0.08, 2.4, 0.8)
    assert (Kit.LID_LIFT, Kit.LID_CLOSE, Kit.LID_PRESS, Kit.LID_HEIGHT) == (0.16, 0.16, 0.1, 3.0)
    assert (Kit.SHAPE_GATHER, Kit.SHAPE_LAY, Kit.SHAPE_PRESS) == (0.14, 0.12, 0.1)
    assert (Kit.FREEZE_GATHER, Kit.FREEZE_SET, Kit.FREEZE_AT, Kit.FROST) == (0.2, 0.3, 0.28, 0xE8F4FF)
    assert (Kit.CHOPS, Kit.CHOP_STROKE, Kit.CHOP_PART) == (2, 0.16, 0.9)
    assert (Kit.KNEAD_PRESS, Kit.KNEAD_PUSHES, Kit.KNEAD_PUSH, Kit.KNEAD_TURN, Kit.KNEAD_SPREAD) == (0.12, 3, 0.09, 22.0, 1.2)


def _javaFinishing(finish, count):
    """assembled 里的 switch（1528-1539）逐字。"""
    if finish == "toss":
        return 0.42 + 0.12
    if finish == "roll":
        return 0.12 + (3 + 1) * 0.14
    if finish == "skewer":
        return 0.18 + (count - 1) * 0.1 + 0.16
    if finish == "knead":
        return 0.12 + 3 * 0.09 * 2.0
    if finish == "arrange":
        return 0.18 + max(0, count - 2) * 0.08
    if finish == "sandwich":
        return 0.16 + 0.16 + 0.1
    if finish == "shape":
        return 0.14 + max(1, count - 1) * 0.12 + 0.1
    if finish == "freeze":
        return 0.2 + 0.3
    if finish == "chop":
        return 2 * 0.16
    return 0.0


def testEveryFinishLastsAsLongAsJavaSaysAndMeltingAddsTheSinkAndOneTick():
    assert sorted(KINDS) == sorted(getattr(Assembly, name) for name in dir(Assembly) if name.startswith("FINISH_")), "十种都在"
    for finish in KINDS:
        for count in range(1, 10):
            assert abs(Kit.finishing(finish, count) - _javaFinishing(finish, count)) < 1.0e-9, (finish, count)
            assert abs(Kit.sinking(finish, count) - (_javaFinishing(finish, count) + 0.28 + 0.05)) < 1.0e-9, (finish, count)
            assert abs(_plan(finish, count).seconds - _javaFinishing(finish, count)) < 1.0e-9, (finish, count)
    for unknown in (None, "", "nonsense", 5, ["toss"], {"toss": 1}):
        assert Kit.finishing(unknown, 4) == 0.0, "认不出的收尾按压算（JE 的 finish() 对不认识的名字回 PRESS）"


def testAPressAndAnEmptyStackHaveNothingToShowAndOnlyTheWait():
    assert _plan(Assembly.FINISH_PRESS, 5).cues == [] and _plan(Assembly.FINISH_PRESS, 5).seconds == 0.0
    plan = Finish.plan(Assembly.FINISH_TOSS, [], lambda name: COLOR)
    assert plan.cues == [] and abs(plan.seconds - 0.54) < 1.0e-9, "没有层：JE 的 lastLayers 不会是空的，这里只是不抛"
    assert Finish.plan("nonsense", _names(3), lambda name: COLOR).cues == []


def testEveryPlanEndsWithEachLayerWhereItsRestSaysAndNothingRunsPastTheFinish():
    """逐帧把动作表放到 Mover 上：收尾演完（Plan.seconds）各层都躺在 rest 里；没有哪个动作超出收尾（夹的盖子随后融掉的除外，它们在 pop 的同一刻开始）。"""
    for finish in KINDS:
        for count in (2, 3, 5, 9):
            plan = _plan(finish, count, base="minecraft:stick" if finish in ("skewer", "freeze") else "arris:cooked_rice" if finish == "shape" else "minecraft:bread")
            for at, op, target, args in plan.ordered():
                if target == Kit.LID and op == Kit.SHOW:
                    continue
                span = args[1] if op in (Kit.MOVE, Kit.SCALE, Kit.ROTATE) and target != Kit.LID else 0.0
                if op == Kit.SCALE and target == Kit.LID and at >= plan.seconds - 1.0e-9:
                    continue
                if op == Kit.MOVE and target == Kit.LID and at >= plan.seconds - 1.0e-9:
                    continue
                assert at + span <= plan.seconds + 1.0e-9, (finish, count, at, op, target)
            movers = _replay(plan, plan.seconds)
            for index in range(count):
                assert _close(movers[index].pos, plan.rest[index], 1.0e-6), (finish, count, index, movers[index].pos, plan.rest[index])


def testRestStartsAsLayersLieAndSomeFinishesRearrangeIt():
    plan = _plan(Assembly.FINISH_SANDWICH, 4)
    assert len(plan.rest) == 9
    for index in range(9):
        jitter = Motion.layerJitter(index)
        assert _close(plan.rest[index], (jitter[0], index * STEP, jitter[1])), "rest(i, jitterX, i * LAYER_STEP, jitterZ)：1522-1524，夹和一起切不改它"


# ---------------------------------------------------------------- 拌

def testTossTheBowlJerksUpAndTheContentsFlyEachItsOwnHeightAndLandBackToFront():
    plan = _plan(Assembly.FINISH_TOSS, 5)
    jitter0 = Motion.layerJitter(0)
    bowl = _cues(plan, Kit.MOVE, 0)
    assert bowl == [(0.0, Kit.MOVE, 0, ((jitter0[0], 0.0, jitter0[1]), 0.16, 0.9))], "碗颠一下：弧高 0.9、0.16 秒"
    assert [(c[0], c[3]) for c in _cues(plan, Kit.ROTATE, 0)] == [(0.0, ((-12.0, 0.0, 0.0), 0.08)), (0.08, ((0.0, 0.0, 0.0), 0.08))], "后仰 12 度再回来"
    for index in range(1, 5):
        lands = 5 - index                                          # 倒着次序落回：最上面的落最低
        x, z = Motion.layerJitter(lands)
        move, = _cues(plan, Kit.MOVE, index)
        height = 4.0 + (index * 37 % 5) * 0.6
        assert move[0] == 0.0 and _close(move[3][0], (x, lands * STEP, z)) and move[3][1:] == (0.42, height), index
        assert _close(plan.rest[index], (x, lands * STEP, z)), "rest 跟着换了次序"
        side = 1.0 if index % 2 == 0 else -1.0
        spin = Motion.layerTurn(lands) + side * (120.0 + (index * 53 % 80))
        first, second = _cues(plan, Kit.ROTATE, index)
        assert _close(first[3][0], (side * 40.0, (Motion.layerTurn(index) + spin) / 2.0, -side * 40.0 * 0.6)) and first[3][1] == 0.21 and first[0] == 0.0
        assert _close(second[3][0], (0.0, spin, 0.0)) and second[3][1] == 0.21 and abs(second[0] - 0.21) < 1.0e-12
    assert _close(plan.rest[0], (jitter0[0], 0.0, jitter0[1])), "碗不动窝"


def testTossSoundsTheLeatherFirstAndEachPieceLandingFromTheTop():
    plan = _plan(Assembly.FINISH_TOSS, 5)
    sounds = _sounds(plan)
    assert sounds[0] == (0.0, (Sounds.ARMOR_EQUIP_LEATHER, 0.5, 1.4)), "开头一声皮革响"
    assert [(at, name, volume) for at, (name, volume, _p) in sounds[1:]] == [(round(0.42 - 0.02 * i, 9), "dig.wood", 0.3) for i in (4, 3, 2, 1)], "每片落定：落在 0.42 - 0.02 * i"
    assert [round(pitch, 9) for _at, (_n, _v, pitch) in sounds[1:]] == [round(1.3 + 0.05 * i, 9) for i in (4, 3, 2, 1)]


# ---------------------------------------------------------------- 卷

def testRollTheLayersGatherIntoOneLogAndRollThreeStrokesEachShorter():
    plan = _plan(Assembly.FINISH_ROLL, 4)
    for index in range(4):
        y = index * STEP * 0.6
        assert _close(plan.rest[index], (0.0, y, 0.0))
        gather = [c for c in _cues(plan, Kit.MOVE, index) if c[0] == 0.0][0]
        assert gather[3] == ((0.0, y, 0.0), 0.12, 0.0), "各层先合拢（0.12 秒）"
        strokes = [c for c in _cues(plan, Kit.MOVE, index) if c[0] > 0.0]
        assert [round(c[0], 9) for c in strokes] == [0.12, 0.26, 0.4, 0.54]
        assert [round(c[3][0][2], 9) for c in strokes] == [1.6, round(-2.0 / 3.0 * 1.6, 9), round(1.6 / 3.0, 9), 0.0], "来回三趟：1、-2/3、1/3，最后回到 0"
        turns = [c for c in _cues(plan, Kit.ROTATE, index) if c[0] > 0.0]
        assert [round(c[3][0][0], 9) for c in turns] == [25.0, round(-2.0 / 3.0 * 25.0, 9), round(25.0 / 3.0, 9), 0.0]
        assert all(abs(c[3][0][1] - Motion.layerTurn(index) * 0.3) < 1.0e-12 and c[3][1] == 0.14 for c in turns)
    assert [(at, v) for at, (_n, v, _p) in _sounds(plan)] == [(0.12, 0.3), (0.26, 0.3), (0.4, 0.3)], "前三趟各响一声，最后回正的不响"
    assert [round(p, 9) for _at, (_n, _v, p) in _sounds(plan)] == [1.2, 1.3, 1.4]


# ---------------------------------------------------------------- 串

def testSkewerThePiecesSlideToTheTipStandAcrossTheStickAndArePushedTowardsTheHandle():
    plan = _plan(Assembly.FINISH_SKEWER, 4, base="minecraft:stick")
    stick = Icon.iconOf("minecraft:stick").axis(10.0)
    tip, stand = stick.at(0.0), math.degrees(math.atan2(stick.dirX, stick.dirZ))
    assert abs(stand + 45.0) < 1.0e-6, "签子从左下（柄）斜到右上（尖）：站的朝向 -45 度"
    base = Motion.layerJitter(0)
    for index in range(1, 4):
        start = (index - 1) * 0.1
        slide, push = _cues(plan, Kit.MOVE, index)
        assert abs(slide[0] - start) < 1.0e-12 and _close(slide[3][0], (base[0] + tip[0], 0.65, base[1] + tip[1])) and slide[3][1] == 0.18, "滑到尖上"
        assert abs(push[0] - (0.18 + 3 * 0.1)) < 1.0e-12 and push[3][0] == plan.rest[index] and push[3][1] == 0.16, "一起往柄推"
        share = 0.62 - (0.62 - 0.12) * (index - 1) / 2.0
        spot = stick.at(share)
        assert _close(plan.rest[index], (base[0] + spot[0], 0.65, base[1] + spot[1])), "先上去的推得最远：0.62、0.37、0.12"
        turn, = _cues(plan, Kit.ROTATE, index)
        assert abs(turn[0] - start) < 1.0e-12 and _close(turn[3][0], (-60.0, stand, 0.0)) and turn[3][1] == 0.18, "立起来 -60 度、脸朝柄"
        scale, = _cues(plan, Kit.SCALE, index)
        assert abs(scale[0] - start) < 1.0e-12 and scale[3] == (0.7, 0.18)
    assert _cues(plan, Kit.MOVE, 0) == [] and _cues(plan, Kit.ROTATE, 0) == [], "签子自己不动"
    line = [(plan.rest[i][0] - base[0], plan.rest[i][2] - base[1]) for i in (1, 2, 3)]
    assert all(abs(line[k][0] * stick.dirZ - line[k][1] * stick.dirX - (stick.x * stick.dirZ - stick.z * stick.dirX)) < 1.0e-9 for k in range(3)), "三片都在签子那条线上"


def testSkewerSoundsAndASingleStickPieceSitsInTheMiddle():
    plan = _plan(Assembly.FINISH_SKEWER, 4, base="minecraft:stick")
    sounds = _sounds(plan)
    assert [(round(at, 9), v, round(p, 9)) for at, (_n, v, p) in sounds[:3]] == [(round(0.144 + 0.1 * k, 9), 0.3, round(1.4 + 0.06 * (k + 1), 9)) for k in range(3)], "每片滑上去 0.8 * 0.18 之后一声"
    assert sounds[3] == (0.48, ("hit.wood", 0.25, 1.6)), "一起推的那一声"
    one = _plan(Assembly.FINISH_SKEWER, 2, base="minecraft:stick")
    stick = Icon.iconOf("minecraft:stick").axis(10.0)
    spot = stick.at((0.12 + 0.62) / 2.0)
    base = Motion.layerJitter(0)
    assert _close(one.rest[1], (base[0] + spot[0], 0.65, base[1] + spot[1])), "只有一片：落在 0.37"


# ---------------------------------------------------------------- 揉

def testKneadPressedIntoALumpThenPushedFlatThreeTimes():
    plan = _plan(Assembly.FINISH_KNEAD, 3, base="minecraft:wheat")
    for index in range(3):
        x, z = Motion.layerJitter(index)
        rest = (x * 0.5, index * STEP * 0.35, z * 0.5)
        assert _close(plan.rest[index], rest)
        moves = _cues(plan, Kit.MOVE, index)
        assert moves[0][0] == 0.0 and _close(moves[0][3][0], rest) and moves[0][3][1] == 0.12, "压成一坨"
        out = (1.0 if index % 2 == 0 else -1.0) * 1.2
        pushes = [c for c in moves[1:] if c[3][0][1] == 0.0 and c[3][0] != rest]
        assert [round(c[0], 9) for c in pushes] == [0.12, 0.3, 0.48], "三次推平，相隔 0.18"
        assert all(_close(c[3][0], (rest[0] + out, 0.0, rest[2] + out * 0.6)) and c[3][1] == 0.09 for c in pushes), "压到板面上、向两边摊 1.2"
        gathers = [c for c in moves[1:] if c not in pushes]
        assert [round(c[0], 9) for c in gathers] == [0.21, 0.39, 0.57] and all(c[3][0] == rest for c in gathers), "推完收拢"
        twists = _cues(plan, Kit.ROTATE, index)
        assert [round(c[3][0][1] - Motion.layerTurn(index), 9) for c in twists] == [22.0, -22.0, 22.0] and all(c[3][1] == 0.18 for c in twists)
    assert [(at, name, v, p) for at, (name, v, p) in _sounds(plan)] == [(0.0, "dig.wood", 0.5, 0.7), (0.12, "step.cloth", 0.45, 0.75),
                                                                        (0.3, "step.cloth", 0.45, 0.75), (0.48, "step.cloth", 0.45, 0.75)], "开头一声，每次推平一声"


# ---------------------------------------------------------------- 摆

def testArrangeTheMainPieceSlidesToTheMiddleAndTheRestToARingAroundIt():
    plan = _plan(Assembly.FINISH_ARRANGE, 5)
    base = Motion.layerJitter(0)
    sides = 3
    for index in range(1, 5):
        if index == 1:
            want = (base[0], 0.65, base[1])
        else:
            around = 2.0 * math.pi * (index - 2) / sides + 0.6
            want = (base[0] + math.cos(around) * 2.4, 0.65, base[1] + math.sin(around) * 2.4)
        assert _close(plan.rest[index], want), index
        move, = _cues(plan, Kit.MOVE, index)
        start = max(0, index - 2) * 0.08
        assert abs(move[0] - start) < 1.0e-12 and move[3] == (plan.rest[index], 0.18, 0.0), "依次滑进来，相隔 0.08"
        scale, = _cues(plan, Kit.SCALE, index)
        assert scale[3] == (1.0 if index == 1 else 0.8, 0.18)
        turn, = _cues(plan, Kit.ROTATE, index)
        assert _close(turn[3][0], (0.0, Motion.layerTurn(index) * 0.5, 0.0)) and turn[3][1] == 0.18
    assert [(round(at, 9), round(p, 9)) for at, (_n, _v, p) in _sounds(plan)] == [(0.144, 1.3), (0.144, 1.35), (0.224, 1.4), (0.304, 1.45)], "主料和第一块配料同一刻，之后每块一声"
    ring = [math.hypot(plan.rest[i][0] - base[0], plan.rest[i][2] - base[1]) for i in (2, 3, 4)]
    assert all(abs(r - 2.4) < 1.0e-9 for r in ring), "半径 2.4 的一圈"


# ---------------------------------------------------------------- 夹

def testSandwichTheLidLiftsComesOverTheFillingClosesAndMeltsWithTheLayers():
    plan = _plan(Assembly.FINISH_SANDWICH, 4)
    assert plan.lid is True and _cues(plan, Kit.MOVE, 0) == [], "底座和馅不动"
    x, z = Motion.layerJitter(0)
    over = 4 * STEP
    moves = [(round(c[0], 9), c[3]) for c in _cues(plan, Kit.MOVE, Kit.LID)]
    assert moves[0][0] == 0.0 and abs(moves[0][1][0][0] - x) < 1.0e-12 and moves[0][1][1] == 0.0, "盖子先在底座那一格里"
    assert moves[1:] == [(0.0, ((x, over + 3.0, z), 0.16, 0.0)), (0.16, ((x, over, z), 0.16, 0.0)), (0.32, ((x, over - 0.3, z), 0.05, 0.0)),
                         (0.37, ((x, over, z), 0.05, 0.0)), (0.42, ((x * 0.4, over * 0.08, z * 0.4), 0.28, 0.0))], "抬 3、盖过馅、压下 0.3、回来、随各层融掉"
    assert [(round(c[0], 9), c[3]) for c in _cues(plan, Kit.SCALE, Kit.LID)] == [(0.42, (0.1, 0.28))]
    assert [(round(c[0], 9), c[3]) for c in _cues(plan, Kit.SHOW, Kit.LID)] == [(0.7, False)], "融完收起来"
    assert [(round(at, 9), s) for at, s in _sounds(plan)] == [(0.32, ("dig.wood", 0.6, 0.9))], "合上那一刻一声"


# ---------------------------------------------------------------- 成形

def testShapeTheRiceIsPressedTheSlicesLaidAlongItAndOnePress():
    plan = _plan(Assembly.FINISH_SHAPE, 4, base="arris:cooked_rice")
    rice = Icon.iconOf("arris:cooked_rice").axis(10.0)
    along = math.degrees(-rice.along())
    x0, z0 = Motion.layerJitter(0)
    assert [(c[0], c[3]) for c in _cues(plan, Kit.SCALE, 0)] == [(0.0, (0.8, 0.14))]
    first = _cues(plan, Kit.MOVE, 0)[0]
    assert first[0] == 0.0 and first[3] == ((x0, 0.0, z0), 0.14, 0.3), "米饭压成块：缩 0.8、跳 0.3、0.14 秒"
    for index in range(1, 4):
        shift = (index - 1.5 - 0.5) * 0.8
        want = (x0 + rice.dirX * shift, 0.65 * 0.8 + (index - 1) * 0.15, z0 + rice.dirZ * shift)
        assert _close(plan.rest[index], want), index
        lay, press = _cues(plan, Kit.MOVE, index)
        assert abs(lay[0] - (0.14 + (index - 1) * 0.12)) < 1.0e-12 and lay[3] == (plan.rest[index], 0.12, 0.0)
        assert abs(press[0] - (0.14 + 3 * 0.12)) < 1.0e-12 and press[3] == (plan.rest[index], 0.1, -0.25), "最后各层往下压 0.25 再回来"
        turn, = _cues(plan, Kit.ROTATE, index)
        assert _close(turn[3][0], (0.0, along + 45.0, 0.0)) and turn[3][1] == 0.12
    assert _close(plan.rest[0], (x0, 0.0, z0))
    assert [(round(at, 9), n, v, round(p, 9)) for at, (n, v, p) in _sounds(plan)] == [
        (0.0, "step.cloth", 0.35, 1.1), (0.14, "dig.wood", 0.3, 1.35), (0.26, "dig.wood", 0.3, 1.4), (0.38, "dig.wood", 0.3, 1.45), (0.5, "step.cloth", 0.4, 0.9)]


# ---------------------------------------------------------------- 冻

def testFreezeTheFruitGathersAtTheTopOfTheStickTheIceIsGoneAndAFrostFliesUp():
    names = ["minecraft:stick", "minecraft:melon_slice", "minecraft:ice", "minecraft:melon_slice", "minecraft:packed_ice"]
    plan = Finish.plan(Assembly.FINISH_FREEZE, names, lambda name: COLOR)
    stick = Icon.iconOf("minecraft:stick").axis(10.0)
    top, base = stick.at(0.28), Motion.layerJitter(0)
    x, z = base[0] + top[0], base[1] + top[1]
    for index in range(1, 5):
        want = (x + ((index * 37) % 5 - 2) * 0.35, 0.65 + index * 0.12, z + ((index * 53) % 5 - 2) * 0.35)
        assert _close(plan.rest[index], want), index
        move, = _cues(plan, Kit.MOVE, index)
        assert move[0] == 0.0 and move[3] == (plan.rest[index], 0.2, 0.0)
        scale, = _cues(plan, Kit.SCALE, index)
        ice = names[index] in ("minecraft:ice", "minecraft:packed_ice")
        assert scale[3] == ((0.0, 0.35) if ice else (0.75, 0.2)), "冰缩没（0.2 + 0.15），别的缩到 0.75"
    dust, = _cues(plan, Kit.DUST)
    assert abs(dust[0] - 0.2) < 1.0e-12 and dust[3][1] == Kit.FROST
    (px, py, pz), velocity, spread, count = dust[3][0]
    assert _close((px, py, pz), (x, 1.0 + 2 * STEP, z)) and velocity == (0.0, 1.5, 0.0) and spread == 1.8 and count == 10
    glint, = _cues(plan, Kit.GLINT)
    assert abs(glint[0] - 0.2) < 1.0e-12 and _close(glint[3][0], (x, 1.0 + 2 * STEP, z)) and glint[3][1:] == (Kit.FROST, 4)
    assert _sounds(plan) == [(0.2, ("random.glass", 0.2, 1.8))], "玻璃碎了一声"


# ---------------------------------------------------------------- 一起切

def testChopTheKnifeGoesThroughTwiceAndTheHalvesPartAlternately():
    plan = _plan(Assembly.FINISH_CHOP, 4, rng=lambda: 0.5)
    for index in range(4):
        x, y, z = plan.rest[index]
        moves = _cues(plan, Kit.MOVE, index)
        assert [round(c[0], 9) for c in moves] == [0.0, 0.08, 0.16, 0.24], "每刀 0.16 秒：错开 0.064 秒，再回来 0.08 秒"
        for stroke in (0, 1):
            side = 1.0 if stroke == 0 else -1.0
            out = (side if index % 2 == 0 else -side) * 0.9
            apart, back = moves[stroke * 2], moves[stroke * 2 + 1]
            assert apart[3] == ((x + out, y, z), 0.16 * 0.4, 0.0) and back[3] == ((x, y, z), 0.16 * 0.5, 0.0), (index, stroke)
    dust = _cues(plan, Kit.DUST)
    assert [round(c[0], 9) for c in dust] == [0.0, 0.16] and all(c[3][1] == COLOR for c in dust), "每刀一阵最上面一层颜色的碎屑"
    for c in dust:
        assert _close(c[3][0][0], (0.0, 1.0 + 4 * STEP + 0.5, 0.0)) and c[3][0][1:] == ((0.0, 4.0, 0.0), 1.2, 5)
    assert _sounds(plan) == [(0.0, ("ambient.cutting_board.knife", 0.8, 0.95 + 0.15 * 0.5)), (0.16, ("ambient.cutting_board.knife", 0.8, 0.95 + 0.15 * 0.5))]
    top = []
    Finish.plan(Assembly.FINISH_CHOP, ["minecraft:bread", "arris:tomato", "arris:cabbage"], lambda name: top.append(name) or COLOR)
    assert top == ["arris:cabbage"], "颜色取最上面一层"


# ---------------------------------------------------------------- 旁观的人只要声音和粒子

def testTheEffectsAreOnlySoundsAndParticlesInTheOrderTheyHappen():
    for finish in KINDS:
        plan = _plan(finish, 4, base="minecraft:stick" if finish in ("skewer", "freeze") else "minecraft:bread")
        effects = plan.effects()
        assert all(cue[1] in (Kit.SOUND, Kit.DUST, Kit.GLINT) and cue[2] is None for cue in effects), finish
        assert [cue[0] for cue in effects] == sorted(cue[0] for cue in effects), finish
    assert _plan(Assembly.FINISH_PRESS, 4).effects() == []


def testTheOneSoundNamesTheFinishesNeedAreTheBedrockOnesAndKnownToTheBoardSounds():
    assert (Sounds.ARMOR_EQUIP_LEATHER, Sounds.WOOL_STEP, Sounds.GLASS_BREAK) == ("armor.equip_leather", "step.cloth", "random.glass")
    used = set(cue[3][0] for finish in KINDS for cue in _plan(finish, 4).effects() if cue[1] == Kit.SOUND)
    assert used == set(["armor.equip_leather", "dig.wood", "step.cloth", "hit.wood", "random.glass", "ambient.cutting_board.knife"])


def testTheVanillaDefinitionsOfTheNewSoundsCarryNoVolumeOrPitchOfTheirOwn():
    """引擎把调用的音量音调乘上采样自带的（Shared/Rules/SoundMix）：收尾用到的三条原版声音什么都不自带，JE 的数原样交给引擎，不用进 SoundMix.BUILT_IN。"""
    SoundMix = fdtest.load("Shared.Rules.SoundMix")
    if VANILLA is None:
        print("（本机没有原版资源包：没查）")
        return
    data = json.load(io.open(VANILLA, encoding="utf-8"))
    definitions = data.get("sound_definitions", data)
    for name in ("armor.equip_leather", "step.cloth", "random.glass"):
        samples = [sample if isinstance(sample, dict) else {"name": sample} for sample in definitions[name]["sounds"]]
        assert samples and all(sample.get("volume", 1.0) == 1.0 and sample.get("pitch", 1.0) == 1.0 for sample in samples), name
        assert name not in SoundMix.BUILT_IN
        assert SoundMix.engineArgs(name, 0.5, 1.4) == (0.5, 1.4)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
