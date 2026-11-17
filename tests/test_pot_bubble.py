# -*- coding: utf-8 -*-
# runner: both
"""经典厨锅（没有站点、实体动画放的）的气泡照 FD 的 CookingPotBlockEntity.animationTick 和原版的 BubblePopParticle
（rp/particles/arris_bubble_pop.json、rp/animations/cooking_pot.animation.json、rp/entity/cooking_pot.json、rp/models/entity/cooking_pot.geo.json）：

animationTick（CookingPotBlockEntity.java:244-251，客户端方块实体每刻）：加热着（只看这一条，锅里有没有菜、盖没盖都不看）时每刻 20% 的概率在方块中心 ±0.3（x、z，
nextDouble * 0.6 - 0.3）、pos.y + 0.7 放一颗 ParticleTypes.BUBBLE_POP，初速三个 0；
BubblePopParticle（1.20.1）：活 4 刻（age++ >= lifetime 才没，所以看得见 5 刻：5 张图各一刻，setSpriteFromAge）、重力 0.008（每刻先 yd -= 0.008 再 move，没有摩擦）、
半边长 0.1F * (nextFloat * 0.5F + 0.5F) * 2.0F = 0.1 ~ 0.2（SingleQuadParticle 的构造）、ParticleRenderType.PARTICLE_SHEET_OPAQUE（不透明，没有半透明）、
getLightColor 没覆盖（跟着方块所在的光照）；贴图 bubble_pop_0 ~ 4（每张 16 x 16）。
原来：用的是老贴图集里的一个水泡，往上飘 2 ~ 3 秒、每两秒里只放一秒、一秒 5 颗、随机斜着飞。
基岩版没有"每刻 20%"的掷骰：实体动画每 0.25 秒放一颗（每秒 4 颗 = 每秒 20 刻 x 20%，平均一样，间隔是匀的），位置每颗自己随机。"""
from __future__ import print_function

import io
import json
import os
import tempfile
import zipfile

import fdtest
import molangkit
import pngkit

RP = os.path.join(fdtest.ROOT, "rp")
TICK = 0.05                              # 一刻 = 0.05 秒
FRAMES = 5
CLIENT_JAR = os.path.expanduser(os.path.join("~", ".gradle", "caches", "fabric-loom", "1.20.1", "minecraft-client.jar"))


def _json(*parts):
    with io.open(os.path.join(*parts), encoding="utf-8-sig") as handle:
        return json.load(handle)


def _low(a, b):
    return a


def _high(a, b):
    return b


def _evaluate(expression, rand=_low, **variables):
    return molangkit.value(expression, _random=rand, **variables)


BUBBLE = _json(RP, "particles", "arris_bubble_pop.json")["particle_effect"]
ANIMATIONS = _json(RP, "animations", "cooking_pot.animation.json")["animations"]
ENTITY = _json(RP, "entity", "cooking_pot.json")["minecraft:client_entity"]["description"]
GEOMETRY = _json(RP, "models", "entity", "cooking_pot.geo.json")["minecraft:geometry"][0]


def _javaDrops(ticks):
    """BubblePopParticle.tick 逐刻照抄：每刻 yd -= 0.008 再 move（初速 0，没有摩擦），第 ticks 刻之后一共落了多少格。"""
    gravity, yd, fell = 0.008, 0.0, 0.0
    for _ in range(ticks):
        yd -= gravity
        fell -= yd
    return fell


# ---------------------------------------------------------------- 粒子自己：BubblePopParticle

