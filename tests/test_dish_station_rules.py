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
                 "arris:apple_pie_item", "minecraft:pumpkin_pie", "arris:roast_chicken_block_stage0"):
        assert Rules.isDishResult(name), name
    for name in ("arris:horse_feed", "arris:milk_bottle", "arris:tomato", "arris:cabbage", "arris:iron_knife"):
        assert not Rules.isDishResult(name), name
    assert len(set(entry["result"][0] for entry in Dishes.DishList)) == 32


def testBasesFollowTheKeywords():
    kinds = dict((dish["result"][0], dish["kind"]) for dish in Rules._dishes)
    assert kinds["arris:egg_sandwich"] == "bread" and kinds["arris:mixed_salad"] == "bowl"
    assert kinds["arris:barbecue_stick"] == "stick" and kinds["arris:kelp_roll"] == "kelp"
    assert kinds["arris:apple_pie_item"] == "crust", "派皮先于小麦"
    assert kinds["minecraft:pumpkin_pie"] == "crust", "HoD 的 pumpkin_pie_from_pie_crust 也从派皮摆起"
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
    sandwich = Rules.completed([BREAD, EGG, EGG])
    assert Rules.roundsOf(sandwich, [(BREAD, 5), (EGG, 2), (EGG, 9)]) == 2
    assert Rules.leftOf(sandwich, BREAD, 5, 2) == 3 and Rules.leftOf(sandwich, EGG, 2, 2) == 0


def testDoughKeepsItsWaterBucketOnTheBoard():
    # HoD 的 Assembling.make：面团配方的水桶每轮都原样放回去，一桶水揉完一整叠小麦，做完水桶还给厨师
    wheat, water = ("minecraft:wheat", 0), ("minecraft:water_bucket", 0)
    dough = Rules.completed([wheat, water])
    assert dough["result"] == ("arris:wheat_dough", 0) and dough["keeps"] == ("minecraft:water_bucket",)
    assert dough["extras"] == [], "水桶不是换成空桶"
    assert Rules.roundsOf(dough, [(wheat, 12), (water, 1)]) == 12
    assert Rules.roundsOf(dough, [(wheat, 40), (water, 1)]) == Rules.BATCH
    assert Rules.leftOf(dough, water, 1, 12) == 1 and Rules.leftOf(dough, wheat, 12, 12) == 0
    eggs = Rules.completed([wheat, wheat, wheat, ("minecraft:egg", 0)])
    assert eggs["count"] == 3 and eggs["keeps"] == () and eggs["extras"] == []


def testTheHint():
    assert "拿走" in Rules.statusText({"dish": {"newItemName": "arris:egg_sandwich", "count": 2}})
    assert "下一层" in Rules.statusText({"layers": [{"newItemName": "minecraft:bread", "count": 3}]})
    ready = Rules.statusText({"layers": [{}, {}], "ready": "arris:x"}, lambda name: "某菜")
    assert "做成某菜" in ready and "%" not in ready


def testDishesGiveBackWhatJavaLeaves():
    milk, bottle = ("minecraft:milk_bucket", 0), ("arris:milk_bottle", 0)
    pies = [dish for dish in Rules.dishes() if dish["result"] == ("arris:chocolate_pie_item", 0)]
    assert sorted(dish["extras"] for dish in pies if dish["ingredients"].count(milk) == 3) == [[("minecraft:bucket", 0, 3)]]
    mixed = [dish["extras"] for dish in pies if dish["ingredients"].count(milk) == 2]
    assert mixed and all(extras == [("minecraft:bucket", 0, 2), ("minecraft:glass_bottle", 0, 1)] for extras in mixed)
    assert all(dish["ingredients"].count(milk) + dish["ingredients"].count(bottle) == 3 for dish in pies)
    roll = next(dish for dish in Rules.dishes() if dish["result"][0] == "arris:cod_roll")
    assert roll["extras"] == [("minecraft:bowl", 0, 1)], "米饭的碗：无序配方也照 JE 的合成剩余物算"
    ham = next(dish for dish in Rules.dishes() if dish["result"][0] == "arris:honey_glazed_ham_block_stage0")
    assert ham["extras"] == [("minecraft:bowl", 0, 2), ("minecraft:glass_bottle", 0, 1)]
    potato = [dish["extras"] for dish in Rules.dishes() if dish["result"][0] == "arris:stuffed_potato"]
    assert sorted(potato) == [[("minecraft:bucket", 0, 1)]] * 2 + [[("minecraft:glass_bottle", 0, 1)]] * 2


def testTheTableBlocksOnlyTheBoardRecipes():
    def names(*items):
        return tuple(sorted(items))
    assert Rules.isDishCraft("arris:egg_sandwich", names("minecraft:bread", "arris:fried_egg", "arris:fried_egg"))
    assert not Rules.isDishCraft("arris:egg_sandwich", ()), "创造模式从物品栏拿：合成格是空的"
    assert not Rules.isDishCraft("arris:egg_sandwich", names("minecraft:bread", "arris:fried_egg"))
    for pieItem, slice_ in (("arris:apple_pie_item", "arris:apple_pie_slice"),
                            ("arris:chocolate_pie_item", "arris:chocolate_pie_slice"),
                            ("arris:sweet_berry_cheesecake_item", "arris:sweet_berry_cheesecake_slice")):
        assert Rules.isDishResult(pieItem) and not Rules.isDishCraft(pieItem, names(*[slice_] * 4)), "切片拼回整个派留在工作台"
    assert Rules.isDishCraft("arris:apple_pie_item", names(*["minecraft:wheat"] * 3 + ["minecraft:apple"] * 3
                                                           + ["minecraft:sugar"] * 2 + ["arris:pie_crust"]))
    assert Rules.isDishCraft("arris:wheat_dough", names("minecraft:wheat", "minecraft:water_bucket"))
    assert not Rules.isDishCraft("arris:milk_bottle", names("minecraft:milk_bucket", *["minecraft:glass_bottle"] * 4))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
