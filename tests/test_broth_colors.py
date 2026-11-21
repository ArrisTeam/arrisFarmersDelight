# -*- coding: utf-8 -*-
# runner: py3
"""汤色 / 碎料色 / 倒进锅里的液体色表（tools/gen_broth_colors.py 按贴图生成的 Shared/Data/BrothColors.py）：形状对、每道厨锅菜和每件配料都有、颜色合理、和贴图一致。

取色规则本身（12 份色相、容器颜色、60% 行、float32……）在 test_pot_colors.py 里按 JDK 的结果钉死。
"""
from __future__ import print_function

import glob
import os
import subprocess
import sys
import tempfile

import fdtest

sys.path.insert(0, os.path.join(fdtest.ROOT, "tools"))
import gen_food_colors as Food  # noqa: E402

Table = fdtest.load("Shared.Data.BrothColors")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes").CookingPotRecipeList
Colors = fdtest.load("Shared.Rules.HandsOn.PotColors")
Sunk = fdtest.load("Shared.Data.PotSunk")
Cuts = fdtest.load("Shared.Data.Cutting").CuttingBoardDict
TOOL = os.path.join(fdtest.ROOT, "tools", "gen_broth_colors.py")
GAME = "D:/MCStudioDownload/game/MinecraftPE_Netease"      # 本机的游戏目录：每个版本一个目录，升级后旧版本的会被删掉


def channels(rgb):
    return (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF


def results():
    found = []
    for recipe in Recipes:
        if recipe["CookResult"][0] not in found:
            found.append(recipe["CookResult"][0])
    return found


def ingredients():
    return sorted(set(name for recipe in Recipes for variant in recipe["Recipe"] for name, _aux in variant))


def testEveryColourIsAnRgbInteger():
    for table in (Table.BrothColors, Table.MainColors, Table.PouredColors):
        assert table and all(isinstance(value, int) and 0 <= value <= 0xFFFFFF for value in table.values())
    assert all(isinstance(raw, str) and isinstance(cooked, str) for raw, cooked in Table.CookedForms.items())


def testTheConstantsAreJavas():
    assert Table.FALLBACK == 0xB0A070 == Colors.FALLBACK, "FoodColors.FALLBACK"
    assert Table.RAW_EGG == 0xF2DC9A == Colors.EGG, "FoodColors.EGG：生蛋搅进去"
    assert Table.PouredColors["minecraft:egg"] == Table.RAW_EGG


def testEveryCookingPotDishHasABrothColour():
    assert len(results()) >= 20
    assert [name for name in results() if name not in Table.BrothColors] == []
    assert sorted(Table.BrothColors) == sorted(results()), "表里不留多余的菜"


def testEveryIngredientHasAMainColourAndSoDoesWhatItCooksInto():
    assert [name for name in ingredients() if name not in Table.MainColors] == []
    for raw, cooked in Table.CookedForms.items():
        assert raw in ingredients(), raw
        assert cooked in Table.MainColors, "碎料按熟的颜色：%s -> %s" % (raw, cooked)
    for name in ("minecraft:beef", "minecraft:potato", "minecraft:rabbit", "arris:minced_beef", "arris:wheat_dough", "minecraft:egg"):
        assert name in Table.CookedForms, name


def testEveryItemTheBoardCutsHasAMainColourForItsDust():
    """砧板切东西飞出的碎屑按被切的东西自己图标的主色染（BoardBehavior.chopped 的 FoodColors.main(worked)）：205 件原料（食物、原木、石头、花、船、门、皮甲……）
    每件都有一项。原来只有 31 件有颜色，174 件落到按工具定的颜色（所有削皮的原木同一个棕色、所有劈的木制品同一个木色）。"""
    names = sorted(set(name for name, _aux in Cuts))
    assert len(names) >= 205, "整张砧板配方表都读到了"
    assert [name for name in names if name not in Table.MainColors] == []
    for name in names:
        assert 0 <= Table.MainColors[name] <= 0xFFFFFF, name
    assert len(set(Table.MainColors[name] for name in names)) > 100, "不是同一个颜色刷了一遍：每种木头、每朵花各有各的"
    red, green, blue = channels(Table.MainColors["minecraft:poppy"])
    assert red > 200 and green < 40 and blue < 40, "虞美人是红的"
    red, green, blue = channels(Table.MainColors["minecraft:blue_orchid"])
    assert blue > red and blue > 200, "蓝色的兰花"
    red, green, blue = channels(Table.MainColors["minecraft:warped_stem"])
    assert green > red and blue > red, "诡异菌柄是青绿的（以前所有削皮的原木都是同一个棕色 0x6B5034）"
    red, green, blue = channels(Table.MainColors["minecraft:crimson_stem"])
    assert red > green and red > blue, "绯红菌柄是红的"
    assert Table.MainColors["minecraft:cherry_log"] != Table.MainColors["minecraft:spruce_log"], "每种木头各有各的颜色"
    assert Table.MainColors["arris:red_mushroom_colony"] != Table.MainColors["arris:brown_mushroom_colony"]


def testThePowdersThatDissolveHaveAMainColourForTheirGrains():
    # 抖进锅里的粉（糖、可可豆、荧石粉、烈焰粉……）落下来的粒子按碎料色染（PotHands.start 的 MainColors）；倒的（蜂蜜）用液色
    for name, _aux in Sunk.DISSOLVES:
        assert name in Table.MainColors or name in Table.PouredColors, "抖下来的粉粒没有颜色：" + name
    for name in ("minecraft:blaze_powder", "minecraft:glowstone_dust", "minecraft:glow_ink_sac"):
        assert name in Table.MainColors, name


def testThePouredLiquidsHaveTheirOwnColour():
    for name in ("minecraft:milk_bucket", "arris:milk_bottle", "arris:tomato_sauce", "minecraft:water_bucket", "minecraft:honey_bottle"):
        assert name in Table.PouredColors, name
    assert min(channels(Table.PouredColors["minecraft:milk_bucket"])) >= 0xF0, "牛奶是白的，不是桶的灰"
    red, green, blue = channels(Table.PouredColors["minecraft:water_bucket"])
    assert blue > red and blue > green, "水是蓝的"
    red, green, blue = channels(Table.PouredColors["arris:tomato_sauce"])
    assert red > green and red > blue, "番茄酱是红的，不是碗的木色"


def testTheSoupsTakeTheirDishesColoursNotTheBowls():
    red, green, blue = channels(Table.BrothColors["arris:tomato_sauce"])
    assert red > 150 and red > green + 100 and red > blue + 100, "番茄酱是红的"
    red, green, blue = channels(Table.BrothColors["arris:hot_cocoa"])
    assert red > green > blue or red > blue, "可可偏棕红"
    red, green, blue = channels(Table.BrothColors["arris:pumpkin_soup"])
    assert red > 200 and red > green > blue, "南瓜汤是橙的"
    for name in results():
        assert Table.BrothColors[name] != 0, name


def testGreensCutIntoLeavesAndTheRestIntoCoins():
    assert Colors.isGreen(Table.MainColors["arris:cabbage"]) and Colors.isGreen(Table.MainColors["arris:cabbage_leaf"])
    assert not Colors.isGreen(Table.MainColors["minecraft:carrot"]) and not Colors.isGreen(Table.MainColors["arris:tomato"])


def _gameVersions():
    """本机游戏目录里带原版资源包、目录名是版本号的那几个版本。"""
    found = []
    for path in glob.glob(GAME + "/*/data/resource_packs/vanilla"):
        name = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(path))))
        if all(part.isdigit() for part in name.split(".")):
            found.append(name)
    return found


