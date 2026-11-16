# -*- coding: utf-8 -*-
# runner: both
"""汤色、碎料色、倒进锅的液体色的取色规则（Shared/Rules/HandsOn/PotColors.py）：照 Hands-On Delight 的 FoodColors / ItemVoxels.contents / PotBehavior.blend。

期望值是把 Java 源码（FoodColors.sampleMain / broth / colours / drawsAny、ItemVoxels.contents、FoodColors.lighter / isGreen、PotBehavior.blend，
NativeImage 换成像素数组）用 JDK 跑出来的，不是这个模块自己算的；另外还拿 JDK 对过 18 万组 RGBtoHSB / HSBtoRGB、3000 张随机图标（含票数并列、
13 种以上颜色的 HashMap 扩容）和 4000 组数，逐位一致。图标用字符画：一个字符一个像素，调色板里没有的（"."）是透明的。
"""
from __future__ import print_function

import struct

import fdtest

Colors = fdtest.load("Shared.Rules.HandsOn.PotColors")

PALETTE = {
    "O": (237, 139, 31, 255),      # 橙（胡萝卜）
    "G": (70, 170, 50, 255),       # 绿（叶子）
    "g": (120, 120, 120, 255),     # 灰
    "k": (20, 20, 20, 255),        # 描边的黑
    "R": (210, 80, 40, 255),       # 汤的红
    "B": (130, 90, 40, 255),       # 碗的木色
    "r": (255, 0, 40, 255),        # 红（色相在环的末端）
    "s": (255, 60, 0, 255),        # 红（色相在环的开头）
    "w": (245, 245, 245, 255),     # 牛奶的白
    "c": (180, 220, 230, 255),     # 玻璃的浅蓝
    "h": (240, 200, 60, 200),      # 黄，alpha 200（还算看得见）
    "x": (240, 200, 60, 127),      # 黄，alpha 127（不算）
}


def art(rows):
    """字符画 -> (pixels, width, height)。"""
    pixels = []
    for row in rows:
        for char in row:
            pixels.append(PALETTE.get(char, (0, 0, 0, 0)))
    return pixels, len(rows[0]), len(rows)


def ties(count, copies=2):
    """count 种颜色（颜色和 alpha 都不同）各 copies 个像素，铺在一张 16 x 16 的图标上：票数全并列。"""
    pixels = []
    for index in range(count):
        color = ((index * 37 + 11) % 256, (index * 91 + 5) % 256, (index * 53 + 200) % 256, 255 if index % 3 else 200)
        pixels += [color] * copies
    pixels += [(0, 0, 0, 0)] * (256 - len(pixels))
    return pixels, 16, 16


