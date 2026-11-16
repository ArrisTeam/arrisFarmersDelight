# -*- coding: utf-8 -*-
# runner: both
"""派方块的资源接线：Shared/Data/Food.pieList 里的每个派（苹果派、芝士派、巧克力派、南瓜派）都要配齐。

JE 的 PieBlock：同一个模板（template_pie：4 块，吃一口少一块），自己的方块战利品表是空的（什么都不掉，
切片靠刀：Server/KnifeSlicing.py），名字是 block.farmersdelight.<名>。基岩版这边一个派要有：
- 行为包 netease_blocks/arris_<名>.json：空战利品表、方块实体（存吃了几口）；
- 资源包 rp/entity/<名>.json：方块实体模型 geometry.arris_pie + 一张 32x32 的图集（顶、底、侧、内芯拼在一起）；
- blocks.json 的条目指向这个客户端实体，block_icon / textures / destroyed_textures 都登记在 terrain_texture.json；
- 中文名 tile.arris:<名>.name；
- 客户端按方块实体数据补动画变量的名单（Client/BlockEntityRestore._PIES）与 pieList 一致。
"""
from __future__ import print_function

import io
import json
import os
import re
import struct

import fdtest

Food = fdtest.load("Shared.Data.Food")
Slicing = fdtest.load("Shared.Data.Slicing")
RP = os.path.join(fdtest.ROOT, "rp")


def _json(path):
    with io.open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _names():
    return [name[len("arris:"):] for name in Food.pieList]


def _pngSize(path):
    with open(path, "rb") as handle:
        head = handle.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def testTheListedPiesAreTheFourJavaPies():
    assert sorted(_names()) == ["apple_pie", "chocolate_pie", "pumpkin_pie", "sweet_berry_cheesecake"]
    assert sorted(Slicing.pieSliceItems) == sorted(Food.pieList)


def testEveryPieBlockHasAnEmptyLootTableAndABlockEntity():
    for name in _names():
        block = _json(os.path.join(fdtest.BP, "netease_blocks", "arris_%s.json" % name))["minecraft:block"]
        assert block["description"]["identifier"] == "arris:" + name
        components = block["components"]
        assert "netease:block_entity" in components, name
        assert _json(os.path.join(fdtest.BP, components["minecraft:loot"]["table"]))["pools"] == [], "JE 派方块自己不掉东西"


def testEveryPieHasTheSharedModelAndItsOwn32x32Atlas():
    for name in _names():
        entity = _json(os.path.join(RP, "entity", name + ".json"))["minecraft:client_entity"]["description"]
        assert entity["identifier"] == "arris:" + name
        assert entity["geometry"]["default"] == "geometry.arris_pie"
        assert entity["animations"]["controller_slice"] == "controller.animation.pie.slice"
        assert "variable.mod_pie = 0.0;" in entity["scripts"]["initialize"]
        assert _pngSize(os.path.join(RP, entity["textures"]["default"] + ".png")) == (32, 32), name


def testEveryPieIsRegisteredInBlocksJsonAndTheTerrainAtlas():
    blocks = _json(os.path.join(RP, "blocks.json"))
    terrain = _json(os.path.join(RP, "textures", "terrain_texture.json"))["texture_data"]
    for name in _names():
        entry = blocks["arris:" + name]
        assert entry["client_entity"]["identifier"] == "arris:" + name
        assert entry["client_entity"]["hand_model_use_client_entity"] is True
        assert entry["sound"] == "cloth", "JE：Blocks.CAKE 的羊毛音效"
        wanted = [entry["textures"], entry["client_entity"]["block_icon"],
                  entry["client_entity"].get("destroyed_textures") or entry["client_entity"].get("destoryed_textures")]
        for key in wanted:
            assert key in terrain, "%s 的 %s 没登记到 terrain_texture.json" % (name, key)


def testEveryPieHasAChineseName():
    lang = io.open(os.path.join(RP, "texts", "zh_CN.lang"), encoding="utf-8").read()
    for name in _names():
        assert re.search(r"^tile\.arris:%s\.name=\S+" % name, lang, re.M), name
    # JE zh_cn：block.farmersdelight.pumpkin_pie = 南瓜派，item.farmersdelight.pumpkin_pie_slice = 南瓜派切片
    assert u"tile.arris:pumpkin_pie.name=南瓜派" in lang and u"item.arris:pumpkin_pie_slice.name=南瓜派切片" in lang


def testTheClientRestoresTheBiteAnimationOfEveryPie():
    source = io.open(os.path.join(fdtest.BP, fdtest.SCRIPTS, "Client", "BlockEntityRestore.py"), encoding="utf-8").read()
    listed = re.search(r"_PIES = \((.*?)\)", source, re.S).group(1)
    assert sorted(re.findall(r'"([^"]+)"', listed)) == sorted(Food.pieList)


def testTheVanillaPumpkinPieIsTheOnlyPieWithoutAnItemOfItsOwn():
    placedBy = dict((block, item) for item, block in Food.itemChangeBlockDict.items())
    for block in Food.pieList:
        assert block in placedBy, block
        isVanilla = block == "arris:pumpkin_pie"
        assert placedBy[block].startswith("minecraft:") == isVanilla, block
    assert placedBy["arris:pumpkin_pie"] == Food.PUMPKIN_PIE == "minecraft:pumpkin_pie"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