def testTheTableMatchesTheTextures():
    """工具缺省拿本机版本号最高的原版资源包比（原来写死 3.10.0.448891：游戏升级后那个目录删了，这条就悄悄只比本包的物品）。
    没有游戏目录的机器上（别的机器、CI）只比读得到的：本包的物品；原版的、盛在原版容器里的沿用现有的值，不报错。"""
    versions = _gameVersions()
    if not versions:
        print("本机没有原版资源包：只比本包的物品")
    run = subprocess.run([sys.executable, "-B", TOOL, "--check"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         env=dict(os.environ, PYTHONIOENCODING="utf-8"), encoding="utf-8")
    assert run.returncode == 0, "贴图变了：py -3 tools/gen_broth_colors.py 重新生成 Shared/Data/BrothColors.py\n" + run.stdout
    assert ("原版资源包不在" in run.stdout) == (not versions), "本机有 %s，原版物品却没比：%s" % (versions, run.stdout)


def testTheNewestVanillaPackIsPickedByVersionNumber():
    """缺省的原版资源包：游戏目录下目录名是版本号、带 data/resource_packs/vanilla 的里面版本号最高的一个（逐段按数字比，3.10 比 3.9 新；
    PCLauncher_x64 这样不是版本号的不算，哪怕里面也有一份）；游戏目录不在返回 None。"""
    with tempfile.TemporaryDirectory() as game:
        for name, pack in (("3.9.0.401155", True), ("3.10.0.436581", True), ("3.10.0.467018", True), ("3.11.0.1", False), ("PCLauncher_x64", True)):
            os.makedirs(os.path.join(game, name, "data", "resource_packs", "vanilla" if pack else "other"))
        newest = Food.newestVanilla(game)
        assert newest == os.path.join(game, "3.10.0.467018", "data", "resource_packs", "vanilla").replace("\\", "/"), newest
        assert Food.newestVanilla(os.path.join(game, "nowhere")) is None
    assert Food.VANILLA_DEFAULT == Food.newestVanilla(), "工具的缺省就是本机最新的那一份（没有是 None）"


def testTheGeneratorStillRunsWithoutTheVanillaPack():
    nowhere = os.path.join(fdtest.ROOT, "no-such-vanilla-pack")
    assert subprocess.call([sys.executable, "-B", TOOL, "--check", "--vanilla", nowhere]) == 0, "没有原版资源包：本包的物品照常重算，其余沿用现有的值"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
