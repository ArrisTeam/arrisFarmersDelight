# -*- coding: utf-8 -*-
# runner: both
"""蘑菇菌落的掉落与方块定义（bp/loot_tables/arris_*_mushroom_colony*.json、netease_blocks/*_mushroom_colony.json）。

JE 的菌落年龄 0-3 掉 2/3/4/5 个蘑菇，剪刀剪满龄的掉菌落本身（loot_tables/blocks/*_mushroom_colony.json）；
Bedrock 方块的 arris:growth 0-7 与年龄的对应写在 Shared/Rules/ColonyRules.py，这里把它和方块 JSON 里的贴图、战利品表对一遍。
"""
from __future__ import print_function

import io
import json
import os

import fdtest
import loottest as L

Colony = fdtest.load("Shared.Rules.ColonyRules")

SHEARS = "minecraft:shears"


def _near(a, b, eps=1e-9):
    assert abs(a - b) < eps, (a, b)


def _drops(name, tool=None):
    return L.evaluate(L.load(name), tool)


def _exactly(dist, count):
    _near(L.prob(dist, count), 1.0)


def _colonyBlock(color):
    path = os.path.join(fdtest.BP, "netease_blocks", "%s_mushroom_colony.json" % color)
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)["minecraft:block"]


def testColonyDropsFollowJeAges():
    for color in ("brown", "red"):
        mushroom = "minecraft:%s_mushroom" % color
        colony = "arris:%s_mushroom_colony" % color
        for age, count in enumerate((2, 3, 4)):
            drops = _drops("arris_%s_mushroom_colony%d.json" % (color, age))
            _exactly(drops[mushroom], count)
            assert list(_drops("arris_%s_mushroom_colony%d.json" % (color, age), SHEARS)) == [mushroom]   # 没长满：剪刀也只掉蘑菇
        drops = _drops("arris_%s_mushroom_colony3.json" % color)
        _exactly(drops[mushroom], 5)
        assert list(drops) == [mushroom]
        drops = _drops("arris_%s_mushroom_colony3.json" % color, SHEARS)
        assert list(drops) == [colony]                      # 剪刀剪满龄的菌落：掉菌落本身
        _exactly(drops[colony], 1)
        _exactly(_drops("arris_%s_mushroom_colony_sprout.json" % color)[mushroom], 1)


def testColonyBlockGrowthStatesMatchTheRules():
    # 方块定义里每个 arris:growth 的战利品与贴图，必须和 ColonyRules 的年龄对应一致
    for color in ("brown", "red"):
        block = _colonyBlock(color)
        assert block["description"]["properties"]["arris:growth"] == list(range(8))
        textures = {}
        for permutation in block["permutations"]:
            growth = int(permutation["condition"].rsplit("==", 1)[1])
            table = permutation["components"]["minecraft:loot"]
            drops = L.evaluate(json.load(io.open(os.path.join(fdtest.BP, table), encoding="utf-8")))
            _exactly(drops["minecraft:%s_mushroom" % color], Colony.mushroomsOfGrowth(growth))
            textures[growth] = permutation["components"]["minecraft:material_instances"]["*"]["texture"]
        assert sorted(textures) == list(range(8))
        # 每个年龄的"标准状态"贴图正好是 JE 的 stage0-3；单个蘑菇的外观只有 growth 0、1
        for age, growth in enumerate(Colony.GROWTH_OF_AGE):
            assert textures[growth] == "%s_mushroom_colony_stage%d" % (color, age), (color, age)
        for growth in range(8):
            age = Colony.ageOfGrowth(growth)
            if growth in Colony.SPROUT_GROWTH:
                assert textures[growth] == "mushroom_%s" % color
            else:
                assert textures[growth] == "%s_mushroom_colony_stage%d" % (color, age), (color, growth)

if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
