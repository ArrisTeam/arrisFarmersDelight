# -*- coding: utf-8 -*-
# runner: both
"""作物阶段表（Shared/Rules/CropGrowth.py）：每一级方块覆盖 JE 的哪几个年龄，与方块定义、cropsDict 对得上。

阶段表原来只有"最大阶段"一列（旧催熟表），现在每族还带 JE 年龄的分段、各次转变的概率和骨粉算法；
旧的 11 族与最大阶段仍然一一对应。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

CropGrowth = fdtest.load("Shared.Rules.CropGrowth")
Farming = fdtest.load("Shared.Data.Farming")

# 旧催熟表（farmCrop.CropAccelerateTheRipening）里的 11 族与最大阶段
_LEGACY_CHAIN = [
    ("arris:cabbages_stage", 7), ("arris:budding_tomatoes_stage", 6), ("arris:tomatoes_vine_stage", 3),
    ("arris:onions_stage", 3), ("arris:rich_soil_wheat", 7), ("arris:rich_soil_beetroot", 3),
    ("arris:rich_soil_carrots", 3), ("arris:rich_soil_potatoes", 3), ("arris:rice_stage", 3),
    ("arris:rice_upper_crop_stage", 3), ("arris:rich_soil_torchflower", 2),
]


def _blockIdentifiers():
    found = set()
    blocks = os.path.join(fdtest.BP, "netease_blocks")
    for folder, _, files in os.walk(blocks):
        for name in files:
            if name.endswith(".json"):
                with io.open(os.path.join(folder, name), encoding="utf-8") as handle:
                    data = json.load(handle)
                found.add(data["minecraft:block"]["description"]["identifier"])
    return found


def testTableCoversExactlyTheLegacyCrops():
    assert sorted(CropGrowth.CROP_MAX_STAGE.items()) == sorted(_LEGACY_CHAIN)
    assert sorted(CropGrowth.FAMILIES) == sorted(prefix for prefix, _ in _LEGACY_CHAIN)


def testSplitStage():
    assert CropGrowth.splitStage("arris:onions_stage2") == ("arris:onions_stage", 2)
    assert CropGrowth.splitStage("arris:budding_tomatoes_stage6") == ("arris:budding_tomatoes_stage", 6)
    assert CropGrowth.splitStage("arris:rich_soil") == (None, None)
    for name in ("arris:organic_compost_stage2", "minecraft:wheat", "arris:cabbages_stagex", "arris:onions_stage4",
                 "arris:cabbages_stage8", "arris:rich_soil_torchflower3", ""):
        assert CropGrowth.splitStage(name) == (None, None), name


def testAgeRangesTileTheJeAgeAxis():
    # 每一级覆盖一段连续的 JE 年龄，所有级拼起来正好是 0..maxAge，没有空洞也不重叠
    for prefix in CropGrowth.FAMILIES:
        covered = []
        for stage in range(CropGrowth.lastStage(prefix) + 1):
            low, high = CropGrowth.ageRange(prefix, stage)
            assert low <= high
            covered.extend(range(low, high + 1))
            for age in range(low, high + 1):
                assert CropGrowth.stageOfAge(prefix, age) == stage, (prefix, stage, age)
        assert covered == list(range(CropGrowth.maxAge(prefix) + 1)), prefix
        assert CropGrowth.stageOfAge(prefix, 99) == CropGrowth.lastStage(prefix)


def testRatesCoverEveryJeTransition():
    for prefix, spec in CropGrowth.FAMILIES.items():
        assert len(spec["rates"]) == CropGrowth.maxAge(prefix), prefix


def testOnionCarrotPotatoAgesFollowJeBlockstate():
    # farmersdelight blockstates/onions.json：age 0,1 → stage0；2,3 → stage1；4,5,6 → stage2；7 → stage3
    for prefix in ("arris:onions_stage", "arris:rich_soil_carrots", "arris:rich_soil_potatoes"):
        assert [CropGrowth.stageOfAge(prefix, age) for age in range(8)] == [0, 0, 1, 1, 2, 2, 2, 3], prefix


def testTomatoAgeAxisJoinsBuddingAndTomatoCrop():
    prefix = "arris:budding_tomatoes_stage"
    # JE 年龄轴：budding 0-3、番茄 0-3 共 8 个；budding 的最大年龄（3）并进第 2 级，所以 Bedrock 只有 7 级
    assert [CropGrowth.stageOfAge(prefix, age) for age in range(8)] == [0, 1, 2, 2, 3, 4, 5, 6]
    assert CropGrowth.ageRange(prefix, 2) == (2, 3)


def testEveryStageHasABlockAndIsInCropsDict():
    identifiers = _blockIdentifiers()
    for prefix in CropGrowth.FAMILIES:
        for stage in range(CropGrowth.lastStage(prefix) + 1):
            name = CropGrowth.stageName(prefix, stage)
            assert name in identifiers, name
            assert name in Farming.cropsDict, name       # 随机刻生长走的是 cropsDict 登记的方块
        assert CropGrowth.stageName(prefix, CropGrowth.lastStage(prefix) + 1) not in identifiers, prefix


def testIsFamilyBlock():
    assert CropGrowth.isFamilyBlock("arris:cabbages_stage3", "arris:cabbages_stage")
    assert not CropGrowth.isFamilyBlock("arris:onions_stage3", "arris:cabbages_stage")
    assert CropGrowth.isFamilyBlock("arris:budding_tomatoes_stage1", "arris:budding_tomatoes_stage", (0, 1, 2))
    assert not CropGrowth.isFamilyBlock("arris:budding_tomatoes_stage4", "arris:budding_tomatoes_stage", (0, 1, 2))
    assert not CropGrowth.isFamilyBlock("minecraft:air", "arris:cabbages_stage")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
