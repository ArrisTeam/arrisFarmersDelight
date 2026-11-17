# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里厨锅的烹饪时间倍率 cooking_pot_time（Server/HandCooking + Shared/Rules/HandsOn/PotCooking + StationBooks）：
锅的每种煮法都按它（搅着的整批、放着不管的、漏斗放进去的、农夫乐事自己的界面读的进度）、夹进 0.1 ~ 10、厨锅站点关了算 1.0、食谱书写的是同一个时间。
JE 的对照是 PotTests.theCookingTimeFollowsTheConfig：1.0 是配方自己的时间，2.0 是它的两倍，总时长是锅的这一步数到的那个，
徽章、农夫乐事自己的界面读的都是它。引擎是 potfake 里的假的。"""
from __future__ import print_function

import fdtest
import potkit as K
from optkit import Config
from potkit import POT, TOMATO, fake

HandCooking = K.HandCooking
PotCooking = HandCooking.PotCooking
Books = fdtest.load("Shared.Rules.StationBooks")
PotMenu = fdtest.load("Shared.Menus.CookingPot")
SAUCE_SECONDS = 5.0           # 番茄酱的配方时间（JE 的 CookTime 100 刻）


def _hand():
    return HandCooking.handOf(0, POT)


def _tomatoes(each):
    fake.setContainer(POT, 0, TOMATO, each)
    fake.setContainer(POT, 1, TOMATO, each)


def testTheTotalIsTheRecipesTimeTimesTheConfig():
    # PotTests.theCookingTimeFollowsTheConfig：1.0 是配方自己的，2.0 是它的两倍；站点关了、越界的也照 HandsOnConfig
    expected = ((1.0, 5.0), (2.0, 10.0), (0.5, 2.5), (10.0, 50.0), (100.0, 50.0), (0.01, 0.5), ("2", 10.0), ("bad", 5.0), (None, 5.0))
    for value, total in expected:
        manager, data = K.setup()
        with Config(cooking_pot_time=value):
            _tomatoes(8)
            K.alone(0.2)
            assert _hand().total == total and data["timerTotal"] == total, (value, _hand().total, data["timerTotal"])


def testAPotWhoseStationIsOffCooksInTheRecipesOwnTime():
    # HandsOnConfig.cookingPotTime()：cookingPot ? cookingPotTime : 1.0（站点是配置还缺省时登记的，之后才把配置改成关）
    manager, data = K.setup()
    with Config(cooking_pot=False, cooking_pot_time=4.0):
        _tomatoes(8)
        K.alone(0.2)
        assert _hand().total == SAUCE_SECONDS
        K.alone(5.5)
        assert K.preview()["count"] == 1, "一份 5 秒，不是 20 秒"


def testFarmersDelightsOwnMenuReadsTheScaledTotalAndTheArrowFollowsIt():
    # 经典界面画箭头读的是方块实体数据里的 timer / timerTotal：timerTotal 是倍率之后的总时长
    for times in (1.0, 2.0):
        manager, data = K.setup()
        with Config(cooking_pot_time=times):
            _tomatoes(8)
            K.alone(0.2)
            K.alone(SAUCE_SECONDS * times / 2.0 - 0.2)
            state = PotMenu.stateFrom(data, SAUCE_SECONDS)
            assert data["timerTotal"] == SAUCE_SECONDS * times, times
            assert abs(state["progress"] - 0.5) < 0.06, (times, state["progress"])
            assert K.preview() == {}, "一半的时候还没出"


def testFoodLeftAloneOrBroughtByAHopperTakesTheScaledTime():
    for times, seconds, servings in ((1.0, 20.2, 4), (2.0, 20.2, 2), (0.5, 21.0, 8)):      # 一份 5 / 10 / 2.5 秒（步长 0.2：2.6）
        manager, data = K.setup()
        with Config(cooking_pot_time=times):
            _tomatoes(8)                               # 漏斗放进来的：FD 原样一份一份煮
            K.alone(seconds)
            assert K.preview()["count"] == servings, (times, K.preview())


def testTheBatchTheCookStirsTakesTheScaledTotalAtTheBatchSpeed():
    # 整批：一份的时长 x 倍率，再按批量速度（1.5 / sqrt(份数)）走；8 份 5 秒的配方，缺省 9.4 秒出，倍率 2 是 18.9 秒
    for times, finishes in ((1.0, 9.4), (2.0, 18.9)):
        manager, data = K.setup()
        with Config(cooking_pot_time=times):
            K.feed(manager, TOMATO, 16)
            K.run(manager, finishes - 1.5, stir=True)
            assert K.preview() == {}, (times, "还没到")
            K.run(manager, 3.0, stir=True)
            assert K.preview()["count"] == 8, (times, K.preview())


def testFoodThatCameInByHandAndWasLeftCooksTheScaledTimeToo():
    manager, data = K.setup()
    with Config(cooking_pot_time=2.0):
        K.feed(manager, TOMATO, 4)
        manager.close("a")
        K.alone(2.0 + 10.0 + 0.5)                     # 走开 2 秒后按 FD 原样煮：一份 10 秒
        assert K.preview()["count"] == 1 and _hand().total == 10.0


def testTheRecipeBookWritesTheSameTimeAsThePotTakes():
    # PotBook：Math.round(cookTime * 倍率 / 20 / PotLogic.speed(1))；站点里一份是配方时间 x 倍率 / 1.5
    recipes = dict((page["item"]["newItemName"], page) for page in Books.potPages())
    sauce, dumplings = recipes["arris:tomato_sauce"], recipes["arris:dumplings"]
    assert (sauce["note"], dumplings["note"]) == ("3 秒", "7 秒"), "缺省：5 / 1.5 = 3.3，10 / 1.5 = 6.7"
    for times, sauceNote, dumplingNote in ((2.0, "7 秒", "13 秒"), (0.5, "2 秒", "3 秒"), (10.0, "33 秒", "67 秒"), (0.1, "0 秒", "1 秒")):
        with Config(cooking_pot_time=times):
            pages = dict((page["item"]["newItemName"], page) for page in Books.potPages())
            assert (pages["arris:tomato_sauce"]["note"], pages["arris:dumplings"]["note"]) == (sauceNote, dumplingNote), times
    with Config(cooking_pot_time=3.0, cooking_pot=False):
        pages = dict((page["item"]["newItemName"], page) for page in Books.potPages())
        assert pages["arris:tomato_sauce"]["note"] == "3 秒", "站点关了书也不乘（反正这时书也不挂）"


def testTheBookRoundsHalvesUpLikeJavaMathRound():
    # 5 秒 x 0.75 / 1.5 = 2.5：Math.round 进到 3（Python 3 的 round 是 2，Python 2 是 3）
    with Config(cooking_pot_time=0.75):
        pages = dict((page["item"]["newItemName"], page) for page in Books.potPages())
        assert pages["arris:tomato_sauce"]["note"] == "3 秒"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
