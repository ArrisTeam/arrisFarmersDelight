# -*- coding: utf-8 -*-
# runner: both
"""砧板的碎屑（Shared/Rules/BoardDust.py、Compat/Diegesis/BoardFx、rp/particles/arris_board_dust.json）：每种工具各自的起点、初速、散布、个数照 HoD 的 chopped（1410-1421）、
方块切到底炸开（1474）、做成时的面粉 / 霜；站点里的人和旁观的人按同一份飞，起点和初速是操作者那边的站点像素、按他的朝向转到世界。
"""
from __future__ import print_function

import io
import json
import re
import os

import dgtest  # noqa: F401 - 把 diegesisBp 放进 sys.path（boardclient 要它的 Geometry / Schema）
import boardclient as C
import fdtest

Dust = fdtest.load("Shared.Rules.BoardDust")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
Scene = fdtest.load("Shared.Rules.HandsOn.BoardScene")
KNIFE = "arris:iron_knife"
POS = C.STATION_POS


def _near(a, b):
    return all(abs(x - y) < 1.0e-6 for x, y in zip(a, b)) and len(a) == len(b)


def testEveryToolHasItsOwnVelocitySpreadAndCountLikeJava():
    expect = {Cutting.TOOL_CUT: ((0, 4, 0), 1.2, 4), Cutting.TOOL_CHOP: ((0, 5, 0), 1.6, 7), Cutting.TOOL_STRIP: ((0, 1, -3), 2.0, 12),
              Cutting.TOOL_SMASH: ((0, 6, 0), 2.2, 10), Cutting.TOOL_DIG: ((0, 5, -3), 1.6, 9), Cutting.TOOL_PRY: ((0, 3, -1), 1.0, 4),
              Cutting.TOOL_SNIP: ((0, 2, 0), 0.8, 3)}
    for stroke, (velocity, spread, count) in expect.items():
        _at, got, gotSpread, gotCount = Dust.strokePuff(stroke, False, 6.0, 7.0, 6.5, 8.0)
        assert _near(got, velocity) and gotSpread == spread and gotCount == count, stroke
    assert Dust.strokePuff("nonsense", False, 6.0, 7.0, 6.5, 8.0)[3] == 4, "认不出的当刀"


def testTheDustStartsOverTheFoodWhereTheKnifeWentInExceptBarkAndShovelfuls():
    top = Scene.TOP + 10.0 / 16.0
    assert _near(Dust.strokePuff(Cutting.TOOL_CUT, False, 6.0, 7.0, 6.5, 8.0)[0], (6.0, top, 7.0)), "平躺的图标：板面 + ITEM_SIZE / 16"
    assert _near(Dust.strokePuff(Cutting.TOOL_SMASH, True, 6.0, 7.0, 6.5, 8.0)[0], (6.0, Scene.TOP + Dust.BLOCK_SIZE, 7.0)), "方块：板面 + 它的边长"
    assert _near(Dust.strokePuff(Cutting.TOOL_STRIP, True, 6.0, 7.0, 6.5, 8.0)[0], (6.0, Scene.TOP + Dust.BLOCK_SIZE * 0.35, 7.0)), "树皮从原木近侧"
    assert _near(Dust.strokePuff(Cutting.TOOL_DIG, True, 6.0, 7.0, 6.5, 8.0)[0], (6.0, Scene.TOP + Dust.BLOCK_SIZE * 0.6, 8.0 - Dust.BLOCK_SIZE / 2.0)), "铲从方块近侧"


def testABlockWorkedToTheEndBurstsAtItsMiddleAndTheDishPopsFlourOrFrost():
    at, velocity, spread, count = Dust.blockDonePuff(Cutting.TOOL_SMASH, 6.5, 8.0)
    assert _near(at, (6.5, Scene.TOP + Dust.BLOCK_SIZE / 2.0, 8.0)) and _near(velocity, (0, 5, 0)) and spread == 3.0 and count == 18
    assert Dust.blockDonePuff(Cutting.TOOL_DIG, 6.5, 8.0)[3] == 14, "铲的少几颗"
    at, velocity, spread, count = Dust.flourPuff(6.5, 8.0)
    assert _near(at, (6.5, Scene.TOP + 1.0, 8.0)) and _near(velocity, (0, 3, 0)) and spread == 2.5 and count == 12
    assert _near(Dust.flourPuff(6.5, 8.0, frost=True)[1], (0, 2, 0)), "冰棒是霜：初速 (0, 2, 0)"


