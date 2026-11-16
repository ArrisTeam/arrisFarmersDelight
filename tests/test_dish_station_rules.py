# -*- coding: utf-8 -*-
# runner: py3
"""砧板摆盘（Shared/Rules/DishStation.py）与菜谱表（tools/gen_dishes.py 生成的 Shared/Data/Dishes.py）。"""
from __future__ import print_function

import os
import subprocess
import sys

import fdtest

Rules = fdtest.load("Shared.Rules.DishStation")
Dishes = fdtest.load("Shared.Data.Dishes")

BREAD, EGG, BACON = ("minecraft:bread", 0), ("arris:fried_egg", 0), ("arris:cooked_bacon", 0)
TOMATO, CABBAGE, LEAF = ("arris:tomato", 0), ("arris:cabbage", 0), ("arris:cabbage_leaf", 0)


def testTheTableIsUpToDateWithTheRecipes():
    tool = os.path.join(fdtest.ROOT, "tools", "gen_dishes.py")
    code = subprocess.call([sys.executable, tool, "--check"])
    assert code == 0, "合成配方改了：py -3 tools/gen_dishes.py 重新生成 Shared/Data/Dishes.py"


def testTheBoardTakesJavasDishesAndLeavesTheRest():
    for name in ("arris:egg_sandwich", "arris:hamburger", "arris:wheat_dough", "arris:pie_crust", "arris:melon_juice",
                 "arris:apple_pie_item", "arris:roast_chicken_block_stage0"):
        assert Rules.isDishResult(name), name
    for name in ("arris:horse_feed", "arris:milk_bottle", "arris:tomato", "arris:cabbage", "arris:iron_knife"):
        assert not Rules.isDishResult(name), name
    assert len(set(entry["result"][0] for entry in Dishes.DishList)) == 30


def testBasesFollowTheKeywords():
    kinds = dict((dish["result"][0], dish["kind"]) for dish in Rules._dishes)
    assert kinds["arris:egg_sandwich"] == "bread" and kinds["arris:mixed_salad"] == "bowl"
    assert kinds["arris:barbecue_stick"] == "stick" and kinds["arris:kelp_roll"] == "kelp"
    assert kinds["arris:apple_pie_item"] == "crust", "派皮先于小麦"
    assert kinds["arris:honey_cookie"] == "wheat", "蜂蜜瓶不算玻璃瓶"
    assert kinds["arris:melon_juice"] == "bottle"
    assert Rules.isBase(BREAD) and Rules.isBase(("minecraft:bowl", 0)) and not Rules.isBase(TOMATO)


def testLayersGrowIntoADish():
    assert Rules.fitsNext([BREAD], EGG) and Rules.fitsNext([BREAD], BACON)
    assert not Rules.fitsNext([BREAD], ("minecraft:dirt", 0))
    assert Rules.completed([BREAD, EGG]) is None, "夹蛋三明治是面包 + 两个煎蛋（JE 和这边都是）：一个蛋一层"
    assert Rules.completed([BREAD, EGG, EGG])["result"] == ("arris:egg_sandwich", 0)
    assert Rules.autoFinishes([BREAD, EGG, EGG]), "没法再往上加：放下第二个蛋就成"
    assert Rules.completed([BREAD, BACON, TOMATO]) is None and not Rules.autoFinishes([BREAD, BACON, TOMATO])
    assert Rules.completed([BREAD, BACON, TOMATO, LEAF])["result"] == ("arris:bacon_sandwich", 0)
    assert Rules.completed([BREAD, TOMATO, CABBAGE, BACON])["result"] == ("arris:bacon_sandwich", 0), "底座之后顺序不限"


def testTheThinnestLayerDecidesHowMany():
    assert Rules.rounds([5, 2, 9]) == 2
    assert Rules.rounds([40, 30]) == Rules.BATCH
    assert Rules.containerOf("arris:cod_roll")["itemName"] == "minecraft:bowl"
    assert Rules.containerOf("arris:egg_sandwich") is None
    # 面团有水桶（桶原样留着）和鸡蛋（什么都不还）两种做法，字典按成品名查分不出来：水桶写在有序配方的 result 数组里
    assert Rules.containerOf("arris:wheat_dough") is None


def testTheHint():
    assert "拿走" in Rules.statusText({"dish": {"newItemName": "arris:egg_sandwich", "count": 2}})
    assert "下一层" in Rules.statusText({"layers": [{"newItemName": "minecraft:bread", "count": 3}]})
    ready = Rules.statusText({"layers": [{}, {}], "ready": "arris:x"}, lambda name: "某菜")
    assert "做成某菜" in ready and "%" not in ready


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