CARROT = art(["...GG...", "..GGGG..", "...OO...", "..OOOO..", "..OOOO..", "...OO...", "...OO...", "....O..."])
STEW = art(["........", "..RRRR..", ".RRRRRR.", "BBBBBBBB", "BBBBBBBB", ".BBBBBB.", "..BBBB..", "........"])
BOWL = art(["........", "........", "........", "BBBBBBBB", "BBBBBBBB", ".BBBBBB.", "..BBBB..", "........"])
SALAD = art(["..R..R..", "..R..R..", "..R..R..", "..R..R..", "..R..R..", "GGGGGGGG", "GGGGGGGG", "GGGGGGGG"])
MILK = art(["..kkkk..", "..kccc..", ".kccck..", "kcwwwwck", "kcwwwwck", "kcwwwwck", "kcwwwwck", ".kkkkkk."])
BOTTLE = art(["..kkkk..", "..kccc..", ".kccck..", "kccccck.", "kccccck.", "kccccck.", "kccccck.", ".kkkkkk."])
CASES = {
    "carrot": (CARROT, None),
    "grey": (art(["gggg"] * 4), None),
    "outline": (art(["kkkk", "kRRk", "kkkk", "kkkk"]), None),
    "empty": (art(["....", "....", "...."]), None),
    "halfAlpha": (art(["xxxx", "xxxx", "hhhh", "hhhh"]), None),
    "redWraps": (art(["rrrGGGGG", "sssG....", "........", "........"]), None),
    "stewNoBowl": (STEW, None),
    "stewInBowl": (STEW, BOWL),
    "saladInBowl": (SALAD, BOWL),
    "milkBottle": (MILK, BOTTLE),
    "milkAlone": (MILK, None),
    "ties2": (ties(2), None),
    "ties5": (ties(5), None),
    "ties12": (ties(12), None),
    "ties13": (ties(13), None),
    "ties14": (ties(14), None),
    "ties30": (ties(30), None),
    "ties30Bottle": (ties(30), ties(4)),
}
# (全图 sampleMain, 只看上 60% 行的 sampleMain, broth, 液体所在的列, 行) —— JDK 跑出来的
EXPECTED = {
    "carrot": (0xFF8600, 0xFF8600, 0xFF8600, 3, 2),
    "empty": (0xB0A070, 0xB0A070, 0xB0A070, 2, 1),
    "grey": (0xB89C72, 0xB89C72, 0xB89C72, 0, 0),
    "halfAlpha": (0xFFC806, 0xFFC806, 0xFFC806, 0, 2),
    "milkAlone": (0x9EECFF, 0x9EECFF, 0x9EECFF, 2, 0),
    "milkBottle": (0x9EECFF, 0x9EECFF, 0xFFD89E, 2, 3),
    "outline": (0xFC3B00, 0xFC3B00, 0xFC3B00, 0, 0),
    "redWraps": (0xFF0B00, 0xFF0B00, 0xFF0B00, 3, 0),
    "saladInBowl": (0x30CC11, 0xFC3B00, 0xFC3B00, 0, 5),
    "stewInBowl": (0xB86E12, 0xB86E12, 0xFC3B00, 2, 1),
    "stewNoBowl": (0xB86E12, 0xB86E12, 0xB86E12, 0, 3),
    "ties12": (0x00CC4C, 0x00CC4C, 0x00CC4C, 0, 1),
    "ties13": (0xFF1D00, 0xFF1D00, 0xFF1D00, 8, 1),
    "ties14": (0xFF2C06, 0xFF2C06, 0xFF2C06, 8, 1),
    "ties2": (0x0700F0, 0x0700F0, 0x0700F0, 0, 0),
    "ties30": (0xFF4117, 0xFF4117, 0xFF4117, 8, 3),
    "ties30Bottle": (0xFF4117, 0xFF4117, 0xFF4117, 8, 3),
    "ties5": (0xB8269F, 0xB8269F, 0xB8269F, 8, 0),
}
GREEN = [
    (0x40A040, True), (0xFF0000, False), (0x20FF20, True), (0xCCFF00, False), (0xFFFF00, False), (0x00FF80, True), (0x00FFA0, True),
    (0x00FFC0, True), (0x00FFCC, True), (0x00FFD0, True), (0x00FF00, True), (0x808080, False), (0x7F9F00, True), (0x99FF00, True),
    (0x00FF7F, True), (0xB0A070, False), (0x3F7F3F, True),
]
LIGHTER = [
    (0x808080, 0.55, 0xC6C6C6), (0xFF0000, 0.55, 0xFF8C8C), (0x000000, 0.55, 0x8C8C8C), (0xB0A070, 0.55, 0xDBD4BF),
    (0x123456, 0.3, 0x597189), (0xFFFFFF, 0.55, 0xFFFFFF), (0xF2DC9A, 0.55, 0xF9EFD2),
]
# blend(0xE0 起头的 start, 0xFF 起头的 end, amount) —— PotBehavior.blend，气泡色就是这么算的
BLEND = [
    (0x336699, 0xFFFFFF, 0.6, 0xF3ADC2D6), (0x000000, 0xFFFFFF, 0.6, 0xF3999999), (0xFFAA00, 0x000000, 0.3, 0xE9B37700),
    (0x808080, 0x808080, 0.5, 0xF0808080), (0x102030, 0xF0E0D0, 1.0, 0xFFF0E0D0),
]
# JDK 的 RGBtoHSB 给出的 float 位（色相, 饱和度, 亮度）
HSB_BITS = [
    ((248, 171, 6), (1038662191, 1064947316, 1064892665)), ((55, 37, 248), (1059999349, 1062850164, 1064892665)),
    ((130, 32, 92), (1063641255, 1061223440, 1057129091)),
]


def bitsOf(value):
    return struct.unpack("I", struct.pack("f", value))[0]


