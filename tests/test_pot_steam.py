# -*- coding: utf-8 -*-
# runner: both
"""经典厨锅（没有站点、实体动画放的）的蒸汽照 FD 的 SteamParticle 和 CookingPotBlockEntity.animationTick（rp/particles/arris_steam.json、
rp/animations/cooking_pot.animation.json、rp/entity/cooking_pot.json、rp/models/entity/cooking_pot.geo.json）：

animationTick（CookingPotBlockEntity.java:244-262，客户端方块实体每刻）：加热着时每刻 5% 的概率在方块中心 ±0.2（x、z）、y + 0.5 放一颗蒸汽，向上 0.015 或 0.005 格每刻 = 平均每秒一颗；
SteamParticle（SteamParticle.java）：缩放 2（半边长 0.2 ~ 0.4 格）、活 80 + nextInt(50) 刻、重力 3e-6、向上 motionY + nextFloat / 500、Factory 里 y + 0.3、alpha 0.6、
最后 60 刻起每刻 -0.02（30 刻减到 0 就不见）、pickSprite 在 12 张图里随机挑一张、getLightColor 是方块所在的光照。
原来：蒸汽按每秒 1 格的加速度往上飘（2 ~ 3 秒飘 2 ~ 4.5 格，JE 是 4 ~ 6.5 秒飘 0.4 ~ 2.2 格）、永远是第 0 张图、每两秒一颗、不受光照。
煎锅的蒸汽（rp/particles/arris_skillet_steam.json）是同一个 SteamParticle，两处的粒子数都对着同一份。"""
from __future__ import print_function

import io
import json
import os

import fdtest
import molangkit
import pngkit

RP = os.path.join(fdtest.ROOT, "rp")
REFS = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "resources", "assets", "farmersdelight", "textures", "particle")
FRAMES = 12


def _json(*parts):
    with io.open(os.path.join(*parts), encoding="utf-8-sig") as handle:
        return json.load(handle)


def _effect(name):
    return _json(RP, "particles", name)["particle_effect"]


def _low(a, b):
    return a


def _high(a, b):
    return b


def _dice(*rolls):
    """math.random(低, 高) 依次给定的 [0, 1] 比例（吐完再要就是用例写少了）。"""
    rolls = list(rolls)
    return lambda a, b: a + (b - a) * rolls.pop(0)


def _evaluate(expression, rand=_low, **variables):
    return molangkit.value(expression, _random=rand, **variables)


POT = _effect("arris_steam.json")
SKILLET = _effect("arris_skillet_steam.json")
ANIMATIONS = _json(RP, "animations", "cooking_pot.animation.json")["animations"]
ENTITY = _json(RP, "entity", "cooking_pot.json")["minecraft:client_entity"]["description"]
GEOMETRY = _json(RP, "models", "entity", "cooking_pot.geo.json")["minecraft:geometry"][0]


# ---------------------------------------------------------------- 粒子自己：SteamParticle