def testTheOwnParticleFileMatchesWhatTheScriptSetsAndIsValidJson():
    path = os.path.join(fdtest.ROOT, "rp", "particles", "arris_board_dust.json")
    text = io.open(path, encoding="utf-8").read()
    effect = json.loads(text)["particle_effect"]
    assert effect["description"]["identifier"] == C.BoardFx.OWN_DUST == "arris:board_dust"
    creation = effect["components"]["minecraft:emitter_initialization"]["creation_expression"]
    defined = set(re.findall(r"variable\.(\w+)\s*=", creation))
    for name in ("tint_set", "tint_r", "tint_g", "tint_b", "count", "vx", "vy", "vz", "spread"):
        assert name in defined, "脚本会 SetVariable 的变量要在粒子的创建表达式里有缺省：%s" % name
    used = set(re.findall(r"variable\.(\w+)", text)) - set(["particle_random_1"])
    assert used <= defined, "粒子里用到的变量都要有缺省：%r" % sorted(used - defined)
    components = effect["components"]
    assert "minecraft:emitter_shape_box" in components and components["minecraft:particle_motion_dynamic"]["linear_drag_coefficient"] == 3.0
    assert effect["description"]["basic_render_parameters"]["texture"] == "textures/particle/particles"


def testOwnDustIsPlacedWithColourCountAndVelocityVariables():
    C.engine.reset()
    pid = C.BoardFx.dust((1.5, 2.5, 3.5), (0.0, 0.25, -0.1), 0.075, 4, 0xFF8040)
    assert pid == 1
    particle = C.engine.particles[0]
    assert particle["id"] == "arris:board_dust" and particle["pos"] == (1.5, 2.5, 3.5)
    variables = particle["vars"]
    assert abs(variables["variable.tint_r"] - 1.0) < 1e-9 and abs(variables["variable.tint_g"] - 0x80 / 255.0) < 1e-9 and abs(variables["variable.tint_b"] - 0x40 / 255.0) < 1e-9
    assert variables["variable.tint_set"] == 1.0 and variables["variable.count"] == 4.0
    assert (variables["variable.vx"], variables["variable.vy"], variables["variable.vz"], variables["variable.spread"]) == (0.0, 0.25, -0.1, 0.075)


def _look(**data):
    return dict(data, dimensionId=0, pos=list(POS), event="chopped")


def testTheOnlookersDustIsTheSameAsTheCooksAtTheSamePlace():
    behavior, view = _open_view()
    behavior.onEffect("chopped", dict(_chop(), stroke="smash", block=True, tool="minecraft:iron_pickaxe", item="minecraft:stone"))
    cook = list(C.engine.particles)
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    C.BoardWatch.OnBoardLook(_look(**dict(_chop(), stroke="smash", block=True, tool="minecraft:iron_pickaxe", item="minecraft:stone")))
    assert len(C.engine.particles) == len(cook) == 1
    assert C.engine.particles[0]["vars"] == cook[0]["vars"] and _near(C.engine.particles[0]["pos"], cook[0]["pos"])


def _chop(**extra):
    return dict({"at": 8.0, "at_x": 6.5, "yaw": 0, "tool": KNIFE, "item": "arris:cabbage"}, **extra)


def _open_view():
    behavior, view, api = C.station()
    view.state.board = C.item("arris:cabbage", 2)
    view.data = {"plan": 1, "marks": 0, "style": "across", "spots": [0.5], "angles": [0.0], "stroke": "cut", "dish": ""}
    behavior.onOpen()
    C.engine.particles[:] = []
    return behavior, view


