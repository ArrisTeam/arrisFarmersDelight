# -*- coding: utf-8 -*-
# runner: both
"""PotMatch 增广路匹配测试。

对应 Hands-On Delight 的 PotTests.theSmallestStackSetsTheBatch（最少的那一堆定批量）与
moreRiceThanAStackStillCooks（同一种料分在两个槽里仍然算在一起）。
"""
from __future__ import print_function


import fdtest

Match = fdtest.load("Shared.Rules.HandsOn.PotMatch")


def acceptor(ingredients, stacks):
    """ingredients: 每个配料接受的物品名集合；stacks: 每个槽里物品名。"""
    return lambda ingredient, stack: stacks[stack] in ingredients[ingredient]


def testTheSmallestStackSetsTheBatch():
    # 牛肉 4、胡萝卜 4、土豆 1：只够一份，牛肉和胡萝卜各剩 3
    ingredients = [set(["beef"]), set(["carrot"]), set(["potato"])]
    stacks = ["beef", "carrot", "potato"]
    accepts = acceptor(ingredients, stacks)
    assert Match.servingsLeft([4, 4, 1], 3, accepts) == 1
    assert Match.servingsLeft([4, 4, 4], 3, accepts) == 4
    assert Match.servingsLeft([0, 0, 0], 3, accepts) == 0
    assert Match.servingsLeft([], 3, accepts) == 0


def testAnEmptySlotIsNotAnIngredient():
    ingredients = [set(["beef"]), set(["carrot"])]
    stacks = ["beef", "none", "carrot"]
    accepts = acceptor(ingredients, stacks)
    assert Match.servingsLeft([3, 0, 2], 2, accepts) == 2, "空槽不参与取最小值，下标仍是槽号"


def testAMissingIngredientMakesNothing():
    ingredients = [set(["beef"]), set(["carrot"])]
    accepts = acceptor(ingredients, ["beef"])
    assert Match.servingsLeft([5], 2, accepts) == 0
    assert not Match.makes([5], 2, 1, accepts)


def testTheSameThingInTwoSlotsCountsTogether():
    # 一个配料"米"，米分在两个槽里：每份只要一个配料，所以锅里有米就有份；min 是 40，makes 能凑出 40 份
    ingredients = [set(["rice"])]
    stacks = ["rice", "rice"]
    accepts = acceptor(ingredients, stacks)
    assert Match.servingsLeft([40, 40], 1, accepts) == 40


def testAnAugmentingPathMovesAnotherIngredientAside():
    # 配料 0 什么肉都行，配料 1 只要牛肉；牛肉 1 件、猪肉 1 件。
    # 贪心：配料 0 先拿走牛肉，配料 1 没牛肉了；增广路：配料 0 让出牛肉去拿猪肉
    ingredients = [set(["beef", "pork"]), set(["beef"])]
    stacks = ["beef", "pork"]
    accepts = acceptor(ingredients, stacks)
    assert Match.makes([1, 1], 2, 1, accepts)
    assert Match.servingsLeft([1, 1], 2, accepts) == 1


def testNoAugmentingPathMeansNoServing():
    # 两个配料都只接受牛肉，牛肉只有 1 件
    ingredients = [set(["beef"]), set(["beef"])]
    accepts = acceptor(ingredients, ["beef"])
    assert not Match.makes([1], 2, 1, accepts)
    assert Match.makes([2], 2, 1, accepts)
    assert not Match.makes([3], 2, 2, accepts), "两份要 4 件牛肉"


def testTwoIngredientsMayShareOneStack():
    # 两个配料都接受牛肉，一个槽里有 4 件：两份刚好用完（Autochef's Delight 那种按堆叠匹配的情况）
    ingredients = [set(["beef"]), set(["beef"])]
    accepts = acceptor(ingredients, ["beef"])
    assert Match.servingsLeft([4], 2, accepts) == 2
    assert Match.servingsLeft([3], 2, accepts) == 1


def testPlaceholderIngredientsAreSkipped():
    ingredients = [set(["beef"]), set()]
    accepts = acceptor(ingredients, ["beef"])
    assert not Match.makes([2], 2, 1, accepts)
    assert Match.makes([2], 2, 1, accepts, isEmpty=lambda ingredient: ingredient == 1)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