def testThePotSteamHasTheSpeedLifetimeGravitySizeAndFadeOfFarmersDelightsSteamParticle():
    """向上 0.015 或 0.005 格每刻（+ 0 ~ 0.002）= 0.3 或 0.1 格每秒（+ 0 ~ 0.04）；寿命 80 + nextInt(50) 刻，alpha 减到 0 就不见：能看见 50 ~ 99 刻 = 2.5 ~ 4.95 秒；
    重力 3e-6 格每二次方刻 = 0.0012 格每二次方秒；半边长 0.2 ~ 0.4；alpha 0.6，最后 1.5 秒线性减到 0。"""
    parts = POT["components"]
    assert POT["description"]["identifier"] == "arris:steam"
    assert parts["minecraft:emitter_shape_point"]["direction"] == [0, 1, 0]
    speed = parts["minecraft:particle_initial_speed"]
    assert abs(_evaluate(speed, _low) - 0.1) < 1e-9 and abs(_evaluate(speed, _high) - 0.34) < 1e-9, "最慢 0.005 格每刻 = 0.1 格每秒，最快 0.015 + 0.002 = 0.34"
    assert abs(_evaluate(speed, _dice(0.49, 1.0)) - 0.14) < 1e-9, "random.nextBoolean() 为假的一档：0.005 + 最多 0.002 格每刻"
    assert abs(_evaluate(speed, _dice(0.5, 0.0)) - 0.3) < 1e-9, "为真的一档：0.015 格每刻 = 0.3 格每秒"
    life = parts["minecraft:particle_lifetime_expression"]["max_lifetime"]
    assert abs(_evaluate(life, _low) - 2.5) < 1e-9 and abs(_evaluate(life, _high) - 4.95) < 1e-9
    motion = parts["minecraft:particle_motion_dynamic"]
    assert motion["linear_acceleration"] == [0, -0.0012, 0] and "linear_drag_coefficient" not in motion, "SteamParticle.tick 只减重力，没有摩擦；原来是向上 1 格每二次方秒"
    size = parts["minecraft:particle_appearance_billboard"]["size"]
    assert size[0] == size[1] and abs(_evaluate(size[0], particle_random_1=0.0) - 0.2) < 1e-9 and abs(_evaluate(size[0], particle_random_1=1.0) - 0.4) < 1e-9, "原来固定 0.4"
    alpha = parts["minecraft:particle_appearance_tinting"]["color"][3]
    for age, want in ((0.0, 0.6), (3.45, 0.6), (4.2, 0.3), (4.95, 0.0)):
        assert abs(_evaluate(alpha, particle_age=age, particle_lifetime=4.95) - want) < 1e-9, age
    assert parts["minecraft:particle_appearance_tinting"]["color"][:3] == [1, 1, 1]
    assert POT["description"]["basic_render_parameters"]["material"] == "particles_blend", "PARTICLE_SHEET_TRANSLUCENT"


def testThePotSteamStartsWhereAnimationTickPutsItAndTheFactoryRaisesItByThreeTenths():
    """x、z：方块中心 ± 0.2（nextDouble * 0.4 - 0.2）；y：pos.y + 0.5（locator 8 像素），Factory 再 + 0.3（发射器偏移）。"""
    offset = POT["components"]["minecraft:emitter_shape_point"]["offset"]
    for roll in (_low, _high):
        assert abs(_evaluate(offset[0], roll) - roll(-0.2, 0.2)) < 1e-9 and abs(_evaluate(offset[2], roll) - roll(-0.2, 0.2)) < 1e-9
    assert offset[1] == 0.3
    assert GEOMETRY["bones"][0]["locators"]["steam"] == [-8, 8, 8], "方块中心（模型里 x -16 ~ 0、z 0 ~ 16），离底面 8 像素 = 0.5 格"


def testEveryPuffPicksOneOfTheTwelveFramesAtRandomLikePickSprite():
    """SteamParticle.Factory：particle.pickSprite(spriteSet) 在 steam.json 的 12 张图里随机挑一张。基岩版：12 张图叠成一张 16 x 192，UV 的纵向由粒子自己的随机数 2 取整挑。"""
    for effect in (POT, SKILLET):
        billboard = effect["components"]["minecraft:particle_appearance_billboard"]
        uv = billboard["uv"]
        assert uv["texture_width"] == 16 and uv["texture_height"] == 16 * FRAMES and uv["uv_size"] == [16, 16]
        assert effect["description"]["basic_render_parameters"]["texture"] == "textures/particle/arris_steam"
        assert uv["uv"][0] == 0
        seen = [_evaluate(uv["uv"][1], particle_random_2=roll / 1000.0) for roll in range(1000)]
        assert sorted(set(seen)) == [16.0 * frame for frame in range(FRAMES)], "12 张都挑得到，一张都不多"
        counts = [seen.count(16.0 * frame) for frame in range(FRAMES)]
        assert min(counts) >= 80 and max(counts) <= 90, "均匀：随机数 [0, 1) 均分成 12 份"
        assert "particle_random_1" not in uv["uv"][1], "挑图和大小不共用一个随机数（JE 里是两次独立的 random）"
    width, height, _rows = pngkit.read(os.path.join(RP, "textures", "particle", "arris_steam.png"))
    assert (width, height) == (16, 16 * FRAMES)


