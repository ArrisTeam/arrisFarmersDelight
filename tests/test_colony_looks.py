# -*- coding: utf-8 -*-
# runner: py3
"""蘑菇丛只用来显示的两件平面物品（arris:brown_mushroom_colony_look / arris:red_mushroom_colony_look）在包里齐不齐。

JE：蘑菇丛的物品模型是一张贴图（item/generated，贴图 block/<名>_stage3），板上像别的食物一样平躺。基岩版它的掉落物是方块模型缩小的立体小蘑菇，
所以板上、世界里的展示、手上画的是另一件物品（Shared/Data/FlatBlockItems.ShownAs）：行为包、资源包各一份定义，图标就是 stage3 那张方块贴图，
创造栏里没有；刀口的图标掩码仍按真物品的名字查（Shared/Data/ItemMasks）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

Shown = fdtest.load("Shared.Data.FlatBlockItems").ShownAs
Masks = fdtest.load("Shared.Data.ItemMasks").ItemMasks
ROOT = fdtest.ROOT


def _json(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return json.load(handle)


def testEachColonyHasItsFlatLookItemInBothPacks():
    assert sorted(Shown) == ["arris:brown_mushroom_colony", "arris:red_mushroom_colony"]
    textures = _json("rp", "textures", "item_texture.json")["texture_data"]
    with io.open(os.path.join(ROOT, "rp", "texts", "zh_CN.lang"), encoding="utf-8") as handle:
        names = handle.read()
    for real, look in sorted(Shown.items()):
        short = look.split(":")[1]
        assert look == real + "_look"
        beh = _json("bp", "netease_items_beh", "arris_%s.json" % short)["minecraft:item"]
        res = _json("rp", "netease_items_res", "arris_%s.json" % short)["minecraft:item"]
        for body in (beh, res):
            assert body["description"]["identifier"] == look and body["description"]["register_to_create_menu"] is False, "创造栏里没有：%s" % look
        assert res["components"]["minecraft:icon"] == look
        path = textures[look]["textures"]
        assert path == "textures/blocks/%s_stage3" % real.split(":")[1], "图标就是 stage3 那张方块贴图（JE 的 block/<名>_stage3）"
        assert os.path.isfile(os.path.join(ROOT, "rp", path + ".png")), path
        assert ("item.%s.name=" % look) in names, "有名字：%s" % look
        assert real in Masks, "刀口的图标掩码按真物品的名字查：%s" % real


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
