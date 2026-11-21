# -*- coding: utf-8 -*-
# runner: both
"""煎锅 / 炉灶上煎着的一件朝上那面的熟色（Shared/Rules/FryingTint、Shared/Data/Fishes）：JE 的 KitchenLooks.fryingTint 用哪两张主色、
哪些算肉和鱼、表里没有颜色的不染，和基岩版用来近似"整件乘上 c"的那一层粒子的 (颜色 q, 不透明度 a)。
fryingTint / mix 本身的算法在 test_handson_from_player.py 里用造出来的颜色钉着，这里只用表里真的颜色。"""
from __future__ import print_function

import random

import fdtest

T = fdtest.load("Shared.Rules.FryingTint")
K = fdtest.load("Shared.Rules.HandsOn.KitchenLooks")
Main = fdtest.load("Shared.Data.BrothColors").MainColors
Sample = fdtest.load("Shared.Data.FoodColors").FoodColors
Cooking = fdtest.load("Shared.Data.Cooking")
Fishes = fdtest.load("Shared.Data.Fishes")
BEEF, COOKED_BEEF = "minecraft:beef", "minecraft:cooked_beef"


def near(a, b, eps=1e-9):
    return abs(a - b) < eps


def channels(argb):
    return [(argb >> shift) & 0xFF for shift in (16, 8, 0)]


def testRawBeefHalfDoneOnTopIsJesTintWithTheIconsMainColours():
    """生牛肉（主色 F11B0F）、熟牛肉（B84E26）：比例 R 184/241、G B 封顶 1 -> 目标 FFC3FFFF；牛肉是肉，往焦色 B8875C 走 4 成 -> FFBFCFBE；
    朝上那面煎到一半：从白往它走 0.5 x 0.7 -> FFE9EEE8。"""
    assert (Main[BEEF], Main[COOKED_BEEF]) == (0xF11B0F, 0xB84E26)
    assert T.tintOf(BEEF, COOKED_BEEF, 0.5) == 0xFFE9EEE8
    assert T.tintOf(BEEF, COOKED_BEEF, 0.25) == 0xFFF4F7F4
    assert T.tintOf(BEEF, COOKED_BEEF, 0.5) == K.fryingTint(0xF11B0F, 0xB84E26, False, True, 0.5)


def testATopNotFriedAtAllOrDoneIsNotTinted():
    """朝上那面一点没煎（0，没画过的 -1 也算 0）：白；熟了（1）换成熟的图，也是白（JE：up >= 1 返回白）。"""
    for up in (0.0, -1.0, 1.0, 1.5):
        assert T.tintOf(BEEF, COOKED_BEEF, up) == T.WHITE == 0xFFFFFFFF, up
        assert T.overlay(T.tintOf(BEEF, COOKED_BEEF, up)) is None, "白：什么都不画"


def testTheColoursAreTheIconsMainColoursNotTheAveragedOnes():
    """JE 的 fryingTint 用 FoodColors.main（色相分 12 份取最大一族），不是砧板碎屑和汤色用的 FoodColors.sample（按鲜艳度加权平均，Shared/Data/FoodColors）。"""
    main = K.fryingTint(Main[BEEF], Main[COOKED_BEEF], False, True, 0.5)
    averaged = K.fryingTint(Sample[BEEF], Sample[COOKED_BEEF], False, True, 0.5)
    assert T.tintOf(BEEF, COOKED_BEEF, 0.5) == main != averaged


def testEverythingThePanAndTheGrillCookHasBothColours():
    """营火配方（煎锅、炉灶、手持煎锅同一张）里的每件和它煎熟的样子都在 MainColors 里（tools/gen_broth_colors.py 的 fryingNames）：原来缺海带。"""
    missing = [name for raw, cooked in Cooking.CanCookedFoodDict.items() for name in (raw, cooked) if name not in Main]
    assert missing == [], missing
    for raw, cooked in Cooking.CanCookedFoodDict.items():
        if raw not in Cooking.OneSidedList:
            assert T.tintOf(raw, cooked, 0.5) is not None, raw
    assert T.tintOf("minecraft:kelp", "minecraft:dried_kelp", 0.5) != T.WHITE


