# -*- coding: utf-8 -*-
# runner: both
"""Cutting 切菜板规则测试。

移植自 Hands-On Delight 的 BoardTests：marksFollowWhatTheFoodFallsInto、marksAreCutInOrderAtNewPlaces、
anIgnoredChopIsAnswered、aHamTakesTwoChopsAndFeedsTheCook、rawChickenFallsIntoItsCuts、sixteenAreCutAtOnce、
anotherCookKeepsTheMarks；以及 ToolStroke.of 的工具判定。
FD 的配方在这里换成"产物件数"：牛肉 [2]、鳕鱼 [2, 1]、海带卷 [3]、苹果派 [4]、蛋糕 [7]、火腿 [2, 1]、鸡肉 [2, 1]。
时间以秒计，原测试的刻数 / 20（落刀间隔 3 刻 = 0.15 秒）。
"""
from __future__ import print_function

import math
import random

import fdtest

Cut = fdtest.load("Shared.Rules.HandsOn.Cutting")


COUNTS = {
    "beef": [2], "cod": [2, 1], "kelp_roll": [3], "apple_pie": [4], "cake": [7],
    "ham": [2, 1], "chicken": [2, 1], "chicken_pizzacraft": [2, 2, 1], "cabbage": [2], "wheat_dough": [1],
}


def planOf(name, wedges=False, strips=False, straight=False):
    return Cut.planCut(COUNTS[name], Cut.chooseStyle(wedges, strips, straight))


def testMarksFollowWhatTheFoodFallsInto():
    assert planOf("beef").marks == 1, "beef into two: one cut"
    assert planOf("cod").marks == 2, "a cod into two slices and its bones: two"
    roll = planOf("kelp_roll", straight=True)
    assert roll.marks == 2 and roll.style == Cut.STYLE_STRAIGHT, "a kelp roll into three even slices"
    pie = planOf("apple_pie", wedges=True)
    assert pie.marks == 2 and pie.style == Cut.STYLE_WEDGES, "a pie into four wedges: two cuts through its middle"
    assert planOf("cake", wedges=True).marks == Cut.MOST_MARKS, "a cake into seven: three cuts at most"
    assert planOf("wheat_dough", strips=True).style == Cut.STYLE_STRIPS, "dough into strips"
    assert planOf("wheat_dough", strips=True).marks == 3, "面条固定 3 刀，不管产物是多少"


def testHamAndRawChickenFallIntoTheirCuts():
    assert planOf("ham").marks == 2, "a ham falls into three pieces: two marks"
    assert planOf("chicken").marks == 2, "two cuts and a bone: two marks, not three"
    # 同一件食材有两个配方时（FD 的 2 块 + 骨粉，PizzaCraft 的 2 + 2 + 骨粉）刀口数不同，
    # 所以两端必须用同一个确定的配方顺序（原版按配方 id 排序），否则客户端画两刀、服务端等第三刀（GitHub #26）
    assert planOf("chicken_pizzacraft").marks == 3


def testPiecesAndTheClamp():
    assert Cut.pieces([]) == 2, "没有产物算 2 件"
    assert Cut.pieces([3]) == 3 and Cut.pieces([2, 1]) == 3 and Cut.pieces([2, 5, 5]) == 4
    assert Cut.planCut([], Cut.STYLE_ACROSS).marks == 1
    assert Cut.planCut([1], Cut.STYLE_ACROSS).marks == 1, "1 件也至少一刀"
    assert Cut.planCut([1], Cut.STYLE_WEDGES).marks == 1
    assert Cut.planCut([3], Cut.STYLE_WEDGES).marks == 2 and Cut.planCut([5], Cut.STYLE_WEDGES).marks == 3, "n 刀过圆心切 2n 块：奇数块向上取整"
    assert Cut.planCut([30], Cut.STYLE_ACROSS).marks == Cut.MOST_MARKS
    assert Cut.countsOf([{"itemName": "a", "count": 2}, {"itemName": "b"}]) == [2, 1]


