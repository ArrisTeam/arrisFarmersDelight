# -*- coding: utf-8 -*-
# runner: both
"""砧板站点里刀口虚线怎么画（Compat/Diegesis/BoardCutter + BoardMarkLine，假引擎和假视图见 boardclient.py）：
- 虚线（HoD drawMarks / fade）：一段一颗粒子 arris:board_mark，白混凝土、半透明（0xA0）、半宽 0.16、每段 0.6 隔 0.45，新的一条 0.18 秒渐显；
- 粒子建不出来（进世界头几秒 Create 回 0）：这一帧用前置包的掉落物虚线（props.line），下一帧再试粒子，建出来就换掉。
朝向的数（SetRot 的偏航）照 Shared/Rules/ParticleQuad，这里用引擎知识库的朝向公式独立核一遍。
"""
from __future__ import print_function

import io
import json
import math
import os
import re

import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Marks = fdtest.load("Shared.Rules.HandsOn.BoardMarks")
Dashes = fdtest.load("Shared.Rules.HandsOn.BoardDashes")

KNIFE = "arris:iron_knife"
MARK = "arris:board_mark"


def _open(board=None, data=None, hand=None, yaw=0):
    behavior, view, api = C.station()
    view.yaw = yaw
    view.state.board, view.state.layers = board, []
    view.data, view.hand = dict(data or {}), hand
    behavior.onOpen()
    return behavior, view


def _data(**more):
    return dict({"plan": 1, "marks": 0, "style": "across", "spots": [0.5], "angles": [0.0], "stroke": "cut", "dish": ""}, **more)


def _frames(behavior, count=40, dt=1.0 / 60.0):
    for _ in range(count):
        behavior.frame(dt)


def _lineOf(index=0, spots=(0.5,), count=1, name="arris:cabbage"):
    icon = Marks.iconOf(name)
    return Marks.markOf(Marks.axisOf(icon), "across", list(spots), [0.0] * len(spots), index, count), icon


def _changed(behavior, view, board=False):
    behavior.onState(type("Changes", (), {"hasSlot": lambda self, ref: board})())


def _lines(view):
    return [prop for prop in view.props.live() if prop.line]


def _basis(yaw):
    """没绑定的发射器 SetRot((0, yaw, 0)) 得到 E = Ry(yaw)：E.x、E.y、E.z（引擎知识库 §5.3）。"""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c)


def _close(a, b, eps=1.0e-6):
    return abs(a - b) < eps


def _unit(dx, dz):
    length = math.hypot(dx, dz)
    return (dx / length, dz / length)


def _worldDirection(view, point, direction):
    """站点里从 point 出发的水平方向 (dx, dz) 在世界里朝哪（两点做差）。"""
    a, b = view.toWorld(*point), view.toWorld(point[0] + direction[0], point[1], point[2] + direction[1])
    return (b[0] - a[0], b[2] - a[2])


# ---------------------------------------------------------------- 虚线

def testTheDashedLineIsOneParticlePerJavaDashLyingAlongTheLineWhicheverSideTheStationIsOn():
    for yaw in (0, 90, 180, 270):
        behavior, view = _open(C.item("arris:cabbage", 2), _data(), yaw=yaw)
        C.engine.inventory[2] = C.item(KNIFE)
        _frames(behavior, 30)
        cut, icon = _lineOf()
        ends = Marks.dashOf(cut, icon)
        draw = behavior.draw
        a, b = (draw.cx + ends[0][0], draw.cz + ends[0][1]), (draw.cx + ends[1][0], draw.cz + ends[1][1])
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        ux, uz = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        height = draw.surface() + C.BoardMarkLine.MARK_LIFT
        want, found = Dashes.dashes(length), C.engine.liveParticles(MARK)
        assert len(found) == len(want) > 3 and not _lines(view), "每段一颗粒子，粒子建得出来：不用掉落物的虚线"
        world = _worldDirection(view, (a[0], height, a[1]), (ux, uz))
        for particle, (first, last) in zip(found, want):
            middle = (first + last) / 2.0
            here = view.toStation(*particle["pos"])
            assert _close(here[0], a[0] + ux * middle) and _close(here[2], a[1] + uz * middle) and _close(here[1], height), (yaw, first, here)
            assert particle["vars"]["variable.half_wide"] == round(0.16 / 16.0, 6) and _close(particle["vars"]["variable.half_len"], (last - first) / 2.0 / 16.0, 1e-6), \
                "半宽 0.16、半长这一段的一半（像素 / 16 = 格）"
            assert particle["rot"][0] == particle["rot"][2] == 0.0
            top = _basis(particle["rot"][1])[2]
            assert _close(-top[0], _unit(*world)[0]) and _close(-top[2], _unit(*world)[1]), "长的那条边（emitter_transform_xz 的上边 = -E.z）顺着线：%s" % (particle["rot"],)
            assert _close(particle["vars"]["variable.alpha"], 0xA0 / 255.0), "渐显完了：0xA0 / 255"
        behavior.onClose()


def testANewLineFadesInFromNothingLinearlyOverTheJavaFadeTime():
    behavior, view = _open(C.item("arris:cabbage", 2), _data())
    C.engine.inventory[2] = C.item(KNIFE)
    behavior.frame(0.045)
    dashes = C.engine.liveParticles(MARK)
    assert dashes and all(particle["vars"].get("variable.alpha", 0.0) == 0.0 for particle in dashes), "换了一条的那一帧还看不见（markFade = 0）"
    for step, byte in ((1, 40), (2, 80), (3, 120), (4, 160), (5, 160)):
        behavior.frame(0.045)
        assert all(_close(particle["vars"]["variable.alpha"], byte / 255.0) for particle in C.engine.liveParticles(MARK)), (step, byte)
    calls = [particle["calls"] for particle in C.engine.liveParticles(MARK)]
    _frames(behavior, 10)
    assert [particle["calls"] for particle in C.engine.liveParticles(MARK)] == calls, "渐显完了不再发任何东西"


