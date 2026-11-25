# -*- coding: utf-8 -*-
# runner: py3
"""方块烧不烧、棕色蘑菇菌落的亮度、两种蘑菇菌落进创造物品栏，对照 JE（FD 1.3.4）。

JE（Forge）里方块可燃要么在原版 FireBlock 的表里（按方块实例登记，copy 原版方块不会带过来），要么自己覆写 getFireSpreadSpeed / getFlammability：
农夫乐事只有稻米捆、稻草捆（60 / 20）和 WildCropBlock 的六种野生作物（60 / 100）——沙生灌木（BushBlock）、野生稻米（DoublePlantBlock）、
蘑菇菌落都不可燃。基岩：catch_chance_modifier（旧格式 flame_odds）是"挨着火时着起来的几率" = JE 的 getFireSpreadSpeed，
destroy_chance_modifier（旧格式 burn_odds）是"着火后被烧掉的几率" = JE 的 getFlammability（原版木板两边都是 5 / 20）；
1.10 格式的方块写旧名字，1.20 起的写新名字；没写就不可燃。
棕色蘑菇菌落 copy 原版棕色蘑菇，亮度 1（这是发光，和 test_block_light.py 管的挡光是两个组件）。
"""
from __future__ import print_function

import io
import os
import re

import blockkit
import fdtest

JE_DIR = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "java", "vectorwing", "farmersdelight", "common")
WILD = ("cabbages", "onions", "tomatoes", "carrots", "potatoes", "beetroots")
# 基岩标识 -> (挨火着起来, 被烧掉)
FLAMMABLE = dict([("arris:straw_bale", (60, 20)), ("arris:rice_bale", (60, 20))]
                 + [("arris:wild_" + name, (60, 100)) for name in WILD])


def _odds(components):
    found = components.get("minecraft:flammable")
    if found is None or found is False:
        return None
    if "flame_odds" in found or "burn_odds" in found:
        return found.get("flame_odds"), found.get("burn_odds")
    return found.get("catch_chance_modifier"), found.get("destroy_chance_modifier")


def testOnlyJavasFlammableBlocksBurn():
    burning = dict((identifier, _odds(components)) for identifier, (components, _description) in blockkit.blockDefinitions().items()
                   if _odds(components) is not None)
    assert burning == FLAMMABLE, sorted(set(burning.items()) ^ set(FLAMMABLE.items()))


def testTheOldFormatUsesTheOldNames():
    for identifier in FLAMMABLE:
        assert set(blockkit.components(identifier)["minecraft:flammable"]) == set(["flame_odds", "burn_odds"]), identifier


def _read(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def testTheTableIsJavasOwn():
    if not os.path.isdir(JE_DIR):
        print("跳过：没有 JE 的源码（.refs/FarmersDelight）")
        return
    overriding = {}
    for name in ("RiceBaleBlock", "StrawBaleBlock", "WildCropBlock", "SandyShrubBlock", "WildRiceBlock", "MushroomColonyBlock"):
        source = _read(os.path.join(JE_DIR, "block", name + ".java"))
        spread = re.search(r"getFireSpreadSpeed\(.*?return (\d+);", source, re.S)
        burn = re.search(r"getFlammability\(.*?return (\d+);", source, re.S)
        overriding[name] = (int(spread.group(1)), int(burn.group(1))) if spread and burn else None
    assert overriding["RiceBaleBlock"] == overriding["StrawBaleBlock"] == FLAMMABLE["arris:straw_bale"]
    assert overriding["WildCropBlock"] == FLAMMABLE["arris:wild_cabbages"]
    assert overriding["SandyShrubBlock"] is overriding["WildRiceBlock"] is overriding["MushroomColonyBlock"] is None
    wildCrops = re.findall(r'register\("wild_(\w+)",\s*\(\) -> new WildCropBlock', _read(os.path.join(JE_DIR, "registry", "ModBlocks.java")))
    assert sorted(wildCrops) == sorted(WILD)


def testTheBrownColonyGlowsLikeABrownMushroom():
    assert blockkit.components("arris:brown_mushroom_colony")["minecraft:light_emission"] == 1
    assert "minecraft:light_emission" not in blockkit.components("arris:red_mushroom_colony"), "原版红色蘑菇不发光"


def testBothColoniesAreInTheCreativeMenuWithTheWildPlants():
    groups = blockkit.readJson(os.path.join(fdtest.BP, "netease_group", "arris_farmers_delight_group.json"))["groups"]
    wild = [group["list"] for group in groups if group["group_name"] == "itemGroup.name.farmer_wild_crop"][0]
    for color in ("brown", "red"):
        identifier = "arris:%s_mushroom_colony" % color
        description = blockkit.description(identifier)
        assert description["register_to_creative_menu"] is True and description["category"] == "arris_farmers_delight", identifier
        assert identifier in wild, "JE 的 ModItems 用 registerWithTab 登记（进创造物品栏），和野生植物放一组"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
