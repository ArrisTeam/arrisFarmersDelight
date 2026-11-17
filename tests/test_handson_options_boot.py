# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里的站点开关（cooking_pot / cutting_board / skillet / stove / remove_crafting_recipes）接到两个联动入口上
（Compat/Diegesis 的 ServerBoot / ClientBoot 和每个站点的 register）：缺省照旧；关了的站点两端都不登记、连带的世界外观广播 /
场景 / 旁观的声音 / 工作台拦截也不开，方块照农夫乐事原样用（前置包认不出这个方块）；两端对每一种开关组合都一致。
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
DEFAULT_ORDER = [B.BOARD, B.POT, B.SKILLET, B.STOVE]       # 缺省的登记顺序（原来的 tryRegister / OnLoadClientAddonScriptsAfter 照这个次序）


def testTheShippedDefaultsRegisterEverythingInTheOrderTheBootsAlwaysDid():
    server, client = B.bootServer(), B.bootClient()
    assert server.stations == DEFAULT_ORDER and client.stations == DEFAULT_ORDER, (server.stations, client.stations)
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


def testServerAndClientAgreeOnEveryCombinationOfTheSwitches():
    for flags in itertools.product((True, False), repeat=len(KEYS) + 1):
        values = dict(zip(KEYS + ("remove_crafting_recipes",), flags))
        with Config(**values):
            server, client = B.bootServer(), B.bootClient()
        on = [stationId for stationId in DEFAULT_ORDER if values[[key for key in KEYS if STATION_OF[key] == stationId][0]]]
        assert server.stations == client.stations == on, (values, server.stations, client.stations)
        assert server.looks == client.looks == dict((LOOK_OF[key], values[key]) for key in KEYS), values
        assert server.dishCrafts is bool(values["cutting_board"] and values["remove_crafting_recipes"]), values
        for stationId, block in BLOCK_OF.items():
            assert (B.ServerRegistry.stationTypeOf(block) is not None) is (B.ClientRegistry.behaviorOf(block) is not None) \
                is (stationId in on), (values, block)


def testAnOldKernelStillKeepsTheStationsItAlwaysKept():
    class Old(object):                # 前置包 API 2：没有厨锅 / 煎锅（要 3），有炉灶（要 2 和朝向钩子）
        API_VERSION = 2
        FACING_HOOK = True
        StationLogic = B.ServerApi.StationLogic
        StationType = B.ServerApi.StationType
        StationSchema = B.ServerApi.StationSchema
        SlotRules = B.ServerApi.SlotRules
        registerStation = staticmethod(B.ServerApi.registerStation)
        ControlSpec = B.ServerApi.ControlSpec
    server = B.bootServer(Old)
    assert server.stations == [B.STOVE] and server.looks == {"pot": False, "pan": False, "stove": True, "board": False}
    assert server.dishCrafts is False, "砧板站点要 API 3"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
