# -*- coding: utf-8 -*-
# runner: both
"""煎锅和炉灶场景的烟（rp/particles/arris_pan_smoke.json）是 HoD 自己的粒子样式 PAN_SMOKE（HandsOnDelightClient.java:93-94），不是 Diegesis 满亮度的蒸汽乘倍数：

    ParticleStyle.builder(蒸汽的 12 帧).color(0x58C8C6C2).size(1.8F, 2.6F).life(1.6F, 2.4F).gravity(-4.0F).drag(0.75F).grow(3.0F).wobble(1.0F).fadeIn(0.3F).build()

没有 emissive（画的时候 packed = style.emissive() ? FULL_BRIGHT : light，SceneParticles.java:252：跟着环境光）；fade 缺省真（alpha 乘 1 - t²，:233）。
SceneParticles 的单位：大小是像素（画出来的边长 = size * lerp(t, 1, grow)），重力是像素每二次方秒（负的往上）、阻力是每秒损失的比例（速度乘 (1 - drag)^dt）、
摆动每秒每秒往 x 加 sin(age * 6 + seed) * wobble * 6、往 z 加 cos(1.3 * 同一个角) * wobble * 6（像素每二次方秒）。基岩版的粒子一格 = 16 像素，size 是半边长。
"""
from __future__ import print_function

import io
import json
import math
import os
import re

import fdtest
import molangkit
import pngkit

RP = os.path.join(fdtest.ROOT, "rp")
PIXEL = 1.0 / 16.0                     # 一像素 = 1/16 格
# ---- HoD 的 PAN_SMOKE（HandsOnDelightClient.java:93-94）
COLOR = 0x58C8C6C2
SIZE = (1.8, 2.6)                      # 像素
LIFE = (1.6, 2.4)                      # 秒
GRAVITY = -4.0                         # 像素每二次方秒，负的往上
DRAG = 0.75
GROW = 3.0
WOBBLE = 1.0
FADE_IN = 0.3
FRAMES = 12


def _effect():
    with io.open(os.path.join(RP, "particles", "arris_pan_smoke.json"), encoding="utf-8-sig") as handle:
        return json.load(handle)["particle_effect"]


EFFECT = _effect()
PARTS = EFFECT["components"]


def _low(a, b):
    return a


def _high(a, b):
    return b


def _evaluate(expression, rand=_low, **variables):
    return molangkit.value(expression, _random=rand, **variables)


def _creation(name):
    """creation_expression 里 variable.<name> 的初值。"""
    return float(re.search(r"variable\.%s = ([0-9.]+);" % name, PARTS["minecraft:emitter_initialization"]["creation_expression"]).group(1))


def testTheStyleIsAnOwnParticleWithTheTwelveSteamFramesStretchedOverItsLife():
    assert EFFECT["description"]["identifier"] == "arris:pan_smoke"
    assert EFFECT["description"]["basic_render_parameters"] == {"material": "particles_blend", "texture": "textures/handson/particle/pan_smoke"}
    uv = PARTS["minecraft:particle_appearance_billboard"]["uv"]
    assert (uv["texture_width"], uv["texture_height"]) == (16, 16 * FRAMES) and uv["flipbook"]["max_frame"] == FRAMES
    assert uv["flipbook"]["stretch_to_lifetime"] is True and uv["flipbook"]["loop"] is False, "frame = (int)(t * 帧数)：SceneParticles.render"
    width, height, _rows = pngkit.read(os.path.join(RP, "textures", "handson", "particle", "pan_smoke.png"))
    assert (width, height) == (16, 16 * FRAMES)


def testTheSheetIsTheLibrarysWhiteSteamFramesWhichTheStyleUses():
    """HoD 的 PAN_SMOKE 用的是 Diegesis 的 steam_0 ~ 11（原版烟的帧染成白的）：本机有前置包的资源（旁边的 diegesisRp）时逐像素对一遍。"""
    ours = pngkit.read(os.path.join(RP, "textures", "handson", "particle", "pan_smoke.png"))
    theirs = os.path.join(fdtest.ROOT, "diegesisRp", "textures", "diegesis", "particle", "steam.png")
    if not os.path.isfile(theirs):
        print("跳过：旁边没有前置包的资源（diegesisRp）")
        return
    assert ours[2] == pngkit.read(theirs)[2]


def testTheSizeIsOneEightyToTwoSixtyPixelsAcrossGrowingToThreeTimesTheWayOverItsLife():
    """画出来的边长 = size * lerp(t, 1, grow) 像素；基岩版的 size 是半边长，单位格：size / 2 / 16。"""
    size = PARTS["minecraft:particle_appearance_billboard"]["size"]
    assert size[0] == size[1]
    for roll, edge in ((0.0, SIZE[0]), (1.0, SIZE[1])):
        for t in (0.0, 0.5, 1.0):
            got = _evaluate(size[0], particle_random_1=roll, scale=1.0, particle_age=t * 2.0, particle_lifetime=2.0)
            want = edge * (1.0 + (GROW - 1.0) * t) / 2.0 * PIXEL
            assert abs(got - want) < 1e-9, (roll, t, got, want)


