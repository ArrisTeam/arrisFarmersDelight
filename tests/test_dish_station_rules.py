# -*- coding: utf-8 -*-
# runner: py3
"""砧板摆盘（Shared/Rules/DishStation.py）与菜谱表（tools/gen_dishes.py 生成的 Shared/Data/Dishes.py）。"""
from __future__ import print_function

import os
import subprocess
import sys

import fdtest

Rules = fdtest.load("Shared.Rules.DishStation")
Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")
Dishes = fdtest.load("Shared.Data.Dishes")

BREAD, EGG, BACON = ("minecraft:bread", 0), ("arris:fried_egg", 0), ("arris:cooked_bacon", 0)
TOMATO, CABBAGE, LEAF = ("arris:tomato", 0), ("arris:cabbage", 0), ("arris:cabbage_leaf", 0)


def testTheTableIsUpToDateWithTheRecipes():
    tool = os.path.join(fdtest.ROOT, "tools", "gen_dishes.py")
    code = subprocess.call([sys.executable, tool, "--check"])
    assert code == 0, "合成配方改了：py -3 tools/gen_dishes.py 重新生成 Shared/Data/Dishes.py"


def testTheBoardTakesJavasDishesAndLeavesTheRest():
    for name in ("arris:egg_sandwich", "arris:hamburger", "arris:wheat_dough", "arris:pie_crust", "arris:melon_juice",
                 "arris:apple_pie_item", "minecraft:pumpkin_pie", "arris:roast_chicken_block_stage0", "minecraft:cake"):
        assert Rules.isDishResult(name), name
    for name in ("arris:horse_feed", "arris:milk_bottle", "arris:tomato", "arris:cabbage", "arris:iron_knife"):
        assert not Rules.isDishResult(name), name
    assert len(set(entry["result"][0] for entry in Dishes.DishList)) == 33, "JE 的 31 道 FD 菜 + 原版南瓜派 + 牛奶瓶蛋糕"


def testBasesFollowTheKeywords():
    kinds = dict((dish["result"][0], dish["kind"]) for dish in Rules._dishes)
    assert kinds["arris:egg_sandwich"] == "bread" and kinds["arris:mixed_salad"] == "bowl"
    assert kinds["arris:barbecue_stick"] == "stick" and kinds["arris:kelp_roll"] == "kelp"
    assert kinds["arris:apple_pie_item"] == "crust", "派皮先于小麦"
    assert kinds["minecraft:pumpkin_pie"] == "crust", "HoD 的 pumpkin_pie_from_pie_crust 也从派皮摆起"
    assert kinds["arris:honey_cookie"] == "wheat", "蜂蜜瓶不算玻璃瓶"
    assert kinds["arris:melon_juice"] == "bottle"
    assert kinds["minecraft:cake"] == "wheat", "JE 的 cake_from_milk_bottle 以小麦打底（BoardTests.everyFoodCraftComesToTheBoard）"
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
    cakes = [dish for dish in Rules.dishes() if dish["result"][0] == "minecraft:cake"]
    assert len(cakes) == 5 and all(len(dish["ingredients"]) == 9 for dish in cakes), "奶瓶 / 奶桶的五种凑法，每种 9 层"
    assert sorted(dish["extras"] for dish in cakes if dish["ingredients"].count(bottle) == 3) == [[("minecraft:glass_bottle", 0, 3)]]
    assert all(dish["ingredients"].count(milk) + dish["ingredients"].count(bottle) == 3 for dish in cakes)
    potato = [dish["extras"] for dish in Rules.dishes() if dish["result"][0] == "arris:stuffed_potato"]
    assert sorted(potato) == [[("minecraft:bucket", 0, 1)]] * 2 + [[("minecraft:glass_bottle", 0, 1)]] * 2


def _finish(name):
    return Rules.finishOf(next(dish for dish in Rules.dishes() if dish["result"][0] == name))


