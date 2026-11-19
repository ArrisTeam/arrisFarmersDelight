# -*- coding: utf-8 -*-
# runner: both
"""砧板摆盘的菜在 JEI 里怎么列、哪些工作台配方该藏（Shared/Rules/DishJei.py，纯规则）。

HoD（compat/jei/HandsOnJeiPlugin.java、compat/AssemblyLayout.java）：每道摆盘菜一条配方——打底的那一样、别的层（三个一排、几排上下居中）、成品；
这些菜的工作台配方藏起来。我们的菜谱表一种写法一行，这里把只差一个位置的几行并回一条（那个位置轮着显示），并出来的每种搭配都是表里真有的；
藏的是"配方"不是"成品"：引擎给的工作台配方，每格的可选物品里能挑出一组正好是某道摆盘菜的配料才算，切片拼回整个派那样的别的配方不藏。
"""
from __future__ import print_function

import fdtest

Jei = fdtest.load("Shared.Rules.DishJei")
Dishes = fdtest.load("Shared.Data.Dishes")
Assembly = fdtest.load("Shared.Rules.HandsOn.Assembly")


def _of(found, name):
    return [recipe for recipe in found if recipe["result"][0] == name]


def _combos(recipe):
    """这条配方轮得出的每一种搭配（排好序的配料名）。"""
    combos = [[]]
    for slot in [recipe["base"]] + list(recipe["layers"]):
        combos = [combo + [item[0]] for combo in combos for item in slot]
    return [tuple(sorted(combo)) for combo in combos]


def testVariantsThatDifferInOnePlaceBecomeOneRecipeWithThatPlaceCycling():
    found = Jei.recipes()
    assert len(found) < len(Dishes.DishList), "并过了：比菜谱表的行数少"
    (stick,) = _of(found, "arris:barbecue_stick")
    assert stick["base"] == [("minecraft:stick", 0)] and [len(slot) for slot in stick["layers"]] == [1, 1, 13], "烤串：13 种熟肉并成一条，那一格轮着显示"
    (sandwich,) = _of(found, "arris:bacon_sandwich")
    assert sandwich["base"] == [("minecraft:bread", 0)] and sorted(len(slot) for slot in sandwich["layers"]) == [1, 1, 2], "卷心菜 / 卷心菜叶并成一格"
    dough = _of(found, "arris:wheat_dough")
    assert sorted((recipe["count"], len(recipe["layers"])) for recipe in dough) == [(1, 1), (3, 3)], "配料个数、出的个数不一样的不并"


def testEveryCombinationShownIsARowOfTheTableAndEveryRowIsShown():
    rows = {}
    for entry in Dishes.DishList:
        rows.setdefault(entry["result"][0], set()).add(tuple(sorted(name for name, _aux in entry["ingredients"])))
    shown = {}
    for recipe in Jei.recipes():
        for combo in _combos(recipe):
            assert combo in rows[recipe["result"][0]], "轮出来的搭配表里没有：%s %s" % (recipe["result"][0], combo)
            shown.setdefault(recipe["result"][0], set()).add(combo)
    assert shown == rows, "表里的每种写法都列出来了"


def testTheBaseIsTheOneTheBoardWantsFirstAndTheRestKeepTheirOrder():
    for recipe in Jei.recipes():
        assert recipe["base"] and len(recipe["layers"]) <= Jei.MOST_LAYERS, recipe["result"]
        names = [recipe["base"][0][0]] + [slot[0][0] for slot in recipe["layers"]]
        assert Assembly.baseOf(names)[0] == 0, "打底的就是 DishStation 认的那个底座：%s" % (recipe["result"],)
    (pie,) = _of(Jei.recipes(), "arris:apple_pie_item")
    assert pie["base"] == [("arris:pie_crust", 0)] and [slot[0][0] for slot in pie["layers"]] == \
        ["minecraft:wheat"] * 3 + ["minecraft:apple"] * 3 + ["minecraft:sugar"] * 2, "别的层照配方里的次序"


