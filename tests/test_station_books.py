# -*- coding: utf-8 -*-
# runner: both
"""四个站点的食谱书页（Shared/Rules/StationBooks.py）：页的写法、当前在做的菜、服务端放料挑写法和份数。"""
from __future__ import print_function

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest
from optkit import Config

Books = fdtest.load("Shared.Rules.StationBooks")
Book = dgtest.load("Shared.Book")
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
    with Config(cooking_pot_time=2.0):
        slow = next(page for page in Books.potPages() if page["item"]["newItemName"] == "arris:dumplings")
        assert slow["note"] == "13 秒", "cooking_pot_time 2.0：书上的时间也翻倍（20 / 1.5）"


def testPotPagesKeepTheAlternativesOfEachSlotForTheBookToCycle():
    # RecipeBook.java:1456-1459：一格是一组备选，每秒换一种；配方表里 _ways 展开的留着每格的选项，书上就是一种写法、一格几个选项
    stew = next(page for page in Books.potPages() if page["item"]["newItemName"] == "minecraft:rabbit_stew")
    assert len(stew["ways"]) == 1, "不再是 2 种写法各占一页上的一种"
    cells = stew["ways"][0]
    assert cells[0] == [("minecraft:potato", 0)] and cells[1] == [("minecraft:rabbit", 0)] and cells[2] == [("minecraft:carrot", 0)]
    assert cells[3] == [("minecraft:brown_mushroom", 0), ("minecraft:red_mushroom", 0)], "蘑菇这一格两种都行"
    soup = next(page for page in Books.potPages() if page["item"]["newItemName"] == "arris:pumpkin_soup")
    assert soup["ways"] == [[[("arris:pumpkin_slice", 0)], [("arris:cabbage", 0), ("arris:cabbage_leaf", 0)],
                             [("minecraft:porkchop", 0), ("arris:bacon", 0)], [("minecraft:milk_bucket", 0), ("arris:milk_bottle", 0)]]],         "卷心菜 / 生猪肉 / 奶：整组备选都在，一格一组"
    # 书按"每格有没有一件"判断现在能不能做：任一备选在背包里就行
    have = {("minecraft:potato", 0): 1, ("minecraft:rabbit", 0): 1, ("minecraft:carrot", 0): 1, ("minecraft:red_mushroom", 0): 1}
    assert Book.bestWay(stew, have) == (0, [True, True, True, True], 0)
    assert Book.bestWay(stew, {("minecraft:potato", 0): 1})[1] == [True, False, False, False]
    for page in Books.potPages():
        _wellShaped(page)


def testRecipesAddedByDownstreamModsStayOneWayPerVariant():
    # 下游模组往 CookingPotRecipeList 追加的配方是普通列表（没有每格的选项）：照旧每种写法一件一格
    recipe = {"Recipe": [[("t:a", 0), ("t:b", 0)], [("t:a", 0), ("t:c", 0)]], "CookResult": ("t:dish", 0), "PushItem": [], "text": "试"}
    Recipes.CookingPotRecipeList.append(recipe)
    try:
        page = Books.potPages()[-1]
        assert page["item"]["newItemName"] == "t:dish"
        assert page["ways"] == [[[("t:a", 0)], [("t:b", 0)]], [[("t:a", 0)], [("t:c", 0)]]]
        assert isinstance(Recipes._ways("t:a", ["t:b", "t:c"]), list) and Recipes._ways("t:a", ["t:b", "t:c"]) == [
            [("t:a", 0), ("t:b", 0)], [("t:a", 0), ("t:c", 0)]], "_ways 的结果还是写法的列表"
    finally:
        Recipes.CookingPotRecipeList.remove(recipe)


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
    assert log["kind"] == "tools" and [item["newItemName"] for item in log["foot"]] == ["minecraft:stripped_oak_log", "arris:tree_bark"],         "脚注列全部产物（含主产物，JE BoardBook.java:55）"
    chicken = next(page for page in pages if page["key"] == "c:minecraft:chicken:0")
    assert [(item["newItemName"], item["count"]) for item in chicken["foot"]] == [("arris:chicken_cuts", 2), ("minecraft:bone_meal", 1)]
    assert chicken["item"]["newItemName"] == "arris:chicken_cuts", "页上的成品还是第一个"
    assert beef["foot"] == [], "只有一种产物的没有脚注"
    assert Books.dishOf("d:arris:egg_sandwich") and Books.dishOf("c:minecraft:beef:0") == [] and Books.dishOf(None) == []