def testEveryDishIsFinishedTheWayJavaFinishesIt():
    # JE BoardTests.everyFoodCraftComesToTheBoard（257-267）逐道断言过的
    toss, arrange, press = Assembly.FINISH_TOSS, Assembly.FINISH_ARRANGE, Assembly.FINISH_PRESS
    expected = {
        "arris:honey_glazed_ham_block_stage0": arrange, "arris:bacon_and_eggs": arrange, "arris:steak_and_potatoes": arrange,
        "arris:grilled_salmon": arrange, "arris:mixed_salad": toss, "arris:fruit_salad": toss, "arris:nether_salad": toss,
        "arris:hamburger": Assembly.FINISH_SANDWICH, "arris:egg_sandwich": Assembly.FINISH_SANDWICH,
        "arris:mutton_wrap": Assembly.FINISH_ROLL, "arris:cod_roll": Assembly.FINISH_SHAPE, "arris:kelp_roll": Assembly.FINISH_ROLL,
        "arris:barbecue_stick": Assembly.FINISH_SKEWER, "arris:melon_popsicle": Assembly.FINISH_FREEZE, "arris:apple_pie_item": press,
        # 同一套规则推出来的：碗里有肉的摆、盛宴（方块）摆、打了 tossed 标签的盛宴拌、蛋糕 / 果汁压、面团饼干揉
        "arris:roasted_mutton_chops": arrange, "arris:shepherds_pie_block_stage0": arrange, "arris:rice_roll_medley_block_stage0": arrange,
        "arris:roast_chicken_block_stage0": arrange, "arris:gleaming_salad_block_stage0": toss, "minecraft:cake": press,
        "arris:melon_juice": press, "arris:stuffed_potato": press, "arris:honey_cookie": Assembly.FINISH_KNEAD,
        "arris:wheat_dough": Assembly.FINISH_KNEAD, "arris:pie_crust": Assembly.FINISH_KNEAD,
    }
    for name, finish in sorted(expected.items()):
        assert _finish(name) == finish, (name, _finish(name), finish)
    for dish in Rules.dishes():
        assert Rules.finishOf(dish) in (toss, arrange, press, Assembly.FINISH_SANDWICH, Assembly.FINISH_ROLL, Assembly.FINISH_SHAPE,
                                        Assembly.FINISH_SKEWER, Assembly.FINISH_FREEZE, Assembly.FINISH_KNEAD), dish["result"]


def testACrackedIngredientIsReadFromTheSameTableAsThePotTheBoardAndThePan():
    """AssemblyRecipes 244 行：碗里有一样 KitchenTags.CRACKED 的料就是摆的、不是拌的。这边的 cracked 和厨锅、砧板、煎锅是同一张
    PotSunk.CRACKED（缺省只有生鸡蛋）：往里临时加一件（番茄，测完换回去），一碗只有菜叶和番茄的也变成摆。"""
    Sunk = fdtest.load("Shared.Data.PotSunk")

    def bowl(*ingredients):
        return {"result": ("test:greens", 0), "ingredients": [("minecraft:bowl", 0)] + list(ingredients), "base": 0, "kind": "bowl"}

    assert Rules.finishOf(bowl(LEAF, TOMATO)) == Assembly.FINISH_TOSS, "纯植物：拌"
    assert Rules.finishOf(bowl(LEAF, ("minecraft:egg", 0))) == Assembly.FINISH_ARRANGE, "有生鸡蛋：摆"
    kept = Sunk.CRACKED
    Sunk.CRACKED = kept + (TOMATO,)
    try:
        assert Rules.finishOf(bowl(LEAF, TOMATO)) == Assembly.FINISH_ARRANGE, "番茄进了 cracked 那张表：摆"
    finally:
        Sunk.CRACKED = kept
    assert Rules.finishOf(bowl(LEAF, TOMATO)) == Assembly.FINISH_TOSS and Sunk.CRACKED == kept
    assert [name for name, _aux in Sunk.CRACKED] == ["minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"], "基岩版的三种蛋"
    assert Rules.finishOf(bowl(LEAF, ("minecraft:brown_egg", 0))) == Assembly.FINISH_ARRANGE, "棕色鸡蛋也是蛋"


def testWhatIsAWholeBlockOfFood():
    for name in ("arris:honey_glazed_ham_block_stage0", "arris:roast_chicken_block_stage0", "arris:apple_pie_item",
                 "arris:sweet_berry_cheesecake_item", "arris:chocolate_pie_item", "minecraft:cake"):
        assert Rules.isBlockResult(name), name
    for name in ("arris:hamburger", "arris:mixed_salad", "arris:cod_roll", "minecraft:pumpkin_pie", "arris:wheat_dough"):
        assert not Rules.isBlockResult(name), name


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
    cake = ["arris:milk_bottle"] * 3 + ["minecraft:sugar"] * 2 + ["minecraft:egg"] + ["minecraft:wheat"] * 3
    assert Rules.isDishCraft("minecraft:cake", names(*cake)), "FD 的牛奶瓶蛋糕搬到砧板上"
    assert not Rules.isDishCraft("minecraft:cake", names(*["arris:cake_slice"] * 7)), "切片拼回蛋糕留在工作台"
    vanilla = ["minecraft:milk_bucket"] * 3 + ["minecraft:sugar"] * 2 + ["minecraft:egg"] + ["minecraft:wheat"] * 3
    assert not Rules.isDishCraft("minecraft:cake", names(*vanilla)), "原版的三桶奶蛋糕不是 FD 的配方（HoD 只收 FD 命名空间），留在工作台"
    assert not Rules.isDishCraft("arris:milk_bottle", names("minecraft:milk_bucket", *["minecraft:glass_bottle"] * 4))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
