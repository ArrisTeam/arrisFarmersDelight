# -*- coding: utf-8 -*-
# runner: both
"""切菜板站点的规则适配（Shared/Rules/CuttingStation.py）：真实配方表上的刀口计划、工具判定、整批产物。"""
from __future__ import print_function

import random

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
    assert Rules.styleOf("minecraft:pumpkin_pie") == Cutting.STYLE_WEDGES, "HoD 的 cut_in_wedges 标签里有原版南瓜派"
    assert Rules.styleOf("minecraft:cake") == Cutting.STYLE_WEDGES
    assert Rules.styleOf("arris:wheat_dough") == Cutting.STYLE_STRIPS
    assert Rules.styleOf("arris:kelp_roll") == Cutting.STYLE_STRAIGHT
    assert Rules.styleOf("minecraft:beef") == Cutting.STYLE_ACROSS
    assert Rules.styleOf("arris:pieces_of_cod") == Cutting.STYLE_ACROSS, "只看整词，pieces 不算 pie"
    assert Rules.styleOf("minecraft:pumpkin") == Cutting.STYLE_WEDGES, "HoD 的 cut_in_wedges 标签里有南瓜"
    assert Rules.styleOf("minecraft:melon_block") == Cutting.STYLE_WEDGES, "也有西瓜"


def testPumpkinAndMelonAreCutInWedgesThroughTheMiddle():
    pumpkin, melon = "minecraft:pumpkin", "minecraft:melon_block"
    assert Rules.planFor(pumpkin, _recipe(pumpkin)).marks == 2, "南瓜 4 片：(4 + 1) / 2 = 2 刀（JE BoardBehavior 的楔形）"
    assert Rules.planFor(melon, _recipe(melon)).marks == Cutting.MOST_MARKS, "西瓜 9 片：5 刀夹到 3 刀"
    assert Rules.planFor("minecraft:cake", _recipe("minecraft:cake")).marks == Cutting.MOST_MARKS
    assert Rules.planFor("minecraft:clay", _recipe("minecraft:clay")).style == Cutting.STYLE_ACROSS, "别的东西照旧横切"


def testBeefTakesOneMarkAndChickenTakesTwo():
    assert Rules.planFor("minecraft:beef", _recipe("minecraft:beef")).marks == 1        # 2 块碎牛肉 = 1 刀
    assert Rules.planFor("minecraft:chicken", _recipe("minecraft:chicken")).marks == 2  # 2 块鸡肉 + 骨粉 = 3 件


def testLogsAreStrippedWithAnAxeAndMeatIsCutWithAKnife():
    assert Rules.strokeOf(_recipe("minecraft:oak_log")) == Cutting.TOOL_STRIP
    assert Rules.strokeOf(_recipe("minecraft:beef")) == Cutting.TOOL_CUT


def testToolsFollowJava():
    beef, log = _recipe("minecraft:beef"), _recipe("minecraft:oak_log")
    assert Rules.fitsTool("arris:iron_knife", "sword", beef, _isKnife)
    assert Rules.fitsTool("othermod:jade_knife", "sword", beef, lambda name: True), "带刀标签的下游刀能切刀切的配方"
    assert not Rules.fitsTool("minecraft:iron_axe", "axe", beef, _isKnife)
    assert Rules.fitsTool("minecraft:iron_axe", "axe", log, _isKnife)
    assert Rules.fitsTool("othermod:obsidian_axe", "axe", log, _isKnife), "斧类物品都能削皮"
    assert not Rules.fitsTool("arris:flint_knife", "sword", log, _isKnife), "JE：原木要斧头削，刀不行"
    assert not Rules.fitsTool("", None, beef, _isKnife)
    gravel, saddle = _recipe("minecraft:gravel"), _recipe("minecraft:saddle")
    assert Rules.fitsTool("minecraft:iron_shovel", "shovel", gravel, _isKnife)
    assert not Rules.fitsTool("arris:iron_knife", "sword", gravel, _isKnife)
    assert Rules.fitsTool("minecraft:shears", "shears", saddle, _isKnife)
    assert Rules.fitsTool("minecraft:stone_pickaxe", "pickaxe", _recipe("minecraft:brick_block"), _isKnife)
    assert Rules.fitsTool("minecraft:golden_hoe", "hoe", _recipe("minecraft:oak_chest_boat"), _isKnife)
    assert Rules.isKnifeRecipe(beef) and not Rules.isKnifeRecipe(log) and not Rules.isKnifeRecipe(saddle)


