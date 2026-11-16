# -*- coding: utf-8 -*-
# runner: both
"""厨锅配方匹配与出料结算（Shared/Rules/CookingPot.py）。"""
from __future__ import print_function

import fdtest

Rules = fdtest.load("Shared.Rules.CookingPot")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")


def _item(name, aux=0, count=1):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def testEveryVariantOfEveryRecipeMatches():
    seen = set()
    for recipeDict in Recipes.CookingPotRecipeList:
        for variant in recipeDict["Recipe"]:
            key = tuple(sorted(variant))
            if key in seen:
                continue  # 键冲突时以先出现的配方为准，另测
            seen.add(key)
            slots = [_item(name, aux) for name, aux in variant] + [{}] * (6 - len(variant))
            result, pushItems = Rules.matchRecipe(slots)
            assert result is not None, variant
            assert (result["newItemName"], result["newAuxValue"]) == recipeDict["CookResult"], variant
            assert result["count"] == 1
            assert pushItems == recipeDict.get("PushItem", [])


def testSlotOrderAndStackSizeDoNotMatter():
    recipeDict = Recipes.CookingPotRecipeList[0]
    variant = recipeDict["Recipe"][0]
    forward = [_item(name, aux, 5) for name, aux in variant]
    backward = [{}] + [_item(name, aux) for name, aux in reversed(variant)]
    assert Rules.matchRecipe(forward)[0] == Rules.matchRecipe(backward)[0]


def testEmptyAndUnknownInputs():
    assert Rules.matchRecipe([{}] * 6) == (None, None)
    assert Rules.matchRecipe([None, {}]) == (None, None)
    assert Rules.matchRecipe([_item("test:nothing")]) == (None, None)
    assert Rules.inputKeyOf([{}, None]) is None


def testFirstRecipeWinsOnKeyCollision():
    recipes = Recipes.CookingPotRecipeList
    variant = [("test:dup_a", 0), ("test:dup_b", 0)]
    first = {"Recipe": [variant], "CookResult": ("test:first", 0), "PushItem": [], "text": "1"}
    second = {"Recipe": [list(reversed(variant))], "CookResult": ("test:second", 0), "PushItem": [], "text": "2"}
    recipes.append(first)
    recipes.append(second)
    try:
        Rules.rebuildIndex()
        result = Rules.matchRecipe([_item("test:dup_b"), _item("test:dup_a")])[0]
        assert result["newItemName"] == "test:first"
        assert Rules.findRecipeByResult("test:second") is second
    finally:
        recipes.remove(first)
        recipes.remove(second)
        Rules.rebuildIndex()


def testTransferAmount():
    # 不超过待出料、产出槽剩余空间、容器数
    assert Rules.transferAmount(5, 0, 64) == 5
    assert Rules.transferAmount(5, 62, 64) == 2
    assert Rules.transferAmount(5, 64, 64) == 0
    assert Rules.transferAmount(5, 0, 64, vesselCount=3) == 3
    assert Rules.transferAmount(5, 0, 64, vesselCount=0) == 0
    assert Rules.transferAmount(5, 70, 64) == 0, "产出槽异常超堆叠时不转移、不出现负数"
    assert Rules.transferAmount(16, 10, 16, vesselCount=64) == 6



def testCookTimesFollowJava():
    """JE 的厨锅配方缺省 200 刻；番茄酱、熟米饭、卷心菜卷 100 刻，南瓜盅 400 刻。"""
    assert Rules.cookSecondsOf("minecraft:mushroom_stew") == 10.0
    for name in ("arris:tomato_sauce", "arris:cooked_rice", "arris:cabbage_rolls"):
        assert Rules.cookSecondsOf(name) == 5.0, name
    assert Rules.cookSecondsOf("arris:stuffed_pumpkin_block_stage0") == 20.0
    assert Rules.cookSecondsOf("mod:unknown") == 10.0

if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
