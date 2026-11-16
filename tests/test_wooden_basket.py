# -*- coding: utf-8 -*-
# runner: py3
"""木篮（JE wooden_basket）对照 JE：配方、砧板配方、方块定义、模型与贴图的接线。

依据 .refs/FarmersDelight 的 recipes/wooden_basket.json（木棍 + 帆布，摆法与竹篮相同）、recipes/cutting/wooden_basket.json
（斧 -> 帆布 + 木棍）、ModBlocks（两种篮子同一个 BasketBlock，strength(1.5F)）、zh_cn.json（木篮）。
"""
from __future__ import print_function

import collections
import io
import json
import os
import struct

import fdtest
import recipekit

Cutting = fdtest.load("Shared.Data.Cutting")

WOODEN = "arris:wooden_basket"
BAMBOO = "arris:basket"
RP = os.path.join(fdtest.ROOT, "rp")


def _json(*path):
    with io.open(os.path.join(*path), encoding="utf-8-sig") as f:
        return json.loads(f.read(), object_pairs_hook=collections.OrderedDict)


def _canonical(rows):
    names = {}
    return ["".join(" " if char == " " else str(names.setdefault(char, len(names))) for char in row) for row in rows]


def testRecipeIsSticksAndCanvasInTheBambooShape():
    byId = recipekit.byIdentifier()
    kind, body = byId[WOODEN]
    assert kind == "shaped"
    # JE：/ /|# #|/#/，/ = 木棍，# = 帆布
    assert _canonical(body["pattern"]) == _canonical(["/ /", "# #", "/#/"])
    assert recipekit.ingredientsOf(kind, body) == collections.Counter({"minecraft:stick": 4, "arris:canvas": 3})
    assert recipekit.resultsOf(body) == [(WOODEN, 1)]
    bambooKind, bambooBody = byId[BAMBOO]
    assert _canonical(body["pattern"]) == _canonical(bambooBody["pattern"])
    assert recipekit.ingredientsOf(bambooKind, bambooBody) == collections.Counter({"minecraft:bamboo": 4, "arris:canvas": 3})


def testCuttingBoardTakesTheWoodenBasketApartWithAnAxe():
    recipe = Cutting.CuttingBoardDict[(WOODEN, 0)]
    assert recipe["itemList"] == [{"itemName": "arris:canvas", "count": 1}, {"itemName": "minecraft:stick", "count": 1}]
    assert recipe["item_type"] == "axe" and recipe["tool"] is Cutting.axeList
    # 竹篮那条没动
    assert Cutting.CuttingBoardDict[(BAMBOO, 0)]["itemList"][1] == {"itemName": "minecraft:bamboo", "count": 1}


def testBlockDefinitionIsTheBambooOneWithJavaStrength():
    wooden = _json(fdtest.BP, "netease_blocks", "arris_wooden_basket.json")["minecraft:block"]
    bamboo = _json(fdtest.BP, "netease_blocks", "arris_basket.json")["minecraft:block"]
    assert wooden["description"]["identifier"] == WOODEN
    assert wooden["description"]["register_to_creative_menu"] is True
    assert wooden["description"]["category"] == bamboo["description"]["category"]
    woodenParts = collections.OrderedDict((k, v) for k, v in wooden["components"].items()
                                          if k not in ("minecraft:destroy_time", "minecraft:explosion_resistance"))
    bambooParts = collections.OrderedDict((k, v) for k, v in bamboo["components"].items()
                                          if k not in ("minecraft:destroy_time", "minecraft:explosion_resistance"))
    assert woodenParts == bambooParts                       # 箱子容量、碰撞盒、斧子挖、触发组件都一样
    assert wooden["components"]["minecraft:destroy_time"]["value"] == 1.5          # JE strength(1.5F)
    assert wooden["components"]["minecraft:explosion_resistance"]["value"] == 1.5
    assert wooden["components"]["netease:block_chest"]["chest_capacity"] == 3       # JE 27 格 = 3 行


def testModelIsTheBambooModelWithItsOwnTexture():
    wooden = _json(RP, "models", "netease_block", "wooden_basket.json")
    bamboo = _json(RP, "models", "netease_block", "basket.json")
    woodenDesc = wooden["netease:block_geometry"].pop("description")
    bambooDesc = bamboo["netease:block_geometry"].pop("description")
    assert wooden == bamboo                                  # 骨骼、方块的 UV 一个字不差
    assert woodenDesc["identifier"] == WOODEN and woodenDesc["textures"] == [WOODEN]
    assert woodenDesc["textures_descriptions"] == bambooDesc["textures_descriptions"] == [{"length": 32, "width": 32}]


def testTextureIsA2x2AtlasRegisteredUnderTheShortName():
    terrain = _json(RP, "textures", "terrain_texture.json")["texture_data"]
    assert terrain[WOODEN]["textures"] == "textures/blocks/wooden_basket"
    with open(os.path.join(RP, "textures", "blocks", "wooden_basket.png"), "rb") as f:
        header = f.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24]) == (32, 32)    # 与竹篮的 32×32 图集同尺寸，UV 才对得上
    blocks = _json(RP, "blocks.json")
    assert blocks[WOODEN] == {"netease_model": WOODEN, "sound": "wood", "textures": WOODEN}


def testChineseName():
    with io.open(os.path.join(RP, "texts", "zh_CN.lang"), encoding="utf-8-sig") as f:
        names = dict(line.rstrip("\r\n").split("=", 1) for line in f if "=" in line)
    assert names["tile.arris:wooden_basket.name"] == u"木篮"      # zh_cn.json: block.farmersdelight.wooden_basket
    assert names["tile.arris:basket.name"] == u"竹篮"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
