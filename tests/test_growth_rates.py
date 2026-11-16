# -*- coding: utf-8 -*-
# runner: both
"""作物生长的概率公式（Shared/Rules/GrowthRates.py）：JE 的 CropBlock 公式与 Bedrock 随机刻的换算。

期望值都是照 JE 源码手算的：CropBlock.getGrowthSpeed + random.nextInt((int)(25.0F / speed) + 1) == 0。
"""
from __future__ import print_function

import fdtest

Rates = fdtest.load("Shared.Rules.GrowthRates")


def _near(a, b, eps=1e-9):
    assert abs(a - b) < eps, (a, b)


def testTickRatioIsThree():
    # JE 随机刻速度 3、Bedrock 1：同样时间 Bedrock 只轮到三分之一次
    assert Rates.TICK_RATIO == 3.0


def testBedrockChanceMultipliesByThreeAndCapsAtOne():
    _near(Rates.bedrockChance(0.25), 0.75)
    _near(Rates.bedrockChance(0.2), 0.6)
    _near(Rates.bedrockChance(1.0 / 7), 3.0 / 7)
    assert Rates.bedrockChance(0.5) == 1.0
    assert Rates.bedrockChance(1.0) == 1.0
    assert Rates.bedrockChance(0.0) == 0.0


def testBedrockChanceStepsDivideTheChance():
    # Bedrock 一级相当于 JE 连续 n 次转变：等的随机刻数相加，概率就除以 n（没封顶时）
    _near(Rates.bedrockChance(1.0 / 13, 2), 3.0 / 26)
    _near(Rates.bedrockChance(1.0 / 3, 2), 0.5)
    _near(Rates.bedrockChance(1.0 / 3, 3), 1.0 / 3)
    assert Rates.bedrockChance(1.0 / 3, 1) == 1.0


def testBedrockChanceOfMixedChances():
    # 一次 1/3 加一次 1/6：JE 平均等 3 + 6 = 9 次随机刻，Bedrock 平均等 3 次
    _near(Rates.bedrockChanceOf([1.0 / 3, 1.0 / 6]), 1.0 / 3)
    assert Rates.bedrockChanceOf([0.5, 0.0]) == 0.0
    assert Rates.bedrockChanceOf([]) == 0.0


def testVanillaChanceMatchesNextIntFormula():
    # nextInt((int)(25 / speed) + 1) == 0 → 1 / (floor(25 / speed) + 1)
    expected = {1.0: 26, 2.0: 13, 2.5: 11, 4.0: 7, 5.0: 6, 10.0: 3, 3.25: 8, 12.5: 3}
    for speed, denominator in expected.items():
        _near(Rates.vanillaChance(speed), 1.0 / denominator)


def testFixedChancesOfRiceAndTomato():
    # RiceBlock：chance = 10 → nextInt(3)；TomatoBlock：speed = 5 → nextInt(6)
    _near(Rates.RICE_CHANCE, 1.0 / 3)
    _near(Rates.TOMATO_CHANCE, 1.0 / 6)
    assert Rates.CROP_LIGHT == 9 and Rates.RICE_LIGHT == 6


def testGrowthSpeedOfWholePlots():
    moist, dry = 3.0, 1.0
    _near(Rates.growthSpeed(moist, [moist] * 8, False, False, False), 10.0)     # 3×3 全是湿耕地
    _near(Rates.growthSpeed(dry, [dry] * 8, False, False, False), 4.0)          # 3×3 全是干耕地
    _near(Rates.growthSpeed(moist, [0.0] * 8, False, False, False), 4.0)        # 只有脚下一块湿耕地
    _near(Rates.growthSpeed(dry, [0.0] * 8, False, False, False), 2.0)          # 只有脚下一块干耕地
    _near(Rates.growthSpeed(0.0, [0.0] * 8, False, False, False), 1.0)          # 脚下不是耕地


def testGrowthSpeedHalvesForNeighbouringCrops():
    ring = [3.0] * 8
    _near(Rates.growthSpeed(3.0, ring, True, True, False), 5.0)     # 东西、南北两个方向都挨着
    _near(Rates.growthSpeed(3.0, ring, False, False, True), 5.0)    # 只在斜角挨着
    _near(Rates.growthSpeed(3.0, ring, True, False, False), 10.0)   # 只有一个方向（一排作物）不减半
    _near(Rates.growthSpeed(3.0, ring, True, False, True), 5.0)     # 一个方向加斜角：减半（只减一次）
    _near(Rates.growthSpeed(3.0, ring, True, True, True), 5.0)      # 减半只算一次


def testChancesForCommonFields():
    # 把公式串起来：满湿 3×3 的田，JE 每次随机刻 1/3；Bedrock 每次随机刻必长
    speed = Rates.growthSpeed(3.0, [3.0] * 8, False, False, False)
    assert Rates.bedrockChance(Rates.vanillaChance(speed)) == 1.0
    # 只有脚下一块湿耕地：1/7，Bedrock 每次随机刻 3/7
    speed = Rates.growthSpeed(3.0, [0.0] * 8, False, False, False)
    _near(Rates.bedrockChance(Rates.vanillaChance(speed)), 3.0 / 7)
    # 干耕地孤零零一块：1/13
    speed = Rates.growthSpeed(1.0, [0.0] * 8, False, False, False)
    _near(Rates.bedrockChance(Rates.vanillaChance(speed)), 3.0 / 13)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
