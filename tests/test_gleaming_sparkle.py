# -*- coding: utf-8 -*-
# runner: both
"""闪亮沙拉的闪光粒子（JE 的 GleamingSaladBlock.animateTick + SparkleParticle）：概率、位置、粒子文件、客户端处理。

JE 的事实（抄在下面，离线可跑）：
- animateTick：servings == 0 直接返回；random.nextFloat() < 0.05F * servings 才放一个粒子，位置
  x = 方块x + 0.5 + (random.nextDouble() * 0.5 - 0.25)、y = 方块y + 0.5、z 同 x；
- SparkleParticle：寿命 4 刻、不动、满亮度、quadSize = 0.1~0.2 的随机值 × 0.75（半边长，所以整边 0.15~0.3 格），
  4 张 8×8 的贴图按 age * 3 / lifetime 取（age 0、1、2、3、4 -> 0、0、1、2、3），第 5 刻被移除。
基岩版：方块 JSON 的 netease:block_animate_random_tick 按 trigger_rate 的概率发客户端事件 BlockAnimateRandomTickEvent，
Client/BlockSparkle.py 收到就在 Shared/Rules/Sparkle.py 算的位置放 rp/particles/sparkle.json 的粒子。
"""
from __future__ import print_function

import ast
import io
import json
import math
import os
import struct
import sys
import types

import fdtest

Sparkle = fdtest.load("Shared.Rules.Sparkle")
BLOCKS_DIR = os.path.join(fdtest.BP, "netease_blocks", "gleaming_salad_block")
RP = os.path.join(fdtest.ROOT, "rp")
handlers = {}
created = []


def _read(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _install():
    """客户端模块只通过 QuModLibs.Client 的 Listen 和 Client/Engine 的 compFactory 碰引擎：先换成假的再导入它。"""
    class _Particles(object):
        def Create(self, name, offset=(0, 0, 0), rotation=(0, 0, 0)):
            created.append((name, offset))
            return 1

    class _Factory(object):
        def CreateParticleSystem(self, target):
            assert target is None, "世界里的粒子不绑实体"
            return _Particles()

    def listen(eventName):
        def register(func):
            handlers[eventName] = func
            return func
        return register

    quMod = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Client")
    quMod.Listen = listen
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory = _Factory()
    sys.modules[quMod.__name__] = quMod
    sys.modules[engine.__name__] = engine
    return fdtest.load("Client.BlockSparkle")


BlockSparkle = _install()


class _Dice(object):
    def __init__(self, *values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)


def _fire(blockName, blockPos=(3.0, 64.0, -2.0), dice=(0.5, 0.5)):
    del created[:]
    BlockSparkle.random = _Dice(*dice)
    handlers["BlockAnimateRandomTickEvent"]({"blockPos": blockPos, "blockName": blockName, "auxData": 0})
    return list(created)


# ---- 概率和位置（纯规则） ----

def testTheChanceIsFivePercentPerRemainingServing():
    for servings, expected in ((0, 0.0), (1, 0.05), (2, 0.1), (3, 0.15), (4, 0.2)):
        assert abs(Sparkle.sparkleChance(servings) - expected) < 1e-9, servings


def testTheSpotIsTheCentreOfTheBlockWithAQuarterBlockOfHorizontalScatter():
    assert Sparkle.sparkleSpot((3, 64, -2), 0.5, 0.5) == (3.5, 64.5, -1.5)
    assert Sparkle.sparkleSpot((3, 64, -2), 0.0, 1.0) == (3.25, 64.5, -1.25)
    for dice in ((0.0, 0.0), (0.999999, 0.999999), (0.3, 0.8)):
        x, y, z = Sparkle.sparkleSpot((10, 5, 20), dice[0], dice[1])
        assert 10.25 <= x < 10.75 and y == 5.5 and 20.25 <= z < 20.75


def testOnlyTheStagesWithServingsSparkle():
    assert Sparkle.SPARKLE_SERVINGS == {"arris:gleaming_salad_block_stage0": 4, "arris:gleaming_salad_block_stage1": 3,
                                        "arris:gleaming_salad_block_stage2": 2, "arris:gleaming_salad_block_stage3": 1}


# ---- 方块 JSON ----

def testEveryStageWithServingsAsksTheEngineForTheEventAtTheJavaChance():
    for name, servings in sorted(Sparkle.SPARKLE_SERVINGS.items()):
        short = name.rsplit("_", 1)[1]
        components = _read(os.path.join(BLOCKS_DIR, "arris_gleaming_salad_block_%s.json" % short))["minecraft:block"]["components"]
        tick = components["netease:block_animate_random_tick"]
        assert tick["send_event"] is True and abs(tick["trigger_rate"] - Sparkle.sparkleChance(servings)) < 1e-9, name
    leftover = _read(os.path.join(BLOCKS_DIR, "arris_gleaming_salad_block_leftover.json"))["minecraft:block"]["components"]
    assert "netease:block_animate_random_tick" not in leftover, "JE：servings == 0 不冒"


# ---- 粒子文件 ----

def _particle():
    return _read(os.path.join(RP, "particles", "sparkle.json"))["particle_effect"]


def testTheParticleIsFourEightPixelFramesThatStandStill():
    effect = _particle()
    assert effect["description"]["identifier"] == Sparkle.SPARKLE
    texture = effect["description"]["basic_render_parameters"]["texture"]
    with io.open(os.path.join(RP, texture + ".png"), "rb") as handle:
        header = handle.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(str(">II"), header[16:24]) == (8, 32), "4 张 8×8 竖着拼"
    components = effect["components"]
    billboard = components["minecraft:particle_appearance_billboard"]
    assert billboard["uv"]["texture_width"] == 8 and billboard["uv"]["texture_height"] == 32 and billboard["uv"]["uv_size"] == [8, 8]
    assert billboard["facing_camera_mode"] == "lookat_xyz"
    assert "minecraft:particle_appearance_lighting" not in components, "JE：getLightColor 恒为满亮度"
    assert "minecraft:particle_motion_dynamic" not in components and components["minecraft:particle_initial_speed"] == 0, "JE：tick 里不动"
    assert components["minecraft:emitter_rate_instant"]["num_particles"] == 1
    assert components["minecraft:particle_lifetime_expression"]["max_lifetime"] == 0.25, "JE：寿命 4 刻，第 5 刻移除"


def _number(node):
    return node.value if hasattr(ast, "Constant") and isinstance(node, ast.Constant) else node.n    # py2 的数字是 ast.Num


def _molang(text, **variables):
    """粒子文件里那两个表达式算一遍：只认数字、变量（variable.x -> 关键字 variable_x）、加减乘除、括号和 math.floor，换了写法这里就要跟着改。"""
    operators = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.BinOp):
            return operators[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.Call):
            assert node.func.id == "floor" and len(node.args) == 1, text
            return float(math.floor(walk(node.args[0])))
        if isinstance(node, ast.Name):
            return variables[node.id]
        return _number(node)
    return walk(ast.parse(text.replace("math.floor", "floor").replace("variable.", "variable_"), mode="eval"))


