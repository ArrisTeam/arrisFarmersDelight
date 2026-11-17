# -*- coding: utf-8 -*-
# runner: both
"""HoD 的配置表和它的读法（Shared/Data/HandsOnConfig.py + Shared/Rules/HandsOnOptions.py）：随包带的值等于 JE 的缺省、
读法照 HandsOnConfig.read / readTime、派生规则（站点关了它的倍率算 1.0、没有砧板站点不拿掉工作台合成、没有厨锅站点没有"要搅"）、scaled。
期望值抄自 HandsOnConfig.java（行号写在各处），不依赖 .refs。"""
from __future__ import print_function

import fdtest
from optkit import Config, MISSING, Options, Table

Contract = fdtest.load("Api.LegacyModAttr")

# HandsOnConfig.java:58-61、71-76：这几项在 JE 里的初值
JE_DEFAULTS = {"cooking_pot": True, "cutting_board": True, "skillet": True, "stove": True, "remove_crafting_recipes": True,
               "stirring_required": True, "recipe_book": True, "cooking_pot_time": 1.0, "skillet_time": 1.0, "stove_time": 1.0}
# JE 里有、本包没有对应方块的键（HandsOnConfig.java:62-70、77）：这里不收
OTHER_MODS = ("keg", "kettle", "grill", "basin", "cuisine_board", "youkai_pots", "youkai_steamer", "youkai_tank", "youkai_hints",
              "kettle_time")
STATIONS = ("cooking_pot", "cutting_board", "skillet", "stove")


def testTheShippedTableHoldsExactlyTheKeysOfThisPortWithJEsDefaults():
    assert Table.CONFIG == JE_DEFAULTS, "随包带的表就是 JE 的缺省：改了表的包就不是缺省了"
    assert Options.DEFAULTS == JE_DEFAULTS, "读错了兜回的缺省也是 JE 的"
    for key in OTHER_MODS:
        assert key not in Table.CONFIG and key not in Options.DEFAULTS, key
    for key, value in JE_DEFAULTS.items():
        assert type(Table.CONFIG[key]) is type(value), "%s 的类型：开关是布尔，倍率是小数" % key


def testNothingOfTheConfigGoesThroughTheLegacyContract():
    for name in ("CONFIG", "HandsOnConfig", "DEFAULTS", "HandsOnOptions") + tuple(JE_DEFAULTS):
        assert name not in Contract._TARGETS, "联动契约白名单不动：%s" % name


def testTheShippedTableGivesJEsDefaultsThroughEveryAccessor():
    assert Options.cookingPot() and Options.cuttingBoard() and Options.skillet() and Options.stove()
    assert Options.removeCraftingRecipes() and Options.stirringRequired() and Options.recipeBook()
    assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (1.0, 1.0, 1.0)


# ---------------------------------------------------------------- 读法

def testFlagsReadLikeHandsOnConfigRead():
    # HandsOnConfig.java:130-139：trim + toLowerCase，true / yes / on / 1 真，false / no / off / 0 假，别的是缺省
    for text in ("true", "yes", "on", "1", "TRUE", "Yes", " On ", "\t1\n"):
        assert Options.readFlag(text, False) is True and Options.readFlag(text, True) is True, repr(text)
    for text in ("false", "no", "off", "0", "FALSE", " No ", "Off"):
        assert Options.readFlag(text, True) is False and Options.readFlag(text, False) is False, repr(text)
    for text in ("", "maybe", "2", "truee", "y", "enabled", "1.0", "-1"):
        assert Options.readFlag(text, True) is True and Options.readFlag(text, False) is False, "别的当缺省：%r" % text
    assert Options.readFlag(True, False) is True and Options.readFlag(False, True) is False, "Python 的布尔直接用"
    assert Options.readFlag(1, False) is True and Options.readFlag(0, True) is False, "整数 1 / 0 当 \"1\" / \"0\""
    for odd in (2, -1, 1.0, 0.0, None, [], {}, ("true",), object()):
        assert Options.readFlag(odd, True) is True and Options.readFlag(odd, False) is False, "类型不对当缺省：%r" % (odd,)


def testTimesReadLikeHandsOnConfigReadTime():
    # HandsOnConfig.java:141-154：数（逗号当小数点）夹进 0.1 ~ 10；读不成数、不是有限的数是缺省
    cases = [(1.0, 1.0), (2, 2.0), (2.5, 2.5), ("2", 2.0), ("2.5", 2.5), ("1,5", 1.5), (" 3 ", 3.0), ("0.5", 0.5),
             (0.1, 0.1), (10, 10.0), (10.0, 10.0),
             (0.01, 0.1), (0, 0.1), (-5, 0.1), ("-3", 0.1), ("0.0", 0.1), (50, 10.0), (100.0, 10.0), ("1e9", 10.0)]
    for value, expected in cases:
        assert Options.readTime(value, 1.0) == expected and isinstance(Options.readTime(value, 1.0), float), repr(value)
    nan, inf = float("nan"), float("inf")
    for odd in ("", "fast", "abc", "NaN", "Infinity", "-Infinity", "1.2.3", "2x", None, True, False, [], {}, nan, inf, -inf, 1e39, -1e39,
                10 ** 400, "1e39", "1e400"):
        assert Options.readTime(odd, 1.0) == 1.0, "读不成有限的数当缺省：%r" % (odd,)
    assert Options.readTime("abc", 3.0) == 3.0, "缺省是调用方给的（这里是 JE 的 1.0）"