def testLayersGoThreeInARowWithTheRowsCentred():
    """AssemblyLayout.layerX / layerY：配方区高 54、格子 18。"""
    assert [Jei.layerPlace(index, 3, 54, 18) for index in range(3)] == [(0, 18), (1, 18), (2, 18)], "一排：居中"
    assert [Jei.layerPlace(index, 4, 54, 18) for index in range(4)] == [(0, 9), (1, 9), (2, 9), (0, 27)], "两排"
    assert [Jei.layerPlace(index, 8, 54, 18)[1] for index in (0, 3, 6)] == [0, 18, 36], "三排占满"
    assert Jei.layerPlace(0, 1, 54, 18) == (0, 18)


def testItemsOfListsEveryThingOnce():
    (stick,) = _of(Jei.recipes(), "arris:barbecue_stick")
    items = Jei.itemsOf(stick)
    assert len(items) == len(set(items)) == 16 and ("minecraft:stick", 0) in items and ("minecraft:cooked_beef", 0) in items


# ---------------------------------------------------------------- 工作台配方

SANDWICH = {"ingredients": [{"item": "minecraft:bread", "data": 0, "count": 1}, {"item": "arris:fried_egg", "count": 2}],
            "result": [{"item": "arris:egg_sandwich", "data": 0, "count": 1}]}
PIE = {"pattern": ["###", "aaa", "xOx"],
       "key": {"#": {"item": "minecraft:wheat"}, "a": {"item": "minecraft:apple"}, "x": {"item": "minecraft:sugar"}, "O": {"item": "arris:pie_crust"}},
       "result": [{"item": "arris:apple_pie_item", "count": 1}]}
PIE_FROM_SLICES = {"pattern": ["##", "##"], "key": {"#": {"item": "arris:apple_pie_slice"}}, "result": [{"item": "arris:apple_pie_item", "count": 1}]}
STICK = {"ingredients": [{"item": "arris:tomato"}, {"item": "arris:onion"}, {"item": ["minecraft:cooked_beef", "minecraft:cooked_chicken"]},
                         {"item": "minecraft:stick"}], "result": [{"item": "arris:barbecue_stick", "count": 1}]}


def testACraftingRecipeIsReadCellByCell():
    assert Jei.craftSlots(SANDWICH) == ("arris:egg_sandwich", [["minecraft:bread"], ["arris:fried_egg"], ["arris:fried_egg"]]), "带数量的展开成几格"
    name, slots = Jei.craftSlots(PIE)
    assert name == "arris:apple_pie_item" and len(slots) == 9 and slots[7] == ["arris:pie_crust"], "有序配方：空格不算、一格一个"
    assert Jei.craftSlots(STICK)[1][2] == ["minecraft:cooked_beef", "minecraft:cooked_chicken"], "一格几种可选的"
    for odd in (None, {}, {"input": "a", "output": "b"}, {"ingredients": [], "result": []}, "text"):
        assert Jei.craftSlots(odd)[1] == [] and not Jei.isDishCraft(odd), odd


def testOnlyTheCraftThatIsADishOnTheBoardIsHidden():
    assert Jei.isDishCraft(SANDWICH) and Jei.isDishCraft(PIE) and Jei.isDishCraft(STICK)
    assert not Jei.isDishCraft(PIE_FROM_SLICES), "切片拼回整个派：成品一样，不是砧板菜，不藏"
    other = dict(SANDWICH, result=[{"item": "minecraft:bread", "count": 1}])
    assert not Jei.isDishCraft(other), "成品不是摆盘菜"
    short = dict(SANDWICH, ingredients=[{"item": "minecraft:bread"}, {"item": "arris:fried_egg"}])
    assert not Jei.isDishCraft(short), "配料对不上（少一个蛋）"
    mine = [{"result": ("test:wrap", 0), "count": 1, "ingredients": [("minecraft:bread", 0), ("test:patty", 0)]}]
    wrap = {"ingredients": [{"item": "test:patty"}, {"item": ["minecraft:bread", "test:bun"]}], "result": [{"item": "test:wrap"}]}
    assert Jei.isDishCraft(wrap, mine) and not Jei.isDishCraft(wrap), "按给的菜谱表判（下游追加的菜也一样）"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
