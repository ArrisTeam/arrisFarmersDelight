# -*- coding: utf-8 -*-
# runner: both
"""有机肥、沃土、蘑菇菌落、稻草的纯规则（Shared/Rules/CompostRules、RichSoilRules、ColonyRules、StrawRules）。

数字都对着 JE：OrganicCompostBlock.randomTick、RichSoilBlock / RichSoilFarmlandBlock、MushroomColonyBlock.tick、
straw_from_* 战利品修改器。
"""
from __future__ import print_function

import random

import fdtest
from farmkit import ScriptRng

Compost = fdtest.load("Shared.Rules.CompostRules")
RichSoil = fdtest.load("Shared.Rules.RichSoilRules")
Colony = fdtest.load("Shared.Rules.ColonyRules")
Straw = fdtest.load("Shared.Rules.StrawRules")
Farming = fdtest.load("Shared.Data.Farming")
Rates = fdtest.load("Shared.Rules.GrowthRates")

# 一格 Bedrock 方块平均隔多少刻轮到一次随机刻：16×16×16 的区段每刻随机挑 randomTickSpeed 个方块
SECTION_BLOCKS = 4096
MINUTE_TICKS = 20 * 60


def _near(a, b, eps=1e-9):
    assert abs(a - b) < eps, (a, b)


# ---------------- 有机肥 ----------------

def testCompostChanceFormula():
    # chance = 0.02 × 催化剂个数 + (露天 0.1 / 被盖住 0.05) + (有水 0.1)
    _near(Compost.jeChance(1, True, False), 0.12)       # 露天，周围只有它自己
    _near(Compost.jeChance(1, False, False), 0.07)      # 在屋顶底下
    _near(Compost.jeChance(1, True, True), 0.22)        # 旁边有水
    _near(Compost.jeChance(27, True, True), 0.74)       # 3×3×3 全是催化剂 + 水
    _near(Compost.jeChance(0, False, False), 0.05)


def testCompostBlockNeedsTwoJeSteps():
    # JE 的 8 档合成 4 个方块：每个方块 2 次前进
    _near(Compost.stageChance(1, True, False), 0.18)    # 3 × 0.12 / 2
    _near(Compost.stageChance(1, True, True), 0.33)
    assert Compost.stageChance(27, True, True) == 1.0   # 0.74 × 3 / 2 封顶


def _jeMinutes(chance):
    # JE：8 次前进，每次平均 1/chance 个随机刻，一格方块平均每 4096 / 3 刻一次随机刻
    return 8.0 / chance * (SECTION_BLOCKS / 3.0) / MINUTE_TICKS


def testCompostTotalTimeMatchesJe():
    for activators, sky, water in ((1, True, False), (1, True, True), (1, False, False), (5, True, True)):
        jeChance = Compost.jeChance(activators, sky, water)
        bedrockTicks = len(Compost.COMPOST_STAGES) / Compost.stageChance(activators, sky, water)
        bedrockMinutes = bedrockTicks * SECTION_BLOCKS / MINUTE_TICKS
        _near(bedrockMinutes, _jeMinutes(jeChance), 1e-6)
    # 原先每刻必长一格：4 个方块约 14 分钟；JE 的是 40-75 分钟（有水 / 没水）
    assert 74 < _jeMinutes(Compost.jeChance(1, True, False)) < 77
    assert 40 < _jeMinutes(Compost.jeChance(1, True, True)) < 43


def testCompostChain():
    stages = Compost.COMPOST_STAGES
    assert [Compost.nextBlock(name) for name in stages] == list(stages[1:]) + ["arris:rich_soil"]
    assert Compost.nextBlock("arris:rich_soil") is None
    assert Compost.nextBlock("minecraft:dirt") is None


def testCompostActivatorTagMatchesJe():
    # farmersdelight:compost_activators
    jeActivators = ["minecraft:brown_mushroom", "minecraft:red_mushroom", "minecraft:podzol", "minecraft:mycelium",
                    "arris:organic_compost_stage0", "arris:rich_soil", "arris:rich_soil_farmland",
                    "arris:brown_mushroom_colony", "arris:red_mushroom_colony"]
    for name in jeActivators:
        assert name in Farming.COMPOST_ACTIVATORS, name
    for name in Compost.COMPOST_STAGES:
        assert name in Farming.COMPOST_ACTIVATORS, name


# ---------------- 沃土 ----------------

def testRichSoilBoostAndDryChances():
    _near(RichSoil.boostChance(), 0.6)              # JE 20% × 3
    _near(RichSoil.dryChance(), 3.0 / 7)            # 湿度 7 → 0 要 7 次不湿的随机刻
    assert RichSoil.WATER_RADIUS == 4


def testHydrationCellsAreTheJeBox():
    cells = list(RichSoil.hydrationCells((10, 64, -3)))
    assert len(cells) == 9 * 9 * 2
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    zs = [c[2] for c in cells]
    assert (min(xs), max(xs)) == (6, 14) and (min(zs), max(zs)) == (-7, 1)
    assert (min(ys), max(ys)) == (64, 65)           # 竖直只看耕地那一层和它上面一层
    assert (10, 65, -3) in cells                     # 正上方有水（水田）也算
    assert (10, 63, -3) not in cells and (15, 64, -3) not in cells