def testWedgesBeatStripsBeatStraight():
    assert Cut.chooseStyle() == Cut.STYLE_ACROSS and Cut.chooseStyle(straight=True) == Cut.STYLE_STRAIGHT
    assert Cut.chooseStyle(strips=True, straight=True) == Cut.STYLE_STRIPS
    assert Cut.chooseStyle(wedges=True, strips=True, straight=True) == Cut.STYLE_WEDGES


def testARollIsCutInEvenSlicesAndPastaInCloseStripsBothSquareAcross():
    spots, angles = Cut.layoutMarks(planOf("kelp_roll", straight=True), random.Random(1))
    assert abs(spots[0] - 1.0 / 3.0) < 1.0e-4 and abs(spots[1] - 2.0 / 3.0) < 1.0e-4, "even slices"
    assert angles == [0.0, 0.0], "square across"
    spots, angles = Cut.layoutMarks(planOf("wheat_dough", strips=True), random.Random(1))
    assert [round(spot, 6) for spot in spots] == [0.375, 0.5, 0.625] and angles == [0.0, 0.0, 0.0], "strips: close side by side"


def testWedgesGoThroughTheMiddleEvenlyRound():
    spots, angles = Cut.layoutMarks(planOf("cake", wedges=True), random.Random(7))
    assert spots == [0.5, 0.5, 0.5]
    for mark in (1, 2):
        assert abs(angles[mark] - angles[mark - 1] - math.pi / 3.0) < 1.0e-12, "三刀均分半圈"
    assert 0.0 <= angles[0] <= math.pi, "起始转角在半圈之内"


def testMarksAreCutInOrderAtNewPlaces():
    for seed in range(300):
        plan = Cut.CutPlan(2, Cut.STYLE_ACROSS)
        spots, angles = Cut.layoutMarks(plan, random.Random(seed))
        assert abs(spots[0] - spots[1]) >= 0.15, "the two marks lie apart"
        for mark in range(2):
            assert 0.2 <= spots[mark] <= 0.8, "on the item, never at its ends"
            assert abs(angles[mark]) <= 1.0, "a share of the most lean: never along the item"
        assert not Cut.crossOnTheItem(spots[0], angles[0] * Cut.MOST_LEAN, spots[1], angles[1] * Cut.MOST_LEAN), \
            "the two cuts never meet on the item (seed %d)" % seed


def testOneAndThreeAcrossMarksStayApartAndNeverMeet():
    seen = set()
    for seed in range(300):
        spots, angles = Cut.layoutMarks(Cut.CutPlan(1, Cut.STYLE_ACROSS), random.Random(seed))
        assert 0.35 - 1e-9 <= spots[0] <= 0.65 + 1e-9 and abs(angles[0]) <= 1.0, "一刀：落在中间附近"
        spots, angles = Cut.layoutMarks(Cut.CutPlan(3, Cut.STYLE_ACROSS), random.Random(seed))
        for a in range(3):
            assert 0.2 <= spots[a] <= 0.8
            for b in range(a + 1, 3):
                assert not Cut.crossOnTheItem(spots[a], angles[a] * Cut.MOST_LEAN, spots[b], angles[b] * Cut.MOST_LEAN)
                assert abs(spots[a] - spots[b]) >= 0.1
        seen.add(round(spots[0], 3))
    assert len(seen) > 100, "不同的种子给出不同的布局"


def testCrossingMarksAreRerolledNotFlattened():
    # 三刀横切初始角度相交的概率不小，重掷 30 次几乎必能解开；全部平行（angles 全相等）只是最后的兜底，不该出现
    for seed in range(300):
        angles = Cut.layoutMarks(Cut.CutPlan(3, Cut.STYLE_ACROSS), random.Random(seed))[1]
        assert len(set(angles)) == 3, (seed, angles)