def testTheBubbleLivesFiveTicksOfFiveFramesAndIsAnOpaqueSpriteNotATranslucentOne():
    """活 4 刻 = 看得见 5 刻（第 5 刻起 age++ >= lifetime 才没）：5 张图各一刻（0.25 秒，每张 0.05 秒）；PARTICLE_SHEET_OPAQUE：不透明（alpha 测试，不混合）。"""
    parts = BUBBLE["components"]
    assert BUBBLE["description"]["identifier"] == "arris:bubble_pop"
    assert BUBBLE["description"]["basic_render_parameters"] == {"material": "particles_alpha", "texture": "textures/particle/arris_bubble_pop"}
    life = parts["minecraft:particle_lifetime_expression"]["max_lifetime"]
    assert abs(_evaluate(life) - FRAMES * TICK) < 1e-9, "5 刻"
    uv = parts["minecraft:particle_appearance_billboard"]["uv"]
    assert (uv["texture_width"], uv["texture_height"]) == (16, 16 * FRAMES) and uv["flipbook"]["max_frame"] == FRAMES
    assert uv["flipbook"]["size_UV"] == [16, 16] and uv["flipbook"]["step_UV"] == [0, 16] and uv["flipbook"]["base_UV"] == [0, 0]
    assert uv["flipbook"]["stretch_to_lifetime"] is True and uv["flipbook"]["loop"] is False, "五张均分寿命：setSpriteFromAge"
    assert "minecraft:particle_appearance_tinting" not in parts, "JE 的气泡不染色"
    assert parts["minecraft:particle_appearance_lighting"] == {}, "getLightColor 没覆盖：跟着方块所在的光照（rp/particles 里的光照表在 test_particle_lighting.py）"
    assert "minecraft:particle_expire_if_not_in_blocks" not in parts, "只活 0.25 秒，不用碰撞范围的粗略办法"


def testTheBubbleHasNoSpeedOfItsOwnAndOnlyFallsTheWayGravityPullsItTickByTick():
    """初速 0、每刻 yd -= 0.008 再 move：第 n 刻共落 0.004 * n * (n + 1) 格（0.008、0.024、0.048、0.080）。基岩版的粒子是连续的：
    初速向下 v0、加速度 a，t = 0.05n 秒时落 v0 t + a t² / 2 = 0.004n² + 0.004n，所以 a = 3.2、v0 = 0.08，每一刻的位置都和 JE 对上。"""
    parts = BUBBLE["components"]
    assert parts["minecraft:emitter_shape_point"]["direction"] == [0, -1, 0]
    v0 = _evaluate(parts["minecraft:particle_initial_speed"])
    accel = parts["minecraft:particle_motion_dynamic"]["linear_acceleration"]
    assert accel[0] == 0 and accel[2] == 0 and "linear_drag_coefficient" not in parts["minecraft:particle_motion_dynamic"], "没有水平的漂、没有摩擦"
    for ticks in range(1, FRAMES):
        t = ticks * TICK
        fell = v0 * t - 0.5 * accel[1] * t * t
        assert abs(fell - _javaDrops(ticks)) < 1e-9, (ticks, fell, _javaDrops(ticks))
    assert abs(_javaDrops(4) - 0.08) < 1e-9


def testTheBubbleIsAsBigAsAnyDefaultParticleOneTenthToOneFifthOfABlockAcross():
    """SingleQuadParticle 的构造：quadSize = 0.1F * (nextFloat * 0.5F + 0.5F) * 2.0F = 0.1 ~ 0.2（半边长，基岩版的 size 也是半边长）；BubblePopParticle 不再缩放。"""
    size = BUBBLE["components"]["minecraft:particle_appearance_billboard"]["size"]
    assert size[0] == size[1]
    assert abs(_evaluate(size[0], particle_random_1=0.0) - 0.1) < 1e-9 and abs(_evaluate(size[0], particle_random_1=1.0) - 0.2) < 1e-9


def testTheBubbleStartsWhereAnimationTickPutsItWithinThreeTenthsOfTheCentreAndSeventyHundredthsHigh():
    """x、z：方块中心 ± 0.3（nextDouble * 0.6 - 0.3，各自掷）；y：pos.y + 0.7（定位点在 11.2 像素）；每颗一颗。"""
    parts = BUBBLE["components"]
    offset = parts["minecraft:emitter_shape_point"]["offset"]
    for roll in (_low, _high):
        assert abs(_evaluate(offset[0], roll) - roll(-0.3, 0.3)) < 1e-9 and abs(_evaluate(offset[2], roll) - roll(-0.3, 0.3)) < 1e-9
    assert offset[1] == 0, "高度由定位点定"
    assert GEOMETRY["bones"][0]["locators"]["blister"] == [-8, 0.7 * 16, 8], "方块中心（模型里 x -16 ~ 0、z 0 ~ 16），离底面 0.7 格 = 11.2 像素"
    assert parts["minecraft:emitter_rate_instant"]["num_particles"] == 1 and parts["minecraft:emitter_lifetime_once"]["active_time"] <= TICK


