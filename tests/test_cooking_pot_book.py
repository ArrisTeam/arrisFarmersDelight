# -*- coding: utf-8 -*-
# runner: both
"""厨锅食谱书的规则（Shared/Rules/CookingPotBook.py）：搜索、详情格、补食材的计划。纯数据，不碰库。"""
from __future__ import print_function

import io
import json
import os
import re

import fdtest

Book = fdtest.load("Shared.Rules.CookingPotBook")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
SCRIPTS = os.path.join(fdtest.BP, fdtest.SCRIPTS)


def testSlotLayoutMatchesTheContainer():
    assert (Book.INPUT_SLOTS, Book.VESSEL_SLOT, Book.RESULT_SLOT, Book.POT_SLOTS) == (6, 6, 7, 8)
    assert Book.BOOK_CELLS == Book.POT_SLOTS


def _serverConstants():
    """服务端那边定义的容器格号（引擎模块离线导不了，按源码文本读）：烹饪 tick 读写的就是这几格。"""
    for name in ("Server/Helpers/PotContainer.py", "Server/CookingPot.py"):
        path = os.path.join(SCRIPTS, *name.split("/"))
        if not os.path.isfile(path):
            continue
        text = io.open(path, encoding="utf-8").read()
        found = dict((key, re.search(r"^%s = (\d+)$" % key, text, re.M)) for key in ("INPUT_SLOTS", "VESSEL_SLOT", "RESULT_SLOT"))
        if all(found.values()):
            return dict((key, int(match.group(1))) for key, match in found.items())
    raise AssertionError("服务端模块里找不到 INPUT_SLOTS / VESSEL_SLOT / RESULT_SLOT 的定义")


def testSlotLayoutMatchesTheServerAndTheBlockJson():
    # 界面模型的格号是写在 Shared 里的一份：与烹饪 tick 读写的格号、方块 JSON 声明的容器大小对不上时，界面会读写错格子
    assert _serverConstants() == {"INPUT_SLOTS": Book.INPUT_SLOTS, "VESSEL_SLOT": Book.VESSEL_SLOT,
                                  "RESULT_SLOT": Book.RESULT_SLOT}
    path = os.path.join(fdtest.BP, "netease_blocks", "arris_cooking_pot.json")
    block = json.load(io.open(path, encoding="utf-8"))["minecraft:block"]["components"]
    assert block["netease:block_container"]["container_size"] == Book.POT_SLOTS
    assert "netease:listen_block_remove" not in block   # 库的方块宿主在运行期开方块移除事件，JSON 里再写会让方块与图标都不画


def testEveryVariantFitsInTheIngredientSlots():
    for recipe in Recipes.CookingPotRecipeList:
        for variant in recipe["Recipe"]:
            assert 0 < len(variant) <= Book.INPUT_SLOTS, recipe["text"]


def testEmptySearchShowsEveryRecipeInTableOrder():
    assert Book.visibleRecipes("") == list(range(len(Recipes.CookingPotRecipeList)))
    assert Book.visibleRecipes(None) == Book.visibleRecipes("")


def testSearchMatchesTheRecipeNameAndKeepsTableOrder():
    word = Recipes.CookingPotRecipeList[0]["text"][:3]   # 第一条食谱名的头一个字（utf-8 字节串 / 文字都一样）
    found = Book.visibleRecipes(word)
    assert found and found[0] == 0
    assert found == sorted(found)
    for index in found:
        assert word in Recipes.CookingPotRecipeList[index]["text"]
    assert Book.visibleRecipes("绝对没有这道菜") == []


def testSearchToleratesUnicodeRecipeNamesFromDownstreamMods():
    # 下游模组追加的食谱名可能是 unicode（py2 下与 utf-8 字节串的搜索词混着比较不能抛异常）；py3 里两者都是 str
    recipe = {"Recipe": [[("test:a", 0)]], "CookResult": ("test:b", 0), "PushItem": [], "text": u"测试菜"}
    Recipes.CookingPotRecipeList.append(recipe)
    try:
        index = len(Recipes.CookingPotRecipeList) - 1
        assert index in Book.visibleRecipes("测试")
        assert index in Book.visibleRecipes(u"测试")
        assert index not in Book.visibleRecipes("蘑菇")
    finally:
        Recipes.CookingPotRecipeList.remove(recipe)


def testPickedRecipeIndexesTheFilteredList():
    shown = Book.visibleRecipes("煲")
    assert len(shown) >= 2
    assert Book.pickedRecipe("煲", 1) is Recipes.CookingPotRecipeList[shown[1]]
    assert Book.pickedRecipe("煲", -1) is None
    assert Book.pickedRecipe("煲", len(shown)) is None
    assert Book.recipeAt(len(Recipes.CookingPotRecipeList)) is None
    assert Book.recipeAt(-1) is None


def testVariantWrapsAround():
    recipe = next(r for r in Recipes.CookingPotRecipeList if len(r["Recipe"]) >= 2)
    count = Book.variantCount(recipe)
    assert count == len(recipe["Recipe"])
    assert Book.variantOf(recipe, 0) == list(recipe["Recipe"][0])
    assert Book.variantOf(recipe, count) == Book.variantOf(recipe, 0)
    assert Book.variantOf(recipe, count + 1) == list(recipe["Recipe"][1])


