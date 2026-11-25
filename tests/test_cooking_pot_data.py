# -*- coding: utf-8 -*-
# runner: both
"""厨锅配方表的写法（Shared/Data/CookingPotRecipes.py）：农夫乐事自己的 28 道每道有 JE 的配方 ID、每格的选项 Slots、展开出来的写法 Recipe。

- Id 是 farmersdelight:cooking/<JE 的配方文件名>，不重复；.refs 在场时正好是 JE 的 28 个厨锅配方文件；
- Slots 一格一格就是 JE 的 ingredients（.refs 在场时逐个文件核对）：JE 的标签换成词表的 common: 名（Shared/Data/Tags.JE_NAMES 反过来查），
  鸡蛋是原版的 minecraft:egg，JE 的物品照写（farmersdelight: 换成 arris:）；
- Recipe（旧读者在读，契约的 AddCookingPotRecipe 往里加）照旧是 170 种写法、普通列表：Slots 按词表里农夫乐事登记的成员展开、鸡蛋只展开普通鸡蛋；
  按标签现在的答案（静态词表）展开比它多出来的，只有蓝色、棕色鸡蛋那几种（有意的差异）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Tags = fdtest.load("Shared.Data.Tags")
Slots = fdtest.load("Shared.Rules.PotSlots")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
JE_COOKING = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "generated", "resources", "data", "farmersdelight", "recipes", "cooking")
PREFIX = "farmersdelight:cooking/"
EGGS = ("minecraft:blue_egg", "minecraft:brown_egg")


def _legacyMembers(tag):
    return ("minecraft:egg",) if tag == Tags.EGG else Tags.ITEM_TAGS.get(tag, ())


def testEveryBuiltInRecipeHasTheIdOfItsJavaFile():
    ids = [recipe["Id"] for recipe in Recipes.CookingPotRecipeList]
    assert len(ids) == 28 and len(set(ids)) == 28, ids
    assert all(recipeId.startswith(PREFIX) for recipeId in ids), ids
    if os.path.isdir(JE_COOKING):
        files = sorted(name[:-len(".json")] for name in os.listdir(JE_COOKING) if name.endswith(".json"))
        assert sorted(recipeId[len(PREFIX):] for recipeId in ids) == files, "28 道菜正好是 JE 的 28 个厨锅配方文件"


def testSlotsAreWellFormedAndTheWaysAreStillTheOldOnes():
    total = 0
    for recipe in Recipes.CookingPotRecipeList:
        slots = recipe["Slots"]
        assert Slots.slotsProblem(slots) is None, (recipe["Id"], Slots.slotsProblem(slots))
        assert all(len(way) == len(slots) for way in recipe["Recipe"]), recipe["Id"]
        assert recipe["Recipe"] == Slots.expand(slots, _legacyMembers, 1 << 20), recipe["Id"]
        assert type(recipe["Recipe"]) is list, "Recipe 是普通的列表：每格的选项在 Slots 键里，过得了线"
        total += len(recipe["Recipe"])
    assert total == 170, total


def testTheTagsAnswerMoreOnlyForTheOtherEggs():
    for recipe in Recipes.CookingPotRecipeList:
        old = set(tuple(sorted(way)) for way in recipe["Recipe"])
        now = set(tuple(sorted(way)) for way in Slots.expand(recipe["Slots"], ItemTags.itemsOf, 1 << 20))
        assert old <= now, recipe["Id"]
        extra = now - old
        assert all(any(name in EGGS for name, _aux in way) for way in extra), (recipe["Id"], sorted(extra)[:3])
        assert bool(extra) == (("#" + Tags.EGG) in [option for slot in recipe["Slots"] for option in slot]), recipe["Id"]


def _option(ingredient, aliases):
    if "tag" in ingredient:
        return "#" + aliases[ingredient["tag"]]
    namespace, path = ingredient["item"].split(":")
    return ("arris" if namespace == "farmersdelight" else namespace) + ":" + path


def testSlotsAreTheJavaIngredientsSlotBySlot():
    if not os.path.isdir(JE_COOKING):
        print("跳过：没有 .refs 里 JE 的配方")
        return
    aliases = {}
    for name, javaNames in Tags.JE_NAMES.items():
        for javaName in javaNames:
            aliases[javaName] = name
    for recipe in Recipes.CookingPotRecipeList:
        path = os.path.join(JE_COOKING, recipe["Id"][len(PREFIX):] + ".json")
        with io.open(path, encoding="utf-8") as handle:
            ingredients = json.load(handle)["ingredients"]
        expected = [[_option(entry, aliases) for entry in (ingredient if isinstance(ingredient, list) else [ingredient])]
                    for ingredient in ingredients]
        assert recipe["Slots"] == expected, (recipe["Id"], recipe["Slots"], expected)


def testWaysStillExpandLikeBefore():
    assert Recipes._ways("t:a", ["t:b", "t:c"]) == [[("t:a", 0), ("t:b", 0)], [("t:a", 0), ("t:c", 0)]]
    mixed = Recipes._ways(["t:b", "t:a"], ["t:a", "t:b"])
    assert mixed == [[("t:b", 0), ("t:a", 0)], [("t:b", 0), ("t:b", 0)], [("t:a", 0), ("t:a", 0)]], "排好序一样的（b+a 与 a+b）只留第一种"
    assert Recipes._ways("#" + Tags.RAW_BEEF) == [[("minecraft:beef", 0)], [("arris:minced_beef", 0)]], "标签按词表的成员展开"
    assert Recipes._ways("#" + Tags.EGG) == [[("minecraft:egg", 0)]], "旧写法里鸡蛋只有普通鸡蛋"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
