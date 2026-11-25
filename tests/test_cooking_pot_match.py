# -*- coding: utf-8 -*-
# runner: both
"""厨锅的逐格配对（Shared/Rules/CookingPot.py + PotRecipeTable.py）：

- 只有农夫乐事在场（标签按静态词表答）时，和原来"预先展开 + 排好序查表"的索引一个结果：今天的每一种写法配成同一道菜、余料一样，
  原来配不上的（一到三件料的组合）照旧配不上；站点的候选摆法（candidatesFor）和原来一模一样；
- 标签格：别的模组的东西进了标签就能用（假的引擎口）。口准备好之前照 ItemTags 的规矩按单件问引擎、枚举只给静态表，而且什么答案都不记
  （引擎改了口马上跟上）；准备好以后记着答案，换代（ItemTags.generation 变了）时作废；
- 表里靠前的赢（格子形和旧写法之间也是）；墓碑（Disabled）配不上（锅里已经煮好的照它盛）；只有 Slots、没有写法的配方也配得上，余料按锅里实际那几件算；
- rebuildIndex 只是作废，下次用到时重算。
"""
from __future__ import print_function

import itertools

import fdtest

Rules = fdtest.load("Shared.Rules.CookingPot")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
TABLE = Recipes.CookingPotRecipeList


def _item(name, aux=0, count=1):
    return {"newItemName": name, "newAuxValue": aux, "count": count}


class Port(object):
    """假的引擎口：准备好以后给出 extra 里的成员（别的模组登记进标签的）。"""

    def __init__(self, extra, ready=True):
        self.extra, self.isReady = extra, ready

    def ready(self):
        return self.isReady

    def itemsOf(self, tag):
        return list(self.extra.get(tag, ()))

    def tagsOf(self, name, aux=0):
        return [tag for tag, members in self.extra.items() if name in members]

    def blocksOf(self, tag):
        return []

    def blockTagsOf(self, name):
        return []


class Rows(object):
    """with Rows(行, ...)：临时往表尾加几行（进去时 rebuildIndex），出来时拿掉。"""

    def __init__(self, *rows):
        self.rows = rows

    def __enter__(self):
        TABLE.extend(self.rows)
        Rules.rebuildIndex()
        return self

    def __exit__(self, *exc):
        for row in self.rows:
            TABLE.remove(row)
        Rules.rebuildIndex()
        return False


def _oldIndex():
    """原来的索引（rebuildIndex 预先展开、排好序的写法查表；撞键时靠前的赢）：键 -> (配方序号, 那种写法)。"""
    index = {}
    for at, recipe in enumerate(TABLE):
        for variant in recipe["Recipe"]:
            index.setdefault(tuple(sorted(variant)), (at, variant))
    return index


def _oldCandidates():
    found = {}
    for at, recipe in enumerate(TABLE):
        for variant in recipe["Recipe"]:
            parts = {}
            for entry in variant:
                parts[entry] = parts.get(entry, 0) + 1
            found.setdefault(frozenset(parts), []).append((at, parts))
    return found


def testEveryWayOfTodayMatchesTheSameDishAsTheOldIndex():
    old = _oldIndex()
    for key, (at, variant) in old.items():
        slots = [_item(name, aux) for name, aux in reversed(variant)]
        assert Rules.matchIndex(slots) == at, (variant, Rules.matchIndex(slots), at)
        result, pushed = Rules.matchRecipe(slots)
        recipe = TABLE[at]
        assert (result["newItemName"], result["newAuxValue"]) == recipe["CookResult"] and result["count"] == recipe.get("CookCount", 1)
        assert pushed == Rules.pushItemsOf(variant, recipe.get("PushItem")), "配上的是旧写法：余料照那种写法算，和原来一样"
        assert Rules.lookupRecipe(key) == (recipe["CookResult"], pushed)


