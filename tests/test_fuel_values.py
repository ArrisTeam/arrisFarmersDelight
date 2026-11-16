# -*- coding: utf-8 -*-
# runner: py3
"""能当熔炉燃料的方块 / 物品和燃烧时长对照 JE（FD 1.20 的 ModItems：FuelBlockItem / FuelItem / RopeItem）。

JE 的数字是刻，netease:fuel 的 duration 是秒（刻 / 20）；FuelItem / FuelBlockItem 不写时长的缺省 100 刻。
下界木头的两个橱柜（绯红、诡异）在 JE 是普通方块物品，不是燃料。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

# 基岩版标识符 -> JE 的燃烧刻数
BLOCK_TICKS = {
    "cutting_board": 200, "wooden_basket": 300, "basket": 300, "straw_bale": 1000, "safety_net": 200, "rope": 200,
    "oak_cabinet": 300, "spruce_cabinet": 300, "birch_cabinet": 300, "jungle_cabinet": 300, "acacia_cabinet": 300,
    "dark_oak_cabinet": 300, "mangrove_cabinet": 300, "cherry_cabinet": 300, "bamboo_cabinet": 300,
    "tatami": 400, "tatami_full_mat": 200, "tatami_half_mat": 100, "canvas_rug": 200, "rope_fence": 200, "rope_fence_gate": 200,
}
ITEM_TICKS = {"straw": 100, "canvas": 400, "tree_bark": 200}
NOT_FUEL = ("crimson_cabinet", "warped_cabinet", "rice_bale")


def _components(folder, name):
    path = os.path.join(fdtest.BP, folder, "arris_%s.json" % name)
    doc = json.load(io.open(path, encoding="utf-8-sig"))
    return [value for key, value in doc.items() if key != "format_version"][0]["components"]


def testFuelBlocksBurnAsLongAsInJava():
    for name, ticks in sorted(BLOCK_TICKS.items()):
        assert _components("netease_blocks", name).get("netease:fuel") == {"duration": ticks // 20}, name


def testFuelItemsBurnAsLongAsInJava():
    for name, ticks in sorted(ITEM_TICKS.items()):
        assert _components("netease_items_beh", name).get("netease:fuel") == {"duration": ticks // 20}, name


def testNetherCabinetsAndRiceBalesAreNotFuel():
    for name in NOT_FUEL:
        assert "netease:fuel" not in _components("netease_blocks", name), name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
