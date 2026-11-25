# -*- coding: utf-8 -*-
# runner: both
"""前置包的原版工作台站点（arrisDiegesis 的 Vanilla/Server/TableHooks：脚本合成，不发引擎的合成事件）上登的两条规则
（Compat/Diegesis/TableHooksLink.py）：砧板菜不让在那张工作台上做（dishVeto，和 DishCrafts 同一份 DishStation.isDishCraft），
本包的无序配方做完把容器放回原来那一格（returns，和 Server/CraftReturns 同一张 Shared/Data/CraftReturns 表；下游包登记的成品每份还一个）。
九格是前置包给的配方朝向的物品字典或 None，个数不影响认配方。不要前置包：它的接口模块由 linkkit 的假环境给（env.tableHooks）；
登在哪一步由 test_presence_boots.py 管。
"""
from __future__ import print_function

import fdtest
import linkkit as L

env = L.install()
Link = fdtest.load("Compat.Diegesis.TableHooksLink")
Tips = fdtest.load("Shared.Data.Tips")
Dishes = fdtest.load("Shared.Rules.DishStation")
Food = fdtest.load("Shared.Data.Food")
BUCKET, BOTTLE, BOWL = "minecraft:bucket", "minecraft:glass_bottle", "minecraft:bowl"


def stack(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def cells(*names):
    """九格：前几格依次放 names（None 空一格），其余空着。"""
    out = [stack(name) if name else None for name in names]
    return out + [None] * (9 - len(out))


def returned(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def testEveryBoardDishIsRefusedWithTheBoardTip():
    """菜谱表里每道菜的每条配方都拒，给的话是 Tips.DISH_ON_BOARD（语言键 + 中文：前置包的客户端按玩家的语言查）。"""
    for dish in Dishes.dishes():
        names = [kind[0] for kind in dish["ingredients"]]
        assert Link.dishVeto("p", stack(dish["result"][0]), cells(*names)) == Tips.DISH_ON_BOARD, dish["result"]
    assert Tips.DISH_ON_BOARD[0] == "arris_fd.tip.dish_on_board" and len(Tips.DISH_ON_BOARD) == 2


def testOnlyTheBoardRecipeIsRefused():
    """拦配方不拦成品（和 DishCrafts 一样）：少一样、多一样就是别的合成；切片拼回整个派、牛奶瓶照常。"""
    salad = ["minecraft:crimson_fungus", "minecraft:warped_fungus", BOWL]
    assert Link.dishVeto("p", stack("arris:nether_salad"), cells(*salad)) == Tips.DISH_ON_BOARD
    assert Link.dishVeto("p", stack("arris:nether_salad"), cells(*salad[:2])) is None
    assert Link.dishVeto("p", stack("arris:nether_salad"), cells(*(salad + [BOWL]))) is None
    assert Link.dishVeto("p", stack("arris:apple_pie_item"), cells(*(["arris:apple_pie_slice"] * 4))) is None
    assert Link.dishVeto("p", stack("arris:milk_bottle", 4), cells("minecraft:milk_bucket", BOTTLE, BOTTLE, BOTTLE, BOTTLE)) is None
    spread = [stack("minecraft:crimson_fungus", 5), None, stack("minecraft:warped_fungus", 3), None, stack(BOWL, 9)] + [None] * 4
    assert Link.dishVeto("p", stack("arris:nether_salad"), spread) == Tips.DISH_ON_BOARD, "摆在哪几格、每格几个都不要紧"


def testShapelessContainersGoBackToTheirOwnCell():
    """JE 的合成剩余物：每份每格还一件，放回那一格（前置包那边放不回再进背包、掉脚下）。"""
    grid = cells(None, "minecraft:milk_bucket", BOTTLE, BOTTLE, BOTTLE, BOTTLE)
    assert Link.returns("p", stack("arris:milk_bottle", 4), grid) == [(1, returned(BUCKET))]
    ham = cells("arris:cooked_rice", "minecraft:honey_bottle", "arris:cooked_rice", BOWL, "arris:smoked_ham",
                "minecraft:sweet_berries", "minecraft:sweet_berries", "minecraft:sweet_berries", "minecraft:sweet_berries")
    assert sorted(Link.returns("p", stack("arris:honey_glazed_ham_block_stage0"), ham)) == \
        [(0, returned(BOWL)), (1, returned(BOTTLE)), (2, returned(BOWL))], "米饭两格各还一只碗、蜂蜜瓶还空瓶；碗本身不是剩余物"
    dough = cells("minecraft:wheat", None, "minecraft:water_bucket")
    assert Link.returns("p", stack("arris:wheat_dough"), dough) == [(2, returned("minecraft:water_bucket"))], "JE 的 DoughRecipe：水桶原样留下"


def testNothingComesBackWhenTheGridIsNotOneOfOurRecipes():
    assert Link.returns("p", stack("arris:milk_bottle", 4), cells("minecraft:milk_bucket", "minecraft:dirt")) == []
    assert Link.returns("p", stack("minecraft:bread"), cells("minecraft:wheat", "minecraft:wheat", "minecraft:wheat")) == []
    assert Link.returns("p", stack("arris:milk_bottle", 4), [None] * 9) == []


def testTheDownstreamContainerDictStillGivesOnePerCraft():
    """下游包在 Food.shapedRecipeContainerDict 登记的成品（契约）：每份还一个容器，进背包（格写 None）。"""
    Food.shapedRecipeContainerDict["test:toast"] = {"itemName": BOTTLE, "auxValue": 0, "perCraft": 2}
    try:
        assert Link.returns("p", stack("test:toast", 2), cells("test:jam")) == [(None, returned(BOTTLE))]
    finally:
        del Food.shapedRecipeContainerDict["test:toast"]


class Hooks(object):
    def __init__(self, version):
        self.API_VERSION = version
        self.vetoes, self.remainders = [], []

    def addVeto(self, fn):
        self.vetoes.append(fn)

    def addRemainder(self, fn):
        self.remainders.append(fn)


def testItRegistersOnlyOnATableHooksModuleThatIsNewEnough():
    """接口模块在、版本够：登上；前置包太旧（没有这个模块）、版本不够：什么都不登，回 False（步骤记成 skipped）。"""
    hooks = env.tableHooks["server"] = Hooks(1)
    assert Link.addReturns() is True and Link.addDishVeto() is True
    assert hooks.remainders == [Link.returns] and hooks.vetoes == [Link.dishVeto]
    assert env.asked["server"][-1] == L.TABLE_HOOKS == Link.HOOKS
    old = env.tableHooks["server"] = Hooks(0)
    assert Link.addReturns() is False and Link.addDishVeto() is False and old.remainders == old.vetoes == []
    env.tableHooks["server"] = None
    assert Link.hooks() is None and Link.addReturns() is False


def testTheGridIsReadTheWayTheCraftingRulesReadIt():
    grid = Link.gridOf(cells("minecraft:milk_bucket", None, BOTTLE))
    assert grid == {0: ("minecraft:milk_bucket", 1), 2: (BOTTLE, 1)}
    assert Link.gridOf(None) == {} and Link.gridOf([None] * 9) == {}
    assert Link.gridOf([{"itemName": "minecraft:stick", "count": 3}]) == {0: ("minecraft:stick", 3)}, "旧写法的物品字典也认"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