def testTheLastStrokeOnABlockBurstsAtItsMiddleButABarkStripRisesInstead():
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    stone = dict(_chop(), stroke="smash", block=True, tool="minecraft:iron_pickaxe", item="minecraft:stone", yields=["minecraft:cobblestone"])
    C.BoardWatch.OnBoardLook(_look(**stone))
    assert len(C.engine.particles) == 1, "不是最后一刀：只有这一刀的碎屑"
    C.engine.reset()
    C.BoardWatch.OnBoardLook(_look(**dict(stone, done=True, count=3)))
    assert [p["vars"]["variable.count"] for p in C.engine.particles] == [10.0, 18.0], "最后一刀：镐的 10 颗，再在方块中心炸 18 颗"
    burst = C.engine.particles[1]
    cx, _, cz = C.BoardFx.centerOf(POS)
    assert _near(burst["pos"], (cx, POS[1] + (Scene.TOP + Dust.BLOCK_SIZE / 2.0) / 16.0, cz)), "在方块中心（板面中心、高度是方块一半）炸开"
    assert burst["vars"]["variable.vy"] == 5.0 / 16.0 and abs(burst["vars"]["variable.spread"] - 3.0 / 16.0) < 1e-9
    C.engine.reset()
    strip = dict(_chop(), stroke="strip", block=True, tool="minecraft:iron_axe", item="minecraft:oak_log", yields=["minecraft:stripped_oak_log"], done=True)
    C.BoardWatch.OnBoardLook(_look(**strip))
    assert [p["vars"]["variable.count"] for p in C.engine.particles] == [12.0], "削皮切出了东西：去皮原木往上升，不炸开"
    C.engine.reset()
    C.BoardWatch.OnBoardLook(_look(**dict(strip, tool="minecraft:iron_shovel", stroke="dig", item="minecraft:gravel", yields=["minecraft:gravel"])))
    assert [p["vars"]["variable.count"] for p in C.engine.particles] == [9.0, 14.0], "铲：9 颗，炸开 14 颗"


def testAnOnlookerSeesFlourWhenADishIsAssembledAndFrostForAnIceLolly():
    C.engine.reset()
    C.BoardWatch.enable(C.Geometry)
    C.BoardWatch.OnBoardLook(dict(_look(finish="sandwich", block=False), event="assembled"))
    flour = C.engine.particles[0]["vars"]
    assert flour["variable.count"] == 12.0 and flour["variable.vy"] == 3.0 / 16.0
    assert abs(flour["variable.tint_r"] - 0xED / 255.0) < 1e-9
    C.engine.reset()
    C.BoardWatch.OnBoardLook(dict(_look(finish="freeze", block=False), event="assembled"))
    frost = C.engine.particles[0]["vars"]
    assert frost["variable.vy"] == 2.0 / 16.0 and abs(frost["variable.tint_b"] - 1.0) < 1e-9, "霜：更白更轻"


def testWithoutTheGeometryAnOnlookerHearsButSeesNothingAndTheSwitchFallsBackToTheKernelsDust():
    C.engine.reset()
    C.BoardWatch.enable()
    C.BoardWatch.OnBoardLook(_look(**_chop()))
    assert C.engine.played and C.engine.particles == [], "没拿到前置包的 Geometry：碎屑没法换算，声音照放"
    C.BoardWatch.enable(C.Geometry)
    C.BoardFx.USE_OWN_DUST = False
    try:
        behavior, view = _open_view()
        behavior.onEffect("chopped", _chop())
        assert C.engine.particles == [] and len(view.dust) == 1 and view.dust[0][0] == "arris_diegesis:dust" and view.dust[0][3] == 4, "退路：前置包自带的碎屑"
        C.BoardWatch.OnBoardLook(_look(**_chop()))
        assert C.engine.particles == [], "旁观的人没有站点视图：退路下没有碎屑"
    finally:
        C.BoardFx.USE_OWN_DUST = True


def testADustTheEngineDidNotMakeIsNotTouched():
    """进世界头几秒粒子系统还没好、或者没有这个粒子：Create 回 0（不是 None）——不能拿 0 当编号去设变量。"""
    C.engine.reset()
    touched = []
    C.engine.Create = lambda identifier, pos: 0
    C.engine.SetVariable = lambda *args: touched.append(args)
    try:
        assert C.BoardFx.dust((1.5, 2.5, 3.5), (0.0, 0.25, -0.1), 0.075, 4, 0xFF8040) is None
    finally:
        del C.engine.Create, C.engine.SetVariable
    assert touched == [] and C.engine.particles == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
