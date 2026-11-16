# -*- coding: utf-8 -*-
# runner: py3
"""篮子、绳子、安全网、炉灶的硬度、爆炸抗性和炉灶亮度对照 JE（ModBlocks，FD 1.3.4）。

JE：两种篮子 strength(1.5F)；绳子 copy(BROWN_CARPET)…strength(0.2F)；安全网 copy(BROWN_CARPET).strength(0.2F)；
炉灶 copy(Blocks.BRICKS)（strength(2.0F, 6.0F)，要对的工具才掉落）.lightLevel(litBlockEmission(13))，熄灭时亮度 0。
strength(a) 把硬度和爆炸抗性都设成 a。基岩版的 block_light_emission 是 0~1 的比例，引擎 ×15 取整。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

BLOCKS = os.path.join(fdtest.BP, "netease_blocks")

# 方块 -> (硬度, 爆炸抗性)
JE_STRENGTH = {
    "arris_basket": (1.5, 1.5),
    "arris_wooden_basket": (1.5, 1.5),
    "arris_rope": (0.2, 0.2),
    "arris_safety_net": (0.2, 0.2),
    "arris_stove": (2.0, 6.0),
    "arris_stove_extinguish": (2.0, 6.0),
}


def _components(fileName):
    with io.open(os.path.join(BLOCKS, fileName + ".json"), encoding="utf-8-sig") as f:
        return json.loads(f.read())["minecraft:block"]["components"]


def testStrengthMatchesJava():
    for fileName, (hardness, resistance) in sorted(JE_STRENGTH.items()):
        components = _components(fileName)
        assert components["minecraft:destroy_time"]["value"] == hardness, fileName
        assert components["minecraft:explosion_resistance"]["value"] == resistance, fileName


def testLitStoveGivesLightThirteenAndTheBurntOutOneNone():
    lit = _components("arris_stove")["minecraft:block_light_emission"]["emission"]
    assert int(lit * 15) == 13 and int(round(lit * 15)) == 13        # 取整、四舍五入都是 13
    assert _components("arris_stove_extinguish")["minecraft:block_light_emission"]["emission"] == 0


def testStoveNeedsAPickaxeToDropLikeBricks():
    for fileName in ("arris_stove", "arris_stove_extinguish"):
        tier = _components(fileName)["netease:tier"]
        assert tier["digger"] == "pickaxe" and tier["destroy_special"] is True


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
