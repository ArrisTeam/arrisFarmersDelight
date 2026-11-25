# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里的站点开关（cooking_pot / cutting_board / skillet / stove / remove_crafting_recipes）接到两个联动入口上
（Compat/Diegesis 的 ServerBoot / ClientBoot，经 Presence 和步骤表，和每个站点的 register）：缺省照旧；关了的站点两端都不登记（它的步骤是 skipped）、
连带的世界外观广播 / 场景 / 旁观的声音 / 工作台拦截也不开，方块照农夫乐事原样用（前置包认不出这个方块）；两端对每一种开关组合都一致；
前置包的接口比本包要的（Presence.REQUIRED_API_VERSION）老，一个站点也不登记（OUTDATED）；没装前置包（STANDALONE）也一样。
真的入口、真的站点模块、真的前置包服务端 Api 和客户端 Registry，引擎是 bootkit 里的无害替身。"""
from __future__ import print_function

import itertools

import bootkit as B
import fdtest
from optkit import Config

KEYS = ("cooking_pot", "cutting_board", "skillet", "stove")
STATION_OF = {"cooking_pot": B.POT, "cutting_board": B.BOARD, "skillet": B.SKILLET, "stove": B.STOVE}
LOOK_OF = {"cooking_pot": "pot", "cutting_board": "board", "skillet": "pan", "stove": "stove"}
BLOCK_OF = {B.POT: B.POT_BLOCK, B.BOARD: B.BOARD_BLOCK, B.SKILLET: B.SKILLET_BLOCK, B.STOVE: B.STOVE_BLOCK}
STEP_OF = {"cooking_pot": "pot", "cutting_board": "board", "skillet": "pan", "stove": "grill"}      # 每个站点在步骤表里的步骤名
DEFAULT_ORDER = [B.BOARD, B.POT, B.SKILLET, B.STOVE]       # 缺省的登记顺序（原来的 tryRegister / OnLoadClientAddonScriptsAfter 照这个次序，现在是步骤表的顺序）
EXTRA_STEPS = {"table": "ok"}                              # 不是站点的步骤：前置包原版工作台上的登记（它真的接口在，两端都 ok）
CLIENT_ONLY = {"settings": "skipped"}                      # 只有客户端有的最后一步（玩家开关）：bootkit 的接口替身没有 SETTINGS（test_settings_link.py 管它）


def _shared(steps):
    return dict((name, status) for name, status in steps.items() if name not in CLIENT_ONLY)


def testTheShippedDefaultsRegisterEverythingInTheOrderTheBootsAlwaysDid():
    server, client = B.bootServer(), B.bootClient()
    assert server.stations == DEFAULT_ORDER and client.stations == DEFAULT_ORDER, (server.stations, client.stations)
    assert server.mode == client.mode == B.Mode.LINKED
    assert server.steps == _shared(client.steps) == dict({"board": "ok", "pot": "ok", "pan": "ok", "grill": "ok"}, **EXTRA_STEPS)
    assert client.steps["settings"] == CLIENT_ONLY["settings"]
    assert server.tableHooks == {"vetoes": 1, "remainders": 1}, "前置包真的原版工作台接口收下了砧板菜的否决和补还剩余物"
    assert client.tableHooks == {"hidden": 1}, "前置包配方书真的客户端登记口收下了砧板菜不进书"
    assert server.looks == {"pot": True, "pan": True, "stove": True, "board": True}
    assert client.looks == {"pot": True, "pan": True, "stove": True, "board": True}
    assert server.dishCrafts is True, "工作台拦截登记了"
    for stationId, block in BLOCK_OF.items():
        assert B.ServerRegistry.stationTypeOf(block).stationId == stationId, "前置包的服务端认得这个方块"
        assert B.ClientRegistry.behaviorOf(block).stationId == stationId, "前置包的客户端认得这个方块：右键它就是开站"


def testEachSwitchTurnsOffOnlyItsOwnStationAndWhatHangsOnIt():
    for key in KEYS:
        with Config(**{key: False}):
            server, client = B.bootServer(), B.bootClient()
        expected = [stationId for stationId in DEFAULT_ORDER if stationId != STATION_OF[key]]
        assert server.stations == expected and client.stations == expected, (key, server.stations, client.stations)
        skipped = dict(dict((step, "skipped" if STEP_OF[key] == step else "ok") for step in STEP_OF.values()), **EXTRA_STEPS)
        assert server.steps == _shared(client.steps) == skipped, (key, server.steps, client.steps)
        assert server.tableHooks == {"vetoes": int(key != "cutting_board"), "remainders": 1}, "否决跟着砧板站点走，补还剩余物一直登"
        assert client.tableHooks == {"hidden": int(key != "cutting_board")}, "书里不列砧板菜也跟着砧板站点走"
        for name in ("pot", "pan", "stove", "board"):
            assert server.looks[name] == client.looks[name] == (name != LOOK_OF[key]), (key, name, server.looks, client.looks)
        assert server.dishCrafts is (key != "cutting_board"), "工作台拦截跟着砧板站点走：没有砧板站点就没有地方做这些菜"
        block = BLOCK_OF[STATION_OF[key]]
        assert B.ServerRegistry.stationTypeOf(block) is None and B.ClientRegistry.behaviorOf(block) is None, \
            "前置包不认这个方块：右键它不开站、不取消，方块原来的使用照常走（厨锅就是经典界面）"


def testTheCraftingGridSwitchOnlyTakesTheTableInterceptionAway():
    with Config(remove_crafting_recipes=False):
        server, client = B.bootServer(), B.bootClient()
    assert server.stations == DEFAULT_ORDER and client.stations == DEFAULT_ORDER, "站点都在"
    assert server.looks == {"pot": True, "pan": True, "stove": True, "board": True} and client.looks == server.looks
    assert server.dishCrafts is False, "工作台照旧出这些菜"
    server = B.bootServer()
    assert server.dishCrafts is True


def testTheTableReallyStopsTheBoardDishCraftOnlyWithTheBoardStationAndTheCraftingSwitchOn():
    # 工作台上拿蛋三明治（面包 + 两个煎蛋，正好是它在砧板上的配方）：登记了 DishCrafts 就取消并提示，没登记什么也不发生
    DishCrafts = fdtest.load("Compat.Diegesis.DishCrafts")
    DishCrafts.readGrid = lambda playerId: {0: ("arris:fried_egg", 1), 1: ("arris:fried_egg", 1), 2: ("minecraft:bread", 1)}

    def craft():
        args = {"playerId": "a", "itemDict": {"newItemName": "arris:egg_sandwich", "newAuxValue": 0, "count": 1}, "cancel": False}
        return B.EventRegistry.dispatch("CraftItemOutputChangeServerEvent", args), args["cancel"]
    cases = ((dict(), True), (dict(remove_crafting_recipes=False), False), (dict(cutting_board=False), False),
             (dict(cutting_board=False, remove_crafting_recipes=False), False), (dict(cooking_pot=False, skillet=False, stove=False), True))
    for values, blocked in cases:
        with Config(**values):
            B.bootServer()
            assert craft() == (blocked, blocked), (values, blocked)


def testServerAndClientAgreeOnEveryCombinationOfTheSwitches():
    for flags in itertools.product((True, False), repeat=len(KEYS) + 1):
        values = dict(zip(KEYS + ("remove_crafting_recipes",), flags))
        with Config(**values):
            server, client = B.bootServer(), B.bootClient()
        on = [stationId for stationId in DEFAULT_ORDER if values[[key for key in KEYS if STATION_OF[key] == stationId][0]]]
        assert server.stations == client.stations == on, (values, server.stations, client.stations)
        assert server.looks == client.looks == dict((LOOK_OF[key], values[key]) for key in KEYS), values
        assert server.dishCrafts is bool(values["cutting_board"] and values["remove_crafting_recipes"]), values
        assert server.tableHooks["vetoes"] == int(server.dishCrafts), "前置包原版工作台上的否决和原版合成格的拦截同一个条件"
        assert client.tableHooks["hidden"] == server.tableHooks["vetoes"], ("配方书不列砧板菜和服务端的否决同一个条件", values)
        for stationId, block in BLOCK_OF.items():
            assert (B.ServerRegistry.stationTypeOf(block) is not None) is (B.ClientRegistry.behaviorOf(block) is not None) \
                is (stationId in on), (values, block)


def testAKernelBelowTheRequiredApiIsOutdatedAndNothingIsRegistered():
    # 原来三个门槛（1 / 2 / 3）按站点分：API 2 的前置包上炉灶登记、厨锅 / 煎锅 / 砧板不登记。现在只有一个（Presence.REQUIRED_API_VERSION = 3）：
    # 前置包从来没有发过比 3 低的版本，低于它的整个不联动，一个站点也不登记
    class Old(object):
        API_VERSION = 2
        FACING_HOOK = True
        StationLogic = B.ServerApi.StationLogic
        StationType = B.ServerApi.StationType
        StationSchema = B.ServerApi.StationSchema
        SlotRules = B.ServerApi.SlotRules
        registerStation = staticmethod(B.ServerApi.registerStation)
        ControlSpec = B.ServerApi.ControlSpec

    class OldClient(B.ClientApi):
        API_VERSION = 2
    server, client = B.bootServer(Old), B.bootClient(OldClient)
    assert server.mode == client.mode == B.Mode.OUTDATED
    assert server.stations == [] and client.stations == [] and server.steps == client.steps == {}
    assert server.looks == {"pot": False, "pan": False, "stove": False, "board": False} and client.looks == server.looks
    assert server.dishCrafts is False
    for block in (B.POT_BLOCK, B.BOARD_BLOCK, B.SKILLET_BLOCK, B.STOVE_BLOCK):
        assert B.ServerRegistry.stationTypeOf(block) is None and B.ClientRegistry.behaviorOf(block) is None, "前置包不认这些方块：走经典玩法"


def testWithoutThePrerequisiteBothSidesAreStandaloneAndRegisterNothing():
    server, client = B.bootServer(B.ABSENT), B.bootClient(B.ABSENT)
    assert server.mode == client.mode == B.Mode.STANDALONE
    assert server.stations == [] and client.stations == [] and server.steps == client.steps == {}
    assert server.looks == {"pot": False, "pan": False, "stove": False, "board": False} and client.looks == server.looks
    assert server.dishCrafts is False
    assert B.Mode.linked() is False


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