def testWhatTheOldIndexDidNotMatchStillDoesNotMatch():
    old = _oldIndex()
    kinds = sorted(set(entry for recipe in TABLE for variant in recipe["Recipe"] for entry in variant))
    checked = 0
    for size in (1, 2, 3):
        for count, combo in enumerate(itertools.combinations_with_replacement(kinds, size)):
            if size == 3 and count % 7:
                continue                                  # 三件的组合抽七分之一（全跑太慢），一到两件的全跑
            expected = old.get(tuple(sorted(combo)))
            assert Rules.matchIndex([_item(name, aux) for name, aux in combo]) == (expected[0] if expected else None), combo
            checked += 1
    assert checked > 3000, checked


def testStationCandidatesAreTheSameAsBefore():
    old = _oldCandidates()
    for kinds, expected in old.items():
        assert Rules.candidatesFor(kinds) == expected, sorted(kinds)
        assert Rules.partsFor(kinds) == [parts for _at, parts in expected]
    assert Rules.candidatesFor([("test:nothing", 0)]) == []


def testATagSlotTakesOtherModsItemsAndNothingIsRememberedBeforeThePortIsReady():
    steak = ("other:steak", 0)
    beef = {"common:raw_beef": ["minecraft:beef", "arris:minced_beef", "other:steak"]}
    port = Port(dict(beef), ready=False)
    stew = TABLE[next(at for at, recipe in enumerate(TABLE) if recipe["Id"] == "farmersdelight:cooking/beef_stew")]
    row = {"Id": "test:cooking/steak_stew", "Slots": [["#common:raw_beef"], ["test:onion"]], "Recipe": [],
           "CookResult": ("test:steak_stew", 0), "PushItem": [], "text": "x"}
    with Rows(row):
        ItemTags.setPort("server", port)
        try:
            pot = [_item("other:steak"), _item("test:onion")]
            assert Rules.matchRecipe(pot)[0]["newItemName"] == "test:steak_stew" and Rules.isIngredient(steak), \
                "口没准备好也按单件问引擎（ItemTags 的规矩）：认得别的模组的东西"
            assert steak not in Rules.optionsOf(row)[0], "枚举标签的成员（书、界面上轮换的）准备好之前只有静态表的"
            port.extra = {}
            assert Rules.matchRecipe(pot) == (None, None) and not Rules.isIngredient(steak), "准备好之前不记答案：引擎改了口马上跟上"
            assert Rules.candidatesFor([steak, ("test:onion", 0)]) == []
            port.extra, port.isReady = dict(beef), True
            result, pushed = Rules.matchRecipe(pot)
            assert result == {"newItemName": "test:steak_stew", "newAuxValue": 0, "count": 1} and pushed == [], "准备好了：换代"
            assert Rules.isIngredient(steak) and Rules.matchIndex(list(reversed(pot))) == len(TABLE) - 1
            assert Rules.candidatesFor([steak, ("test:onion", 0)]) == [(len(TABLE) - 1, {steak: 1, ("test:onion", 0): 1})]
            assert steak in Rules.optionsOf(row)[0]
            port.extra = {}
            assert Rules.matchRecipe(pot)[0]["newItemName"] == "test:steak_stew", "准备好以后记着答案，直到换代"
            ItemTags.refresh()
            assert Rules.matchRecipe(pot) == (None, None) and not Rules.isIngredient(steak), "换代：记着的答案作废"
            assert stew["Recipe"] and Rules.matchRecipe([_item("minecraft:beef"), _item("minecraft:carrot"), _item("minecraft:potato")])[0]
        finally:
            ItemTags.setPort("server", None)


def testTheEarlierRecipeWinsBetweenSlotsAndWays():
    first = {"Id": "test:cooking/first", "Slots": [["test:a", "test:b"], ["test:c"]], "Recipe": [], "CookResult": ("test:first", 0),
             "PushItem": [], "text": "1"}
    second = {"Recipe": [[("test:b", 0), ("test:c", 0)]], "CookResult": ("test:second", 0), "PushItem": [], "text": "2"}
    third = {"Id": "test:cooking/third", "Slots": [["test:c"], ["test:d"]], "Recipe": [], "CookResult": ("test:third", 0),
             "PushItem": [], "text": "3"}
    fourth = {"Recipe": [[("test:d", 0), ("test:c", 0)]], "CookResult": ("test:fourth", 0), "PushItem": [], "text": "4"}
    with Rows(first, second, third, fourth):
        assert Rules.matchRecipe([_item("test:c"), _item("test:b")])[0]["newItemName"] == "test:first", "格子形在前"
        assert Rules.matchRecipe([_item("test:d"), _item("test:c")])[0]["newItemName"] == "test:third"
    with Rows(second, first):
        assert Rules.matchRecipe([_item("test:c"), _item("test:b")])[0]["newItemName"] == "test:second", "旧写法在前"
        assert Rules.matchRecipe([_item("test:a"), _item("test:c")])[0]["newItemName"] == "test:first"