def testATableWithBadValuesFallsBackToTheDefaultsKeyByKey():
    with Config(cooking_pot="maybe", skillet=MISSING, stove=None, cutting_board=[], recipe_book=2, remove_crafting_recipes="no",
                cooking_pot_time="fast", skillet_time=MISSING, stove_time=99):
        assert Options.cookingPot() is True and Options.skillet() is True and Options.stove() is True
        assert Options.cuttingBoard() is True and Options.recipeBook() is True, "别的类型、缺键都当缺省"
        assert Options.removeCraftingRecipes() is False, "写得对的照写（\"no\"）"
        assert Options.cookingPotTime() == 1.0 and Options.skilletTime() == 1.0, "读不成数、缺键：1.0"
        assert Options.stoveTime() == 10.0, "越界夹进范围"
    assert Table.CONFIG == JE_DEFAULTS, "with 块出来表放回原样"


# ---------------------------------------------------------------- 派生规则

def testTheAccessorsReadTheTableAtTheTimeOfTheCall():
    accessors = {"cooking_pot": Options.cookingPot, "cutting_board": Options.cuttingBoard, "skillet": Options.skillet,
                 "stove": Options.stove, "recipe_book": Options.recipeBook}
    for key, accessor in accessors.items():
        assert accessor() is True
        with Config(**{key: False}):
            assert accessor() is False, key
        assert accessor() is True, "放回原样"


def testAStationTurnedOffTakesItsCookingTimeBackToOne():
    # HandsOnConfig.java:235-247：cookingPot ? cookingPotTime : 1.0（煎锅、炉灶同）
    with Config(cooking_pot_time=2.0, skillet_time=3.0, stove_time=0.5):
        assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (2.0, 3.0, 0.5)
        with Config(cooking_pot=False):
            assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (1.0, 3.0, 0.5), "只有它自己的站点关了才算 1"
        with Config(skillet=False):
            assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (2.0, 1.0, 0.5)
        with Config(stove=False):
            assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (2.0, 3.0, 1.0)
        with Config(cutting_board=False):
            assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (2.0, 3.0, 0.5), "砧板不管倍率"
        with Config(cooking_pot=False, skillet=False, stove=False):
            assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (1.0, 1.0, 1.0)


def testTheTimesAreClampedAfterTheStationSwitch():
    with Config(cooking_pot_time=0.0, skillet_time=1000, stove_time="2,5"):
        assert (Options.cookingPotTime(), Options.skilletTime(), Options.stoveTime()) == (0.1, 10.0, 2.5)


def testDishesLeaveTheCraftingGridOnlyWhereTheBoardCanMakeThem():
    # HandsOnConfig.java:222-225：removeCraftingRecipes && cuttingBoard
    assert Options.removeCraftingRecipes() is True
    with Config(remove_crafting_recipes=False):
        assert Options.removeCraftingRecipes() is False, "关了就是不拿掉"
    with Config(cutting_board=False):
        assert Options.removeCraftingRecipes() is False, "没有砧板站点不拿掉：没有地方做这些菜"
    with Config(cutting_board=False, remove_crafting_recipes=False):
        assert Options.removeCraftingRecipes() is False
    with Config(cooking_pot=False, skillet=False, stove=False):
        assert Options.removeCraftingRecipes() is True, "别的站点不管"


def testStirringIsRequiredOnlyWithThePotStation():
    # HandsOnConfig.java:227-229：stirringRequired && cookingPot
    assert Options.stirringRequired() is True
    with Config(stirring_required=False):
        assert Options.stirringRequired() is False
    with Config(cooking_pot=False):
        assert Options.stirringRequired() is False, "没有厨锅站点就没有勺子"
    with Config(cutting_board=False, skillet=False, stove=False):
        assert Options.stirringRequired() is True


def testScaledIsJEsRoundWithAFloorOfOneTick():
    # HandsOnConfig.java:262-264：Math.max(1, Math.round(ticks * times))，Math.round 是 floor(x + 0.5)
    assert Options.scaled(200, 1.0) == 200 and Options.scaled(200, 2.0) == 400 and Options.scaled(200, 0.5) == 100
    assert Options.scaled(120, 1.5) == 180 and Options.scaled(7, 0.5) == 4, "3.5 进到 4（Math.round 半数进位，不是 Python 的 round）"
    assert Options.scaled(5, 0.5) == 3 and Options.scaled(3, 0.5) == 2 and Options.scaled(25, 0.1) == 3
    assert Options.scaled(1, 0.1) == 1 and Options.scaled(4, 0.1) == 1 and Options.scaled(0, 2.0) == 1, "至少一刻"
    assert Options.scaled(600, 10.0) == 6000 and Options.scaled(600, 0.1) == 60


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
