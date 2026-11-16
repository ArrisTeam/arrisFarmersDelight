# -*- coding: utf-8 -*-
# runner: both
"""种植相关的数据表（Shared/Data/Farming.py）：堆肥表对 JE 的 CommonSetup，野生作物的地面对 JE 的方块标签。"""
from __future__ import print_function

import io
import json
import os

import fdtest

Farming = fdtest.load("Shared.Data.Farming")

# JE CommonSetup.registerCompostables：{概率: [本模组里对应的物品标识]}（JE 物品名 → Bedrock 标识）
JE_COMPOSTABLES = {
    30: ["arris:tree_bark", "arris:straw", "arris:cabbage_seeds", "arris:tomato_seeds", "arris:rice", "arris:rice_panicle",
         "arris:sandy_shrub"],
    50: ["arris:pumpkin_slice", "arris:cabbage_leaf", "arris:kelp_roll_slice"],
    65: ["arris:cabbage", "arris:onion", "arris:tomato", "arris:wild_cabbages", "arris:wild_onions", "arris:wild_tomatoes",
         "arris:wild_carrots", "arris:wild_potatoes", "arris:wild_beetroots", "arris:wild_rice", "arris:pie_crust"],
    85: ["arris:rice_bale", "arris:sweet_berry_cookie", "arris:honey_cookie", "arris:cake_slice", "arris:apple_pie_slice",
         "arris:sweet_berry_cheesecake_slice", "arris:chocolate_pie_slice", "arris:raw_pasta", "arris:rotten_tomato",
         "arris:kelp_roll"],
    # 派的物品形态叫 *_item，填馅南瓜是厨锅做出来的整块（stuffed_pumpkin_block_stage0），菌落是方块物品
    100: ["arris:apple_pie_item", "arris:sweet_berry_cheesecake_item", "arris:chocolate_pie_item", "arris:dumplings",
          "arris:stuffed_pumpkin_block_stage0", "arris:brown_mushroom_colony", "arris:red_mushroom_colony"],
}


def _identifiers():
    found = set()
    for sub, key in (("netease_items_beh", "minecraft:item"), ("netease_blocks", "minecraft:block")):
        for root, _, files in os.walk(os.path.join(fdtest.BP, sub)):
            for name in files:
                if name.endswith(".json"):
                    with io.open(os.path.join(root, name), encoding="utf-8") as handle:
                        found.add(json.load(handle)[key]["description"]["identifier"])
    return found


def testComposterTableIsJeCommonSetup():
    expected = {}
    for percent, names in JE_COMPOSTABLES.items():
        for name in names:
            expected[(name, 0)] = percent
    assert Farming.ComposterItemDict == expected
    assert len(Farming.ComposterItemDict) == 38


def testEveryCompostableIsARealItemOrBlock():
    identifiers = _identifiers()
    for name, aux in Farming.ComposterItemDict:
        assert name in identifiers, name
        assert aux == 0


def testComposterChancesAreWholePercents():
    for percent in Farming.ComposterItemDict.values():
        assert isinstance(percent, int) and 0 < percent <= 100


# JE 1.20.1：BlockTags.DIRT = dirt、grass_block、podzol、coarse_dirt、mycelium、rooted_dirt、moss_block、mud、muddy_mangrove_roots，
# FD 再把 rich_soil 加进去；BlockTags.SAND = sand、red_sand
JE_WILD_GROUND = ["minecraft:dirt", "minecraft:grass_block", "minecraft:podzol", "minecraft:coarse_dirt", "minecraft:mycelium",
                  "minecraft:dirt_with_roots", "minecraft:moss_block", "minecraft:mud", "minecraft:muddy_mangrove_roots",
                  "arris:rich_soil", "minecraft:sand", "minecraft:red_sand"]


def testWildCropsGrowOnTheJeDirtAndSandTags():
    for plant in ("beetroots", "carrots", "cabbages", "onions", "rice", "tomatoes", "potatoes"):
        ground = Farming.WildCropDict["arris:wild_" + plant]
        for name in JE_WILD_GROUND:
            assert name in ground, (plant, name)
        assert "minecraft:farmland" in ground                  # Bedrock 的 dirt 标签里有耕地，早先就能种，留着
    # 每种持有自己的一份拷贝
    grounds = [Farming.WildCropDict["arris:wild_" + p] for p in ("beetroots", "carrots", "cabbages")]
    assert grounds[0] is not grounds[1] and grounds[1] is not grounds[2]


def testSandyShrubOnlyOnSand():
    assert sorted(Farming.WildCropDict["arris:sandy_shrub"]) == ["minecraft:red_sand", "minecraft:sand"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