def testTombstonesAreSkippedEverywhere():
    """墓碑配不上、不是食材、不出摆法；但锅里已经煮好的那道菜照样盛得出来（T 复核时复现的：以前容器查不到、经典界面不转出、站点不给盛）：
    按成品查的（findRecipeByResult、容器、时间、经验、是不是容器）没有活配方时退回墓碑那一行，有活的用活的。"""
    dead = {"Id": "test:cooking/dead", "Slots": [["test:x"]], "Recipe": [[("test:x", 0)]], "CookResult": ("test:dead", 0),
            "Vessel": ("test:cup", 0), "PushItem": [], "text": "x", "Disabled": True, "CookTime": 3.0, "Experience": 2.0}
    alive = {"Recipe": [[("test:x", 0)]], "CookResult": ("test:dead", 0), "PushItem": [], "text": "y"}
    with Rows(dead):
        assert Rules.matchRecipe([_item("test:x")]) == (None, None) and not Rules.isIngredient(("test:x", 0))
        assert Rules.candidatesFor([("test:x", 0)]) == []
        assert Rules.findRecipeByResult("test:dead") is dead and Rules.vesselOf("test:dead") == ("test:cup", 0) and Rules.isVessel("test:cup")
        assert Rules.cookSecondsOf("test:dead") == 3.0 and Rules.servingExperienceOf("test:dead") == 2.0
        with Rows(alive):
            assert Rules.matchIndex([_item("test:x")]) == len(TABLE) - 1 and Rules.findRecipeByResult("test:dead") is alive
            assert Rules.vesselOf("test:dead") is None and Rules.cookSecondsOf("test:dead") == Rules.DEFAULT_COOK_SECONDS, "有活的用活的"


def testASlotsOnlyRecipeGivesBackWhatThePotActuallyHeld():
    row = {"Id": "test:cooking/milky", "Slots": [["minecraft:milk_bucket", "arris:milk_bottle"], [("minecraft:dye", 4)]], "Recipe": [],
           "CookResult": ("test:milky", 0), "CookCount": 3, "PushItem": [("test:spoon", 0)], "text": "x"}
    with Rows(row):
        result, pushed = Rules.matchRecipe([_item("minecraft:dye", 4), _item("arris:milk_bottle")])
        assert result["count"] == 3 and pushed == [("test:spoon", 0), ("minecraft:glass_bottle", 0)]
        assert Rules.matchRecipe([_item("minecraft:dye", 1), _item("arris:milk_bottle")]) == (None, None), "aux 不对"
        assert Rules.isIngredient(("minecraft:dye", 4)) and not Rules.isIngredient(("minecraft:dye", 1))


def testRebuildIndexOnlyInvalidates():
    before = Rules.revision()
    row = {"Recipe": [[("test:late", 0)]], "CookResult": ("test:late_dish", 0), "PushItem": [], "text": "x"}
    assert Rules.matchRecipe([_item("test:late")]) == (None, None)
    TABLE.append(row)
    try:
        assert Rules.matchRecipe([_item("test:late")]) == (None, None), "没调 rebuildIndex：还是记着的答案"
        Rules.rebuildIndex()
        assert Rules.revision() == before + 1
        assert Rules.matchRecipe([_item("test:late")])[0]["newItemName"] == "test:late_dish"
    finally:
        TABLE.remove(row)
        Rules.rebuildIndex()


