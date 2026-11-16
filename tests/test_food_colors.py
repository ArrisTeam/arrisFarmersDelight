# -*- coding: utf-8 -*-
# runner: py3
"""物品颜色表（tools/gen_food_colors.py 按贴图生成的 Shared/Data/FoodColors.py）：形状对、常用食材都有、和贴图一致。"""
from __future__ import print_function

import os
import subprocess
import sys

import fdtest

Colors = fdtest.load("Shared.Data.FoodColors").FoodColors
Recipes = fdtest.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
Sunk = fdtest.load("Shared.Data.PotSunk")
Poured = fdtest.load("Shared.Data.BrothColors").PouredColors
TOOL = os.path.join(fdtest.ROOT, "tools", "gen_food_colors.py")
VANILLA = "D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.448891/data/resource_packs/vanilla"


def testEveryColourIsAnRgbInteger():
    assert Colors and all(isinstance(value, int) and 0 <= value <= 0xFFFFFF for value in Colors.values())


def testTheIngredientsCutOnTheBoardHaveAColour():
    for name in ("arris:tomato", "arris:cabbage", "arris:ham", "arris:wheat_dough", "minecraft:beef", "minecraft:porkchop",
                 "minecraft:salmon", "minecraft:pumpkin", "minecraft:cake"):
        assert name in Colors, name
    red, green, _blue = (Colors["arris:tomato"] >> 16) & 0xFF, (Colors["arris:tomato"] >> 8) & 0xFF, Colors["arris:tomato"] & 0xFF
    assert red > green, "番茄是红的"


def testEveryThingThatCanGoInAPotHasAColourOrIsAPouredLiquid():
    # 锅里还没凑成菜时汤色取各料的颜色（HoD 的 FoodColors.of）：倒的液体用液色（PouredColors），其余读图标，不能有落到兜底色的
    names = set(name for recipe in Recipes for variant in recipe["Recipe"] for name, _aux in variant)
    names.update(name for name, _aux in Sunk.SUNK)
    assert len(names) >= 45
    for name in sorted(names):
        assert name in Colors or (name, 0) in Sunk.POURED and name in Poured, "没有颜色，会落到兜底色：" + name


def testTheTableMatchesTheTextures():
    if not os.path.isdir(VANILLA):
        print("跳过：本机没有原版资源包", VANILLA)
        return
    code = subprocess.call([sys.executable, "-B", TOOL, "--check", "--vanilla", VANILLA])
    assert code == 0, "贴图变了：py -3 tools/gen_food_colors.py 重新生成 Shared/Data/FoodColors.py"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