def testTheNextCutReplacesTheLineAndTheNewOneFadesInAgain():
    data = _data(plan=2, spots=[0.3, 0.7], angles=[0.0, 0.0])
    behavior, view = _open(C.item("arris:cabbage", 2), data)
    C.engine.inventory[2] = C.item(KNIFE)
    _frames(behavior, 30)
    first = C.engine.liveParticles(MARK)
    assert first and all(_close(particle["vars"]["variable.alpha"], 0xA0 / 255.0) for particle in first)
    view.data = dict(data, marks=1)
    _changed(behavior, view)
    behavior.frame(0.02)
    second = C.engine.liveParticles(MARK)
    assert second and not [particle for particle in first if particle["alive"]], "上一条的每一段都收了"
    assert all(particle["vars"].get("variable.alpha", 0.0) == 0.0 for particle in second), "新的一条从透明起"
    cut, icon = _lineOf(1, (0.3, 0.7), 2)
    ends = Marks.dashOf(cut, icon)
    assert len(second) == len(Dashes.dashes(math.hypot(ends[1][0] - ends[0][0], ends[1][1] - ends[0][1]))), "第二刀的那一条"
    _frames(behavior, 30)
    assert all(_close(particle["vars"]["variable.alpha"], 0xA0 / 255.0) for particle in second)


def testTheLineGoesWhenTheToolIsPutAwayOrTheStationCloses():
    behavior, view = _open(C.item("arris:cabbage", 2), _data())
    C.engine.inventory[2] = C.item(KNIFE)
    _frames(behavior, 10)
    assert C.engine.liveParticles(MARK)
    C.engine.inventory[2] = None
    _frames(behavior, 3)
    assert not C.engine.liveParticles(MARK), "没有工具：不显示线"
    C.engine.inventory[2] = C.item(KNIFE)
    _frames(behavior, 3)
    assert C.engine.liveParticles(MARK)
    behavior.onClose()
    assert not C.engine.liveParticles() and not view.props.live(), "关站：粒子和道具都收了"


def testTheLineMovesWithTheFoodHeightWhenThePileChanges():
    """JE 的 key 里有 itemHeight：一件变一叠（顶面抬高 0.65）线要重画到新的高度。"""
    behavior, view = _open(C.item("arris:cabbage", 1), _data())
    C.engine.inventory[2] = C.item(KNIFE)
    _frames(behavior, 10)
    low = C.engine.liveParticles(MARK)
    heights = set(round(view.toStation(*particle["pos"])[1], 3) for particle in low)
    view.state.board = C.item("arris:cabbage", 5)
    _changed(behavior, view, True)
    _frames(behavior, 10)
    high = C.engine.liveParticles(MARK)
    assert high and not [particle for particle in low if particle["alive"]]
    assert set(round(view.toStation(*particle["pos"])[1], 3) for particle in high) != heights, "一叠的顶面高一些"


def testWithoutParticlesTheOldDroppedItemLineShowsAndTheParticlesTakeOverOnceTheyCanBeMade():
    behavior, view = _open(C.item("arris:cabbage", 2), _data())
    C.engine.inventory[2] = C.item(KNIFE)
    C.engine.particlesReady = False
    _frames(behavior, 5)
    assert not C.engine.liveParticles() and len(_lines(view)) == 1, "进世界头几秒粒子系统没好（Create 回 0）：这一帧用前置包的掉落物虚线"
    C.engine.particlesReady = True
    behavior.frame(0.02)
    assert len(C.engine.liveParticles(MARK)) > 3 and not _lines(view), "下一帧再试，建出来就把掉落物的虚线换掉"
    behavior.onClose()
    assert not C.engine.liveParticles() and not view.props.live()


def testALineThatCannotBeMadeWholeIsNotLeftHalfMade():
    behavior, view = _open(C.item("arris:cabbage", 2), _data())
    C.engine.inventory[2] = C.item(KNIFE)
    real, calls = C.engine.Create, []

    def flaky(identifier, pos, rot=(0.0, 0.0, 0.0)):
        calls.append(identifier)
        return 0 if len(calls) == 3 else real(identifier, pos, rot)

    C.engine.Create = flaky
    try:
        behavior.frame(0.02)
        assert not C.engine.liveParticles() and len(C.engine.particles) == 2 and len(_lines(view)) == 1, "第三颗建不出来：前两颗收掉，整条先用掉落物"
        behavior.frame(0.02)
    finally:
        del C.engine.Create
    assert len(C.engine.liveParticles(MARK)) > 3 and not _lines(view)


# ---------------------------------------------------------------- 脚本发的变量和粒子定义对得上

def _definition(name):
    path = os.path.join(fdtest.ROOT, "rp", "particles", name)
    with io.open(path, encoding="utf-8") as handle:
        effect = json.loads(handle.read())["particle_effect"]
    declared = set(re.findall(r"variable\.(\w+)\s*=", effect["components"]["minecraft:emitter_initialization"]["creation_expression"]))
    return effect["description"]["identifier"], declared


def testEveryVariableTheScriptSendsIsDeclaredByTheParticleDefinition():
    behavior, view = _open(C.item("arris:cabbage", 2), _data())
    C.engine.inventory[2] = C.item(KNIFE)
    _frames(behavior, 30)
    name, declared = _definition("arris_board_mark.json")
    found = C.engine.liveParticles(MARK)
    assert name == MARK and found
    for particle in found:
        assert set(key.split(".", 1)[1] for key in particle["vars"]) == declared, sorted(particle["vars"])


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
