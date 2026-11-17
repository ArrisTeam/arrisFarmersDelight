# -*- coding: utf-8 -*-
# runner: both
"""砧板刀口虚线和借来的工具的样子（Shared/Rules/HandsOn/BoardDashes.py、Shared/Rules/ParticleQuad.py、rp/particles 里的两个粒子定义和那张贴图）：
每一段多长、多宽、多不透明、渐显多久照 HoD 的 BoardBehavior（81-85、178、203、1181-1182、1206-1208）；
粒子四边形怎么转照引擎知识库的朝向公式（PARTICLE_ENGINE §5.3 / §5.4），平躺那一支 2026-11-17 实机核对过：不转时上边朝 -z、右边朝 +x，
SetRot((0, ψ, 0)) 把上边转到 (-sin ψ, -cos ψ)、右边转到 (cos ψ, -sin ψ)。
"""
from __future__ import print_function

import io
import json
import math
import os
import re

import fdtest
import pngkit

Dashes = fdtest.load("Shared.Rules.HandsOn.BoardDashes")
Quad = fdtest.load("Shared.Rules.ParticleQuad")

PARTICLES = os.path.join(fdtest.ROOT, "rp", "particles")
TEXTURES = os.path.join(fdtest.ROOT, "rp", "textures", "particle")


def _close(a, b, eps=1.0e-9):
    return abs(a - b) < eps


def _same(a, b, eps=1.0e-9):
    return all(_close(x, y, eps) for x, y in zip(a, b)) and len(a) == len(b)


def _unit(dx, dz):
    length = math.hypot(dx, dz)
    return (dx / length, 0.0, dz / length)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _basis(yaw):
    """没绑定的发射器 SetRot((0, yaw, 0)) 得到 E = Ry(yaw)：三列 E.x、E.y、E.z（知识库 §5.3）。"""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c)


def _flat(yaw):
    """emitter_transform_xz（知识库 §5.4）：右 = E.x、上 = -E.z。"""
    ex, _ey, ez = _basis(yaw)
    return ex, tuple(-value for value in ez)


def _upright(yaw):
    """emitter_transform_xy：右 = E.x、上 = E.y、正面（法线）= E.z。"""
    return _basis(yaw)


# ---------------------------------------------------------------- 虚线：每一段、渐显

def testTheConstantsAreTheJavaOnes():
    assert (Dashes.MARK_WIDTH, Dashes.DASH, Dashes.DASH_GAP) == (0.16, 0.6, 0.45), "BoardBehavior:81-83：半宽 0.16（整宽 0.32）、段 0.6、隔 0.45"
    assert Dashes.MARK_ALPHA == 0xA0 and Dashes.MARK_FADE == 0.18 and Dashes.OFFERED_ALPHA == 0x8C, "MARK_COLOR 0xA0FFFFFF、MARK_FADE 0.18、OFFERED 0x8CFFFFFF"


def testADashedLineIsEveryDashPlusGapAndTheLastDashIsCutAtTheEndWhateverItsLength():
    assert Dashes.dashes(0.6) == [(0.0, 0.6)]
    for length in (0.3, 0.6, 1.0, 1.2, 3.3, 7.35, 14.14):
        found = Dashes.dashes(length)
        assert found[0][0] == 0.0 and found[-1][1] == min(length, found[-1][0] + 0.6), length
        assert all(0.0 <= first < last <= length for first, last in found), "每段都落在线上、起点在线尾之前（t < 线尾）"
        assert all(_close(last - first, 0.6) for first, last in found[:-1]) and all(_close(second[0] - first[0], 1.05) for first, second in zip(found, found[1:])), \
            "段与段每 DASH + DASH_GAP 一个，只有最后一段可能被线尾截短"
    long = Dashes.dashes(10.0)
    assert len(long) == 10 and long[0] == (0.0, 0.6) and _close(long[1][0], 1.05) and _close(long[-1][0], 9.45) and long[-1][1] == 10.0, long
    assert all(_close(last - first, 0.6) for first, last in long[:-1]), "中间的段都是 0.6"
    sliver = Dashes.dashes(1.2)
    assert len(sliver) == 2 and _close(sliver[1][0], 1.05) and sliver[1][1] == 1.2 and _close(sliver[1][1] - sliver[1][0], 0.15), "末尾不足一段的截短、再短也画（HoD 没有最短一段）"
    assert Dashes.dashes(0.0) == [], "没有长度没有线"


