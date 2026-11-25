# -*- coding: utf-8 -*-
# runner: both
"""作物、野生作物、沙地灌木的掉落（bp/loot_tables）与 JE 的战利品表一致（蘑菇菌落见 test_mushroom_colony_loot.py）。

期望值来自 FarmersDelight 1.3.4 的 data/farmersdelight/loot_tables/blocks/*.json（时运 / 爆炸衰减那两项不在表里：
时运由 Server/FortuneDrops 在方块被打掉时补，见 test_fortune_bonus.py；爆炸衰减不搬）：
用 loottest.py 精确算出每件物品每种数量的概率，再和 JE 对账；方块定义里的战利品表路径也对一遍。
"""
from __future__ import print_function

import io
import json
import os
import re

import fdtest
import loottest as L

CropGrowth = fdtest.load("Shared.Rules.CropGrowth")

SHEARS = "minecraft:shears"
# apply_bonus binomial_with_bonus_count，extra 3，probability 0.5714286（4/7）：3 次摇骰各 4/7 出一个
BIN = [27.0 / 343, 108.0 / 343, 144.0 / 343, 64.0 / 343]


def _near(a, b, eps=1e-9):
    assert abs(a - b) < eps, (a, b)


def _drops(name, tool=None):
    return L.evaluate(L.load(name), tool)


def _exactly(dist, count):
    _near(L.prob(dist, count), 1.0)


def _binomialPlus(dist, base):
    """数量 = base + Binomial(3, 4/7)。"""
    for extra, probability in enumerate(BIN):
        _near(L.prob(dist, base + extra), probability)
    assert L.spread(dist) == (base, base + 3)


# ---------------- 卷心菜 / 洋葱 / 番茄 / 稻米 ----------------

def testMatureCabbage():
    drops = _drops("mature_cabbages.json")
    _exactly(drops["arris:cabbage"], 1)
    _binomialPlus(drops["arris:cabbage_seeds"], 1)          # 1 个底子 + binomial(3, 4/7)
    assert sorted(drops) == ["arris:cabbage", "arris:cabbage_seeds"]


def testImmatureCabbageOnionAndBudding():
    _exactly(_drops("immaturate_cabbages.json")["arris:cabbage_seeds"], 1)
    _exactly(_drops("immaturate_onions.json")["arris:onion"], 1)       # JE：没熟的洋葱掉一个洋葱
    _exactly(_drops("immaturate_tomatoes.json")["arris:tomato_seeds"], 1)
    assert list(_drops("immaturate_tomatoes.json")) == ["arris:tomato_seeds"]


def testMatureOnion():
    drops = _drops("mature_onions.json")
    _binomialPlus(drops["arris:onion"], 2)                    # 保底 1 + 额外池的 1 + binomial(3, 4/7)
    assert list(drops) == ["arris:onion"]


def testMatureTomatoOnTheGround():
    drops = _drops("mature_tomatoes.json")
    _near(L.prob(drops["arris:tomato"], 1), 0.5)
    _near(L.prob(drops["arris:tomato"], 2), 0.5)
    _exactly(drops["arris:tomato_seeds"], 1)
    _near(L.prob(drops["arris:rotten_tomato"], 1), 0.05)
    assert sorted(drops) == ["arris:rotten_tomato", "arris:tomato", "arris:tomato_seeds"]


def testMatureHangingTomatoHasNoSeeds():
    drops = _drops("mature_tomato_vines.json")
    _near(L.prob(drops["arris:tomato"], 1), 0.5)
    _near(L.prob(drops["arris:tomato"], 2), 0.5)
    _near(L.prob(drops["arris:rotten_tomato"], 1), 0.05)
    assert sorted(drops) == ["arris:rotten_tomato", "arris:tomato"]
    assert L.evaluate(L.load("air_loot.json")) == {}


def testRiceDrops():
    _exactly(_drops("rice_crop.json")["arris:rice"], 1)
    _exactly(_drops("rice_upper_riped.json")["arris:rice_panicle"], 1)      # 刀收成稻米由脚本换（Server/Straw.py）


# ---------------- 野生作物 / 沙地灌木 ----------------

def _wild(name, plant, crop=None, cropChance=None, seeds=None, tool=None):
    """野生作物：没剪刀时 crop（cropChance 或必掉）+ seeds；剪刀只掉 plant 本身。"""
    drops = _drops(name, tool)
    if tool == SHEARS:
        assert sorted(drops) == [plant], drops
        _exactly(drops[plant], 1)
        return drops
    assert plant not in drops
    if crop:
        _near(L.prob(drops[crop], 1), cropChance if cropChance else 1.0)
    if seeds:
        _exactly(drops[seeds], 1)
    return drops