def testTheFramesFollowTheJavaSpriteSet():
    # JE：age 0、1、2、3、4 取第 age * 3 // 4 张（0、0、1、2、3）；每个 age 占一刻（0.05 秒），所以第 n 刻中间时的帧号就是它
    uv = _particle()["components"]["minecraft:particle_appearance_billboard"]["uv"]["uv"]
    assert uv[0] == 0
    for ticks in range(5):
        seconds = (ticks + 0.5) * 0.05
        assert _molang(uv[1], variable_particle_age=seconds) == (ticks * 3 // 4) * 8, ticks


def testTheSizeIsJavasQuadSizeTimesThreeQuarters():
    # JE：quadSize = 0.1 * (nextFloat() * 0.5 + 0.5) * 2 = 0.1 ~ 0.2，× 0.75 = 0.075 ~ 0.15（半边长，Bedrock 的 size 也是半边长）
    size = _particle()["components"]["minecraft:particle_appearance_billboard"]["size"]
    assert size[0] == size[1], "方形"
    assert abs(_molang(size[0], variable_particle_random_1=0.0) - 0.075) < 1e-9
    assert abs(_molang(size[0], variable_particle_random_1=1.0) - 0.15) < 1e-9


# ---- 客户端处理 ----

def testTheEventMakesOneSparkleAtTheJavaSpot():
    assert "BlockAnimateRandomTickEvent" in handlers
    assert _fire("arris:gleaming_salad_block_stage1", (3.0, 64.0, -2.0), dice=(0.0, 1.0)) == [(Sparkle.SPARKLE, (3.25, 64.5, -1.25))]
    assert _fire("arris:gleaming_salad_block_stage0", (0.0, 70.0, 0.0), dice=(0.5, 0.5)) == [(Sparkle.SPARKLE, (0.5, 70.5, 0.5))]


def testOtherBlocksAndTheEmptyBowlDoNothing():
    for name in ("arris:gleaming_salad_block_leftover", "minecraft:oak_leaves", "othermod:leaves"):
        assert _fire(name) == [], name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