def testChanceOutputsAndFortune():
    cabbages = _recipe("arris:wild_cabbages")
    rolls = [0.1, 0.9, 0.4, 0.6]
    assert Rules.resultsFor(cabbages, 2, roll=lambda: rolls.pop(0)) == [("arris:cabbage_seeds", 0, 2), ("minecraft:yellow_dye", 0, 2)],         "每件切出的 2 个染料各掷一次：4 次里中 2 次 = 2 个（JE ChanceResult.rollOutput）"
    assert Rules.resultsFor(cabbages, 2, roll=lambda: 0.55, fortune=1) == [("arris:cabbage_seeds", 0, 2), ("minecraft:yellow_dye", 0, 4)]
    assert Rules.resultsFor(cabbages, 2, roll=lambda: 0.55) == [("arris:cabbage_seeds", 0, 2)], "一个都没掷中的不列"
    assert Rules.fortuneOf({"enchantData": [(9, 1), (18, 3)]}) == 3 and Rules.fortuneOf({}) == 0 and Rules.fortuneOf(None) == 0
    planks = _recipe("minecraft:wooden_door")["itemList"][0]
    assert planks == {"itemName": "minecraft:oak_planks", "count": 1, "chance": 0.75}


def testEachItemOfAChanceResultIsRolledOnItsOwn():
    # 数量 2、概率 50% 的染料：切一件得 0 / 1 / 2 个，大约 25 / 50 / 25%（以前是 0 或 2 各一半）
    dye = _recipe("arris:wild_cabbages")["itemList"][1]
    assert dye["count"] == 2 and dye["chance"] == 0.5
    rng = random.Random(20261117)
    seen = {}
    for _ in range(2000):
        got = Rules.countOf(dye, 1, roll=rng.random)
        seen[got] = seen.get(got, 0) + 1
    assert sorted(seen) == [0, 1, 2], seen
    assert 800 < seen[1] < 1200 and 350 < seen[0] < 650 and 350 < seen[2] < 650, seen
    assert Rules.countOf({"count": 2}, 5) == 10 and Rules.countOf({"count": 3, "chance": 1.0}, 2) == 6, "没有概率的照旧每件都给"
    assert Rules.countOf(dye, 3, roll=lambda: 0.99, fortune=5) == 6, "时运加成封顶 100%：每一个都中"


def testUnbreakingSkipsSomeWearAndTheBatchStopsWhenTheToolBreaks():
    assert Rules.unbreakingOf({"enchantData": [(9, 1), (17, 3)]}) == 3 and Rules.unbreakingOf({}) == 0 and Rules.unbreakingOf(None) == 0
    assert Rules.wearFor(12, 5) == (5, 5), "没有附魔：磨一件少一点耐久，耐久用完批就停"
    assert Rules.wearFor(40, None) == (Rules.BATCH, 0), "创造模式 / 不会坏的工具：整批 16 件，不磨"
    assert Rules.wearFor(3, 100) == (3, 3)
    assert Rules.wearFor(0, 5) == (0, 0) and Rules.wearFor(5, 0) == (0, 0)
    picks = [0, 1, 2, 0, 0]                # 等级 2：取到 0 才磨（1 / 3），1、2 是免掉的（2 / 3）
    assert Rules.wearFor(12, 3, 2, pick=lambda low, high: picks.pop(0)) == (5, 3), "耐久 3 的刀在第 5 件上坏了：磨 3 次、切 5 件"
    assert not picks
    assert Rules.wearFor(12, 5, 3, pick=lambda low, high: high) == (12, 0), "每一下都免磨：12 件切完，耐久没动"
    asked = []
    assert Rules.wearFor(2, 5, 0, pick=lambda low, high: asked.append(1) or 0) == (2, 2) and not asked, "没有附魔不掷骰子"


def testTheUnbreakingRollIsLevelOverLevelPlusOne():
    knife = {"enchantData": [(17, 2)]}
    assert Rules.ignoresWear(knife, pick=lambda low, high: 1) and Rules.ignoresWear(knife, pick=lambda low, high: 2)
    assert not Rules.ignoresWear(knife, pick=lambda low, high: 0)
    assert not Rules.ignoresWear({}, pick=lambda low, high: 5) and not Rules.ignoresWear(None), "没有附魔总是磨"
    rng = random.Random(7)
    freed = sum(1 for _ in range(3000) if Rules.ignoresWear(knife, pick=rng.randint))
    assert 1850 < freed < 2150, freed         # 2 / 3


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
    assert Cutting.batchSize(40, None) == Rules.BATCH == 16, "一刀切透 16 件；板上能放整叠，不是 16 个（BoardStation.BOARD_MAX）"


def testResultsAreMultipliedMergedAndSplitIntoStacks():
    chicken = _recipe("minecraft:chicken")
    assert Rules.resultsFor(chicken, 16) == [("arris:chicken_cuts", 0, 32), ("minecraft:bone_meal", 0, 16)]
    merged = {"itemList": [{"itemName": "a:x", "count": 2}, {"itemName": "a:x", "count": 1}]}
    assert Rules.resultsFor(merged, 3) == [("a:x", 0, 9)]
    assert Rules.stacks(112, 64) == [64, 48] and Rules.stacks(16, 16) == [16] and Rules.stacks(0, 64) == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
