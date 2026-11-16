# -*- coding: utf-8 -*-
# runner: both
"""四个站点的食谱书页（Shared/Rules/StationBooks.py）：页的写法、当前在做的菜、服务端放料挑写法和份数。"""
from __future__ import print_function

import fdtest

Books = fdtest.load("Shared.Rules.StationBooks")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
PotCooking = fdtest.load("Shared.Rules.HandsOn.PotCooking")


def _item(name, count=1, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


def _wellShaped(page):
    assert page["item"]["newItemName"] and page["ways"], page["key"]
    for way in page["ways"]:
        assert 1 <= len(way) <= 9, page["key"]
        for options in way:
            assert options and all(len(option) == 2 for option in options), page["key"]


def testPotPagesFollowTheRecipeTable():
    pages = Books.potPages()
    assert [page["key"] for page in pages] == list(range(len(Recipes.CookingPotRecipeList)))
    for page in pages:
        _wellShaped(page)
    dumplings = next(page for page in pages if page["item"]["newItemName"] == "arris:dumplings")
    assert dumplings["item"]["count"] == 2 and dumplings["note"] == "7 秒", "10 秒的配方在站点里一份 10 / 1.5 = 6.7 秒（HoD 的 PotBook）"
    assert [item["newItemName"] for item in dumplings["foot"]] == [Books.CLOCK], "饺子不要容器，只有时钟"
    sauce = next(page for page in pages if page["item"]["newItemName"] == "arris:tomato_sauce")
    assert sauce["note"] == "3 秒" and sauce["foot"][0]["newItemName"] == "minecraft:bowl"
    before = PotCooking.COOKING_POT_TIME
    try:
        PotCooking.COOKING_POT_TIME = 2.0
        slow = next(page for page in Books.potPages() if page["item"]["newItemName"] == "arris:dumplings")
        assert slow["note"] == "13 秒", "cooking_pot_time 2.0：书上的时间也翻倍（20 / 1.5）"
    finally:
        PotCooking.COOKING_POT_TIME = before


def testBoardPagesHaveDishesBaseFirstAndCutsWithTheirTools():
    pages = Books.boardPages()
    for page in pages:
        _wellShaped(page)
    kinds = set(page["kind"] for page in pages)
    assert kinds == {"dishes", "knife", "tools"}
    sandwich = next(page for page in pages if page["key"] == "d:arris:egg_sandwich")
    assert sandwich["ways"][0][0] == [("minecraft:bread", 0)], "底座在前"
    beef = next(page for page in pages if page["key"] == "c:minecraft:beef:0")
    assert beef["kind"] == "knife" and beef["item"]["newItemName"] == "arris:minced_beef"
    assert ("arris:iron_knife", 0) in beef["ways"][0][1]
    log = next(page for page in pages if page["key"] == "c:minecraft:oak_log:0")
    assert log["kind"] == "tools" and [item["newItemName"] for item in log["foot"]] == ["arris:tree_bark"]
    assert Books.dishOf("d:arris:egg_sandwich") and Books.dishOf("c:minecraft:beef:0") == [] and Books.dishOf(None) == []


def testCookingBooksListWhatThePanAndStoveTake():
    pan, grill = Books.panPages(), Books.grillPages()
    egg = next(page for page in pan if page["key"] == "minecraft:egg")
    bacon = next(page for page in pan if page["key"] == "arris:bacon")
    assert egg["item"]["newItemName"] == "arris:fried_egg"
    assert int(egg["note"].split()[0]) * 2 == int(bacon["note"].split()[0]), "蛋只煎一面"
    assert all(page["note"] for page in grill)


def testWhatTheStationIsMakingNow():
    assert Books.potCurrent([_item("arris:tomato", 3), _item("arris:tomato", 2), {}]) == next(
        index for index, recipe in enumerate(Recipes.CookingPotRecipeList) if recipe["CookResult"][0] == "arris:tomato_sauce")
    assert Books.potCurrent([_item("minecraft:dirt")]) is None
    soup = next(index for index, recipe in enumerate(Recipes.CookingPotRecipeList) if recipe["CookResult"][0] == "arris:chicken_soup")
    assert Books.potCurrent([], _item("arris:chicken_soup", 4)) == soup, "料做不成菜：锅里那锅煮好的汤"
    assert Books.potCurrent([_item("arris:tomato", 2), _item("arris:tomato", 2)], _item("arris:chicken_soup", 4)) != soup, "正在做的那道在先"
    assert Books.potCurrent([], {}) is None
    assert Books.boardCurrent([_item("minecraft:bread"), _item("arris:fried_egg"), _item("arris:fried_egg")], None) \
        == "d:arris:egg_sandwich"
    assert Books.boardCurrent([], _item("minecraft:beef")) == "c:minecraft:beef:0"
    assert Books.boardCurrent([], None) is None
    assert Books.cookCurrent([None, _item("minecraft:cooked_beef"), _item("arris:bacon")]) == "arris:bacon"


def testFillingPicksTheWayThePlayerCanMakeMostOf():
    stew = next(recipe for recipe in Recipes.CookingPotRecipeList if recipe["CookResult"][0] == "arris:cookbeef_stew")
    pool = {("arris:minced_beef", 0): 5, ("minecraft:beef", 0): 1, ("minecraft:carrot", 0): 9, ("minecraft:potato", 0): 9}
    kinds = Books.bestKinds(stew["Recipe"], pool)
    assert ("arris:minced_beef", 0) in kinds
    assert Books.setsOf(kinds, pool, 16) == 5 and Books.setsOf(kinds, pool, 1) == 1
    assert Books.bestKinds(stew["Recipe"], {("minecraft:carrot", 0): 9}) is None
    sauce = [("arris:tomato", 0), ("arris:tomato", 0)]
    assert Books.needOf(sauce) == {("arris:tomato", 0): 2} and Books.setsOf(sauce, {("arris:tomato", 0): 7}, 16) == 3
    assert Books.potRecipe(0) is Recipes.CookingPotRecipeList[0] and Books.potRecipe(-1) is None
    assert Books.potRecipe(True) is None and Books.potRecipe("0") is None


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