def testTheLifeIsAnyTimeBetweenOnePointSixAndTwoPointFourSecondsUnlessTheScriptSaysSo():
    life = PARTS["minecraft:particle_lifetime_expression"]["max_lifetime"]
    assert abs(_evaluate(life, _low, life=0.0) - LIFE[0]) < 1e-9 and abs(_evaluate(life, _high, life=0.0) - LIFE[1]) < 1e-9
    assert _evaluate(life, _low, life=1.234) == 1.234


def testItRisesAtFourPixelsPerSecondSquaredWobblesByOneAndSlowsDownByThreeQuartersASecond():
    """重力 -4 像素每二次方秒 = 往上 0.25 格每二次方秒；摆动 x += sin(t) * wobble * 6、z += cos(1.3t) * wobble * 6（t = age * 6 + seed）；阻力：速度每秒剩 (1 - 0.75)。"""
    motion = PARTS["minecraft:particle_motion_dynamic"]
    accel = motion["linear_acceleration"]
    assert abs(accel[1] - (-GRAVITY) * PIXEL) < 1e-9
    amplitude = WOBBLE * 6.0 * PIXEL
    quarter = math.pi / 12.0                       # age * 6 = pi / 2：sin 取到 1
    assert abs(_evaluate(accel[0], particle_age=quarter, particle_random_2=0.0) - amplitude) < 1e-4
    assert abs(_evaluate(accel[2], particle_age=0.0, particle_random_2=0.0) - amplitude) < 1e-9, "cos(0) = 1"
    angle = 0.3 * 6.0 + 0.4 * 100.0                # 任意一个时刻：t = age * 6 + seed（seed 是 0 ~ 100 的随机数）
    assert abs(_evaluate(accel[0], particle_age=0.3, particle_random_2=0.4) - amplitude * math.sin(angle)) < 1e-4
    assert abs(_evaluate(accel[2], particle_age=0.3, particle_random_2=0.4) - amplitude * math.cos(1.3 * angle)) < 1e-4
    assert abs(math.exp(-motion["linear_drag_coefficient"]) - (1.0 - DRAG)) < 1e-5, "每秒剩 25%"


def testItFadesInOverTheFirstThreeTenthsAndOutWithOneMinusTSquaredFromTheTintsAlpha():
    """alpha = 颜色的 alpha * min(1, t / fadeIn) * (1 - t * t)（fade 缺省真）：SceneParticles.render 233-236。"""
    base = (COLOR >> 24) / 255.0
    assert abs(_creation("alpha") - base) < 1e-6
    tint = PARTS["minecraft:particle_appearance_tinting"]["color"]
    for t in (0.0, 0.1, 0.3, 0.5, 0.9, 1.0):
        got = _evaluate(tint[3], alpha=base, particle_age=t * 2.0, particle_lifetime=2.0)
        want = base * min(1.0, t / FADE_IN) * (1.0 - t * t)
        assert abs(got - want) < 1e-9, (t, got, want)


def testItsOwnColourIsGreyishWhiteUnlessTheScriptTintsIt():
    """0xC8C6C2：脚本没给颜色（tint_set 为 0）就是这个；给了就用给的。"""
    tint = PARTS["minecraft:particle_appearance_tinting"]["color"]
    want = ((COLOR >> 16) & 0xFF, (COLOR >> 8) & 0xFF, COLOR & 0xFF)
    own = tuple(round(_evaluate(channel, tint_set=0.0, tint_r=9.0, tint_g=9.0, tint_b=9.0) * 255) for channel in tint[:3])
    assert own == want
    given = tuple(_evaluate(channel, tint_set=1.0, tint_r=0.25, tint_g=0.5, tint_b=0.75) for channel in tint[:3])
    assert given == (0.25, 0.5, 0.75)


def testItRisesAtFourPixelsPerSecondWhenTheScriptGivesNoVelocityAndAtTheGivenOneWhenItDoes():
    """HoD 放的时候给 (±0.5 随机, 4.0, ±0.5) 像素每秒；没给就是 (0, 4, 0)。"""
    speed = PARTS["minecraft:particle_initial_speed"]
    assert abs(_evaluate(speed, speed_set=0.0, vx=7.0, vy=7.0, vz=7.0) - 4.0 * PIXEL) < 1e-9
    assert abs(_evaluate(speed, speed_set=1.0, vx=0.3, vy=4.0, vz=-0.4) - math.sqrt(0.3 ** 2 + 4.0 ** 2 + 0.4 ** 2) * PIXEL) < 1e-9
    direction = PARTS["minecraft:emitter_shape_point"]["direction"]
    assert [_evaluate(axis, speed_set=0.0, vx=7.0, vy=7.0, vz=7.0) for axis in direction] == [0.0, 4.0, 0.0]


def testItFollowsTheAmbientLightLikeJavaDoesBecauseTheStyleIsNotEmissive():
    assert PARTS["minecraft:particle_appearance_lighting"] == {}, "没有 emissive：packed = light（SceneParticles.java:252）；检查表在 test_particle_lighting.py"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