def testWildCabbagesBeetrootsTomatoesDropTwentyPercentCropAndASeed():
    for name, plant, crop, seeds in (("wild_cabbages.json", "arris:wild_cabbages", "arris:cabbage", "arris:cabbage_seeds"),
                                     ("wild_beetroots.json", "arris:wild_beetroots", "minecraft:beetroot", "minecraft:beetroot_seeds"),
                                     ("wild_tomatoes.json", "arris:wild_tomatoes", "arris:tomato", "arris:tomato_seeds")):
        for tool in (None, "minecraft:iron_axe"):
            drops = _wild(name, plant, crop, 0.2, seeds, tool)
            assert sorted(drops) == sorted([crop, seeds]), drops
        _wild(name, plant, tool=SHEARS)


def testWildCarrotsPotatoesOnionsRice():
    drops = _wild("wild_carrots.json", "arris:wild_carrots", "minecraft:carrot")
    assert list(drops) == ["minecraft:carrot"]
    drops = _wild("wild_potatoes.json", "arris:wild_potatoes", "minecraft:potato")
    assert list(drops) == ["minecraft:potato"]                  # 从不掉毒马铃薯
    drops = _wild("wild_onions.json", "arris:wild_onions", "arris:onion")
    assert sorted(drops) == ["arris:onion", "minecraft:allium"]
    for count in (1, 2, 3):
        _near(L.prob(drops["minecraft:allium"], count), 1.0 / 3)
    drops = _wild("wild_rice.json", "arris:wild_rice", "arris:rice")
    assert list(drops) == ["arris:rice"]
    for name, plant in (("wild_carrots.json", "arris:wild_carrots"), ("wild_potatoes.json", "arris:wild_potatoes"),
                        ("wild_onions.json", "arris:wild_onions"), ("wild_rice.json", "arris:wild_rice")):
        _wild(name, plant, tool=SHEARS)


def testSandyShrub():
    drops = _drops("sandy_shrub.json")
    assert list(drops) == ["minecraft:beetroot_seeds"]
    _near(L.prob(drops["minecraft:beetroot_seeds"], 1), 0.125)
    drops = _drops("sandy_shrub.json", SHEARS)
    assert list(drops) == ["arris:sandy_shrub"]
    _exactly(drops["arris:sandy_shrub"], 1)
    assert list(_drops("sandy_shrub.json", "minecraft:iron_axe")) == ["minecraft:beetroot_seeds"]


def testShearsConditionNeedsARealToolInHand():
    # match_tool 对空手也会成立（引擎只跳过 item 检查）：表里必须同时限定 count
    for name in ("wild_cabbages.json", "wild_rice.json", "sandy_shrub.json"):
        text = json.dumps(L.load(name))
        assert '"item": "minecraft:shears"' in text and '"count": 1' in text, name
    assert "arris:sandy_shrub" in _drops("sandy_shrub.json", SHEARS)
    assert "arris:sandy_shrub" not in _drops("sandy_shrub.json", None)


def testLootTablesUseBareConditionNames():
    # 引擎按原文查条件名，带 minecraft: 前缀的会被静默丢掉，条目就变成必掉
    folder = os.path.join(fdtest.BP, "loot_tables")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            text = io.open(os.path.join(folder, name), encoding="utf-8").read()
            assert '"condition": "minecraft:' not in text, name


# ---------------- 方块 → 战利品表 ----------------

def _lootOf(identifier):
    folder = os.path.join(fdtest.BP, "netease_blocks")
    for root, _, files in os.walk(folder):
        for name in files:
            if name.endswith(".json"):
                with io.open(os.path.join(root, name), encoding="utf-8") as handle:
                    block = json.load(handle)["minecraft:block"]
                if block["description"]["identifier"] == identifier:
                    loot = block["components"]["minecraft:loot"]
                    return loot["table"] if isinstance(loot, dict) else loot
    raise AssertionError("找不到方块 " + identifier)


