# -*- coding: utf-8 -*-
# runner: both
"""厨锅配方表的写法（Shared/Data/CookingPotRecipes.py）：农夫乐事自己的 28 道每道有 JE 的配方 ID、每格的选项 Slots、展开出来的写法 Recipe。

- Id 是 farmersdelight:cooking/<JE 的配方文件名>，不重复；.refs 在场时正好是 JE 的 28 个厨锅配方文件；
- Slots 写法对（Shared/Rules/PotSlots.slotsProblem），格数等于每种写法的件数；
- Recipe（旧读者在读，契约的 AddCookingPotRecipe 往里加）照旧是 170 种写法，是普通的列表，就是把 Slots 一格一格展开
  （最后一格变得最快、排好序一样的只留第一种）。
"""
from __future__ import print_function

import os

import fdtest

Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Slots = fdtest.load("Shared.Rules.PotSlots")
JE_COOKING = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "generated", "resources", "data", "farmersdelight", "recipes", "cooking")
PREFIX = "farmersdelight:cooking/"


def testEveryBuiltInRecipeHasTheIdOfItsJavaFile():
    ids = [recipe["Id"] for recipe in Recipes.CookingPotRecipeList]
    assert len(ids) == 28 and len(set(ids)) == 28, ids
    assert all(recipeId.startswith(PREFIX) for recipeId in ids), ids
    if os.path.isdir(JE_COOKING):
        files = sorted(name[:-len(".json")] for name in os.listdir(JE_COOKING) if name.endswith(".json"))
        assert sorted(recipeId[len(PREFIX):] for recipeId in ids) == files, "28 道菜正好是 JE 的 28 个厨锅配方文件"


def testSlotsAreWellFormedAndTheWaysAreTheirExpansion():
    total = 0
    for recipe in Recipes.CookingPotRecipeList:
        slots = recipe["Slots"]
        assert Slots.slotsProblem(slots) is None, (recipe["Id"], Slots.slotsProblem(slots))
        assert all(len(way) == len(slots) for way in recipe["Recipe"]), recipe["Id"]
        assert recipe["Recipe"] == Slots.expand(slots, lambda tag: (), 1 << 20), recipe["Id"]
        assert type(recipe["Recipe"]) is list, "Recipe 是普通的列表：每格的选项在 Slots 键里，过得了线"
        total += len(recipe["Recipe"])
    assert total == 170, total


def testWaysStillExpandLikeBefore():
    assert Recipes._ways("t:a", ["t:b", "t:c"]) == [[("t:a", 0), ("t:b", 0)], [("t:a", 0), ("t:c", 0)]]
    mixed = Recipes._ways(["t:b", "t:a"], ["t:a", "t:b"])
    assert mixed == [[("t:b", 0), ("t:a", 0)], [("t:b", 0), ("t:b", 0)], [("t:a", 0), ("t:a", 0)]], "排好序一样的（b+a 与 a+b）只留第一种"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