def testCookingBooksListWhatThePanAndStoveTake():
    pan, grill = Books.panPages(), Books.grillPages()
    egg = next(page for page in pan if page["key"] == "minecraft:egg")
    bacon = next(page for page in pan if page["key"] == "arris:bacon")
    assert egg["item"]["newItemName"] == "arris:fried_egg"
    assert egg["note"] == bacon["note"], "SkilletBook 每道都是 2 * sideTicks：蛋不翻面，从下往上煎透用的也是两面的时间"
    assert all(page["note"] for page in grill)
    assert all(page["key"] != "minecraft:egg" for page in grill) and egg in pan, "炉灶的书不列蛋（HoD 的 StoveBook 只列烤架收的），煎锅的书列"
    assert next(page for page in grill if page["key"] == "minecraft:beef")["note"] == "20 秒", "两面各 10 秒"


def testTheThreeEggsShareOnePage():
    """基岩版的三种蛋都煎成煎蛋（都在原版的 minecraft:egg 标签里）：煎锅的书一页，原料那一格三种轮换；锅上放哪种蛋都翻到这一页。
    成品不同的、不在这个标签里的照旧一件一页；JEI 的煎锅 / 炉灶页用同一个分组（Compat/Jei/CookPages）。"""
    Cooking = fdtest.load("Shared.Data.Cooking")
    pan = Books.panPages()
    eggs = [page for page in pan if page["item"]["newItemName"] == "arris:fried_egg"]
    assert len(eggs) == 1 and eggs[0]["key"] == "minecraft:egg", eggs
    assert eggs[0]["ways"] == [[[("minecraft:egg", 0), ("minecraft:blue_egg", 0), ("minecraft:brown_egg", 0)]]]
    assert all(len(page["ways"][0][0]) == 1 for page in pan if page is not eggs[0]), "别的一件一页"
    assert len(pan) == len(Cooking.CanCookedFoodDict) - 2
    for name in ("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"):
        assert Books.cookCurrent([_item("arris:fried_egg"), _item(name)]) == "minecraft:egg", name
    assert ([("minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg")] ==
            [tuple(raws) for raws, result in Books.cookGroups() if result == "arris:fried_egg"])
    Cooking.CanCookedFoodDict["minecraft:brown_egg"] = "test:brown_omelette"
    try:
        groups = dict((tuple(raws), result) for raws, result in Books.cookGroups())
        assert groups[("minecraft:egg", "minecraft:blue_egg")] == "arris:fried_egg" and groups[("minecraft:brown_egg",)] == "test:brown_omelette"
        assert Books.cookCurrent([_item("minecraft:brown_egg")]) == "minecraft:brown_egg", "成品不同：自己一页"
    finally:
        Cooking.CanCookedFoodDict["minecraft:brown_egg"] = "arris:fried_egg"


def testAOneSidedFoodIsWrittenWithTheTimeOfBothSidesInEitherBook():
    """HoD 的 SkilletBook（31 行）、StoveBook（36 行）都写 2 * sideTicks、不看 one_sided：只煎一面的从下往上煎透，用的也是两面的时间。
    缺省（OneSidedList 只有蛋，蛋上不了烤架）两本书都看不出；往 OneSidedList 里临时加一件烤架收的（马铃薯，测完删掉），炉灶书上它照样是两面的 20 秒，
    煎锅书上和别的一样。"""
    Cooking = fdtest.load("Shared.Data.Cooking")

    def notes(name):
        pan = next(page for page in Books.panPages() if page["key"] == name)["note"]
        return pan, next(page for page in Books.grillPages() if page["key"] == name)["note"]

    beef = notes("minecraft:beef")
    assert beef[1] == "20 秒" and notes("minecraft:potato") == beef, "缺省：马铃薯和牛肉一样"
    Cooking.OneSidedList.append("minecraft:potato")
    try:
        assert notes("minecraft:potato") == beef, "只煎一面的也写两面的时间：炉灶书不是一面的 10 秒"
        assert next(page for page in Books.panPages() if page["key"] == "minecraft:egg")["note"] == beef[0], "蛋照旧"
    finally:
        Cooking.OneSidedList.remove("minecraft:potato")
    assert Cooking.OneSidedList == ["minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"]


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


def testThePotsCurrentPageIsNeverATombstone():
    """T 复核 3.4：锅里那道已经删掉的菜（墓碑）没有书页，potCurrent 以前返回墓碑的下标，前置包的书拿到找不到页的键会丢掉玩家上次选的页。"""
    soup = next(recipe for recipe in Recipes.CookingPotRecipeList if recipe["CookResult"][0] == "arris:chicken_soup")
    soup["Disabled"] = True
    try:
        assert Books.potCurrent([], _item("arris:chicken_soup", 4)) is None
    finally:
        del soup["Disabled"]
    assert Books.potCurrent([], _item("arris:chicken_soup", 4)) is not None


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
