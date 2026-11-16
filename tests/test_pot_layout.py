# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点怎么选菜、摆料、照书放料（Shared/Rules/PotLayout.py）：HoD StationRecipes 的 choose / lay / fill，
和 PotTests 里"两个一样的扔进去""最后一种料放进去才做更全的那道""书里点的那道留着"这几条。"""
from __future__ import print_function

import fdtest

CookingPot = fdtest.load("Shared.Rules.CookingPot")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Layout = fdtest.load("Shared.Rules.PotLayout")

TOMATO = ("arris:tomato", 0)
ONION = ("arris:onion", 0)
DUST = ("minecraft:glowstone_dust", 0)
DYE = ("minecraft:red_dye", 0)
AMETHYST = ("minecraft:amethyst_shard", 0)
PRISM = ("minecraft:prismarine_shard", 0)
ECHO = ("minecraft:echo_shard", 0)
NAUTILUS = ("minecraft:nautilus_shell", 0)


def _stack64(key):
    return 64


def _item(key, count):
    return {"newItemName": key[0], "newAuxValue": key[1], "count": count}


def _cells(*stacks):
    """[(种类, 数量) 或 None] 凑成 6 格；数量 0 / None 是空格。"""
    cells = [_item(s[0], s[1]) if s else None for s in stacks]
    return cells + [None] * (6 - len(cells))


def _shape(cells):
    return [(Layout.keyOf(c), Layout.countOf(c)) if c else None for c in cells]


class WithRecipes(object):
    """临时往配方表里加几道菜（测完还原），每道 (名字, 配料种类列表)。"""

    def __init__(self, *recipes):
        self.recipes = recipes
        self.before = None

    def __enter__(self):
        self.before = list(Recipes.CookingPotRecipeList)
        for name, kinds in self.recipes:
            Recipes.CookingPotRecipeList.append({"Recipe": [list(kinds)], "CookResult": ("test:" + name, 0), "PushItem": [],
                                                 "text": name})
        CookingPot.rebuildIndex()
        return len(self.before)          # 第一道新菜的序号

    def __exit__(self, *exc):
        Recipes.CookingPotRecipeList[:] = self.before
        CookingPot.rebuildIndex()


def _index(name):
    return next(i for i, r in enumerate(Recipes.CookingPotRecipeList) if r["CookResult"][0] == name)


def _chosen(cells, **options):
    kinds = Layout.kindsOf(cells)
    choice = Layout.choose(kinds, _stack64, **options)
    return choice[0] if choice else None


def testKindsAreAlikeStacksCountedTogetherInSlotOrder():
    assert Layout.kindsOf(_cells((TOMATO, 5), (ONION, 3), None, (TOMATO, 2))) == [(TOMATO, 7), (ONION, 3)]
    assert Layout.kindsOf(_cells()) == []


def testTwoAlikeThrownInLieInTwoSlotsForTheDishThatWantsTwo():
    sauce = _index("arris:tomato_sauce")
    assert _chosen(_cells((TOMATO, 16))) == sauce
    out, rest = Layout.layout(_cells((TOMATO, 16)), _stack64)
    assert _shape(out) == [(TOMATO, 8), (TOMATO, 8), None, None, None, None] and rest == []
    assert Layout.layout(out, _stack64) is None, "已经摆好就不再动"
    assert Layout.layout(_cells((ONION, 3), (("minecraft:dirt", 0), 1)), _stack64) is None, "凑不成菜的料原样放着"
    assert Layout.layout(_cells((TOMATO, 1)), _stack64) is None, "一个番茄不够两格"


def testAKindKeepsTheSlotItLayInAndTheRightSlotsAreLeftAlone():
    out, rest = Layout.layout(_cells(None, None, None, (TOMATO, 16)), _stack64)
    assert _shape(out) == [(TOMATO, 8), None, None, (TOMATO, 8), None, None], "留在原来的第 3 格，另一半放进第一个空格"
    odd, _ = Layout.layout(_cells((TOMATO, 7)), _stack64)
    assert _shape(odd)[:2] == [(TOMATO, 4), (TOMATO, 3)]
    already = _cells((TOMATO, 3), None, (TOMATO, 4))
    out, _ = Layout.layout(already, _stack64)
    assert _shape(out) == [(TOMATO, 4), None, (TOMATO, 3), None, None, None], "第 0 格和第 2 格各是一半：多的那堆分过去"


def testWhatDoesNotFitGoesBackToTheCookAsOneStack():
    cells = _cells((TOMATO, 10))
    assert Layout.layout(cells, lambda key: 4, overflow=False) is None, "没人在场时不整理装不下的（不退料）"
    out, rest = Layout.layout(cells, lambda key: 4)
    assert _shape(out) == [(TOMATO, 4), (TOMATO, 4), None, None, None, None]
    assert [(Layout.keyOf(s), Layout.countOf(s)) for s in rest] == [(TOMATO, 2)], "Java 的 lay：每种料一堆，不按格拆"


def testTheFullerDishOnceItsLastIngredientIsIn():
    with WithRecipes(("burek", [AMETHYST, PRISM, ECHO]), ("cevapi", [AMETHYST, PRISM, PRISM, ECHO, NAUTILUS])) as first:
        three = _cells((AMETHYST, 1), (PRISM, 2), (ECHO, 1))
        assert _chosen(three) == first, "burek 的料，多的那块棱镜碎片躺在一边"
        four = _cells((AMETHYST, 1), (PRISM, 2), (ECHO, 1), (NAUTILUS, 1))
        assert _chosen(four) == first + 1, "最后一样放进去，做 cevapi"


def testTwoSugarsAndADyeMakeTheDishOfTwoNotTheDishOfOne():
    with WithRecipes(("cane", [DUST, DUST, DYE]), ("cane_half", [DUST, DYE])) as first:
        assert _chosen(_cells((DUST, 2), (DYE, 1))) == first
        assert _chosen(_cells((DUST, 10), (DYE, 6))) == first + 1, "十份粉六份染料：做六份半的，不做五份整的"
        three = _cells((DUST, 3), (DYE, 1))
        assert _chosen(three) == first, "三份粉一份染料谁也做不整：剩得少的那道"
        assert _chosen(three, found=first + 1) == first + 1, "锅按现在的摆法读成哪道，就还煮哪道"


def testTheDishPickedInTheBookStaysTheChoiceWhileTheFoodMakesIt():
    with WithRecipes(("pair", [DUST, DYE]), ("pairs", [DUST, DUST, DYE, DYE])) as first:
        cells = _cells((DUST, 2), (DYE, 2))
        assert _chosen(cells) == first + 1, "扔进去的：四件的那道"
        assert _chosen(cells, wanted=first) == first, "书里点的两件的那道"
        assert _chosen(cells, wanted=_index("arris:tomato_sauce")) == first + 1, "点的那道凑不成时不管它"


def testOverflowKeepsTheDishThatHoldsTheMost():
    with WithRecipes(("big", [DUST, DUST, DYE]), ("small", [DUST, DYE])) as first:
        cells = _cells((DUST, 9), (DYE, 3))
        assert _chosen(cells, overflow=False) is not None, "装得下全部的先选"
        crowded = _cells((DUST, 9), (DYE, 3))
        assert Layout.choose(Layout.kindsOf(crowded), lambda key: 4, overflow=False) is None
        choice = Layout.choose(Layout.kindsOf(crowded), lambda key: 4, overflow=True)
        assert choice[0] == first, "装不下时留装得下最多的那道（big：4 + 4 + 3 = 11 件）"


def testPlanFillTakesWholeSetsOnlyAndNeverMoreThanTheSlotsHold():
    sauce = Recipes.CookingPotRecipeList[_index("arris:tomato_sauce")]["Recipe"]
    assert Layout.planFill(sauce, {}, {TOMATO: 40}, 16, _stack64) == ({TOMATO: 2}, 16)
    assert Layout.planFill(sauce, {}, {TOMATO: 7}, 16, _stack64) == ({TOMATO: 2}, 3)
    assert Layout.planFill(sauce, {}, {TOMATO: 40}, 1, _stack64) == ({TOMATO: 2}, 1)
    assert Layout.planFill(sauce, {TOMATO: 120}, {TOMATO: 100}, 16, _stack64) == ({TOMATO: 2}, 4), "两格 2 x 64 = 128，锅里已有 120"
    assert Layout.planFill(sauce, {TOMATO: 127}, {TOMATO: 100}, 16, _stack64) is None, "再放一份（2 个）装不下：一份都不放"
    assert Layout.planFill(sauce, {ONION: 1}, {TOMATO: 40}, 16, _stack64) is None, "锅里有这道菜用不上的料：书什么也不放"
    assert Layout.planFill(sauce, {}, {ONION: 40}, 16, _stack64) is None, "背包里没有料"


def testPlanFillPicksTheWayThatMakesTheMostAndStaysWithWhatLiesInThePot():
    stew = Recipes.CookingPotRecipeList[_index("arris:cookbeef_stew")]["Recipe"]
    mince, beef, carrot, potato = ("arris:minced_beef", 0), ("minecraft:beef", 0), ("minecraft:carrot", 0), ("minecraft:potato", 0)
    pool = {mince: 5, beef: 1, carrot: 9, potato: 9}
    kinds, sets = Layout.planFill(stew, {}, pool, 16, _stack64)
    assert mince in kinds and beef not in kinds and sets == 5, "份数最多的写法（肉馅 5 份）"
    kinds, sets = Layout.planFill(stew, {beef: 1}, pool, 16, _stack64)
    assert beef in kinds and mince not in kinds and sets == 1, "锅里已有牛肉：只能走牛肉那种写法"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
