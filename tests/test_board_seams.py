# -*- coding: utf-8 -*-
# runner: both
"""砧板站点里切过的那几刀留下的缝（Compat/Diegesis/BoardSeams + Shared/Rules/HandsOn 的 BoardDashes.GAP / gapAfter、BoardMarks.cutsMade，假引擎见 boardclient.py）。

JE（HoD）：BoardBehavior.cutsMade（729-737）给出已经切过的几刀（服务端说的 + 本地刚落的），ItemVoxels.build（305-345）把图标的像素沿每一刀的法线
往两边各挪 gap / 2；新切一刀（同一件东西、刀数变多）gap 归 0、用 GAP_TIME 0.12 秒张到 GAP 0.8 像素（refresh 412-416、frame 790-793）。
这里板上的东西切不开：每条切过的线上压一条 gap 宽的黑色半透明细条（粒子 arris:board_seam），只在图标的实心像素那一段。
"""
from __future__ import print_function

import io
import json
import math
import os

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Marks = fdtest.load("Shared.Rules.HandsOn.BoardMarks")
Dashes = fdtest.load("Shared.Rules.HandsOn.BoardDashes")
Seams = fdtest.load("Compat.Diegesis.BoardSeams")

SEAM, MARK = "arris:board_seam", "arris:board_mark"
FOOD = "arris:cabbage"
SPOTS, ANGLES = [0.3, 0.7], [0.0, 0.0]
DT = 1.0 / 60.0


def _open(board=None, data=None, hand=None, yaw=0):
    behavior, view, _api = C.station()
    view.yaw = yaw
    view.state.board, view.state.layers = board, []
    view.data, view.hand = dict(data or {}), hand
    behavior.onOpen()
    return behavior, view


def _data(**more):
    return dict({"plan": 2, "marks": 0, "style": "across", "spots": list(SPOTS), "angles": list(ANGLES), "stroke": "cut", "dish": ""}, **more)


def _frames(behavior, count=1, dt=DT):
    for _ in range(count):
        behavior.frame(dt)


def _said(behavior, view, board=False, **data):
    """服务端的状态来了：data 里的键换成新值。"""
    view.data.update(data)
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: board})())


def _seams():
    return C.engine.liveParticles(SEAM)


def _close(a, b, eps=1.0e-6):
    return abs(a - b) < eps


def _basis(yaw):
    """没绑定的发射器 SetRot((0, yaw, 0)) 得到 E = Ry(yaw)：E.x、E.y、E.z（引擎知识库 PARTICLE_ENGINE §5.3）。"""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c)


def _cutOf(index, name=FOOD):
    icon = Marks.iconOf(name)
    return Marks.markOf(Marks.axisOf(icon), "across", SPOTS, ANGLES, index, 2), icon


# ---------------------------------------------------------------- 规则

def testTheGapIsJavasAndOpensLinearlyInJavasTime():
    assert (Dashes.GAP, Dashes.GAP_TIME) == (0.8, 0.12), "BoardBehavior.java:65-66"
    assert Dashes.gapAfter(0.0, 0.06) == 0.4 and Dashes.gapAfter(0.0, 0.12) == 0.8 and Dashes.gapAfter(0.5, 1.0) == 0.8, "每秒 GAP / GAP_TIME，到 GAP 为止（:791）"
    assert 0.0 < Dashes.SEAM_ALPHA < 1.0


def testTheCutsMadeAreTheFirstMarksAndNeverMoreThanThePlan():
    icon = Marks.iconOf(FOOD)
    axis = Marks.axisOf(icon)
    assert Marks.cutsMade(axis, "across", SPOTS, ANGLES, 0, 2) == []
    for made, want in ((1, 1), (2, 2), (5, 2), (-1, 0)):
        found = Marks.cutsMade(axis, "across", SPOTS, ANGLES, made, 2)
        assert len(found) == want
        for index, cut in enumerate(found):
            same = Marks.markOf(axis, "across", SPOTS, ANGLES, index, 2)
            assert (cut.x, cut.z, cut.angle) == (same.x, same.z, same.angle), "第 index 刀就是虚线画的那一条"