def testANewLineFadesInLinearlyToTheJavaAlphaByteInOneEighteenthOfASecond():
    assert Dashes.markAlpha(0.0) == 0.0
    assert Dashes.markAlpha(0.045) == 40 / 255.0 and Dashes.markAlpha(0.09) == 80 / 255.0, "每过 0.045 秒长 40 / 255"
    assert Dashes.markAlpha(0.18) == 0xA0 / 255.0 and Dashes.markAlpha(0.18) == Dashes.markAlpha(30.0), "0.18 秒到 0xA0 / 255 = 0.627，不再长"
    assert Dashes.markAlpha(-1.0) == 0.0
    assert Dashes.markAlpha(0.18 * 0.003) == 0.0 and Dashes.markAlpha(0.18 * 0.004) == 1 / 255.0, "Math.round：160 x 0.48 -> 0、160 x 0.64 -> 1"
    ages = [i * 0.01 for i in range(40)]
    assert [Dashes.markAlpha(age) for age in ages] == sorted(Dashes.markAlpha(age) for age in ages)


def testAToolOfferedFromTheBagIsHalfSeeThroughUntilItStrikes():
    assert Dashes.offeredAlpha(False) == 0x8C / 255.0 and abs(Dashes.offeredAlpha(False) - 0.549) < 1e-3
    assert Dashes.offeredAlpha(True) == 1.0, "落下去那一下变实"


# ---------------------------------------------------------------- 粒子四边形怎么转

def testAFlatQuadIsTurnedSoItsTopRunsAlongTheWantedDirection():
    assert _same(_flat(0.0)[0], (1.0, 0.0, 0.0)) and _same(_flat(0.0)[1], (0.0, 0.0, -1.0)), "实机：不转时右边朝 +x、上边朝 -z"
    for dx, dz in ((0.0, -1.0), (0.0, 1.0), (1.0, 0.0), (-1.0, 0.0), (0.3, -0.8), (-2.0, 0.5), (1.7, 1.7)):
        yaw = Quad.flatYaw(dx, dz)
        right, top = _flat(yaw)
        assert _same(top, _unit(dx, dz), 1e-9), (dx, dz, yaw, top)
        assert _same(_cross(right, top), (0.0, 1.0, 0.0)), "右 x 上 = 朝上：从上往下看图标不镜像"
    yaw = 37.0
    right, top = _flat(yaw)
    assert _same(top, (-math.sin(math.radians(yaw)), 0.0, -math.cos(math.radians(yaw)))), "实机：转 ψ 后上边朝 (-sin ψ, -cos ψ)"
    assert _same(right, (math.cos(math.radians(yaw)), 0.0, -math.sin(math.radians(yaw)))), "右边朝 (cos ψ, -sin ψ)"
    assert _close(Quad.flatYaw(0.0, -1.0), 0.0) and _close(abs(Quad.flatYaw(0.0, 1.0)), 180.0), "朝 -z 不用转、朝 +z 转半圈"


def testAnUprightQuadFacesTheWantedWayAndShowsItsIconTheRightWayRoundToWhoeverLooksAtIt():
    """正面朝 (dx, dz) 的竖立图标，从正面看（看的人在正面一侧、朝 -正面 方向看、头朝上）：右边就是看的人的右手边，图标不镜像。"""
    for dx, dz in ((0.0, -1.0), (0.0, 1.0), (1.0, 0.0), (-1.0, 0.0), (0.4, -0.9), (-0.7, -0.2), (1.1, 0.9)):
        yaw = Quad.uprightYaw(dx, dz)
        right, up, front = _upright(yaw)
        assert _same(front, _unit(dx, dz), 1e-9), (dx, dz, yaw, front)
        assert _same(up, (0.0, 1.0, 0.0))
        viewersRight = _cross(tuple(-value for value in front), up)
        assert _same(right, viewersRight, 1e-9), (dx, dz, right, viewersRight)
    assert _close(abs(Quad.uprightYaw(0.0, -1.0)), 180.0), "站点里镜头在 -z 一侧：正面朝 -z（朝镜头）的卡片要转半圈（不转时正面朝 +z）"
    assert _close(Quad.uprightYaw(0.0, 1.0), 0.0)


def testTheInPlaneTurnOfAnUprightIconIsTheDropItemsRollWithTheSenseFlipped():
    """掉落物的 roll 是从正面看顺时针转几度；粒子的 rotation 从正面看逆时针为正（知识库 §5.5）。"""
    assert Quad.uprightRotation(135.0) == -135.0 and Quad.uprightRotation(-20.0) == 20.0 and Quad.uprightRotation(0.0) == 0.0