def testFoodADownstreamModAddedWithoutColoursIsNotTinted():
    """下游模组经联动契约往 CanCookedFoodDict 里追加的东西：JE 运行时从图标现算颜色，这边没有它的贴图，表里没有——不染（None，不是白）。"""
    assert T.tintOf("othermod:raw_steak", "othermod:steak", 0.5) is None
    assert T.tintOf(BEEF, "othermod:steak", 0.5) is None and T.tintOf("othermod:raw_steak", COOKED_BEEF, 0.5) is None
    assert T.overlay(None) is None
    assert T.tintOf("othermod:raw_steak", "othermod:steak", 1.0) == T.WHITE, "熟了本来就不染"


def testMeatAndFishSearButSlicesPotatoesAndKelpDoNot():
    """JE：food.isMeat() || raw.is(ItemTags.FISHES)。isMeat 是 PotPieceTraits.MEAT（原版和农夫乐事带 meat() 的），
    鱼是原版标签 minecraft:fishes（1.20.1 数据包：生熟鳕鱼、生熟鲑鱼、河豚、热带鱼）；农夫乐事的鳕鱼片、鲑鱼片两样都不是（FoodValues 里没有 meat()，
    也不在 minecraft:fishes 里，在 forge:raw_fishes 里）。"""
    assert Fishes.FISHES == frozenset(("minecraft:cod", "minecraft:cooked_cod", "minecraft:salmon", "minecraft:cooked_salmon",
                                       "minecraft:pufferfish", "minecraft:tropical_fish"))
    seared = ("minecraft:beef", "minecraft:chicken", "minecraft:mutton", "minecraft:porkchop", "minecraft:rabbit", "minecraft:cod",
              "minecraft:salmon", "arris:minced_beef", "arris:chicken_cuts", "arris:bacon", "arris:mutton_chops")
    plain = ("minecraft:potato", "minecraft:kelp", "arris:cod_slice", "arris:salmon_slice", "minecraft:egg")
    assert sorted(raw for raw in Cooking.CanCookedFoodDict if T.sears(raw)) == sorted(seared)
    assert not [raw for raw in plain if T.sears(raw)]
    cod, slice_ = Main["minecraft:cod"], Main["arris:cod_slice"]
    assert T.tintOf("minecraft:cod", "minecraft:cooked_cod", 0.5) == K.fryingTint(cod, Main["minecraft:cooked_cod"], False, True, 0.5)
    assert T.tintOf("arris:cod_slice", "arris:cooked_cod_slice", 0.5) == K.fryingTint(slice_, Main["arris:cooked_cod_slice"], False, False, 0.5)


def testTheOverlayOfHalfDoneBeefDarkensByNinePercent():
    """c = (233, 238, 232) / 255：最暗的通道 232 -> 不透明度 a = 1 - 232/255 = 23/255；颜色 q = (c - 232/255) / a = (1/23, 6/23, 0)。"""
    r, g, b, a = T.overlay(0xFFE9EEE8)
    assert near(a, 23.0 / 255.0) and near(r, 1.0 / 23.0) and near(g, 6.0 / 23.0) and b == 0.0
    r, g, b, a = T.overlay(0xFFF4F7F4)
    assert near(a, 11.0 / 255.0) and r == 0.0 and near(g, 3.0 / 11.0) and b == 0.0, "煎到 1/4：浅一半"


def testTheOverlayRebuildsTheTintAndUsesTheLeastAlphaThatCan():
    """叠上去画出来 = (1 - a)·底下 + a·q·底下：要等于 c·底下，(1 - a) + a·q = c，每个通道；q 都在 0..1 里，最暗的通道 q = 0（a 再小就不够暗）。
    alpha 只看 RGB（JE 的 alpha 不是 FF 的只有蛋，蛋是 EggLook 的显示物品，不走这里）。"""
    rand = random.Random(7)
    for _ in range(300):
        tint = 0xFF000000 | rand.randint(0, 0xFFFFFF)
        r, g, b, a = T.overlay(tint) or (0.0, 0.0, 0.0, 0.0)
        c = [value / 255.0 for value in channels(tint)]
        if min(c) >= 1.0:
            continue
        for want, q in zip(c, (r, g, b)):
            assert -1e-12 <= q <= 1.0 + 1e-12 and near((1.0 - a) + a * q, want), (hex(tint), want, q, a)
        assert near(1.0 - a, min(c)) and min((r, g, b)) == 0.0
    assert T.overlay(0xFFFFFFFF) is None and T.overlay(0x80FFFFFF) is None, "白（不管 alpha）：不画"
    assert T.overlay(0xFF808080)[:3] == (0.0, 0.0, 0.0), "灰：一层半透明的黑"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
