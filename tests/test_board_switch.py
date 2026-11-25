# -*- coding: utf-8 -*-
# runner: both
"""玩家报上来的"砧板站点对我开不开"（Compat/Diegesis/BoardSwitch，端点 BoardSwitchReport；跟着砧板的否决在 board 那一步开）：
收到关 -> 这个玩家两处都不否决（原版合成格 DishCrafts.onCraft、前置包原版工作台 TableHooksLink.dishVeto），收到开 / 没收到 -> 否决照旧；
别的玩家不受影响；玩家下线（DelServerPlayerEvent）清掉；没登否决（remove_crafting_recipes 关着）时不收、不挂下线的处理；坏的、缺值的消息不算，
值只当布尔用。客户端什么时候报由 test_settings_link.py 管。真的入口、真的步骤模块，引擎是 linkkit 里的假环境。只用本仓库的东西。"""
from __future__ import print_function

import importlib

import fdtest
import linkkit as L
from optkit import Config

env = L.install()
EventRegistry = fdtest.load("Server.EventRegistry")
SANDWICH = (("arris:fried_egg", 1), ("arris:fried_egg", 1), ("minecraft:bread", 1))      # 蛋三明治在砧板上的配方：工作台九格里正好是它
PRODUCT = {"newItemName": "arris:egg_sandwich", "newAuxValue": 0, "count": 1}


class Api(object):
    """前置包服务端接口的替身（站点的 register 由 env.stubRegisters 换成记账的）。"""
    API_VERSION = 3
    FACING_HOOK = True


class TableHooks(object):
    """前置包原版工作台接口（Vanilla/Server/TableHooks）的替身：记下登了哪些否决。"""

    API_VERSION = 1

    def __init__(self):
        self.vetoes = []

    def addVeto(self, fn):
        self.vetoes.append(fn)

    def addRemainder(self, fn):
        pass


def mod(name):
    return importlib.import_module(L.DIEGESIS + "." + name)


def bootServer(**config):
    """服务端启动一次（四个站点都登上）：返回前置包原版工作台接口的替身。"""
    env.reset()
    EventRegistry.clearAll()
    hooks = env.tableHooks["server"] = TableHooks()
    env.apis["server"] = Api
    env.stubRegisters("server", [])
    with Config(**config):
        env.boot("server")
    mod("DishCrafts").readGrid = lambda playerId: dict(enumerate(SANDWICH))
    return hooks


def crafts(playerId):
    """原版合成格里拿蛋三明治：被拦了没有。"""
    args = {"playerId": playerId, "itemDict": dict(PRODUCT), "cancel": False}
    return EventRegistry.dispatch("CraftItemOutputChangeServerEvent", args) is True and args["cancel"] is True


def vetoes(playerId):
    """前置包的原版工作台上拿蛋三明治：被否决了没有。"""
    cells = [{"newItemName": name, "newAuxValue": 0, "count": count} for name, count in SANDWICH] + [None] * 6
    return mod("TableHooksLink").dishVeto(playerId, dict(PRODUCT), cells) is not None


def report(playerId, data):
    mod("BoardSwitch").BoardSwitchReport(playerId, data)


def testTheServerKeepsVetoingUntilThePlayerReportsTheBoardOff():
    hooks = bootServer()
    assert hooks.vetoes == [mod("TableHooksLink").dishVeto], "联动着、remove_crafting_recipes 开着：前置包工作台上登了否决"
    assert crafts("a") and vetoes("a"), "没收到过：两处否决照旧"
    report("a", {"on": False})
    assert not crafts("a") and not vetoes("a"), "这个玩家关了砧板：工作台照做"
    assert crafts("b") and vetoes("b"), "别的玩家照旧"
    report("a", {"on": True})
    assert crafts("a") and vetoes("a"), "开回来：又否决"


def testAPlayerWhoLeavesIsForgotten():
    bootServer()
    report("a", {"on": False})
    assert not crafts("a") and mod("BoardSwitch").choices.players() == ["a"]
    EventRegistry.dispatch("DelServerPlayerEvent", {"id": "a"})
    assert crafts("a") and mod("BoardSwitch").choices.players() == [], "下线清掉：下次进来没报之前照旧否决"


def testBrokenReportsChangeNothingAndTheValueIsReadAsABoolean():
    bootServer()
    for playerId, data in (("a", {"off": True}), ("a", None), ("a", "False"), ("", {"on": False}), (None, {"on": False})):
        report(playerId, data)
    assert crafts("a") and mod("BoardSwitch").choices.players() == []
    report("a", {"on": 0})
    assert not crafts("a"), "值只当布尔用"


def testWithoutTheCraftingRemovalNothingIsCollected():
    hooks = bootServer(remove_crafting_recipes=False)
    report("a", {"on": False})
    assert hooks.vetoes == [] and mod("BoardSwitch").choices.players() == [], "没登否决：不收"
    assert EventRegistry.handlerNames("DelServerPlayerEvent") == [], "也不挂下线的处理"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