# ---------------------------------------------------------------- 站点里

def testNothingIsDrawnBeforeTheFirstCut():
    behavior, _view = _open(C.item(FOOD, 1), _data())
    _frames(behavior, 5)
    assert _seams() == []
    behavior.onClose()


def testACutLeavesOneStripAlongItOverTheSolidPartOfTheIconWhicheverSideTheStationIsOn():
    for yaw in (0, 90, 180, 270):
        behavior, view = _open(C.item(FOOD, 1), _data(), yaw=yaw)
        _frames(behavior, 2)
        _said(behavior, view, marks=1)
        _frames(behavior, 30)
        found = _seams()
        assert len(found) == 1, (yaw, len(found))
        cut, icon = _cutOf(0)
        ends = Marks.ends(cut, icon)
        draw = behavior.draw
        a, b = (draw.cx + ends[0][0], draw.cz + ends[0][1]), (draw.cx + ends[1][0], draw.cz + ends[1][1])
        here = view.toStation(*found[0]["pos"])
        assert _close(here[0], (a[0] + b[0]) / 2.0) and _close(here[2], (a[1] + b[1]) / 2.0), "粒子在这一刀的实心那一段的正中"
        assert _close(here[1], draw.surface() + Seams.SEAM_LIFT), "压在食物顶面上方"
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        assert length > 1.0 and _close(found[0]["vars"]["variable.half_len"], length / 2.0 / 16.0), "半长是这一段的一半（像素 / 16 = 格）"
        assert _close(found[0]["vars"]["variable.half_wide"], 0.4 / 16.0), "张开完了：整宽 GAP 0.8 像素"
        assert found[0]["vars"]["variable.alpha"] == Dashes.SEAM_ALPHA
        wa, wb = view.toWorld(a[0], 0.0, a[1]), view.toWorld(b[0], 0.0, b[1])
        along = (wb[0] - wa[0], wb[2] - wa[2])
        top = _basis(found[0]["rot"][1])[2]
        unit = math.hypot(*along)
        assert found[0]["rot"][0] == found[0]["rot"][2] == 0.0
        assert _close(-top[0], along[0] / unit) and _close(-top[2], along[1] / unit), "长的那条边（emitter_transform_xz 的上边 = -E.z）顺着刀口"
        behavior.onClose()
        assert _seams() == [], "关站：缝收掉"


def testANewCutOpensFromNothingInJavasTimeAndEveryEarlierSeamOpensAgainWithIt():
    behavior, view = _open(C.item(FOOD, 1), _data())
    _frames(behavior, 2)
    _said(behavior, view, marks=1)
    behavior.frame(DT)
    assert [p["vars"]["variable.half_wide"] for p in _seams()] == [0.0], "切下去的那一帧缝还是合着的（refresh 里 gap = 0）"
    behavior.frame(0.06)
    assert _close(_seams()[0]["vars"]["variable.half_wide"], 0.2 / 16.0), "0.06 秒张开一半"
    behavior.frame(0.06)
    behavior.frame(DT)
    assert _close(_seams()[0]["vars"]["variable.half_wide"], 0.4 / 16.0), "0.12 秒张完，之后不再变"
    _said(behavior, view, marks=2)
    behavior.frame(DT)
    assert [p["vars"]["variable.half_wide"] for p in _seams()] == [0.0, 0.0], "又切一刀：两条缝都从 0 重新张开（JE 的 gap 只有一个数）"
    _frames(behavior, 20)
    assert all(_close(p["vars"]["variable.half_wide"], 0.4 / 16.0) for p in _seams()) and len(_seams()) == 2
    middles = sorted(view.toStation(*p["pos"])[0] for p in _seams())
    assert middles[1] - middles[0] > 1.0, "两条缝在两条不同的线上"
    behavior.onClose()