def testBadRowsAreNotRecipes():
    rows = ({"Recipe": [], "CookResult": ("", 0), "PushItem": [], "text": ""},                      # 表同步占着下标的空行
            {"Recipe": [[("test:y", "x")], "nope", [("test:y", 0)]], "CookResult": ("test:half", 0), "CookTime": "slow",
             "Experience": None, "text": "x"},
            {"Slots": [["bad"]], "Recipe": [], "CookResult": ("test:bad_slots", 0), "text": "x"},
            "not a dict")
    with Rows(*rows):
        assert Rules.matchRecipe([_item("test:y")])[0]["newItemName"] == "test:half", "写坏的写法跳过，好的照用"
        assert Rules.cookSecondsOf("test:half") == Rules.DEFAULT_COOK_SECONDS and Rules.experienceOf("test:half") == Rules.DEFAULT_EXPERIENCE
        assert Rules.optionsOf(rows[2]) is None and Rules.matchRecipe([_item("bad")]) == (None, None)


def testFramesAreRememberedWhileTheTagsAreReadyUntilTheTableChanges():
    """T 复核时指出的性能：framesOf / extraWays 每次都把旧写法过一遍格子配对。现在按 (配方表的版本, 标签代数) 记住；
    引擎口没准备好时不记（照 ItemTags 的规矩），配方表改过（rebuildIndex）就重算。"""
    stew = TABLE[next(at for at, recipe in enumerate(TABLE) if recipe["Id"] == "farmersdelight:cooking/beef_stew")]
    assert Rules.framesOf(stew) is not Rules.framesOf(stew), "没有口：不记"
    ItemTags.setPort("server", Port({}, ready=True))
    try:
        first = Rules.framesOf(stew)
        assert Rules.framesOf(stew) is first and Rules.extraWays(stew) is Rules.extraWays(stew)
        Rules.rebuildIndex()
        again = Rules.framesOf(stew)
        assert again is not first and again == first
    finally:
        ItemTags.setPort("server", None)


def testAnAnswerComputedWhileTheStampChangedIsNotRemembered():
    """T 复核时复现的：framesOf 先取戳再算，算到一半标签口变成准备好（嵌套的 extraWays 用新代数重打了戳），外层按旧口径算出的答案
    就记在新戳下面、一直错。现在算完再取一次戳，和开始时一样才记。假的口第 k 次问 ready() 起才答"好了"。"""
    row = {"Slots": [["#common:test_race"], ["test:x"]], "Recipe": [[("test:old", 0)]], "CookResult": ("test:race", 0),
           "PushItem": [], "text": "x"}

    class Late(Port):
        def __init__(self, k):
            Port.__init__(self, {"common:test_race": ["test:member"]}, ready=False)
            self.k, self.calls = k, 0

        def ready(self):
            self.calls += 1
            return self.calls >= self.k

    try:
        for k in range(1, 12):
            ItemTags.setPort("server", Late(k))
            Rules.framesOf(row)
            while not ItemTags.ready():
                pass                                  # 口已经变成准备好（之后戳不再变），再算一份对照
            fresh = Rules._framesOf(row)
            assert Rules.framesOf(row) == fresh and Rules.extraWays(row) == Rules._extraWays(row), k
    finally:
        ItemTags.setPort("server", None)


def testRememberedAnswersHoldOnToTheirRow():
    """记住的答案按 id(行) 找：存着行本身、命中时核对是同一行，行对象不会被回收、地址不会被另一行重用（主会话指出的）。"""
    import gc
    import weakref

    class Row(dict):
        pass

    row = Row({"Slots": [["test:a"]], "Recipe": [], "CookResult": ("test:b", 0), "PushItem": [], "text": "x"})
    ItemTags.setPort("server", Port({}, ready=True))
    try:
        ref = weakref.ref(row)
        Rules.framesOf(row)
        del row
        gc.collect()
        assert ref() is not None, "准备好时记住的答案留着那一行"
        other = Row({"Slots": [["test:c"]], "Recipe": [], "CookResult": ("test:d", 0), "PushItem": [], "text": "y"})
        assert Rules.framesOf(other) == [[("test:c", 0)]]
    finally:
        ItemTags.setPort("server", None)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