def testBlocksUseTheRightLootTables():
    table = lambda stage, prefix: _lootOf(CropGrowth.stageName(prefix, stage))     # noqa: E731
    for stage in range(7):
        assert table(stage, "arris:cabbages_stage") == "loot_tables/immaturate_cabbages.json"
    assert table(7, "arris:cabbages_stage") == "loot_tables/mature_cabbages.json"
    for stage in range(3):
        assert table(stage, "arris:onions_stage") == "loot_tables/immaturate_onions.json"
    assert table(3, "arris:onions_stage") == "loot_tables/mature_onions.json"
    for stage in range(6):
        assert table(stage, "arris:budding_tomatoes_stage") == "loot_tables/immaturate_tomatoes.json"
    assert table(6, "arris:budding_tomatoes_stage") == "loot_tables/mature_tomatoes.json"
    for stage in range(3):
        assert table(stage, "arris:tomatoes_vine_stage") == "loot_tables/air_loot.json"
    assert table(3, "arris:tomatoes_vine_stage") == "loot_tables/mature_tomato_vines.json"
    for stage in range(4):
        assert table(stage, "arris:rice_stage") == "loot_tables/rice_crop.json"
    assert _lootOf("arris:rice_supporting") == "loot_tables/rice_crop.json"
    for stage in range(3):
        assert table(stage, "arris:rice_upper_crop_stage") == "loot_tables/air_loot.json"
    assert table(3, "arris:rice_upper_crop_stage") == "loot_tables/rice_upper_riped.json"
    for wild in ("beetroots", "carrots", "cabbages", "onions", "potatoes", "rice", "tomatoes"):
        assert _lootOf("arris:wild_" + wild) == "loot_tables/wild_%s.json" % wild
    assert _lootOf("arris:sandy_shrub") == "loot_tables/sandy_shrub.json"


def testEveryReferencedLootTableExists():
    folder = os.path.join(fdtest.BP, "netease_blocks")
    for root, _, files in os.walk(folder):
        for name in files:
            if not name.endswith(".json"):
                continue
            text = io.open(os.path.join(root, name), encoding="utf-8").read()
            for table in set(re.findall(r'"(loot_tables/[^"]+\.json)"', text)):
                assert os.path.isfile(os.path.join(fdtest.BP, table)), (name, table)


# 沃土上的原版作物（成熟的 arris:rich_soil_wheat7 / carrots3 / potatoes3 / beetroot3）照基岩原版作物掉：数据来自 2026-11-26 的实机测量（INGAME-FACTS-1 §3，不带工具打掉成熟作物，
# 每种 196~980 株）。额外的 0~3 个合起来 p = 0.529 ± 0.008，按 Binomial(3, 8/15) 写（权重 343 : 1176 : 1344 : 512）——是按数据推的模型，
# 不是读到的源码；土豆另有独立的 2% 毒马铃薯（有毒马铃薯的那几次土豆照掉）；甜菜根 1 或 2 个各一半
B815 = [343.0 / 3375, 1176.0 / 3375, 1344.0 / 3375, 512.0 / 3375]


def _binomial815(dist, base):
    for extra, probability in enumerate(B815):
        _near(L.prob(dist, base + extra), probability, 1e-6)
    assert L.spread(dist) == (base, base + 3)


def testRichSoilVanillaCropsDropLikeBedrockVanillaCrops():
    wheat = _drops("crops/wheat_riped.json")
    _exactly(wheat["minecraft:wheat"], 1)
    _binomial815(wheat["minecraft:wheat_seeds"], 0)
    carrots = _drops("crops/carrot_riped.json")
    _binomial815(carrots["minecraft:carrot"], 1)
    potatoes = _drops("crops/potato_riped.json")
    _binomial815(potatoes["minecraft:potato"], 1)
    _near(L.prob(potatoes["minecraft:poisonous_potato"], 1), 0.02)
    beetroots = _drops("crops/beetroot_riped.json")
    _near(L.prob(beetroots["minecraft:beetroot"], 1), 0.5)
    _near(L.prob(beetroots["minecraft:beetroot"], 2), 0.5)
    _binomial815(beetroots["minecraft:beetroot_seeds"], 0)
    assert sorted(wheat) == ["minecraft:wheat", "minecraft:wheat_seeds"] and list(carrots) == ["minecraft:carrot"]
    assert sorted(potatoes) == ["minecraft:poisonous_potato", "minecraft:potato"]
    assert sorted(beetroots) == ["minecraft:beetroot", "minecraft:beetroot_seeds"]


def testRichSoilRipeCropsUseThoseTables():
    for crop, table in (("wheat7", "wheat"), ("carrots3", "carrot"), ("potatoes3", "potato"), ("beetroot3", "beetroot")):
        assert _lootOf("arris:rich_soil_" + crop) == "loot_tables/crops/%s_riped.json" % table, crop


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
