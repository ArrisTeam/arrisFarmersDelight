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
            assert result["count"] == recipeDict.get("CookCount", 1)
            assert pushItems == Rules.pushItemsOf(variant, recipeDict.get("PushItem"))


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

def _match(*names):
    return Rules.matchRecipe([_item(name) for name in names])


def testIngredientsFollowJava():
    """JE 的配料：鱼肉炖、两种意面用番茄酱；面条汤用生鸡蛋和生猪肉；卷心菜卷两样料、不要容器；标签含生肉 / 整颗卷心菜 / 奶桶。"""
    assert _match("minecraft:cod", "arris:tomato_sauce", "arris:onion")[0]["newItemName"] == "arris:fish_stew"
    assert _match("arris:mutton_chops", "arris:raw_pasta", "arris:tomato_sauce")[0]["newItemName"] == "arris:pasta_with_mutton_chop"
    assert _match("arris:minced_beef", "arris:raw_pasta", "arris:tomato_sauce")[0]["newItemName"] == "arris:pasta_with_meatballs"
    assert _match("arris:cod_slice", "arris:tomato", "arris:onion") == (None, None), "鱼肉炖不用生番茄"
    assert _match("arris:raw_pasta", "minecraft:egg", "minecraft:dried_kelp", "minecraft:porkchop")[0]["newItemName"] == "arris:noodle_soup"
    assert _match("arris:cabbage", "minecraft:carrot")[0]["newItemName"] == "arris:cabbage_rolls"
    assert Rules.findRecipeByResult("arris:cabbage_rolls").get("Vessel") is None
    assert _match("minecraft:beef", "minecraft:carrot", "minecraft:potato")[0]["newItemName"] == "arris:cookbeef_stew"
    assert _match("minecraft:brown_mushroom", "minecraft:brown_mushroom") == (None, None), "蘑菇煲是一红一棕"


def testDumplingsMakeTwoWithoutAContainer():
    result, pushItems = _match("arris:wheat_dough", "arris:cabbage_leaf", "arris:onion", "minecraft:brown_mushroom")
    assert result["newItemName"] == "arris:dumplings" and result["count"] == 2 and pushItems == []
    assert Rules.findRecipeByResult("arris:dumplings").get("Vessel") is None


def testUsedUpContainersComeBack():
    assert _match("minecraft:milk_bucket", "minecraft:sugar", "minecraft:cocoa_beans", "minecraft:cocoa_beans")[1] == [("minecraft:bucket", 0)]
    assert _match("arris:milk_bottle", "minecraft:sugar", "minecraft:cocoa_beans", "minecraft:cocoa_beans")[1] == [("minecraft:glass_bottle", 0)]
    variant = [("arris:milk_bottle", 0), ("test:x", 0)]
    assert Rules.pushItemsOf(variant, [("minecraft:glass_bottle", 0)]) == [("minecraft:glass_bottle", 0)], "下游写过的不重复给"
    assert Rules.pushItemsOf(variant, [("test:y", 0)]) == [("test:y", 0), ("minecraft:glass_bottle", 0)]


def testExperienceFollowsJava():
    assert Rules.experienceOf("arris:fried_rice") == 1.0
    assert Rules.experienceOf("arris:tomato_sauce") == 0.35
    assert Rules.experienceOf("arris:stuffed_pumpkin_block_stage0") == 2.0
    assert Rules.experienceOf("arris:dumplings") == 0.5, "JE 按煮了几份给经验：一份 2 个饺子，每个一半"
    assert Rules.experienceOrb(0.35, 3, 0.04) == 2 and Rules.experienceOrb(0.35, 3, 0.06) == 1
    assert Rules.experienceOrb(1.0, 4, 0.99) == 4
    assert Rules.experienceOrb(0.0, 4, 0.0) == 0


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
