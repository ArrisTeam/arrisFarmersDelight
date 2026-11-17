# -*- coding: utf-8 -*-
# runner: both
"""PotLiquid / PotLiquidColor / PotLiquidRates（厨锅汤面）的测试。数字全部来自 Hands-On Delight 与 Diegesis 的源码，
每条用例注明出处（PB = client/PotBehavior.java，PL = station/PotLogic.java，LS = LiquidSim.java，LR = LiquidRenderer.java）。"""
from __future__ import print_function

import math

import fdtest

L = fdtest.load("Shared.Rules.HandsOn.PotLiquid")
C = fdtest.load("Shared.Rules.HandsOn.PotLiquidColor")


def near(a, b, eps=1.0e-9):
    assert abs(a - b) <= eps, "%r != %r" % (a, b)


def channel(a, b, t):
    """Java 的 Math.round(lerp(t, a, b))：floor(x + 0.5)。"""
    return int(math.floor(a + t * (b - a) + 0.5))


def argbOf(a, r, g, b):
    return (a << 24) | (r << 16) | (g << 8) | b


def testTankAmountFromStacksAndServings():
    # PL:39-43, 721-729：58 + 6 * 非空格；有成品时至少 min(100, 74 + 5 * 份数)
    assert [L.tankAmount(n) for n in range(7)] == [58, 64, 70, 76, 82, 88, 94]
    assert [L.tankAmount(0, s) for s in range(1, 8)] == [79, 84, 89, 94, 99, 100, 100]
    assert L.tankAmount(6, 1) == 94, "成品不会让水位比料多时更低"
    assert L.tankAmount(3, 1) == 79 and L.tankAmount(3, 0) == 76


def testSurfaceHeightsMatchTheJavaNumbers():
    # PB:531 brothFloor + brothDepth * level：2 + 6.5 * 水量 / 100
    heights = [L.surfaceHeight(L.tankAmount(n)) for n in range(7)]
    for got, want in zip(heights, [5.77, 6.16, 6.55, 6.94, 7.33, 7.72, 8.11]):
        near(got, want)
    meals = [L.surfaceHeight(L.tankAmount(0, s)) for s in range(1, 8)]
    for got, want in zip(meals, [7.135, 7.46, 7.785, 8.11, 8.435, 8.5, 8.5]):
        near(got, want)
    near(L.surfaceHeight(58) - L.BROTH_FLOOR, 3.77)            # 空锅已经有 3.77 px 深的水
    near(L.RIM - L.surfaceHeight(100), 1.5)                    # 满水在锅沿下 1.5 px（PB:49-55）
    near(L.surfaceHeight(L.tankAmount(0, 2)) - L.surfaceHeight(L.tankAmount(0, 1)), 0.325)   # 每份 0.325 px


def testOpacityOfWaterAndSoup():
    # LR:49-53, 287, 333-335：1 - exp(ln(1 - A / 255) * path)，液面 path 0.85
    near(C.opacity(0xA0), 1.0 - math.exp(math.log(1.0 - 160 / 255.0) * 0.85))
    assert abs(C.opacity(0xA0) - 0.568) < 0.001, "清水约 57%"
    assert abs(C.opacity(0xF0) - 0.910) < 0.001, "煮好的汤约 91%"
    near(C.opacity(0xA0, 1.0), 160 / 255.0)                   # path 1 就是 alpha 本身
    near(C.opacity(0), 0.0)
    near(C.opacity(255), 1.0 - 0.002 ** 0.85)                 # 能透过多少的下限 0.002
    assert C.SURFACE_PATH == 0.85
    assert C.opacity(0xF0) > C.opacity(0xA0)


def testWallLookDarkensAndThickensWithDepth():
    # LR:320-331：近侧壁明暗 1 - 0.42 * deep，透过去的远侧壁 0.8 - 0.3 * deep
    shade0, alpha0 = C.wallLook(0xA0, 0.0)
    near(shade0, 1.0)
    near(alpha0, C.opacity(0xA0, 0.6))
    shadeDeep, alphaDeep = C.wallLook(0xA0, 100.0)
    assert abs(shadeDeep - 0.58) < 1.0e-6 and alphaDeep > alpha0
    near(C.wallLook(0xA0, 0.0, inside=True)[0], 0.8)
    near(C.wallLook(0xA0, 100.0, inside=True)[0], 0.5, 1.0e-6)
    near(C.wallLook(0xA0, 0.0, inside=True)[1], C.opacity(0xA0, 0.35))