def testBookCells():
    recipe = Recipes.CookingPotRecipeList[0]
    cells = Book.bookCells(recipe, 0)
    variant = Book.variantOf(recipe, 0)
    for index, (name, aux) in enumerate(variant):
        assert cells[index] == {"newItemName": name, "newAuxValue": aux, "count": 1}
    assert cells[Book.VESSEL_SLOT]["newItemName"] == recipe["Vessel"][0]
    assert cells[Book.RESULT_SLOT]["newItemName"] == recipe["CookResult"][0]
    assert set(cells) == set(range(len(variant))) | {Book.VESSEL_SLOT, Book.RESULT_SLOT}
    bare = {"Recipe": [[("test:a", 0)]], "CookResult": ("test:b", 1), "PushItem": [], "text": "x"}
    assert sorted(Book.bookCells(bare, 0)) == [0, Book.RESULT_SLOT]   # 没有容器的食谱，容器格空着


def testListRowsAreTheResultsInOrder():
    rows = Book.listRows([0, 2])
    assert [row["newItemName"] for row in rows] == [Recipes.CookingPotRecipeList[0]["CookResult"][0],
                                                    Recipes.CookingPotRecipeList[2]["CookResult"][0]]
    assert all(row["count"] == 1 for row in rows)


def testVesselNamesFollowTheRecipeTable():
    assert "minecraft:bowl" in Book.vesselNames()
    recipe = {"Recipe": [[("test:a", 0)]], "CookResult": ("test:b", 0), "Vessel": ("test:jar", 0), "PushItem": [],
              "text": "x"}
    Recipes.CookingPotRecipeList.append(recipe)
    try:
        assert "test:jar" in Book.vesselNames()   # 下游追加的容器也算，不缓存
    finally:
        Recipes.CookingPotRecipeList.remove(recipe)
    assert "test:jar" not in Book.vesselNames()


def testVesselAndIngredientRoles():
    assert Book.isPureVessel("minecraft:bowl") and not Book.isAmbiguous("minecraft:bowl")
    # FD 1.3.4 的卷心菜叶只是食材；下游配方拿它当容器时就两样都是
    assert not Book.isAmbiguous("arris:cabbage_leaf") and not Book.isPureVessel("arris:cabbage_leaf")
    wrap = {"Recipe": [[("test:filling", 0)]], "CookResult": ("test:wrap", 0), "Vessel": ("arris:cabbage_leaf", 0),
            "PushItem": [], "text": "x"}
    Recipes.CookingPotRecipeList.append(wrap)
    try:
        assert Book.isAmbiguous("arris:cabbage_leaf") and not Book.isPureVessel("arris:cabbage_leaf")
    finally:
        Recipes.CookingPotRecipeList.remove(wrap)
    assert "minecraft:carrot" in Book.ingredientNames()
    assert not Book.isPureVessel("minecraft:carrot") and not Book.isAmbiguous("minecraft:carrot")
    assert not Book.isPureVessel(None) and not Book.isAmbiguous(None)


def testKeyOfIgnoresUserDataAndEmptyStacks():
    assert Book.keyOf(None) is None
    assert Book.keyOf({}) is None
    assert Book.keyOf({"newItemName": "a:b", "newAuxValue": 0, "count": 0}) is None
    assert Book.keyOf({"newItemName": "a:b", "newAuxValue": None, "count": 3, "userData": {"x": 1}}) == ("a:b", 0)


def _key(name, aux=0):
    return (name, aux)


def testPlanFillPutsEachIngredientInItsOwnEmptySlot():
    variant = [_key("a"), _key("a"), _key("b")]
    placements, topUps = Book.planFill(variant, [None] * 6)
    assert placements == [(0, _key("a")), (1, _key("a")), (2, _key("b"))]
    assert topUps == []


def testPlanFillTopsUpSlotsAlreadyHoldingAnIngredient():
    variant = [_key("a"), _key("b"), _key("a")]
    slots = [None, _key("a"), None, _key("c"), None, None]   # 1 号格已有 a，3 号格是不相干的东西
    placements, topUps = Book.planFill(variant, slots)
    assert topUps == [(1, _key("a"))]
    assert placements == [(0, _key("b")), (2, _key("a"))]   # 第二个 a 不能叠在已有的那一格，要另占一格


def testPlanFillGivesUpWhenThereAreNotEnoughEmptySlots():
    variant = [_key("a")] * 3
    slots = [_key("z")] * 4 + [None, None]
    assert Book.planFill(variant, slots) is None
    assert Book.planFill([_key("z")], slots) == ([], [(0, _key("z"))])   # 已有的算数，不再占空格


def testPlanFillDistinguishesAuxValues():
    placements, topUps = Book.planFill([_key("dye", 1)], [_key("dye", 2), None, None, None, None, None])
    assert topUps == [] and placements == [(1, _key("dye", 1))]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