# ---------------------------------------------------------------- 贴图：原版的五张

def _javaFrames():
    """原版 1.20.1 的 bubble_pop_0 ~ 4 的像素（本机 gradle 缓存里有客户端 jar 才有）。"""
    if not os.path.isfile(CLIENT_JAR):
        return None
    frames = []
    with zipfile.ZipFile(CLIENT_JAR) as archive:
        for frame in range(FRAMES):
            data = archive.read("assets/minecraft/textures/particle/bubble_pop_%d.png" % frame)
            handle, path = tempfile.mkstemp(suffix=".png")
            try:
                os.write(handle, data)
            finally:
                os.close(handle)
            try:
                frames.append(pngkit.read(path))
            finally:
                os.remove(path)
    return frames


def testTheSheetHoldsTheFiveVanillaBubblePopFramesInOrder():
    """原版（Mojang）的图直接用，不重画：16 x 80，五张叠在一起；本机有 JE 的客户端 jar 时逐像素对一遍。"""
    width, height, rows = pngkit.read(os.path.join(RP, "textures", "particle", "arris_bubble_pop.png"))
    assert (width, height) == (16, 16 * FRAMES)
    java = _javaFrames()
    if java is None:
        print("跳过：没有 JE 的客户端 jar（~/.gradle/caches/fabric-loom/1.20.1/minecraft-client.jar）")
        return
    for frame, (w, h, want) in enumerate(java):
        assert (w, h) == (16, 16), frame
        assert rows[16 * frame:16 * frame + 16] == want, frame


# ---------------------------------------------------------------- 实体怎么放它

def testTheEntityPutsFourBubblesASecondWhileTheLidIsOnAndItIsHot():
    """animationTick 每刻 20%，一秒 20 刻平均 4 颗：动画 0.25 秒一圈、圈首放一颗（原来两秒一圈、放一秒 5 颗，不是 JE 的数）。
    只要加热着（和蒸汽同一个条件：盖着、没有站点场景接管）：锅里有没有菜不看。"""
    animation = ANIMATIONS["animation.cooking_pot.bubble"]
    assert animation["loop"] is True and animation["animation_length"] == 0.25
    assert animation["particle_effects"] == {"0.0": {"effect": "bubble", "locator": "blister"}}
    assert len(animation["particle_effects"]) / animation["animation_length"] == 0.2 * 20
    assert ENTITY["particle_effects"]["bubble"] == "arris:bubble_pop" and ENTITY["animations"]["bubble"] == "animation.cooking_pot.bubble"
    assert {"bubble": "variable.mod_heat == 1.0 && variable.mod_open < 0.5"} in ENTITY["scripts"]["animate"]
    assert {"smoke": "variable.mod_heat == 1.0 && variable.mod_open < 0.5"} in ENTITY["scripts"]["animate"], "蒸汽同一个条件"
    assert not any("mod_food" in str(entry) and "bubble" in str(entry) for entry in ENTITY["scripts"]["animate"]), "气泡不看锅里有没有菜"


def testTheOldWaterBubbleAndItsSheetAreGone():
    """原来的 arris:bubble（rp/particles/bubble.json）和它独占的 128 x 128 贴图集：没有别的东西用了。"""
    assert not os.path.exists(os.path.join(RP, "particles", "bubble.json"))
    assert not os.path.exists(os.path.join(RP, "textures", "particle", "arris_particles.png"))
    assert "arris:bubble" not in ENTITY["particle_effects"].values()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
