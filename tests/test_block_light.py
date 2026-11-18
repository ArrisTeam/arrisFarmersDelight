# -*- coding: utf-8 -*-
# runner: both
"""哪些方块挡光对照 JE（旧写法 minecraft:block_light_absorption {"value": n}，新写法 minecraft:light_dampening n）。

JE（BlockBehaviour.getLightBlock）：方块"实心渲染"（canOcclude、遮挡形状是整格）时挡住全部的光，15；否则 0（天光照样往下）或 1。
FD 1.20 的 ModBlocks 里整格不透明的方块都是 copy 原版的整格方块、类里没改形状：六种箱子 copy(OAK_PLANKS)，稻米捆、稻草捆 copy(HAY_BLOCK)，
米袋、榻榻米 copy(WHITE_WOOL)，十一种橱柜 copy(BARREL)，炉灶 copy(BRICKS)（点着、熄着在 JE 是一个方块），有机肥、沃土 copy(DIRT)：这些写 15。
别的不是整格，光透过去，写 0：厨锅、砧板、煎锅、绳子、安全网、绳栅栏、帆布地毯、榻榻米垫、馅饼、大菜、作物、蘑菇菌落……
两种篮子的碰撞箱是整格，可 JE 的遮挡形状是 1~15 的小盒子（BasketBlock.getOcclusionShape），也透光。
沃土耕地照原版耕地写 0：JE 的 FarmBlock 15/16 高，只有整面的底面挡住往下的光（它自己那格是亮的）；基岩版没有按面挡光，原版耕地不挡光（lightBlock 0）。
网易的旧写法不写吸收 = 不透光（官方文档），所以每个方块都写出来。

挡光的必须是整格、实心、不透明的立方体：画整格方块的面时取面外那一格的亮度，挡不挡光它自己看起来一样；
网易模型、十字花草、薄片取自己那一格的亮度，挡光就画成黑的（tests/test_gleaming_salad.py：网易模型方块要写 0，否则模型会变黑）。
"""
from __future__ import print_function

import io
import os
import re

import blockkit
import fdtest

ALL, NONE = 15, 0
CRATES = ["arris:%s_crate" % crop for crop in ("beetroot", "cabbage", "carrot", "onion", "potato", "tomato")]
CABINETS = ["arris:%s_cabinet" % wood for wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo",
                                                   "crimson", "warped")]
# JE 里挡住全部光的方块：本包的标识 → JE 的注册名（ModBlocks 里 BLOCKS.register 的第一个参数）
JE_OPAQUE = dict([(name, name.split(":")[1]) for name in CRATES + CABINETS + ["arris:rice_bag", "arris:rice_bale", "arris:straw_bale",
                                                                             "arris:stove", "arris:rich_soil", "arris:tatami"]]
                 + [("arris:stove_extinguish", "stove")]                                          # 熄着的炉灶 = JE 炉灶 LIT=false
                 + [("arris:organic_compost_stage%d" % stage, "organic_compost") for stage in range(4)])   # JE 的 COMPOSTING 0~7 分成四个方块
FULL_BOX = {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 1.0]}

JE = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "java", "vectorwing", "farmersdelight", "common")
FULL_VANILLA = ("OAK_PLANKS", "HAY_BLOCK", "WHITE_WOOL", "BARREL", "BRICKS", "DIRT")       # FD copy 的原版整格不透明方块
RESHAPED = re.compile(r"(public|protected)\s+[\w<>\[\]]+\s+(getShape|getOcclusionShape|useShapeForLightOcclusion|propagatesSkylightDown|"
                      r"getLightBlock)\s*\(")


def _blocks():
    """{标识: minecraft:block}：bp/netease_blocks 下（含子目录）的全部方块，连 permutations。"""
    found = {}
    for root, _dirs, files in os.walk(blockkit.BLOCKS_DIR):
        for name in files:
            if name.endswith(".json"):
                block = blockkit.readJson(os.path.join(root, name))["minecraft:block"]
                found[block["description"]["identifier"]] = block
    return found


