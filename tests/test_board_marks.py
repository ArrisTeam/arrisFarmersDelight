# -*- coding: utf-8 -*-
# runner: both
"""砧板刀口的几何（Shared/Rules/HandsOn/BoardMarks.py）：图标主轴、刀口线、虚线两端、吸附、光标在不在食物上。

对应 HoD 的 ItemVoxels.Icon.axis / solidSpan、BoardBehavior.line / clip / overItem。
真图标上的数是拿 HoD 的原算法（逐行抄成不依赖 Minecraft 的 Java，JDK 25 跑）对过的：320 个数最大差 6e-7（float 和 double 之差）。
"""
from __future__ import print_function

import math
import random

import fdtest

Marks = fdtest.load("Shared.Rules.HandsOn.BoardMarks")
Cutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
Masks = fdtest.load("Shared.Data.ItemMasks").ItemMasks
Data = fdtest.load("Shared.Data.Cutting")
Station = fdtest.load("Shared.Rules.CuttingStation")


def _close(a, b, eps=1.0e-4):
    return abs(a - b) < eps


def _bar(width, height, left, right, top, bottom):
    """16x16 的图标，[left, right] x [top, bottom] 是实心。"""
    rows = [sum(1 << x for x in range(left, right + 1)) if top <= y <= bottom else 0 for y in range(height)]
    return Marks.Icon(width, height, rows)


def testBoundsAndPixelSize():
    icon = _bar(16, 16, 2, 13, 5, 8)
    assert icon.bounds() == [2, 13, 5, 8]
    assert icon.solid(2, 5) and not icon.solid(1, 5) and not icon.solid(2, 9) and not icon.solid(-1, 0) and not icon.solid(0, 16)
    assert _close(icon.pixel(10.0), 0.625), "16 格画 10 像素"
    assert _close(Marks.Icon(32, 16, [0] * 16).pixel(10.0), 10.0 / 32), "按最长边"
    assert Marks.Icon(16, 16, [0] * 16).bounds() == [16, -1, 16, -1], "一格实心都没有"


def testAFlatBarLiesAlongX():
    # 12 格宽 4 格高的横条：长边顺着 x（dirZ 为 0 时取 +x），上下左右对称，长宽比约 3
    axis = _bar(16, 16, 2, 13, 6, 9).axis()
    assert _close(axis.dirX, 1.0) and abs(axis.dirZ) < 1e-6
    assert _close(axis.x, 0.0) and _close(axis.z, 0.0), "图标中心就是它的中心"
    assert _close(axis.start, -6.0 * 0.625) and _close(axis.end, 6.0 * 0.625), "12 格 x 0.625"
    assert axis.elongation > 2.0
    assert _close(axis.across(), math.pi / 2.0), "垂直于横条的线是顺着 z 的：和 x 轴夹 90 度"


def testATallBarPointsFarAndIsCutStraightAcrossIt():
    axis = _bar(16, 16, 6, 9, 2, 13).axis()
    assert abs(axis.dirX) < 1e-6 and _close(axis.dirZ, 1.0), "指向远端（图标上方）"
    assert _close(axis.across(), 0.0), "垂直于竖条的线笔直横过去"
    assert _close(axis.at(0.0)[1], axis.end) and _close(axis.at(1.0)[1], axis.start), "spot 0 是远端、1 是近端"
    assert _close(axis.at(0.5)[1], 0.0)


def testADiagonalAndARoundThing():
    rows = [1 << (15 - y) | 1 << (14 - y) if y < 14 else 0 for y in range(16)]     # 左上到右下的斜条（图标坐标）
    axis = Marks.Icon(16, 16, rows).axis()
    assert axis.dirZ > 0.0 and abs(abs(axis.dirX) - abs(axis.dirZ)) < 0.05, "斜 45 度，指向远端"
    disc = Marks.Icon(16, 16, [sum(1 << x for x in range(16) if (x - 7.5) ** 2 + (y - 7.5) ** 2 <= 36) for y in range(16)])
    assert _close(disc.axis().elongation, 1.0, 0.02), "圆的长宽比是 1"
    assert Marks.Icon(16, 16, [0] * 16).axis().elongation == 1.0, "没有实心像素：当 10 像素的方块"
    assert _close(Marks.Icon(16, 16, [0] * 16).axis().end, 5.0)