def testBlendRoundsEveryChannelLikeJavaMathRound():
    # PB:1105-1111：每个通道 Math.round(Mth.lerp(amount, from, to))，.5 进位
    assert C.blend(0x00000000, 0xFF646464, 0.3) == 0x4D1E1E1E         # 76.5 -> 77，30 -> 30
    assert C.blend(0xFF000000, 0xFF000001, 0.5) == 0xFF000001, "0.5 进位（Python 的 round 会给 0）"
    assert C.blend(0x11223344, 0xAABBCCDD, 0.0) == 0x11223344
    assert C.blend(0x11223344, 0xAABBCCDD, 1.0) == 0xAABBCCDD
    assert C.blend(0xFFFFFFFF, 0x00000000, 0.25) == 0xBFBFBFBF         # 255 * 0.75 = 191.25
    assert C.blend(-1, 0, 0.0) == 0xFFFFFFFF, "Java 的负 int 位模式也认"


def testMixColorsIsTheIntegerMeanPerChannel():
    # FoodColors.mix（FoodColors.java:218-234）：逐通道整数平均（向下取整），没有就是 0xB0A070
    assert C.mixColors([0xFF0000, 0x0000FF]) == 0x7F007F
    assert C.mixColors([0x102030]) == 0x102030
    assert C.mixColors([]) == 0xB0A070 == C.FALLBACK
    assert C.mixColors([0x010101, 0x020202, 0x020202]) == 0x010101, "(1 + 2 + 2) / 3 = 1"
    assert C.mixColors(iter([0x000000, 0xFEFEFE])) == 0x7F7F7F, "任何可迭代的都行"


def testWaterColors():
    # PB:1048-1049：生物群系水色配 0xA0；怪物锅的黏液配 0xE0
    assert C.waterColor(0x3F76E4) == 0xA03F76E4
    assert C.waterColor() == 0xA044AFF5 == C.argb(C.WATER_ALPHA, C.DEFAULT_BIOME_WATER), "没给群系水色：基岩版的缺省水色"
    assert C.waterColor(0x3F76E4, 0x47A44F) == 0xE047A44F


def testBrothTargetGoesFromRawToDone():
    # PB:1047-1084：cooked = 没成品 ? 0.3 + 0.7 * 进度 : 1；颜色 = blend(水, 0xF0 | 汤, cooked)，mottle = cooked
    water = C.waterColor(0x3F76E4)
    soup = 0xC8A040
    for progress, cooked in ((0.0, 0.3), (0.5, 0.65), (1.0, 1.0)):
        colour, mottle = C.brothTarget(water, [soup], False, progress, dishBroth=soup)
        near(mottle, cooked)
        want = argbOf(channel(0xA0, 0xF0, cooked), channel(0x3F, 0xC8, cooked), channel(0x76, 0xA0, cooked), channel(0xE4, 0x40, cooked))
        assert colour == want, "%x != %x" % (colour, want)
    assert (C.brothTarget(water, [soup], False, 0.0, soup)[0] >> 24) == 184                # 进度 0：alpha 184
    assert (C.brothTarget(water, [soup], False, 0.5, soup)[0] >> 24) == 212
    assert C.brothTarget(water, [soup], True, 0.0, soup) == (0xF0C8A040, 1.0), "有成品：满色，不看进度"
    assert C.brothTarget(water, [], False, 0.0) == (water, 0.0), "没有食物：还是清水，mottle 0"


def testBrothTargetFallsBackToTheMeanOfTheFood():
    # PB:1073：不知道做什么菜（preview 空）就用 FoodColors.mix(food)
    water = C.waterColor(0x3F76E4)
    colour, mottle = C.brothTarget(water, [0xFF0000, 0x00FF00], False, 1.0)
    near(mottle, 1.0)
    assert colour == C.blend(water, 0xF07F7F00, 1.0) == 0xF07F7F00
    colour, _ = C.brothTarget(water, [0xFF0000, 0x00FF00], False, 1.0, dishBroth=0x0000FF)
    assert colour == 0xF00000FF, "知道菜就用菜的汤色"


