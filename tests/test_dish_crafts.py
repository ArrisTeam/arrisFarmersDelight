# -*- coding: utf-8 -*-
# runner: both
"""工作台和砧板摆盘的分工，逐道对一遍（HoD BoardTests 的 bowlDishesLeaveTheCraftingTable / burgersLeaveTheCraftingTable 的站点级版本）：
菜谱表里每道菜的每条配方，玩家的合成格（工作台、背包里的 2x2）拿成品时都被拦（Compat/Diegesis/DishCrafts，ServerBoot 登记）；
留在工作台的合成（切片拼回整个派、叶子压回卷心菜、马饲料、牛奶瓶、厨锅……）一条也不拦。真的入口、真的事件分发，引擎是 bootkit 里的无害替身。
"""
from __future__ import print_function

import bootkit as B
import fdtest
import recipekit

DishCrafts = fdtest.load("Compat.Diegesis.DishCrafts")
Dishes = fdtest.load("Shared.Rules.DishStation")
BOWL_DISHES = ("bacon_and_eggs", "steak_and_potatoes", "roasted_mutton_chops", "grilled_salmon", "mixed_salad", "fruit_salad", "nether_salad")


def _craft(result, names):
    """玩家在合成格里摆好 names（一格一个）、取走 result：被拦了吗（取消事件）。"""
    grid = dict((slot, (name, 1)) for slot, name in enumerate(names))
    DishCrafts.readGrid = lambda playerId: grid
    args = {"playerId": "a", "itemDict": {"newItemName": result, "newAuxValue": 0, "count": 1}, "cancel": False}
    handled = B.EventRegistry.dispatch("CraftItemOutputChangeServerEvent", args)
    assert handled is args["cancel"] is not None
    return args["cancel"]


def _namesOf(kind, body):
    return sorted(name for name, count in recipekit.ingredientsOf(kind, body).items() for _ in range(count))


def testTheBowlDishesStartFromTheirBowlSoTheyLeaveTheCraftingTable():
    """JE bowlDishesLeaveTheCraftingTable 的前半：套餐和沙拉从碗打底；每一条配方在工作台都被拦（合成格是这道菜在砧板上的原料）。"""
    B.bootServer()
    kinds = dict((dish["result"][0], dish["kind"]) for dish in Dishes.dishes())
    for name in BOWL_DISHES:
        assert kinds["arris:" + name] == "bowl", name
        recipes = [dish for dish in Dishes.dishes() if dish["result"][0] == "arris:" + name]
        assert recipes, name
        for dish in recipes:
            assert _craft(dish["result"][0], [kind[0] for kind in dish["ingredients"]]) is True, name


def testTheNetherSaladIsNotMadeAtTheCraftingTable():
    """JE 的 netherSalad：绯红菌 + 诡异菌 + 碗，玩家的工作台出不了沙拉；少一样、多一样（不是这条配方）就是别的合成，照常。"""
    B.bootServer()
    grid = ["minecraft:crimson_fungus", "minecraft:warped_fungus", "minecraft:bowl"]
    assert _craft("arris:nether_salad", grid) is True
    assert _craft("arris:nether_salad", grid[:2]) is False and _craft("arris:nether_salad", grid + ["minecraft:bowl"]) is False


def testEveryDishRecipeTheBoardTakesIsStoppedAtTheTableAndNothingElseIs():
    """逐道：菜谱表里每道菜的每条配方（33 道、86 条写法）在工作台被拦；bp/recipes 里别的每一条合成（切片拼回整个派、叶子压回卷心菜、
    马饲料、牛奶瓶、厨锅、箱子拆回来……）一条也不拦。"""
    B.bootServer()
    board = set()
    for dish in Dishes.dishes():
        names = sorted(kind[0] for kind in dish["ingredients"])
        board.add((dish["result"][0], tuple(names)))
        assert _craft(dish["result"][0], names) is True, (dish["result"][0], names)
    assert len(Dishes.dishes()) >= 80 and len(set(result for result, _names in board)) == 33
    crafts = 0
    for fileName, (kind, body) in recipekit.loadRecipes().items():
        if kind not in ("shaped", "shapeless"):
            continue
        result, names = recipekit.resultsOf(body)[0][0], _namesOf(kind, body)
        assert _craft(result, names) is ((result, tuple(names)) in board), fileName
        crafts += 1
    assert crafts > 150, "把整个配方目录都过了一遍"


def testTheCraftsJavaLeavesInTheCraftingTableStayThere():
    """JE bowlDishesLeaveTheCraftingTable 的后半：apple_pie_from_slices、cabbage_from_leaves、horse_feed、milk_bottle、cooking_pot 留在工作台。"""
    B.bootServer()
    wanted = {"arris_apple_pie_from_slices.json": "arris:apple_pie_item", "arris_cabbage_from_leaves.json": "arris:cabbage",
              "arris_horse_feed1.json": "arris:horse_feed", "arris_horse_feed2.json": "arris:horse_feed", "arris_milk_bottle.json": "arris:milk_bottle",
              "arris_cooking_pot.json": "arris:cooking_pot"}
    recipes = recipekit.loadRecipes()
    for fileName, result in sorted(wanted.items()):
        kind, body = recipes[fileName]
        assert recipekit.resultsOf(body)[0][0] == result, fileName
        assert _craft(result, _namesOf(kind, body)) is False, fileName
    assert Dishes.isDishResult("arris:apple_pie_item") and not Dishes.isDishResult("arris:horse_feed"), "派的另一种做法（派皮 + 料）在砧板上"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