# ---------------------------------------------------------------- 粒子定义

def _definition(name):
    with io.open(os.path.join(PARTICLES, name), encoding="utf-8") as handle:
        return json.loads(handle.read())["particle_effect"]


def _declared(effect):
    """creation_expression 里声明的变量。"""
    expression = effect["components"]["minecraft:emitter_initialization"]["creation_expression"]
    return set(re.findall(r"variable\.(\w+)\s*=", expression))


def _used(effect):
    text = json.dumps(effect["components"]["minecraft:particle_appearance_billboard"]) + json.dumps(effect["components"]["minecraft:particle_appearance_tinting"])
    text += json.dumps(effect["components"].get("minecraft:particle_motion_parametric", {}))
    return set(re.findall(r"variable\.(\w+)", text))


def testTheDashParticleIsAFlatBlendedQuadOfTheWhiteConcreteTextureWithOneAlphaVariable():
    effect = _definition("arris_board_mark.json")
    components = effect["components"]
    assert effect["description"]["identifier"] == "arris:board_mark"
    assert effect["description"]["basic_render_parameters"] == {"material": "particles_blend", "texture": "textures/particle/arris_board_mark"}
    assert components["minecraft:particle_appearance_billboard"]["facing_camera_mode"] == "emitter_transform_xz", "平躺"
    assert components["minecraft:particle_appearance_billboard"]["size"] == ["variable.half_wide", "variable.half_len"], "宽（x）、长（上边）各一个变量，数是脚本按 HoD 的常量发的"
    assert components["minecraft:particle_appearance_tinting"]["color"] == [1, 1, 1, "variable.alpha"], "白、不透明度一个变量：白混凝土的颜色靠贴图"
    assert "minecraft:particle_appearance_lighting" not in components, "没有 lighting 组件 = 满亮度（HoD 的 setShape(..., glowing = true)）"
    assert _used(effect) <= _declared(effect) == {"half_wide", "half_len", "alpha"}


def testTheDashTextureIsJavasWhiteConcreteBlock():
    width, height, rows = pngkit.read(os.path.join(TEXTURES, "arris_board_mark.png"))
    pixels = [pixel for row in rows for pixel in row]
    mean = [sum(pixel[channel] for pixel in pixels) / float(len(pixels)) for channel in range(4)]
    assert (width, height) == (16, 16) and abs(mean[0] - 207.1) < 0.2 and abs(mean[1] - 213.1) < 0.2 and abs(mean[2] - 214.1) < 0.2 and mean[3] == 255.0, \
        "BoardBehavior.WHITE = block/white_concrete：(207, 213, 214)，不透明（HoD 满亮度画，所以虚线是微微发灰的白、不是纯白）"
    uv = _definition("arris_board_mark.json")["components"]["minecraft:particle_appearance_billboard"]["uv"]
    assert uv["texture_width"] == 1 and uv["uv"] == [0.25, 0.25] and uv["uv_size"] == [0.5, 0.5], "取贴图正中一块，不管贴图多大"


def testTheToolParticleIsAnUprightBlendedIconQuadFromTheItemAtlasTurnedByOneVariable():
    effect = _definition("arris_board_tool.json")
    components = effect["components"]
    assert effect["description"]["identifier"] == "arris:board_tool"
    assert effect["description"]["basic_render_parameters"] == {"material": "particles_blend", "texture": "atlas.items"}
    billboard = components["minecraft:particle_appearance_billboard"]
    assert billboard["facing_camera_mode"] == "emitter_transform_xy", "竖立"
    assert billboard["uv"]["uv"] == ["variable.u", "variable.v"] and billboard["uv"]["uv_size"] == ["variable.w", "variable.h"] and billboard["uv"]["texture_width"] == 1
    assert billboard["size"] == ["variable.half", "variable.half"]
    assert components["minecraft:particle_motion_parametric"] == {"rotation": "variable.turn"}, "图标在平面里转多少度：逐帧由脚本给"
    assert components["minecraft:particle_appearance_tinting"]["color"] == [1, 1, 1, "variable.alpha"]
    assert "minecraft:particle_appearance_lighting" not in components
    assert _used(effect) <= _declared(effect) == {"u", "v", "w", "h", "half", "turn", "alpha"}
    for name in ("arris_board_mark.json", "arris_board_tool.json"):
        life = _definition(name)["components"]
        assert life["minecraft:emitter_rate_instant"]["num_particles"] == 1 and life["minecraft:particle_lifetime_expression"]["max_lifetime"] >= 1000000, "一个发射器一颗、活到被删"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