def testCrossOnTheItem():
    assert Cut.crossOnTheItem(0.5, 0.5, 0.5, -0.5), "two marks through one point do"
    assert not Cut.crossOnTheItem(0.2, 0.0, 0.8, 0.0), "two straight across do not"
    assert not Cut.crossOnTheItem(0.3, 0.3, 0.7, 0.3), "平行不相交"
    # 两条斜线 0.2 / 0.8 处各斜 35 度（最大斜度），在 x = 0.93 会合，还在食材上；斜 20 度则要到 x = 1.32 才会合，已出了食材
    assert Cut.crossOnTheItem(0.2, Cut.MOST_LEAN, 0.8, -Cut.MOST_LEAN), "meet just inside the item"
    assert not Cut.crossOnTheItem(0.2, math.radians(20), 0.8, -math.radians(20)), "meet beyond the item's edge"
    # 刀口是过食材中线的整条直线，往两头都延伸：反过来斜的一对在 x = 0.07 处会合，同样还在食材上
    assert Cut.crossOnTheItem(0.2, -Cut.MOST_LEAN, 0.8, Cut.MOST_LEAN), "they meet at x = 0.07"
    assert not Cut.crossOnTheItem(0.2, -math.radians(20), 0.8, math.radians(20)), "x = -0.32: off the item"
    assert Cut.MOST_LEAN == math.radians(35.0)


def testMarksCutInOrderAndAnIgnoredChopIsAnswered():
    board = Cut.BoardCut()
    board.restart(planOf("ham"), random.Random(3))
    assert not board.accept(0.0, 1), "the second mark before the first: refused"
    assert board.accept(0.0, 0)
    assert not board.accept(0.0, 1), "two chops in one tick: the second refused"
    assert board.strike() is False, "one chop does not cut a ham"
    assert board.marks == 1
    assert not board.accept(0.2, 0), "nor two on the same mark"
    assert board.accept(0.4, 1)
    assert board.strike() is True, "the second mark cuts"


def testTheChopGapIsThreeTicks():
    board = Cut.BoardCut()
    board.restart(planOf("ham"), random.Random(3))
    assert board.accept(0.0, 0) and not board.strike()
    assert not board.accept(0.10, 1), "两刀之间不到 0.15 秒"
    assert not board.accept(0.14, 1)
    assert board.accept(0.15, 1), "原版 now - lastChop < 3 才拒绝：第 3 刻就行"


def testAFirstChopIsNeverTooSoonAndNoItemNoChop():
    board = Cut.BoardCut()
    board.restart(planOf("beef"), random.Random(3))
    assert not board.accept(5.0, 0, hasItem=False)
    assert board.accept(0.0, 0), "lastChop 初值是 -CHOP_GAP：开局第一刀不受间隔限制；没食材时被拒也不占间隔"


def testSixteenAreCutAtOnce():
    # 20 个卷心菜（每个切两片叶子）：一刀切 16 个，剩 4 个；0.2 秒后下一刀切完
    board = Cut.BoardCut()
    stack = 20
    board.restart(planOf("cabbage"), random.Random(3))
    assert board.accept(0.0, 0) and board.strike()
    done = Cut.batchSize(stack)
    assert done == Cut.BATCH == 16
    stack -= done
    assert stack == 20 - Cut.BATCH, "one cut goes through sixteen cabbages"
    assert done * COUNTS["cabbage"][0] == 2 * Cut.BATCH, "two leaves each"
    board.restart(planOf("cabbage"), random.Random(4))
    assert board.marks == 0, "the next item of the stack comes with marks of its own"
    assert board.accept(0.2, 0) and board.strike()
    assert Cut.batchSize(stack) == 4, "the next cut takes the rest"


def testTheToolsDurabilityLimitsTheBatch():
    assert Cut.batchSize(20, toolLeft=5) == 5, "每切一件磨损 1 点：最多切到工具坏"
    assert Cut.batchSize(20, toolLeft=100) == 16 and Cut.batchSize(3, toolLeft=100) == 3
    assert Cut.batchSize(20, toolLeft=0) == 0 and Cut.batchSize(0) == 0


