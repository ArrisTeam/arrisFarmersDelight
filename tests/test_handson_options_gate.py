# -*- coding: utf-8 -*-
# runner: both
"""没联动（前置包没装 / 太旧 / 还没判定）时 Hands-On Delight 的配置不生效，农夫乐事走自己原样的时间和玩法：
HandsOnOptions 的每个取值函数在三种没联动的模式里都说 HoD 不在（站点开关假、倍率 1.0），不看 Shared/Data/HandsOnConfig.py 的表；联动了才照表读；
厨锅按配方自己的时间煮、不要搅拌；存档里留着手放的煎锅 / 炉灶（以前装过前置包）交给农夫乐事原样煎 / 烤；从厨锅盛菜不往玩家数据里记 HoD 的"做过几份"。
只用本仓库的东西（假引擎是 fakeengine / skilletkit，不要沉浸式交互前置包的源码）。"""
from __future__ import print_function

import fakeengine
import fdtest
import linkkit as L
import skilletkit
from optkit import Config, Options

world = fakeengine.install()
skilletkit.extend(world)
HandCooking = fdtest.load("Server.HandCooking")
HandFrying = fdtest.load("Server.HandFrying")
HandGrill = fdtest.load("Server.HandGrill")
PotContainer = fdtest.load("Server.Helpers.PotContainer")
PotCooking = fdtest.load("Shared.Rules.HandsOn.PotCooking")
PanStation = fdtest.load("Shared.Rules.PanStation")
GrillStation = fdtest.load("Shared.Rules.GrillStation")
Mode = L.Mode

FLAGS = (("cooking_pot", Options.cookingPot), ("cutting_board", Options.cuttingBoard), ("skillet", Options.skillet), ("stove", Options.stove),
         ("remove_crafting_recipes", Options.removeCraftingRecipes), ("stirring_required", Options.stirringRequired),
         ("recipe_book", Options.recipeBook))
TIMES = (("cooking_pot_time", Options.cookingPotTime), ("skillet_time", Options.skilletTime), ("stove_time", Options.stoveTime))
SLOW = dict(cooking_pot_time=3.0, skillet_time=2.0, stove_time=0.5)       # 表里写着别的倍率
NOT_LINKED = (Mode.PENDING, Mode.OUTDATED, Mode.STANDALONE)
POS = (1, 2, 3)
RICE = {"newItemName": "arris:rice", "newAuxValue": 0, "count": 1}          # 一份 5 秒（配方表的 CookTime，默认是 10）
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}


def testEveryGetterSaysHandsOnDelightIsAbsentWhileNotLinked():
    for mode in NOT_LINKED:
        for config in ({}, SLOW, dict(SLOW, stirring_required=True, recipe_book=True)):
            with L.Modes(mode), Config(**config):
                for name, getter in FLAGS:
                    assert getter() is False, (mode, config, name)
                for name, getter in TIMES:
                    assert getter() == 1.0, (mode, config, name)


def testEveryGetterReadsTheConfigAsBeforeOnceLinked():
    for modes in (dict(both=Mode.LINKED), dict(server=Mode.LINKED), dict(client=Mode.LINKED), dict(server=Mode.LINKED, client=Mode.OUTDATED)):
        with L.Modes(**modes):
            for name, getter in FLAGS:
                assert getter() is True, (modes, name)
            assert [getter() for _, getter in TIMES] == [1.0, 1.0, 1.0]
            with Config(**SLOW):
                assert [getter() for _, getter in TIMES] == [3.0, 2.0, 0.5], modes
            with Config(cooking_pot=False, cutting_board=False, stove_time=4.0):
                assert Options.cookingPot() is False and Options.stirringRequired() is False and Options.cookingPotTime() == 1.0
                assert Options.removeCraftingRecipes() is False and Options.stoveTime() == 4.0, "站点关了的派生规则照旧"


def testTheModeIsReadEveryTimeNotOnce():
    with Config(**SLOW):
        with L.Modes(Mode.STANDALONE):
            assert Options.cookingPotTime() == 1.0
        with L.Modes(Mode.LINKED):
            assert Options.cookingPotTime() == 3.0
        with L.Modes(Mode.PENDING):
            assert Options.cookingPotTime() == 1.0


# ---------------------------------------------------------------- 厨锅：FD 原样的时间

def _pot(byHand=False):
    HandCooking.forget(0, POS)
    PotContainer.maxStackOf = lambda name, aux=0: 64          # 引擎的堆叠上限，这里都是 64
    data = skilletkit.EngineData()
    data["heatEnable"] = True
    hand = HandCooking.handOf(0, POS, data)
    if byHand:
        hand.clock.restore(True, 0.0)                         # 存档里读回来：料是手放的（以前装过前置包）
    return hand, data


def _cook(hand, data, attended=False, now=100.0, dt=0.2):
    if attended:
        hand.clock.attend(now)
    HandCooking.cook(hand, 0, POS, data, [dict(RICE), {}, {}, {}, {}, {}], now, dt)
    return hand


def testAPotCooksTheRecipesOwnTimeWhileNotLinkedWhateverTheConfigSays():
    for mode in NOT_LINKED:
        with L.Modes(mode), Config(cooking_pot_time=2.0):
            hand, data = _pot()
            _cook(hand, data)
            assert hand.total == 5.0 and data["timerTotal"] == 5.0, (mode, hand.total)
            assert PotCooking.timeFor(10.0) == 10.0 and PotCooking.bookSeconds(10.0) == 10.0 / PotCooking.batchSpeed(1)
    with L.Modes(Mode.LINKED), Config(cooking_pot_time=2.0):
        hand, data = _pot()
        _cook(hand, data)
        assert hand.total == 10.0 and data["timerTotal"] == 10.0, "联动了倍率才生效：5 秒 x 2"