def testRealIconsGiveTheNumbersOfTheJavaOriginal():
    expected = {
        # 物品: (x, z, dirX, dirZ, start, end, elongation, across)
        "minecraft:beef": (-0.4977, -0.7870, -0.7742, 0.6329, -4.6412, 4.5595, 1.6225, 0.8855),
        "arris:ham": (-0.4335, 0.4335, -0.7071, 0.7071, -6.2288, 4.1189, 1.8866, 0.7854),
        "arris:cabbage": (-0.1333, -0.3833, 0.9991, 0.0420, -4.3401, 4.4814, 1.0392, -1.5288),
        "arris:kelp_roll": (0.0, -0.3125, -0.8819, 0.4714, -4.7792, 4.7792, 2.3164, 1.0800),
        "minecraft:cod": (0.0456, -0.1562, -0.6814, 0.7319, -5.0569, 5.3477, 2.2133, 0.7497),
    }
    for name, numbers in expected.items():
        axis = Marks.iconOf(name).axis()
        got = (axis.x, axis.z, axis.dirX, axis.dirZ, axis.start, axis.end, axis.elongation, axis.across())
        for a, b in zip(got, numbers):
            assert _close(a, b, 2.0e-4), (name, got, numbers)


def testSolidSpanOnlyCountsSolidPixels():
    # 左右各一块实心（第 1、2 列和第 11、12 列，第 6 到 9 行），中间空着：穿过中心的横线从一块的外沿到另一块的外沿，不管中间的空
    rows = [(0x3 << 1) | (0x3 << 11) if 6 <= y <= 9 else 0 for y in range(16)]
    icon = Marks.Icon(16, 16, rows)
    first, last = icon.solidSpan(0.0, 0.0, 0.0)
    assert _close(first, -3.125, 0.2) and _close(last, 4.375, 0.2), (first, last)
    assert icon.solidSpan(0.0, 8.0, 0.0) == (Marks.INFINITY, -Marks.INFINITY), "线在图标外面：碰不到"
    up = icon.solidSpan(3.5, 0.0, math.pi / 2.0)
    assert _close(up[0], -1.25, 0.2) and _close(up[1], 1.25, 0.2), "顺着 z 穿过第 2 列：4 行高的实心"
    assert icon.solidSpan(0.0, 0.0, math.pi / 2.0) == (Marks.INFINITY, -Marks.INFINITY), "第 8 列是空的"
    assert Marks.Icon.full().solidSpan(0.0, 0.0, 0.0)[1] >= 4.9, "整格实心：一直画到图标边上"