def mainOf(image, rows=1.0):
    return Colors.sampleMain(image[0], image[1], image[2], rows)


def channels(rgb):
    return (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF


def testRgbToHsbIsJavasToTheLastBit():
    for (r, g, b), want in HSB_BITS:
        assert tuple(bitsOf(v) for v in Colors.rgbToHsb(r, g, b)) == want, (r, g, b)
    assert Colors.rgbToHsb(50, 50, 50) == (0.0, 0.0, Colors.f32(50 / 255.0)), "灰：色相 0、饱和度 0"
    assert Colors.rgbToHsb(0, 0, 0) == (0.0, 0.0, 0.0)


def testHsbToRgbRoundTripsAndOverflowsLikeJava():
    assert Colors.hsbToRgb(0.0, 1.0, 1.0) == 0xFF0000 and Colors.hsbToRgb(1.0 / 3, 1.0, 1.0) == 0x00FF00
    assert Colors.hsbToRgb(0.5, 0.0, 0.5) == 0x808080, "饱和度 0 是灰"
    assert Colors.hsbToRgb(1.141808271408081, 1.0577187538146973, 0.792483389377594) == 0xFFFFF5, "超出 0..1 的参数和 Java 一样溢出再掩码"
    for r, g, b in ((12, 200, 90), (255, 128, 0), (3, 3, 250)):
        hue, saturation, brightness = Colors.rgbToHsb(r, g, b)
        assert Colors.hsbToRgb(hue, saturation, brightness) == r << 16 | g << 8 | b


def testIsGreenIsAHueBandBetweenTwoTenthsAndFourSevenths():
    for rgb, green in GREEN:
        assert Colors.isGreen(rgb) == green, hex(rgb)


def testLighterMovesEachChannelTowardsWhite():
    for rgb, amount, want in LIGHTER:
        assert Colors.lighter(rgb, amount) == want, (hex(rgb), amount)
    assert Colors.FAT_LIGHT == Colors.f32(0.55), "CookedPieces 的浮油比汤亮 0.55"


def testBlendMatchesThePotsBubbleColours():
    for start, end, amount, want in BLEND:
        assert Colors.blend(0xE0000000 | start, 0xFF000000 | end, amount) == want, (hex(start), hex(end), amount)
    assert Colors.blend(0x80102030, 0xFF405060, 0.0) == 0x80102030 and Colors.blend(0x80102030, 0xFF405060, 1.0) == 0xFF405060


def testMixAveragesPerChannelWithIntegerDivision():
    assert Colors.mix([]) == Colors.FALLBACK == 0xB0A070
    assert Colors.mix([0x102030]) == 0x102030
    assert Colors.mix([0x000001, 0x000002]) == 0x000001, "整数除，向下取"
    assert Colors.mix([0xFF0000, 0x00FF00, 0x0000FF]) == 0x555555


def testEveryCaseMatchesJava():
    for name, (meal, container) in sorted(CASES.items()):
        main, bowl, broth, column, row = EXPECTED[name]
        pixels, width, height = meal
        assert Colors.sampleMain(pixels, width, height) == main, name
        assert Colors.sampleMain(pixels, width, height, Colors.BOWL_TOP) == bowl, name
        assert Colors.brothOf(pixels, width, height, container) == broth, name
        assert Colors.liquidAt(meal, container) == (column, row), name


def testTheMainColourIsTheBiggestFamilyNotTheAverage():
    red, green, blue = channels(mainOf(CARROT))
    assert red == 255 and 100 < green < 160 and blue < 30, "胡萝卜是橙的：绿叶没把它平均成棕色"
    assert Colors.isGreen(mainOf(art(["GGGG"] * 4))), "全是叶子才是绿的"


def testGreyFoodIsGivenTheToneOfSomethingCooked():
    hue, saturation, brightness = Colors.rgbToHsb(*channels(mainOf(CASES["grey"][0])))
    assert abs(hue - 0.1) < 0.01 and abs(saturation - 0.38) < 0.01 and abs(brightness - 0.72) < 0.01, "灰 -> 暖色相 0.1、饱和度和亮度取下限"


def testNothingToReadIsTheFallback():
    assert mainOf(CASES["empty"][0]) == Colors.FALLBACK
    assert mainOf(art(["xxxx"] * 3)) == Colors.FALLBACK, "alpha 127 不算看得见"
    assert mainOf(CASES["halfAlpha"][0]) == 0xFFC806, "alpha 200 算"


def testTheDarkOutlineSaysNothing():
    assert mainOf(CASES["outline"][0]) == 0xFC3B00, "黑描边亮度 < 0.3，只剩汤的红"


def testRedAtBothEndsOfTheHueCircleIsOneFamily():
    # 三个 r（色相 0.97）+ 三个 s（色相 0.04）合起来比五片绿叶重；只有一端的红斗不过绿叶
    assert mainOf(CASES["redWraps"][0]) == 0xFF0B00
    assert Colors.isGreen(mainOf(art(["rrrGGGGG", "........", "........", "........"])))


def testBrothTakesTheContainerOutOfTheSoup():
    assert mainOf(STEW) == 0xB86E12, "没有容器：碗的木色占多数，汤成了棕色"
    assert Colors.brothOf(STEW[0], STEW[1], STEW[2], BOWL) == 0xFC3B00, "去掉碗自己的颜色，剩下汤的红"
    assert Colors.brothOf(STEW[0], STEW[1], STEW[2]) == 0xB86E12


def testWhenTheDishDoesNotDrawTheContainerOnlyTheTopRowsCount():
    assert Colors.isGreen(mainOf(SALAD)), "整个图标：下面三整行绿叶多"
    assert Colors.brothOf(SALAD[0], SALAD[1], SALAD[2], BOWL) == 0xFC3B00, "容器的颜色一个都没画：只看上面 60% 的行（8 * 0.6 = 4.8，第 0..4 行）"
    assert mainOf(SALAD, Colors.BOWL_TOP) == 0xFC3B00
    assert mainOf(SALAD, 0.0) == Colors.FALLBACK, "一行都不看"


def testRowsLimitIsFloat32():
    assert Colors.BOWL_TOP == Colors.f32(0.6) and Colors.BOWL_TOP != 0.6


def testTheLiquidIsTheCommonestColourWhereTheEmptyContainerDiffers():
    assert Colors.liquidAt(MILK, BOTTLE) == (2, 3) and Colors.liquidColor(MILK, BOTTLE) == 0xF5F5F5
    assert Colors.liquidAt(MILK) == (2, 0) and Colors.liquidColor(MILK) == 0x141414, "没有容器：全图里票最多的颜色（描边的黑 21 个，浅蓝 14，白 16）"
    nothing = art(["wwww"] * 4)
    assert Colors.liquidAt(nothing, nothing) == (2, 2), "一个不一样的都没有：图标正中"
    assert Colors.liquidAt(art(["...", "..."]), None) == (1, 1), "全透明也是正中"
    assert Colors.liquidAt(MILK, art(["wwww"] * 4)) == Colors.liquidAt(MILK), "大小不同的容器图标不比较"


def testTiedColoursFollowJavasHashMapOrder():
    # 票数全并列：谁赢取决于 HashMap 的遍历顺序（merge 把新结点放桶头、扩容在每次调用之前）。13 种以上颜色就扩容成 32 个桶
    for name in ("ties2", "ties5", "ties12", "ties13", "ties14", "ties30", "ties30Bottle"):
        meal, container = CASES[name]
        assert Colors.liquidAt(meal, container) == EXPECTED[name][3:], name


def testHashOrderPutsNewNodesAtTheBucketHeadAndGrowsOnTheNextCall():
    base = 0xFF000000
    # 0xFF0000jj 的桶号是 jj & (桶数 - 1)；jj = 1 和 17 在 16 个桶里同桶，merge 把后来的放在桶头
    assert Colors._hashOrder([base | 1, base | 17]) == [base | 17, base | 1]
    twelve = [base | j for j in range(12)]
    # 第十三个键（17）放进去之后只要没有下一次调用，表还是 16 个桶：17 在 1 号桶的桶头
    assert Colors._hashOrder(twelve + [base | 17]) == [base | 0, base | 17] + [base | j for j in range(1, 12)]
    # 再有一次 merge（哪怕是已有的键）就先扩成 32 个桶：17 排到 11 之后
    assert Colors._hashOrder(twelve + [base | 17, base | 0]) == twelve + [base | 17]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