def testAPotLeftWithHandPlacedFoodDoesNotWaitForASpoonWhileNotLinked():
    # 存档里这口锅的料是手放的、厨师还在旁边（以前装过前置包）：没联动时没人能搅，料按农夫乐事的煮法自己煮
    for mode in NOT_LINKED:
        with L.Modes(mode):
            hand, data = _pot(byHand=True)
            _cook(hand, data, attended=True)
            assert hand.mode == PotCooking.FD_WAY, mode
            assert hand.clock.cookTime > 0.0, "进度在走"
    with L.Modes(Mode.LINKED):
        hand, data = _pot(byHand=True)
        _cook(hand, data, attended=True)
        assert hand.mode == PotCooking.WAITING and hand.clock.cookTime == 0.0, "联动了：厨师在旁边就等勺子"


# ---------------------------------------------------------------- 煎锅 / 炉灶：手放的交还给农夫乐事

def _pan(byHand=True):
    HandFrying.forget(0, POS)
    data = skilletkit.EngineData()
    data["cookingDict"] = dict(BEEF)
    data["heatEnable"] = True
    hand = HandFrying.handOf(0, POS, data)
    if byHand:
        hand.frying.layByHand()
    return hand, data


def testASkilletLeftWithHandFriedFoodIsFriedTheFarmersDelightWayWhileNotLinked():
    for mode in NOT_LINKED:
        with L.Modes(mode), Config(skillet_time=2.0):
            hand, data = _pan()
            assert HandFrying.fry(hand, 0, POS, data, 0.25) is False, "不归手工管：Server/Skillet 接着按 6 秒一件煎"
            assert hand.frying.byHand is False and data[HandFrying.SAVE_KEY] is None, "手放的记号清掉了，不会再被读回来"
    with L.Modes(Mode.LINKED):
        hand, data = _pan()
        assert HandFrying.fry(hand, 0, POS, data, 0.25) is True, "联动了：还是手工煎，等人颠锅"
        assert hand.frying.byHand is True


def testTheSkilletsHandTimeIsNotMultipliedWhileNotLinked():
    def sides():
        return [PanStation.sideSeconds(batch, 0) for batch in (1, 4)]
    with Config(skillet_time=1.0), L.Modes(Mode.LINKED):
        base = sides()
    with Config(skillet_time=2.0):
        with L.Modes(Mode.STANDALONE):
            off = sides()
        with L.Modes(Mode.LINKED):
            on = sides()
    assert off == base, "没联动 = 倍率 1.0"
    assert all(abs(slow - 2 * plain) <= 0.05 for plain, slow in zip(base, on)), (base, on)


def _stove():
    HandGrill.forget(0, POS)
    data = skilletkit.EngineData()
    data["0"] = {"itemDict": dict(BEEF, count=1), "cookTimer": 30}
    hand = HandGrill.handOf(0, POS, data)
    hand.grill.layByHand(0)
    return hand, data


def testAStoveLeftWithHandGrilledFoodHandsItBackToFarmersDelightWhileNotLinked():
    for mode in NOT_LINKED:
        with L.Modes(mode), Config(stove_time=2.0):
            hand, data = _stove()
            handled, changed = HandGrill.grill(hand, data, 0.25)
            assert handled == set() and hand.grill.byHand(0) is False, (mode, handled)
            assert data["0"]["cookTimer"] == 30.0, "农夫乐事的 30 秒，不乘配置里的倍率"
            assert GrillStation.sideSeconds() == GrillStation.RECIPE_SECONDS / 1.5 / 2.0 == 10.0, "手放的一面也不乘"
    with L.Modes(Mode.LINKED), Config(stove_time=2.0):
        hand, data = _stove()
        handled, changed = HandGrill.grill(hand, data, 0.25)
        assert handled == set([0]) and hand.grill.byHand(0) is True, "联动了：手放的归手工管"
        assert GrillStation.sideSeconds() == 20.0


# ---------------------------------------------------------------- 盛菜的记账

class _Extra(object):
    def __init__(self, store):
        self.store = store

    def GetExtraData(self, key):
        return self.store.get(key)

    def SetExtraData(self, key, value):
        self.store[key] = value


class _Comp(object):
    def __init__(self):
        self.store = {}

    def CreateExtraData(self, playerId):
        return _Extra(self.store)


def _book():
    comp = _Comp()
    HandCooking.compFactory = comp
    HandCooking._made.clear()
    return comp


def testServingWritesNothingToThePlayersDataWhileNotLinked():
    for mode in NOT_LINKED:
        comp = _book()
        with L.Modes(mode):
            assert HandCooking.addMade("p", "arris:tomato_sauce", 3) == 0
            assert comp.store == {}, "没联动：不往玩家数据里写 HoD 的做过几份（FD 本来没有这个记账）"
            assert HandCooking.madeOf("p", "arris:tomato_sauce") == 0


def testServingCountsTheDishesOnceLinkedAsBefore():
    comp = _book()
    with L.Modes(Mode.LINKED):
        assert HandCooking.addMade("p", "arris:tomato_sauce", 3) == 3
        assert HandCooking.addMade("p", "arris:tomato_sauce", 2) == 5
        assert comp.store[HandCooking.MADE_KEY] == {"arris:tomato_sauce": 5}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
