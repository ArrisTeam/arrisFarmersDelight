# -*- coding: utf-8 -*-
# runner: both
"""切菜板站点的规则适配（Shared/Rules/CuttingStation.py）：真实配方表上的刀口计划、工具判定、整批产物。"""
from __future__ import print_function

import fdtest

Rules = fdtest.load("Shared.Rules.CuttingStation")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
Data = fdtest.load("Shared.Data.Cutting")


def _recipe(name, aux=0):
    return Data.CuttingBoardDict[(name, aux)]


def _isKnife(name):
    return name in Data.knifeList


def testEveryRecipeGetsOneToThreeMarksAndAKnownStroke():
    strokes = set(Cutting.STROKES)
    for (name, aux), recipe in Data.CuttingBoardDict.items():
        plan = Rules.planFor(name, recipe)
        assert 1 <= plan.marks <= Cutting.MOST_MARKS, (name, plan)
        assert Rules.strokeOf(recipe) in strokes, name


def testTheLayoutFollowsTheFood():
    assert Rules.styleOf("arris:apple_pie_item") == Cutting.STYLE_WEDGES
    assert Rules.styleOf("minecraft:cake") == Cutting.STYLE_WEDGES
    assert Rules.styleOf("arris:wheat_dough") == Cutting.STYLE_STRIPS
    assert Rules.styleOf("arris:kelp_roll") == Cutting.STYLE_STRAIGHT
    assert Rules.styleOf("minecraft:beef") == Cutting.STYLE_ACROSS
    assert Rules.styleOf("arris:pieces_of_cod") == Cutting.STYLE_ACROSS, "只看整词，pieces 不算 pie"


def testBeefTakesOneMarkAndChickenTakesTwo():
    assert Rules.planFor("minecraft:beef", _recipe("minecraft:beef")).marks == 1        # 2 块碎牛肉 = 1 刀
    assert Rules.planFor("minecraft:chicken", _recipe("minecraft:chicken")).marks == 2  # 2 块鸡肉 + 骨粉 = 3 件


def testLogsAreStrippedWithAnAxeAndMeatIsCutWithAKnife():
    assert Rules.strokeOf(_recipe("minecraft:oak_log")) == Cutting.TOOL_STRIP
    assert Rules.strokeOf(_recipe("minecraft:beef")) == Cutting.TOOL_CUT


def testToolsFitLikeTheClassicBoard():
    beef, log = _recipe("minecraft:beef"), _recipe("minecraft:oak_log")
    assert Rules.fitsTool("arris:iron_knife", "sword", beef, _isKnife)
    assert not Rules.fitsTool("minecraft:iron_axe", "axe", beef, _isKnife)
    assert Rules.fitsTool("minecraft:iron_axe", "axe", log, _isKnife)
    assert Rules.fitsTool("othermod:obsidian_axe", "axe", log, _isKnife), "斧类物品都能削皮"
    assert Rules.fitsTool("arris:flint_knife", "sword", log, _isKnife), "经典玩法里刀什么都能切"
    assert not Rules.fitsTool("", None, beef, _isKnife)


def testPickToolPrefersTheHandThenOffhandThenInventory():
    knife = {"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1, "durability": 10}
    flint = {"newItemName": "arris:flint_knife", "newAuxValue": 0, "count": 1}
    apple = {"newItemName": "minecraft:apple", "newAuxValue": 0, "count": 3}
    beef = _recipe("minecraft:beef")
    typeOf = lambda item: "sword" if "knife" in item["newItemName"] else "food"  # noqa: E731
    assert Rules.pickTool([("hand", apple), ("offhand", None), ("inv", flint), ("inv2", knife)], beef, _isKnife, typeOf) \
        == ("inv", flint)
    assert Rules.pickTool([("hand", knife), ("inv", flint)], beef, _isKnife, typeOf)[0] == "hand"
    assert Rules.pickTool([("hand", apple)], beef, _isKnife, typeOf) is None


def testTheLastChopCutsTheWholeStackWithinTheToolsDurability():
    knife = {"newItemName": "arris:iron_knife", "durability": 5}
    assert Rules.toolLeft(knife) == 5 and Rules.toolLeft({"newItemName": "x"}) is None
    assert Rules.toolLeft(knife, 126) == 5
    assert Rules.toolLeft({"newItemName": "mod:stone_knife", "durability": 0}, 0) is None, "不会损坏的刀：耐久读作 0 也不限"
    assert Cutting.batchSize(12, Rules.toolLeft(knife)) == 5
    assert Cutting.batchSize(40, None) == Rules.BOARD_LIMIT == 16


def testResultsAreMultipliedMergedAndSplitIntoStacks():
    chicken = _recipe("minecraft:chicken")
    assert Rules.resultsFor(chicken, 16) == [("arris:chicken_cuts", 0, 32), ("minecraft:bone_meal", 0, 16)]
    merged = {"itemList": [{"itemName": "a:x", "count": 2}, {"itemName": "a:x", "count": 1}]}
    assert Rules.resultsFor(merged, 3) == [("a:x", 0, 9)]
    assert Rules.stacks(112, 64) == [64, 48] and Rules.stacks(16, 16) == [16] and Rules.stacks(0, 64) == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