def testTheLocalChopShowsItsSeamBeforeTheServerAnswersAndLosesItWhenTheAnswerNeverComes():
    behavior, view = _open(C.item(FOOD, 1), _data())
    _frames(behavior, 2)
    behavior.cutter.pending.add(behavior.cutter.clock)
    behavior.frame(DT)
    assert len(_seams()) == 1, "本地刚落的一刀算切过（cutsMade 的 MARKS + pendingChops）"
    _said(behavior, view, marks=1)
    _frames(behavior, 3)
    assert len(_seams()) == 1 and behavior.cutter.pending.count == 0, "服务端回话了：还是这一条，不重画成两条"
    behavior.cutter.pending.add(behavior.cutter.clock)
    behavior.frame(DT)
    assert len(_seams()) == 2
    behavior.cutter.pending.reset()
    behavior.frame(DT)
    found = _seams()
    assert len(found) == 1 and _close(found[0]["vars"]["variable.half_wide"], 0.4 / 16.0), "等着的那一刀作废：少一条，剩下的直接是张开的（刀数没变多不从 0 起）"
    behavior.onClose()


def testOpeningTheStationOnFoodAlreadyCutShowsItsSeamsOpenAtOnce():
    behavior, _view = _open(C.item(FOOD, 1), _data(marks=1))
    behavior.frame(DT)
    found = _seams()
    assert len(found) == 1 and _close(found[0]["vars"]["variable.half_wide"], 0.4 / 16.0), "开站时板上已经切过的：不演张开"
    behavior.onClose()


def testTheSeamsGoWhenTheFoodDoes():
    behavior, view = _open(C.item(FOOD, 1), _data(marks=1))
    behavior.frame(DT)
    assert len(_seams()) == 1
    view.state.board = None
    _said(behavior, view, board=True, plan=0, marks=0)
    behavior.frame(DT)
    assert _seams() == [], "切完 / 取走：缝跟着没了"
    behavior.onClose()


def testBlocksCarvedToolsLayersAndThingsWithNoPlanHaveNoSeams():
    behavior, _view = _open(C.item("minecraft:oak_log", 1), _data(marks=1, stroke="strip"))
    _frames(behavior, 3)
    assert _seams() == [], "方块类：JE 里不是体素图标，没有缝"
    behavior.onClose()
    behavior, _view = _open(C.item(FOOD, 1), _data(plan=0, marks=0))
    _frames(behavior, 3)
    assert _seams() == [], "不用切的东西"
    behavior.onClose()
    behavior, view = _open(C.item(FOOD, 1), _data(marks=1))
    view.state.layers = [C.item("minecraft:bread")]
    _frames(behavior, 3)
    assert _seams() == [], "摆着层的板"
    behavior.onClose()


def testWhileTheParticleSystemIsNotReadyNothingBreaksAndTheSeamComesAsSoonAsItIs():
    behavior, _view = _open(C.item(FOOD, 1), _data(marks=1))
    C.engine.particlesReady = False
    _frames(behavior, 3)
    assert _seams() == []
    C.engine.particlesReady = True
    behavior.frame(DT)
    assert len(_seams()) == 1
    behavior.onClose()


def testTheSeamLiesUnderTheDashedLineAndHighEnoughToShow():
    assert 0.35 <= Seams.SEAM_LIFT < C.BoardMarkLine.MARK_LIFT, "零厚度的四边形从 +0.35 起才露出来（实机量的）；比虚线低，交叉的地方不闪"


def testTheSeamParticleIsAFlatBlackTranslucentQuadSizedAndFadedByTheScript():
    with io.open(os.path.join(fdtest.ROOT, "rp", "particles", "arris_board_seam.json"), encoding="utf-8-sig") as handle:
        effect = json.load(handle)["particle_effect"]
    assert effect["description"]["identifier"] == SEAM
    assert effect["description"]["basic_render_parameters"]["material"] == "particles_blend"
    components = effect["components"]
    board = components["minecraft:particle_appearance_billboard"]
    assert board["facing_camera_mode"] == "emitter_transform_xz" and board["size"] == ["variable.half_wide", "variable.half_len"]
    assert components["minecraft:particle_appearance_tinting"]["color"] == [0, 0, 0, "variable.alpha"], "黑色，不透明度由脚本给"
    assert components["minecraft:emitter_rate_instant"]["num_particles"] == 1 and "minecraft:particle_motion_dynamic" not in components, "一条缝一颗、不动"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
