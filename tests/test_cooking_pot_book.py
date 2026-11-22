# -*- coding: utf-8 -*-
# runner: both
"""厨锅经典界面的食谱规则（Shared/Rules/CookingPotBook.py）：搜索与食谱格、详情格与写法轮换、补食材的计划与试写法的先后。纯数据，不碰库。"""
from __future__ import print_function

import io
import json
import os
import re

import fdtest

Book = fdtest.load("Shared.Rules.CookingPotBook")
PotRules = fdtest.load("Shared.Rules.CookingPot")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
SCRIPTS = os.path.join(fdtest.BP, fdtest.SCRIPTS)


def testSlotLayoutMatchesTheContainer():
    assert (Book.INPUT_SLOTS, Book.VESSEL_SLOT, Book.RESULT_SLOT, Book.POT_SLOTS) == (6, 6, 7, 8)
    assert Book.BOOK_CELLS == Book.VESSEL_SLOT + 1, "详情格是食材格加容器格；成品画在锅形预览框里，另是一样界面数据"


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
    assert set(cells) == set(range(len(variant))) | {Book.VESSEL_SLOT}
    assert max(cells) < Book.BOOK_CELLS
    assert Book.resultOf(recipe) == {"newItemName": recipe["CookResult"][0], "newAuxValue": recipe["CookResult"][1], "count": 1}
    bare = {"Recipe": [[("test:a", 0)]], "CookResult": ("test:b", 1), "PushItem": [], "text": "x"}
    assert sorted(Book.bookCells(bare, 0)) == [0]   # 没有容器的食谱，容器格空着
    assert Book.resultOf(bare)["newAuxValue"] == 1


def testGridCellsAreTheResultsOfTheFilteredRecipesInOrder():
    table = Recipes.CookingPotRecipeList
    cells = Book.gridCells("")
    assert sorted(cells) == list(range(len(table))) == list(range(Book.shownCount("")))
    assert [cells[slot]["newItemName"] for slot in range(len(table))] == [recipe["CookResult"][0] for recipe in table]
    assert all(cell["count"] == 1 for cell in cells.values())
    shown = Book.visibleRecipes("煲")
    found = Book.gridCells("煲")
    assert sorted(found) == list(range(len(shown))) == list(range(Book.shownCount("煲")))
    assert [found[slot]["newItemName"] for slot in range(len(shown))] == [table[index]["CookResult"][0] for index in shown]
    assert Book.gridCells("绝对没有这道菜") == {} and Book.shownCount("绝对没有这道菜") == 0


def testSearchResultsAreRememberedUntilTheTableChanges():
    # 界面画食谱格时每一格都来要一遍：同一个搜索词给同一个字典；表变长了、配方索引重建了（联动接口改表、客户端并表）就重算
    first = Book.gridCells("")
    assert Book.gridCells("") is first and Book.gridCells(u"") is first
    shown = Book.visibleRecipes("")
    shown.append(-1)   # 给出去的下标表是一份拷贝：用的人改了它，记着的不跟着变
    assert -1 not in Book.visibleRecipes("")
    recipe = {"Recipe": [[("test:a", 0)]], "CookResult": ("test:grid", 0), "PushItem": [], "text": u"测试格"}
    Recipes.CookingPotRecipeList.append(recipe)
    try:
        grown = Book.gridCells("")
        assert grown is not first and grown[len(first)]["newItemName"] == "test:grid"
        assert len(Book.visibleRecipes("测试格")) == 1
        recipe["text"] = u"改过的名字"   # 就地改了一行（客户端并表、联动接口加写法都是就地改，之后都重建索引）：重建之后才认
        assert len(Book.visibleRecipes("测试格")) == 1
        PotRules.rebuildIndex()
        assert Book.visibleRecipes("测试格") == [] and len(Book.visibleRecipes("改过")) == 1
    finally:
        Recipes.CookingPotRecipeList.remove(recipe)
        PotRules.rebuildIndex()
    assert Book.gridCells("") == first


def testTheShownVariantTurnsOncePerPeriodStartingWithTheFirst():
    assert Book.VARIANT_SECONDS == 1.0
    assert [Book.shownVariant(3, 10.0, now) for now in (10.0, 10.99, 11.0, 12.5, 13.0, 14.0)] == [0, 0, 1, 2, 0, 1]
    assert [Book.shownVariant(1, 10.0, now) for now in (10.0, 11.0, 500.0)] == [0, 0, 0], "只有一种写法：总是第一种"
    assert Book.shownVariant(3, 10.0, 9.0) == 0, "钟往回走了：当刚选中"
    assert Book.shownVariant(4, 0.0, 5.0, period=2.0) == 2


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


def testPresentCountMatchesOneSlotPerIngredient():
    slots = [_key("a"), _key("a"), _key("b"), None, _key("z"), None]
    assert Book.presentCount([_key("a"), _key("a"), _key("a")], slots) == 2   # 第三个 a 锅里没有
    assert Book.presentCount([_key("a"), _key("b")], slots) == 2
    assert Book.presentCount([_key("c")], slots) == 0
    assert Book.presentCount([_key("a")], [None] * 6) == 0
    placements, topUps = Book.planFill([_key("a"), _key("a"), _key("a")], slots)
    assert len(topUps) == Book.presentCount([_key("a"), _key("a"), _key("a")], slots), "和补料计划认的是同一套"


def testFillOrderPutsTheVariantThePotHoldsMostOfFirstAndKeepsTableOrderOnTies():
    recipe = {"Recipe": [[_key("a"), _key("a")], [_key("b"), _key("b")], [_key("a"), _key("b")], [_key("c")]],
              "CookResult": ("test:r", 0), "PushItem": [], "text": "x"}
    rows = recipe["Recipe"]
    assert Book.fillOrder(recipe, [None] * 6) == rows, "锅是空的：照表里的先后"
    assert Book.fillOrder(recipe, [_key("b")] + [None] * 5) == [rows[1], rows[2], rows[0], rows[3]]
    assert Book.fillOrder(recipe, [_key("a"), _key("b")] + [None] * 4) == [rows[2], rows[0], rows[1], rows[3]]
    assert Book.fillOrder(recipe, [_key("c")] + [None] * 5) == [rows[3], rows[0], rows[1], rows[2]]
    assert Book.fillOrder({"Recipe": [[_key("a")]], "CookResult": ("test:r", 0)}, [None] * 6) == [[_key("a")]]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