def testUnaffectedByRichSoilTagMatchesJe():
    # farmersdelight:unaffected_by_rich_soil 里属于本模组的那些：菌落、沙地灌木、所有野生作物
    for name in ("arris:sandy_shrub", "arris:brown_mushroom_colony", "arris:red_mushroom_colony", "arris:wild_carrots",
                 "arris:wild_potatoes", "arris:wild_beetroots", "arris:wild_cabbages", "arris:wild_tomatoes",
                 "arris:wild_onions", "arris:wild_rice", "minecraft:short_grass", "minecraft:fern"):
        assert name in Farming.UNAFFECTED_BY_RICH_SOIL, name
    for name in ("arris:cabbages_stage3", "arris:onions_stage1", "arris:rice_stage0", "arris:budding_tomatoes_stage2"):
        assert name not in Farming.UNAFFECTED_BY_RICH_SOIL, name


# ---------------- 蘑菇菌落 ----------------

def testColonyAgesFollowTheBlockStates():
    assert [Colony.ageOfGrowth(g) for g in range(8)] == [0, 0, 0, 0, 1, 1, 2, 3]
    assert [Colony.mushroomsOfGrowth(g) for g in range(8)] == [1, 1, 2, 2, 3, 3, 4, 5]
    assert Colony.GROWTH_OF_AGE == (2, 4, 6, 7)
    for age, growth in enumerate(Colony.GROWTH_OF_AGE):
        assert Colony.ageOfGrowth(growth) == age
    assert Colony.ageOfGrowth(9) == 3 and Colony.ageOfGrowth(-1) == 0


def testColonyGrowsAtThreeQuartersPerTick():
    # JE 25% → Bedrock 75%：年龄 0 → 1 → 2 → 3 三次转变，平均 4 次随机刻，等于 JE 的 12 次 ÷ 3
    _near(Rates.bedrockChance(Rates.COLONY_CHANCE), 0.75)
    for roll, expected in ((0.0, 4), (0.749, 4), (0.75, None), (0.99, None)):
        assert Colony.tickGrowth(2, ScriptRng(randoms=[roll])) == expected, roll
    assert Colony.tickGrowth(4, ScriptRng(randoms=[0.0])) == 6
    assert Colony.tickGrowth(6, ScriptRng(randoms=[0.0])) == 7
    assert Colony.tickGrowth(7, ScriptRng(randoms=[0.0])) is None          # 满龄不再长
    # 旧存档里的非标准状态照年龄走
    assert Colony.tickGrowth(3, ScriptRng(randoms=[0.0])) == 4
    assert Colony.tickGrowth(3, ScriptRng(randoms=[0.9])) is None
    assert Colony.tickGrowth(5, ScriptRng(randoms=[0.0])) == 6


def testSproutLooksLikeAColonyAfterTheFirstTick():
    # 单个蘑菇外观（growth 0、1）：没长成时换成年龄 0 的外观，长成时直接到年龄 1
    for sprout in Colony.SPROUT_GROWTH:
        assert Colony.tickGrowth(sprout, ScriptRng(randoms=[0.9])) == 2
        assert Colony.tickGrowth(sprout, ScriptRng(randoms=[0.1])) == 4


def testColonyTotalTimeMatchesJe():
    rnd = random.Random(7)
    trials = 3000
    total = 0
    for _ in range(trials):
        growth = 2
        ticks = 0
        while growth != 7:
            ticks += 1
            new = Colony.tickGrowth(growth, rnd)
            growth = new if new is not None else growth
        total += ticks
    assert abs(total / float(trials) - 4.0) < 0.2


def testColonyMushroomsBecomeColoniesOnRichSoilOnly():
    assert Colony.MUSHROOM_TO_COLONY["minecraft:brown_mushroom"] == "arris:brown_mushroom_colony"
    assert Colony.MUSHROOM_TO_COLONY["minecraft:red_mushroom"] == "arris:red_mushroom_colony"
    assert Colony.GROWABLE_ON == ("arris:rich_soil",)


# ---------------- 稻草 ----------------

def testStrawChances():
    table = Farming.STRAW_SOURCES
    chance = lambda name, aux=0: Straw.strawChance(table, name, aux)        # noqa: E731
    assert chance("minecraft:short_grass") == 20
    assert chance("minecraft:tall_grass") == 20
    assert chance("arris:sandy_shrub") == 30
    assert chance("arris:rice_upper_crop_stage3") == 100
    assert chance("arris:rich_soil_wheat7") == 100
    assert chance("minecraft:wheat", 7) == 100
    assert chance("minecraft:wheat", 6) == 0               # 麦子没熟没有
    for name in ("minecraft:fern", "minecraft:large_fern", "arris:rice_supporting", "arris:rice_upper_crop_stage2",
                 "arris:rich_soil_wheat6", "minecraft:stone"):
        assert chance(name) == 0, name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