def testAnotherCookKeepsTheMarks():
    # 一个人离开不动刀口；最后一个人离开才重新布局（restart）
    board = Cut.BoardCut()
    board.restart(planOf("ham"), random.Random(3))
    first = list(board.spots)
    assert board.accept(0.0, 0) and not board.strike()
    assert board.marks == 1 and board.spots == first, "the first mark stays cut for the other cook"
    board.restart(planOf("ham"), random.Random(99))
    assert board.marks == 0, "and starts over when the board is left"
    assert board.spots != first, "the next item has marks of its own"


def testToolKinds():
    assert Cut.toolKindOf("arris:iron_knife") == "knife"
    assert Cut.toolKindOf("minecraft:iron_axe") == "axe"
    assert Cut.toolKindOf("minecraft:iron_pickaxe") == "pickaxe", "pickaxe 不是斧"
    assert Cut.toolKindOf("minecraft:diamond_shovel") == "shovel"
    assert Cut.toolKindOf("minecraft:golden_hoe") == "hoe"
    assert Cut.toolKindOf("minecraft:shears") == "shears"
    assert Cut.toolKindOf("minecraft:stick") is None and Cut.toolKindOf("minecraft:shoe") is None
    assert Cut.toolKindOf("axe") == "axe"


def testWhichStrokeARecipeNeeds():
    assert Cut.strokeKind(["arris:iron_knife"]) == Cut.TOOL_CUT
    assert Cut.strokeKind([]) == Cut.TOOL_CUT, "没写工具按刀"
    assert Cut.strokeKind(["minecraft:iron_axe", "arris:iron_knife"]) == Cut.TOOL_CUT, "刀也能用就按刀"
    assert Cut.strokeKind(["minecraft:iron_axe"], ["minecraft:stripped_oak_log"]) == Cut.TOOL_STRIP
    assert Cut.strokeKind(["minecraft:iron_axe"], ["minecraft:stick"]) == Cut.TOOL_CHOP
    assert Cut.strokeKind(["minecraft:iron_axe"]) == Cut.TOOL_CHOP
    assert Cut.strokeKind(["minecraft:iron_pickaxe"]) == Cut.TOOL_SMASH
    assert Cut.strokeKind(["minecraft:iron_shovel"]) == Cut.TOOL_DIG
    assert Cut.strokeKind(["minecraft:iron_hoe"]) == Cut.TOOL_PRY
    assert Cut.strokeKind(["minecraft:shears"]) == Cut.TOOL_SNIP
    assert Cut.strokeKind(["modx:rolling_pin"]) == Cut.TOOL_CUT, "an addon's own tool: the knife"
    assert Cut.strokeKind(["modx:rolling_pin", "minecraft:iron_hoe"]) == Cut.TOOL_PRY, "第一个认得的说了算"


def testStrokeTimes():
    assert Cut.STROKES[Cut.TOOL_CHOP] == (0.19, 0.42) and Cut.STROKES[Cut.TOOL_STRIP] == (0.27, 0.42)
    assert Cut.STROKES[Cut.TOOL_SMASH] == (0.19, 0.40) and Cut.STROKES[Cut.TOOL_DIG] == (0.17, 0.38)
    assert Cut.STROKES[Cut.TOOL_PRY] == (0.20, 0.40) and Cut.STROKES[Cut.TOOL_SNIP] == (0.36, 0.46)
    for kind, (impact, length) in Cut.STROKES.items():
        assert impact <= length, kind
    times = Cut.snipTimes()
    assert [round(t, 6) for t in times] == [0.06, 0.16, 0.26]
    assert abs(Cut.SNIP_START + Cut.SNIPS * Cut.SNIP_TIME - Cut.STROKES[Cut.TOOL_SNIP][0]) < 1e-12, "最后一下剪完正好是落点"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