def testPouredLiquidsTintTheWaterOnlyBeforeAMeal():
    # PB:1050-1058：没有成品时每件倒好的液体把水往它的颜色拉 60%（0xF0 的 alpha）
    water = C.waterColor(0x3F76E4)
    once = C.blend(water, 0xF0FFFFFF, 0.6)
    assert C.brothTarget(water, [], False, 0.0, poured=[0xFFFFFF]) == (once, 0.0)
    twice = C.blend(once, 0xF0FF0000, 0.6)
    assert C.brothTarget(water, [], False, 0.0, poured=[0xFFFFFF, 0xFF0000])[0] == twice
    assert C.brothTarget(water, [0xC8A040], True, 0.0, 0xC8A040, poured=[0xFFFFFF])[0] == 0xF0C8A040, "有成品时不染水"


def testMonsterPotOozeTakesAtMostAThirdOfTheFoodColour():
    # PB:1048, 1075：黏液锅 liquid != 0，混合量 cooked * 0.35
    water = C.waterColor(0x3F76E4, 0x47A44F)
    colour, mottle = C.brothTarget(water, [0xFF0000], True, 0.0, 0xFF0000, liquid=0x47A44F)
    assert colour == C.blend(water, 0xF0FF0000, 0.35) and mottle == 1.0


def testBubbleTintAndWakeLook():
    # PB:1101：0xE0 的 alpha + 汤色往白走 60%；PB:1081：拖尾留多久 / 多清晰
    shown = 0xF0C8A040
    want = argbOf(0xE0, channel(0xC8, 0xFF, 0.6), channel(0xA0, 0xFF, 0.6), channel(0x40, 0xFF, 0.6))
    assert C.bubbleTint(shown) == want
    assert C.wakeLook(0.0) == (1.2, 0.25) and C.wakeLook(1.0) == (9.0, 1.0)
    life, contrast = C.wakeLook(0.5)
    near(life, 5.1)
    near(contrast, 0.625)


def testToUnitGivesRgbaFloats():
    r, g, b, a = C.toUnit(0x80FF8000)
    near(r, 1.0)
    near(g, 128 / 255.0)
    near(b, 0.0)
    near(a, 128 / 255.0)


def testPotMoodFollowsHeatStirDishAndMeal():
    # PB:1174-1178：cooking = 有火 && 被搅 && 有菜可煮 && 没成品；soup = 有菜可煮或有成品；没火一律冷
    assert L.potMood(False, True, True, False) == L.COLD
    assert L.potMood(True, False, False, False) == L.HOT_WATER
    assert L.potMood(True, True, False, False) == L.HOT_WATER, "没有菜可煮，搅也只是热水"
    assert L.potMood(True, False, True, False) == L.SOUP
    assert L.potMood(True, True, True, False) == L.COOKING
    assert L.potMood(True, True, True, True) == L.SOUP, "有成品就不在煮了"
    assert L.potMood(True, True, False, True) == L.SOUP


def testRatesByMood():
    # PB:1206-1222（每秒）：气泡 0 / 0.8 / 2.2 / 7，蒸汽 0 / 1.6 / 3.2 / 6.5，边泡 0 / 4 / 8 / 16，躁动 0 / 0.03 / 0.03 / 0.12，边沿沸腾 0 / 0.3 / 0.55 / 0.9
    assert L.BUBBLE_RATES == (0.0, 0.8, 2.2, 7.0)
    assert L.STEAM_RATES == (0.0, 1.6, 3.2, 6.5)
    assert L.EDGE_BUBBLE_RATES == (0.0, 4.0, 8.0, 16.0)
    assert L.AGITATIONS == (0.0, 0.03, 0.03, 0.12)
    assert L.EDGE_BOILS == (0.0, 0.3, 0.55, 0.9)
    assert L.bubbleRate(L.COOKING) == 7.0 and L.bubbleRate(L.COOKING, 2.0) == 14.0
    assert L.steamRate(L.COOKING) == 6.5 and L.edgeBubbleRate(L.SOUP, 0.5) == 4.0
    assert (L.COLD, L.HOT_WATER, L.SOUP, L.COOKING) == (0, 1, 2, 3)


