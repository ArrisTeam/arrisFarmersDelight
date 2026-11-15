# -*- coding: utf-8 -*-
# runner: both
"""作物催熟阶段表与旧 if/elif 链（farmCrop.CropAccelerateTheRipening，1862a1f 及以前）逐项等价。

旧实现的 11 段分支只差"前缀"和"最大阶段"两个数，下面的 _legacyGrow 原样保留它的判断顺序，
对每种作物、每个阶段、每种步数（骨粉 2/3 级，湿润沃土耕地 1 级）对拍。
"""
from __future__ import print_function

import fdtest

CropGrowth = fdtest.load("Shared.Rules.CropGrowth")

_LEGACY_CHAIN = [
    ("arris:cabbages_stage", 7), ("arris:budding_tomatoes_stage", 6), ("arris:tomatoes_vine_stage", 3),
    ("arris:onions_stage", 3), ("arris:rich_soil_wheat", 7), ("arris:rich_soil_beetroot", 3),
    ("arris:rich_soil_carrots", 3), ("arris:rich_soil_potatoes", 3), ("arris:rice_stage", 3),
    ("arris:rice_upper_crop_stage", 3), ("arris:rich_soil_torchflower", 2),
]


def _legacyGrow(blockName, num):
    """旧实现：stage = int(blockName[-1])；命中前缀且 stage < 上限才长，最多到上限；否则不变（None）。"""
    stage = int(blockName[-1])
    for prefix, top in _LEGACY_CHAIN:
        if blockName[:-1] == prefix:
            if stage < top:
                stage = min(stage + num, top)
                return prefix + str(stage)
            return None
    return None


def testMatchesLegacyChainForEveryStage():
    checked = 0
    for prefix, top in _LEGACY_CHAIN:
        for stage in range(0, top + 1):
            name = prefix + str(stage)
            for steps in (1, 2, 3):
                assert CropGrowth.grownName(name, steps) == _legacyGrow(name, steps), (name, steps)
                checked += 1
    assert checked == sum((top + 1) * 3 for _, top in _LEGACY_CHAIN)


def testTableCoversExactlyTheLegacyCrops():
    assert sorted(CropGrowth.CROP_MAX_STAGE.items()) == sorted(_LEGACY_CHAIN)


def testUnknownOrNonNumericNamesDoNotGrow():
    for name in ("arris:rich_soil", "arris:organic_compost_stage2", "minecraft:wheat", "arris:cabbages_stagex", ""):
        assert CropGrowth.grownName(name, 3) is None, name
    assert CropGrowth.splitStage("arris:onions_stage2") == ("arris:onions_stage", 2)
    assert CropGrowth.splitStage("arris:rich_soil") == (None, None)


def testEveryGrowableCropIsInCropsDict():
    # 能被催熟的每个阶段都应该也在 cropsDict 里（随机刻生长走的是那张表）
    cropsDict = fdtest.load("Shared.Data.Farming").cropsDict
    for prefix, top in _LEGACY_CHAIN:
        for stage in range(0, top + 1):
            assert prefix + str(stage) in cropsDict, prefix + str(stage)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
