# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点的纯规则（Shared/Rules/PotStation.py）：份数、放料、按真实配方表摆料、取回、提示文字。"""
from __future__ import print_function

import fdtest

Rules = fdtest.load("Shared.Rules.PotStation")
PotCooking = fdtest.load("Shared.Rules.HandsOn.PotCooking")
CookingPot = fdtest.load("Shared.Rules.CookingPot")

TOMATO = ("arris:tomato", 0)
ONION = ("arris:onion", 0)
RED = ("minecraft:red_mushroom", 0)
BROWN = ("minecraft:brown_mushroom", 0)


def _item(key, count):
    return {"newItemName": key[0], "newAuxValue": key[1], "count": count}


def _cells(*stacks):
    cells = [_item(key, count) for key, count in stacks]
    return cells + [None] * (Rules.INPUT_SLOTS - len(cells))


def _shape(cells):
    return [(Rules.keyOf(c), Rules.countOf(c)) for c in cells if Rules.keyOf(c)]


def _stack64(key):
    return 64


def testServingsAreTheSmallestFilledSlot():
    assert Rules.servingsLeft(_cells((TOMATO, 5), (ONION, 3))) == 3
    assert Rules.servingsLeft([None, {}, {"newItemName": "arris:tomato", "count": 0}]) == 0
    assert Rules.foodCount(_cells((TOMATO, 5), (ONION, 3))) == 8


def testAStackGoesOntoItsKindFirstThenIntoAnEmptySlot():
    cells, placed = Rules.placeStack(_cells((TOMATO, 60), (ONION, 2)), _item(TOMATO, 10), 64)
    assert placed == 10
    assert _shape(cells) == [(TOMATO, 64), (ONION, 2), (TOMATO, 6)]
    full = _cells(*[((("x:%d" % i), 0), 64) for i in range(6)])
    cells, placed = Rules.placeStack(full, _item(TOMATO, 3), 64)
    assert placed == 0 and _shape(cells) == _shape(full), "锅满了什么也放不进去"


def testTwoTomatoesMakeTomatoSauceOnlyWhenLaidOverTwoSlots():
    cells = _cells((TOMATO, 16))
    assert CookingPot.matchRecipe(cells)[0] is None, "一格番茄凑不出番茄酱"
    cells, rest = Rules.layout(cells, _stack64)
    assert _shape(cells) == [(TOMATO, 8), (TOMATO, 8)] and rest == []
    assert CookingPot.matchRecipe(cells)[0]["newItemName"] == "arris:tomato_sauce"
    assert Rules.layout(cells, _stack64) is None, "已经摆好就不再动"


def testAnOddCountSplitsAsEvenlyAsItCanAndTheStackCapHandsTheRestBack():
    cells, rest = Rules.layout(_cells((TOMATO, 7)), _stack64)
    assert _shape(cells) == [(TOMATO, 4), (TOMATO, 3)]
    cells, rest = Rules.layout(_cells((TOMATO, 10)), lambda key: 4)
    assert _shape(cells) == [(TOMATO, 4), (TOMATO, 4)] and _shape(rest) == [(TOMATO, 1), (TOMATO, 1)]


def testFoodThatMakesNothingStaysAsItLies():
    lonely = _cells((ONION, 3), (("minecraft:dirt", 0), 1))
    assert Rules.layout(lonely, _stack64) is None
    assert Rules.bestParts([(TOMATO, 1)]) is None, "一个番茄不够两格"


def testTheVariantThatMakesTheMostServingsWins():
    # 蘑菇煲：两个红蘑菇 / 两个棕蘑菇 / 红 + 棕（看配方表里有哪些写法）
    parts = Rules.bestParts([(RED, 6), (BROWN, 2)])
    assert parts is not None
    servings = min(dict([(RED, 6), (BROWN, 2)])[key] // count for key, count in parts.items())
    assert servings >= 2


def testTakingASlotTakesItsWholeKind():
    cells, taken = Rules.takeKind(_cells((TOMATO, 8), (ONION, 2), (TOMATO, 8)), 2)
    assert _shape(cells) == [(ONION, 2)]
    assert _shape(taken) == [(TOMATO, 8), (TOMATO, 8)]
    cells, taken = Rules.takeKind(_cells((TOMATO, 8)), 4)
    assert taken == [] and _shape(cells) == [(TOMATO, 8)]


def testOnlyRecipeIngredientsCount():
    assert Rules.isIngredient(TOMATO) and Rules.isIngredient(RED)
    assert not Rules.isIngredient(("minecraft:dirt", 0))
    assert not Rules.isIngredient(("minecraft:bowl", 0)), "碗是盛菜的，不下锅"


def testTheBadgeShowsTheDishWhileCookingAndTheMealWhenDone():
    assert Rules.badgeOf({"inputs": [{}] * 6}) is None
    cooking = {"dish": _item(("arris:tomato_sauce", 0), 1), "stars": 1.4, "open": 2, "progress": 0.25}
    assert Rules.badgeOf(cooking) == {"item": cooking["dish"], "stars": 1.4, "open": 2, "progress": 0.25}
    done = dict(cooking, meals=8, meal=_item(("arris:tomato_sauce", 0), 8), grade=3, open=2)
    badge = Rules.badgeOf(done)
    assert badge["item"] == done["meal"] and badge["stars"] == 3 and badge["progress"] is None
    assert badge["open"] == 3, "出锅时的星数总是亮着"


def testTheHintFollowsThePot():
    empty = {"inputs": [{}] * 6}
    assert "放进锅里" in Rules.statusText(empty)
    junk = {"inputs": [_item(ONION, 1)], "dish": {}}
    assert "凑不出" in Rules.statusText(junk)
    cold = {"inputs": [_item(TOMATO, 1)], "dish": _item(("arris:tomato_sauce", 0), 1), "heated": False}
    assert "热源" in Rules.statusText(cold)
    waiting = dict(cold, heated=True, mode=PotCooking.WAITING, batch=8, progress=0.25, stars=1.0, open=2)
    assert "搅拌才会煮" in Rules.statusText(waiting) and "8 份" in Rules.statusText(waiting)
    stirred = dict(waiting, mode=PotCooking.STIRRED, left=12)
    assert "还要 12 秒" in Rules.statusText(stirred)
    assert all("%" not in Rules.statusText(d) for d in (waiting, stirred)), "标签会把 % 当格式符吞掉"
    assert "自己" in Rules.statusText(dict(waiting, mode=PotCooking.FD_WAY))
    ready = dict(stirred, meals=5, vesselName="碗")
    assert "盛出 5 份" in Rules.statusText(ready) and "碗" in Rules.statusText(ready)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
