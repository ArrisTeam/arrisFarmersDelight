# -*- coding: utf-8 -*-
# runner: both
"""前置包原版工作台的配方书不列砧板菜（Compat/Diegesis/TableClientLink.hidden，规则 Shared/Rules/DishStation.isDishRecipe）：
书给每条配方的成品 + 每格能放的几种 [(物品名, aux 或 None)]（前置包 Vanilla/Client/TableBookHooks 的写法）。砧板菜的每条配方都挡，
先后不要紧；同一成品的别的配方照列（拦配方不拦成品：切片拼回整个派），料多一件、少一件、换一样都不挡——和服务端的否决
（TableHooksLink.dishVeto）同一张表、同一个判法。登在哪一步、什么条件由 test_presence_boots.py 管。
"""
from __future__ import print_function

import fdtest
import linkkit as L

env = L.install()
Link = fdtest.load("Compat.Diegesis.TableClientLink")
Server = fdtest.load("Compat.Diegesis.TableHooksLink")
Dishes = fdtest.load("Shared.Rules.DishStation")
APPLE_PIE, SLICE = "arris:apple_pie_item", "arris:apple_pie_slice"


def product(name):
    return {"newItemName": name, "newAuxValue": 0, "count": 1}


def slots(*names):
    """每格一样东西（数据值 0）。"""
    return [[(name, 0)] for name in names]


def testEveryBoardDishRecipeIsHiddenInAnyOrder():
    for dish in Dishes.dishes():
        names = [name for name, _aux in dish["ingredients"]]
        made = product(dish["result"][0])
        assert Link.hidden(made, slots(*names)) and Link.hidden(made, slots(*reversed(names))), dish["result"]
        assert not Link.hidden(made, slots(*names[:-1])), ("少一件", dish["result"])
        assert not Link.hidden(made, slots(*(names + ["minecraft:stick"]))), ("多一件", dish["result"])


def testOtherRecipesOfTheSameProductStayListed():
    assert Dishes.isDishResult(APPLE_PIE)
    assert not Link.hidden(product(APPLE_PIE), slots(SLICE, SLICE, SLICE, SLICE)), "切片拼回整个派：不是砧板菜，照列"
    assert not Link.hidden(product("minecraft:stick"), slots("minecraft:oak_planks", "minecraft:oak_planks"))
    assert not Link.hidden(None, slots(SLICE)) and not Link.hidden(product(APPLE_PIE), [])


def testSeveralOptionsAndAnyDataValue():
    sandwich = [dish for dish in Dishes.dishes() if dish["result"][0] == "arris:egg_sandwich"][0]
    names = [name for name, _aux in sandwich["ingredients"]]
    loose = [[(name, None), ("minecraft:dirt", 0)] for name in names]
    assert Link.hidden(product("arris:egg_sandwich"), loose), "一格能放几种、数据值任意：有一种对得上就算"
    wrong = [[("minecraft:dirt", 0)]] + slots(*names[1:])
    assert not Link.hidden(product("arris:egg_sandwich"), wrong), "有一格放不了它要的那件：不挡"


def testTheSameJudgementAsTheServerVeto():
    """九格放的正好是这条配方的料时，服务端拒（dishVeto 不是 None）当且仅当书里不列。"""
    cases = [(dish["result"][0], [name for name, _aux in dish["ingredients"]]) for dish in Dishes.dishes()]
    cases += [(APPLE_PIE, [SLICE] * 4), ("arris:egg_sandwich", ["minecraft:bread"])]
    for name, names in cases:
        cells = [{"newItemName": item, "newAuxValue": 0, "count": 1} for item in names] + [None] * (9 - len(names))
        assert (Server.dishVeto("p", product(name), cells) is not None) == bool(Link.hidden(product(name), slots(*names))), name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
