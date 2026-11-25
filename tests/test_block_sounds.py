# -*- coding: utf-8 -*-
# runner: py3
"""方块的音效（rp/blocks.json 的 sound）对照 JE 的 SoundType（FD 1.3.4 的 ModBlocks）：厨锅、煎锅是 LANTERN，五种大份菜（feastProperties）是 WOOD，
樱花木 / 竹 / 绯红木 / 诡异木橱柜各是 CHERRY_WOOD / BAMBOO_WOOD / NETHER_WOOD（别的橱柜 copy 木桶：WOOD），竹篮 BAMBOO_WOOD、木篮 WOOD，
有机堆肥 CROP。基岩没有 CROP：原版作物（小麦……）在 blocks.json 里写 grass，就用 grass。写的值都得是原版 blocks.json 里出现过的。
"""
from __future__ import print_function

import io
import json
import os
import re

import blockkit
import fdtest

JE_BLOCKS = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "java", "vectorwing", "farmersdelight", "common",
                         "registry", "ModBlocks.java")
# JE 的 SoundType -> 基岩 blocks.json 的 sound（原版方块写的那个）
JE_TO_BEDROCK = {"LANTERN": "lantern", "WOOD": "wood", "CHERRY_WOOD": "cherry_wood", "BAMBOO_WOOD": "bamboo_wood",
                 "NETHER_WOOD": "nether_wood", "CROP": "grass", "WOOL": "cloth"}
FEASTS = ("honey_glazed_ham_block", "roast_chicken_block", "shepherds_pie_block", "rice_roll_medley_block", "stuffed_pumpkin_block")
# JE 注册名 -> 这边的方块（JE 的竹篮叫 bamboo_basket，这边是 arris:basket）
NAMES = {"cooking_pot": "arris:cooking_pot", "skillet": "arris:skillet", "wooden_basket": "arris:wooden_basket",
         "bamboo_basket": "arris:basket", "cherry_cabinet": "arris:cherry_cabinet", "bamboo_cabinet": "arris:bamboo_cabinet",
         "crimson_cabinet": "arris:crimson_cabinet", "warped_cabinet": "arris:warped_cabinet", "oak_cabinet": "arris:oak_cabinet",
         "organic_compost": "arris:organic_compost_stage"}


def _sounds():
    return dict((name, entry.get("sound")) for name, entry in blockkit.resourceBlocks().items() if isinstance(entry, dict))


def _expected():
    expected = {"arris:cooking_pot": "lantern", "arris:skillet": "lantern", "arris:wooden_basket": "wood", "arris:basket": "bamboo_wood",
                "arris:cherry_cabinet": "cherry_wood", "arris:bamboo_cabinet": "bamboo_wood", "arris:crimson_cabinet": "nether_wood",
                "arris:warped_cabinet": "nether_wood"}
    for wood in ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove"):
        expected["arris:%s_cabinet" % wood] = "wood"
    for name in _sounds():
        if any(name.startswith("arris:" + feast) for feast in FEASTS):
            expected[name] = "wood"
        if name.startswith("arris:organic_compost_stage"):
            expected[name] = "grass"
    return expected


def testSoundsFollowJavasSoundTypes():
    sounds, expected = _sounds(), _expected()
    assert len([name for name in expected if "compost" in name]) == 4
    assert len([name for name in expected if any(feast in name for feast in FEASTS)]) >= 20
    wrong = sorted((name, sounds.get(name), sound) for name, sound in expected.items() if sounds.get(name) != sound)
    assert not wrong, wrong


def testEverySoundIsOneTheVanillaBlocksUse():
    path = fdtest.vanilla("blocks.json")
    if path is None:
        print("跳过：本机没有游戏目录")
        return
    with io.open(path, encoding="utf-8-sig") as handle:
        vanilla = json.loads(re.sub(r"//[^\n]*", "", handle.read()))
    known = set(entry.get("sound") for entry in vanilla.values() if isinstance(entry, dict))
    unknown = sorted((name, sound) for name, sound in _sounds().items() if sound and sound not in known)
    assert not unknown, unknown
    for je, bedrock in JE_TO_BEDROCK.items():
        assert bedrock in known, je
    assert vanilla["wheat"]["sound"] == "grass" and vanilla["cherry_planks"]["sound"] == "cherry_wood"


def _jeSoundType(source, name):
    found = re.search(r'register\("%s",\s*\(\) -> new \w+\((.*?)\)\);' % name, source, re.S)
    assert found, name
    body = found.group(1)
    explicit = re.search(r"sound\(SoundType\.(\w+)\)", body)
    if explicit:
        return explicit.group(1)
    if "feastProperties()" in body or "copy(Blocks.BARREL)" in body:
        return "WOOD"
    raise AssertionError("看不出 %s 的 SoundType：%s" % (name, body[:120]))


def testTheTableIsJavasOwn():
    if not os.path.isfile(JE_BLOCKS):
        print("跳过：没有 JE 的源码（.refs/FarmersDelight）")
        return
    source = io.open(JE_BLOCKS, encoding="utf-8").read()
    sounds = _sounds()
    for je, ours in NAMES.items():
        bedrock = JE_TO_BEDROCK[_jeSoundType(source, je)]
        mine = sounds[ours + "0"] if ours.endswith("_stage") else sounds[ours]
        assert mine == bedrock, (je, mine, bedrock)
    for feast in FEASTS:
        assert _jeSoundType(source, feast) == "WOOD", feast


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