def testTheSheetHoldsFarmersDelightsTwelveSteamFramesInOrder():
    """steam_0 ~ steam_11：本机有 JE 的资源（.refs/FarmersDelight）时逐像素对一遍。"""
    _width, _height, rows = pngkit.read(os.path.join(RP, "textures", "particle", "arris_steam.png"))
    if not os.path.isdir(REFS):
        print("跳过：没有 JE 的资源（.refs/FarmersDelight）")
        return
    for frame in range(FRAMES):
        _w, _h, want = pngkit.read(os.path.join(REFS, "steam_%d.png" % frame))
        assert rows[16 * frame:16 * frame + 16] == want, frame


def testTheOldOneFramePerFileSetIsGone():
    """arris:steam_0 ~ steam_11 十二份几乎一样的粒子文件和十二张单图，只有第 0 张用过：换成一张图 + 一个粒子。"""
    assert not os.path.isdir(os.path.join(RP, "particles", "steam")) or not os.listdir(os.path.join(RP, "particles", "steam"))
    for frame in range(FRAMES):
        assert not os.path.exists(os.path.join(RP, "textures", "particle", "steam_%d.png" % frame)), frame


# ---------------------------------------------------------------- 两个蒸汽是同一个 SteamParticle

def testThePotAndTheSkilletUseTheSameSteamParticleAndOnlyTheStartingSpotDiffers():
    """JE 里 CookingPotBlockEntity 和 SkilletBlockEntity 放的是同一个 ModParticleTypes.STEAM：速度、寿命、大小、渐隐、挑图、光照都一样，
    起点不同（煎锅的 x、z 偏移由脚本掷，锅的写在粒子里）。"""
    pot, skillet = POT["components"], SKILLET["components"]
    for name in ("minecraft:emitter_rate_instant", "minecraft:emitter_lifetime_once", "minecraft:particle_initial_speed", "minecraft:particle_lifetime_expression",
                 "minecraft:particle_motion_dynamic", "minecraft:particle_appearance_billboard", "minecraft:particle_appearance_tinting", "minecraft:particle_appearance_lighting"):
        assert pot[name] == skillet[name], name
    assert pot["minecraft:emitter_shape_point"]["direction"] == skillet["minecraft:emitter_shape_point"]["direction"]
    assert pot["minecraft:emitter_shape_point"]["offset"][1] == skillet["minecraft:emitter_shape_point"]["offset"][1] == 0.3
    assert POT["description"]["basic_render_parameters"] == SKILLET["description"]["basic_render_parameters"]


def testThePotSteamStaysInsideTheColumnAbovePotWhichIsTheOnlyPlaceItExpires():
    """原来就有的：离开锅和空气就消失（经典的粗略碰撞）。JE 是碰到方块停住，这里没改。"""
    assert POT["components"]["minecraft:particle_expire_if_not_in_blocks"] == ["minecraft:air", "arris:cooking_pot"]


# ---------------------------------------------------------------- 实体怎么放它

def testTheEntityPutsOnePuffEverySecondAtTheLocatorWhileTheLidIsOnAndItIsHot():
    """animationTick 每刻 5%，一秒 20 刻平均 1 颗：动画一秒一圈、圈首放一颗（原来两秒一颗，是 JE 的一半）。"""
    animation = ANIMATIONS["animation.cooking_pot.smoke"]
    assert animation["loop"] is True and animation["animation_length"] == 1
    assert animation["particle_effects"] == {"0.0": {"effect": "steam", "locator": "steam"}}
    assert ENTITY["particle_effects"]["steam"] == "arris:steam" and ENTITY["animations"]["smoke"] == "animation.cooking_pot.smoke"
    assert {"smoke": "variable.mod_heat == 1.0 && variable.mod_open < 0.5"} in ENTITY["scripts"]["animate"]
    assert "steam_0" not in ENTITY["particle_effects"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