def testLevelEasesAtThreePerSecondWhileTheDrawnLiquidFollowsInNinetyMilliseconds():
    liquid = L.PotLiquid()
    liquid.step(0.1, 100)                                      # 第一次：渲染的液面直接到位（LS:129-138）
    near(liquid.fraction, 1.0)
    near(liquid.level, 0.3)                                    # PB:1181：lerp(min(1, 3 * 0.1), 0, 1)
    near(liquid.surfaceY(), 2.0 + 6.5 * 0.3)
    liquid.step(0.1, 100)
    near(liquid.level, 0.3 + 0.3 * 0.7)
    low = L.PotLiquid()
    low.step(0.1, 58)
    near(low.fraction, 0.58)
    low.step(0.09, 94)                                         # 半衰期 0.09 s：一个半衰期走一半
    near(low.fraction, 0.76)
    near(low.drawnSurfaceY(), 2.0 + 6.5 * 0.76)
    full = L.PotLiquid()
    full.step(0.1, 100)
    near(full.drawnSurfaceY(), 2.0 + 6.5 * 0.995)              # LR:83 画出来的最多到 0.995


def testSnapAndRestartPutTheLiquidAtTheTankAtOnce():
    liquid = L.PotLiquid()
    liquid.snap(94)
    near(liquid.level, 0.94)
    near(liquid.fraction, 0.94)
    liquid.step(1.0 / 60, 94)
    near(liquid.level, 0.94, 1.0e-9)
    assert liquid.color == liquid.target, "restart 之后第一步颜色直接到位"
    liquid.setTarget(0xF0102030, 1.0)
    liquid.restart()
    liquid.step(0.016, 94)
    assert liquid.shown == 0xF0102030 and liquid.color == 0xF0102030


def testShownColourFollowsTheTargetInTwoStages():
    # PB:1094 blend(shown, target, min(1, 4 dt))，再 LS:549-552 每个通道半衰期 0.18 s
    liquid = L.PotLiquid()
    liquid.step(0.1, 100)
    start = 0xA044AFF5
    assert liquid.shown == start and liquid.color == start
    liquid.setTarget(0xF0C8A040, 0.0)
    liquid.step(0.1, 100)
    first = argbOf(channel(0xA0, 0xF0, 0.4), channel(0x44, 0xC8, 0.4), channel(0xAF, 0xA0, 0.4), channel(0xF5, 0x40, 0.4))
    assert liquid.shown == first
    keep = 0.5 ** (0.1 / 0.18)
    want = [int(math.floor(t + (s - t) * keep + 0.5)) for s, t in
            ((0xA0, (first >> 24) & 0xFF), (0x44, (first >> 16) & 0xFF), (0xAF, (first >> 8) & 0xFF), (0xF5, first & 0xFF))]
    assert liquid.color == argbOf(*want)
    assert liquid.brothColor == first & 0xFFFFFF
    assert liquid.bubbleColor == C.bubbleTint(first)


def testShownColourStallsWithinSevenLevelsLikeJava():
    # Java 的怪癖，原样保留：blend 的步长不到半级就四舍五入成 0，所以 60 帧时颜色停在离目标几级的地方
    liquid = L.PotLiquid()
    liquid.setTarget(0xF0000000, 0.0)
    liquid.step(1.0 / 60, 100)
    liquid.setTarget(0xF0000007, 0.0)
    for _ in range(600):
        liquid.step(1.0 / 60, 100)
    assert liquid.shown == 0xF0000000 and liquid.target == 0xF0000007, "7 * (4 / 60) = 0.47 < 0.5"
    liquid.setTarget(0xF0000008, 0.0)
    for _ in range(600):
        liquid.step(1.0 / 60, 100)
    assert 0xF0000001 <= liquid.shown <= 0xF0000008, "8 * (4 / 60) = 0.53 进到 1，之后又停住"