def _absorption(components):
    """方块挡多少光；没写返回 None（网易的缺省是不透光）。"""
    if "minecraft:light_dampening" in components:
        return components["minecraft:light_dampening"]
    old = components.get("minecraft:block_light_absorption")
    return old["value"] if isinstance(old, dict) else old


def testJavasFullOpaqueBlocksAbsorbAllLight():
    blocks = _blocks()
    wrong = ["%s: %r" % (name, _absorption(blocks[name]["components"])) for name in sorted(JE_OPAQUE)
             if _absorption(blocks[name]["components"]) != ALL]
    assert not wrong, "JE 里挡光的整格方块要写 15：" + ", ".join(wrong)


def testEveryOtherBlockSaysItLetsTheLightThrough():
    wrong = ["%s: %r" % (name, _absorption(block["components"])) for name, block in sorted(_blocks().items())
             if name not in JE_OPAQUE and _absorption(block["components"]) != NONE]
    assert not wrong, "不是整格不透明的方块要写 0（不写 = 不透光）：" + ", ".join(wrong)


def _opaqueInstances(components):
    return all(instance.get("render_method", "opaque") == "opaque" for instance in components.get("minecraft:material_instances", {}).values())


def testOnlyFullSolidOpaqueCubesAbsorbLight():
    resource = blockkit.resourceBlocks()
    for name, block in sorted(_blocks().items()):
        components = block["components"]
        if not _absorption(components):
            continue
        assert components.get("netease:solid") == {"value": True}, name
        box = components.get("netease:aabb")
        assert box is None or (box["clip"] == FULL_BOX and box["collision"] == FULL_BOX), name
        if "minecraft:geometry" in components:
            assert components["minecraft:geometry"] == "minecraft:geometry.full_block", name
            assert all(_opaqueInstances(part["components"]) for part in [block] + block.get("permutations", [])), name
        else:
            assert components["netease:render_layer"] == {"value": "opaque"}, name
        assert "netease_model" not in resource.get(name, {}), name


def _read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _javaRegistrations():
    """{JE 注册名: (方块类, copy 的原版方块或 None, 写没写 noOcclusion)}。"""
    found = {}
    for chunk in _read(os.path.join(JE, "registry", "ModBlocks.java")).split("BLOCKS.register(")[1:]:
        chunk = chunk.split("public static")[0]
        copied = re.search(r"copy\(Blocks\.(\w+)\)", chunk)
        found[re.match(r'\s*"(\w+)"', chunk).group(1)] = (re.search(r"new\s+(\w+)\(", chunk).group(1), copied and copied.group(1),
                                                          "noOcclusion" in chunk)
    return found


def _keepsTheFullCube(className):
    """FD 的这个方块类连同它在 FD 里的父类都没改形状、遮光（找不到文件的是原版的类：Block、BaseEntityBlock、HayBlock……）。"""
    while className:
        path = os.path.join(JE, "block", className + ".java")
        if not os.path.isfile(path):
            return True
        text = _read(path)
        if RESHAPED.search(text):
            return False
        parent = re.search(r"class\s+%s\s+extends\s+(\w+)" % className, text)
        className = parent and parent.group(1)
    return True


def testTheTableIsJavasOwnList():
    if not os.path.isdir(JE):
        print("跳过：没有 JE 的源码（.refs/FarmersDelight）")
        return
    opaque = set(name for name, (className, copied, open_) in _javaRegistrations().items()
                 if copied in FULL_VANILLA and not open_ and _keepsTheFullCube(className))
    assert opaque == set(JE_OPAQUE.values()), sorted(opaque ^ set(JE_OPAQUE.values()))
    assert "cutting_board" not in opaque and "full_tatami_mat" not in opaque, "copy 了整格方块、自己改了形状的不挡光"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