def testLineFollowsTheStyle():
    axis = _bar(16, 16, 2, 13, 6, 9).axis()                          # 顺 x 的横条：across = 90 度
    across = Marks.line(axis, Cutting.STYLE_ACROSS, 0.5, 0.0)
    assert _close(across.angle, math.pi / 2.0) and _close(across.x, axis.x), "横条的刀口顺着 z，落在长边中间"
    leaning = Marks.line(axis, Cutting.STYLE_ACROSS, 0.5, 1.0)
    assert axis.elongation < 3.5
    assert _close(Marks.normalized(leaning.angle - across.angle), Cutting.MOST_LEAN if axis.elongation < Marks.LONG else Marks.LONG_LEAN)
    thin = _bar(16, 16, 1, 14, 7, 8).axis()
    assert thin.elongation >= Marks.LONG
    flat = Marks.line(thin, Cutting.STYLE_ACROSS, 0.5, 0.0)
    slanted = Marks.line(thin, Cutting.STYLE_ACROSS, 0.5, 1.0)
    assert _close(Marks.normalized(slanted.angle - flat.angle), Marks.LONG_LEAN), "长的东西最多偏 20 度，不是 35 度"
    square = Marks.Axis(0.0, 0.0, 0.0, 1.0, -5.0, 5.0, 1.0)
    assert _close(Marks.normalized(Marks.line(square, Cutting.STYLE_ACROSS, 0.5, 1.0).angle), Cutting.MOST_LEAN), "不长的最多偏 35 度"
    straight = Marks.line(axis, Cutting.STYLE_STRAIGHT, 0.25, 1.0)
    assert _close(straight.angle, math.pi / 2.0) and _close(straight.x, axis.at(0.25)[0]), "卷：笔直横过去，spot 决定位置，角度份额不起作用"
    wedge = Marks.line(axis, Cutting.STYLE_WEDGES, 0.9, 1.2)
    assert _close(wedge.x, axis.x) and _close(wedge.z, axis.z) and _close(wedge.angle, 1.2), "楔形过食物中心，spot 不起作用"
    assert _close(Marks.line(axis, Cutting.STYLE_WEDGES, 0.5, 3.5).angle, Marks.normalized(3.5))
    assert -math.pi / 2.0 < Marks.normalized(3.5) <= math.pi / 2.0
    block = Marks.Axis.square(Marks.BLOCK_SIZE / 2.0)
    assert _close(Marks.line(block, Cutting.STYLE_ACROSS, 0.5, 0.0).angle, 0.0), "方块的刀口笔直横过去"


def testAMarkTheServerHasNotSentYetIsEvenAndSquare():
    axis = _bar(16, 16, 6, 9, 2, 13).axis()
    first = Marks.markOf(axis, Cutting.STYLE_ACROSS, [], [], 0, 2)
    second = Marks.markOf(axis, Cutting.STYLE_ACROSS, [], [], 1, 2)
    assert _close(first.z, axis.at(1.0 / 3.0)[1]) and _close(second.z, axis.at(2.0 / 3.0)[1]) and _close(first.angle, 0.0)
    sent = Marks.markOf(axis, Cutting.STYLE_ACROSS, [0.25, 0.75], [0.0, 0.0], 1, 2)
    assert _close(sent.z, axis.at(0.75)[1])


def testCutDistanceHasASignAndALineIsItsOwnNormalSide():
    cut = Marks.Cut(1.0, 2.0, 0.0)                                   # 顺 x 的线 z = 2
    assert _close(cut.normalX(), 0.0) and _close(cut.normalZ(), 1.0)
    assert _close(cut.distance(5.0, 3.5), 1.5) and _close(cut.distance(-3.0, 0.5), -1.5)
    slanted = Marks.Cut(0.0, 0.0, math.pi / 4.0)
    assert _close(slanted.distance(1.0, 1.0), 0.0) and slanted.distance(-1.0, 1.0) > 0.0


def testClipAndABlocksDashedLine():
    assert Marks.clip(0.0, 1.0, -2.6, 2.6, -100.0, 100.0) == (-2.6, 2.6)
    assert Marks.clip(5.0, 0.0, -2.6, 2.6, -100.0, 100.0) == (0.0, 0.0), "平行于边又在外面：什么都没有"
    assert Marks.clip(0.0, 0.0, -2.6, 2.6, -3.0, 3.0) == (-3.0, 3.0), "平行于边又在里面：不收窄"
    assert Marks.clip(0.0, -1.0, -2.6, 2.6, -1.0, 100.0) == (-1.0, 2.6)
    cut = Marks.Cut(0.0, 0.0, 0.0)
    first, last = Marks.endsOf(None, cut, isBlock=True)
    assert _close(first, -Marks.BLOCK_SIZE / 2.0) and _close(last, Marks.BLOCK_SIZE / 2.0), "5.2 像素见方的方块"
    diagonal = Marks.endsOf(None, Marks.Cut(0.0, 0.0, math.pi / 4.0), isBlock=True)
    assert _close(diagonal[1], Marks.BLOCK_SIZE / 2.0 * math.sqrt(2.0)), "斜着穿方块的角"
    points = Marks.ends(cut, None, isBlock=True)
    assert _close(points[0][0], -2.6) and _close(points[1][0], 2.6) and _close(points[0][1], 0.0)
    assert Marks.ends(Marks.Cut(0.0, 9.0, 0.0), None, isBlock=True) is None, "线在方块外面：没有虚线"
    scattered = Marks.Icon(16, 16, [0x0001 if y == 0 else (0x8000 if y == 15 else 0) for y in range(16)])
    miss = Marks.Cut(0.0, 0.0, 0.0)
    assert Marks.ends(miss, scattered) is None and Marks.dashOf(miss, scattered) is not None, "碰不到实心像素：改按外框裁"