def testMottleAndEdgeBoilEaseWithTheirOwnHalfLives():
    # LS:140-142：mottle 半衰期 0.3 s，边沿沸腾 0.5 s
    liquid = L.PotLiquid()
    liquid.step(0.1, 100, L.COOKING)                           # 第一次不缓动
    assert liquid.mottle == 0.0 and liquid.edgeBoil == 0.0
    liquid.setTarget(0xF0C8A040, 1.0)
    liquid.step(0.3, 100, L.COOKING)
    near(liquid.mottle, 0.5)
    near(liquid.edgeBoil, 0.9 * (1.0 - 0.5 ** (0.3 / 0.5)))
    near(liquid.agitation, 0.12)
    life, contrast = liquid.wakeLife, liquid.wakeContrast
    assert (life, contrast) == (9.0, 1.0)


def testAgitationAndEdgeBoilTargetsByMood():
    liquid = L.PotLiquid()
    liquid.step(0.1, 100)
    for mood, agitation, edge in ((L.COLD, 0.0, 0.0), (L.HOT_WATER, 0.03, 0.3), (L.SOUP, 0.03, 0.55), (L.COOKING, 0.12, 0.9)):
        liquid.step(0.1, 100, mood)
        near(liquid.agitation, agitation)
        near(liquid.edgeBoilWanted, edge)
    liquid.step(0.1, 100, L.COOKING, boil=2.0)
    near(liquid.agitation, 0.24)
    near(liquid.edgeBoilWanted, 1.0)                           # min(1, 0.9 * 2)


def run(mood, seconds, dt=0.05, boil=1.0):
    liquid = L.PotLiquid()
    liquid.step(dt, 100, mood)
    totals = [0, 0, 0, 0]
    for _ in range(int(round(seconds / dt))):
        liquid.step(dt, 100, mood, boil=boil)
        totals[0] += liquid.emitBubbles
        totals[1] += liquid.emitSteam
        totals[2] += liquid.emitEdge
        totals[3] += liquid.boilCount
    return totals


def testEmissionTotalsFollowTheRatesPerSecond():
    cold = run(L.COLD, 10.0)
    assert cold == [0, 0, 0, 0]
    water = run(L.HOT_WATER, 10.0)
    assert abs(water[0] - 8) <= 1 and abs(water[1] - 16) <= 1 and abs(water[2] - 40) <= 1
    assert abs(water[3] - 8) <= 1, "26 * 0.03 = 0.78 个/秒的沸腾水波"
    soup = run(L.SOUP, 10.0)
    assert abs(soup[0] - 22) <= 1 and abs(soup[1] - 32) <= 1 and abs(soup[2] - 80) <= 1
    cooking = run(L.COOKING, 10.0)
    assert abs(cooking[0] - 70) <= 1 and abs(cooking[1] - 65) <= 1 and abs(cooking[2] - 160) <= 1
    assert abs(cooking[3] - 31) <= 1, "26 * 0.12 = 3.12 个/秒"
    boiling = run(L.COOKING, 10.0, boil=2.0)
    assert abs(boiling[0] - 140) <= 1 and abs(boiling[1] - 65) <= 1, "boil 乘气泡和边泡，不乘蒸汽（PB:1217）"


def testEmissionCarriesTheRemainderLikeTheJavaAccumulator():
    # PB:1212-1216：攒 dt * 速率，够 1 个就放 (int) 个，剩下的留着；每步 0.7 个气泡
    liquid = L.PotLiquid()
    seen = []
    for _ in range(5):
        liquid.step(0.1, 100, L.COOKING)
        seen.append(liquid.emitBubbles)
    assert seen == [0, 1, 1, 0, 1], seen
    near(liquid.bubbles, 0.5)


def testBoilImpulseSpansTheTankAndScalesWithAgitation():
    # LS:420：位置 rand * 0.9 + 0.05，高度 0.1 + 0.28 * agitation
    liquid = L.PotLiquid()
    liquid.step(0.1, 100, L.COOKING)
    values = iter([0.0, 1.0])
    u, v, height = liquid.impulse(lambda: next(values))
    near(u, 0.05)
    near(v, 0.95)
    near(height, 0.1 + 0.28 * 0.12)


def testTurnedAccumulatesTheCurrent():
    liquid = L.PotLiquid()
    liquid.step(0.1, 100)
    for _ in range(10):
        liquid.step(0.1, 100, L.COLD, current=1.5)
    near(liquid.turned, 1.5)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