def testExtentOfAnIcon():
    icon = _bar(16, 16, 2, 13, 4, 11)
    right, left, near, far = Marks.extentOf(icon)
    assert _close(right, (8 - 13 - 1) * 0.625) and _close(left, (8 - 2) * 0.625)
    assert _close(near, (8 - 11 - 1) * 0.625) and _close(far, (8 - 4) * 0.625)
    assert all(_close(a, b) for a, b in zip(Marks.extentOf(None, isBlock=True), (-2.6, 2.6, -2.6, 2.6)))


def testTheKnifeIsOnTheItemOnlyNearIt():
    assert Marks.overItem(0.0, 0.0) == (0.0, 0.0)
    assert Marks.overItem(5.9, -5.9) == (Marks.REACH, -Marks.REACH), "食物边上 1 像素以内都算，刀夹进 4 像素"
    assert Marks.overItem(6.1, 0.0) is None and Marks.overItem(0.0, -6.0) is None, "离中心 6 像素就不算了"
    assert Marks.overItem(-3.0, 2.0) == (-3.0, 2.0)


def testSnapIsWithinOnePointFourPixels():
    cut = Marks.Cut(0.0, 1.0, 0.0)
    assert _close(Marks.snapOffset(cut, 3.0, 2.2), 1.2) and _close(Marks.snapOffset(cut, 3.0, -0.2), -1.2)
    assert Marks.snapOffset(cut, 0.0, 2.4) is None and Marks.snapOffset(cut, 0.0, 2.5) is None, "1.4 以外不吸附"
    assert Marks.SNAP == 1.4 and Marks.REACH == 4.0 and Marks.ITEM_SIZE == 10.0 and _close(Marks.BLOCK_SIZE, 5.2)


def testEveryRealIconGetsADashedLineOnItForAnyLayout():
    names = sorted(Masks)
    assert len(names) >= 30
    for name in names:
        icon = Marks.iconOf(name)
        axis = icon.axis()
        assert axis.start < 0.0 < axis.end and axis.elongation >= 1.0 and abs(axis.dirX * axis.dirX + axis.dirZ * axis.dirZ - 1.0) < 1e-9, name
        recipe = Data.CuttingBoardDict.get((name, 0))
        if recipe is None:
            continue
        plan = Station.planFor(name, recipe)
        for seed in range(40):
            spots, angles = Cutting.layoutMarks(plan, random.Random(seed))
            for index in range(plan.marks):
                cut = Marks.markOf(axis, plan.style, spots, angles, index, plan.marks)
                span = Marks.dashOf(cut, icon)
                assert span is not None, (name, seed, index, plan.style)
                if Marks.ends(cut, icon) is None:
                    assert name == "minecraft:leather_horse_armor", (name, "实心像素碎成几块的图标才会碰不到")
                length = math.hypot(span[1][0] - span[0][0], span[1][1] - span[0][1])
                assert 0.2 < length <= 2.0 * Marks.ITEM_SIZE, (name, seed, index, length)


def testAnIconNotInTheTableIsASolidSquare():
    icon = Marks.iconOf("somemod:mystery_food")
    assert icon.bounds() == [0, 15, 0, 15] and _close(icon.axis().elongation, 1.0, 1e-6)
    assert Marks.iconOf("somemod:mystery_food") is icon, "缓存"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
