# -*- coding: utf-8 -*-
# runner: both
"""取别的模组的模块：沉浸式交互前置原版工作台的两个登记口——服务端 Vanilla/Server/TableHooks（Compat/Diegesis/TableHooksLink，board 那一步
登砧板菜的否决、table 那一步登还容器）和客户端 Vanilla/Client/TableBookHooks（TableClientLink，table 那一步登"砧板菜不进书"）。
五种回答（抛 ImportError、抛别的异常、返回 None、前置包装着却没有这个模块、返回正常的模块）：它导入出错、它不在、前置包旧得还没有它都一样——
table 一步 skipped，什么都不登；服务端 board 那一步照样做完：收玩家报来的砧板开关（BoardSwitch）、旁观的切菜声（BoardLook）照开
（原来 board 那一步在登否决时把异常抛出去，后面两样没做、记 failed）；服务端两步各取一次。导入出错的日志只打一次；没有这个模块是正常配置
（新的农夫乐事配旧的前置包），不打日志——引擎这时抛的 ImportError 的文字照 3.10 实机两种都测。
真的入口和步骤模块，引擎是 linkkit 的假环境，站点的 register 是记账的。只用本仓库的东西。
"""
from __future__ import print_function

import importlib

import fdtest
import linkkit as L
import otherkit
from optkit import Config
from otherkit import Captured

env = L.install()
EventRegistry = fdtest.load("Server.EventRegistry")
BoardLook = fdtest.load("Server.BoardLook")
DISH_CRAFTS = (L.DIEGESIS + ".DishCrafts", "onCraft")
STATIONS = ("board", "pot", "pan", "grill")
OLD_PREREQ = {"server": ("No module named Vanilla.Server.TableHooks",          # 前置包没有 Vanilla 子包：从它起的一整截（3.10 实机的文字）
                         "No module named TableHooks"),                        # 有 Vanilla、没有这个模块：最后一段
              "client": ("No module named Vanilla.Client.TableBookHooks",
                         "No module named TableBookHooks")}


class Hooks(object):
    """前置包两个登记口的替身（服务端 addVeto / addRemainder，客户端 addHidden）：记下登了什么。"""

    API_VERSION = 1

    def __init__(self):
        self.vetoes, self.remainders, self.hidden = [], [], []

    def addVeto(self, fn):
        self.vetoes.append(fn)

    def addRemainder(self, fn):
        self.remainders.append(fn)

    def addHidden(self, fn):
        self.hidden.append(fn)


def mod(name):
    return importlib.import_module(L.DIEGESIS + "." + name)


def boot(side, answer):
    """那一端启动一次（前置包的接口够新、带朝向钩子），它的原版工作台登记口怎么回答是 answer。返回 (每一步的状态, 打印的)。"""
    otherkit.fresh()
    env.reset()
    EventRegistry.clearAll()
    BoardLook.enable(False)
    env.apis[side] = type("Api", (object,), {"API_VERSION": 3, "FACING_HOOK": True, "Geometry": "Geometry"})
    env.tableHooks[side] = answer
    env.stubRegisters(side, [])
    with Captured() as out:
        with Config():
            env.boot(side)
            if side == "client":
                env.fire("client")
    steps = dict((name, status) for name, status, _ in mod("Presence").report(side)["steps"])
    return steps, out


def _serverBooted(name, steps, absent):
    assert steps == dict([(station, "ok") for station in STATIONS] + [("table", "skipped" if absent else "ok")]), (name, steps)
    assert BoardLook.enabled() is True and mod("BoardSwitch")._state["on"] is True, "board 那一步做完了：旁观的切菜声、收砧板开关都开着"
    assert DISH_CRAFTS in EventRegistry.handlerNames("CraftItemOutputChangeServerEvent"), "原版合成格的拦截照旧"
    assert env.asked["server"].count(L.TABLE_HOOKS) == 2, "board、table 两步各取一次"


def _clientBooted(name, steps, absent):
    expected = dict([(station, "ok") for station in STATIONS] + [("table", "skipped" if absent else "ok"), ("settings", "skipped")])
    assert steps == expected, (name, steps)
    assert env.asked["client"].count(L.BOOK_HOOKS) == 1


def testTheServerTreatsABrokenTableHooksModuleAsAbsentAndStillFinishesTheBoardStep():
    for name, answer, absent, loud in otherkit.kinds(Hooks(), L.TABLE_HOOKS):
        steps, out = boot("server", answer)
        _serverBooted(name, steps, absent)
        raised = 1 if loud else 0
        assert out.logged(L.TABLE_HOOKS) == raised and out.tracebacks() == raised, (name, out.text)
        if not absent:
            assert answer.vetoes == [mod("TableHooksLink").dishVeto] and answer.remainders == [mod("TableHooksLink").returns]


def testTheClientTreatsABrokenBookHooksModuleAsAbsent():
    for name, answer, absent, loud in otherkit.kinds(Hooks(), L.BOOK_HOOKS):
        steps, out = boot("client", answer)
        _clientBooted(name, steps, absent)
        raised = 1 if loud else 0
        assert out.logged(L.BOOK_HOOKS) == raised and out.tracebacks() == raised, (name, out.text)
        if not absent:
            assert answer.hidden == [mod("TableClientLink").hidden]


def testAnOlderPrerequisiteWithoutTheTwoModulesIsSkippedQuietly():
    """前置包装着、但旧得还没有这两个登记口：引擎抛 ImportError（文字照 3.10 实机：没有 Vanilla 子包时是从 Vanilla 起的一整截，
    有 Vanilla、没有那个模块时是最后一段）。两种都和它不在一样：服务端 board 一步做完、table 一步 skipped，客户端 table 一步 skipped；
    没有日志、没有调用栈，failures 里也没有。"""
    for side, booted, path in (("server", _serverBooted, L.TABLE_HOOKS), ("client", _clientBooted, L.BOOK_HOOKS)):
        for text in OLD_PREREQ[side]:
            steps, out = boot(side, ImportError(text))
            booted(text, steps, True)
            assert out.logged(path) == 0 and out.tracebacks() == 0, (side, text, out.text)
            assert otherkit.OtherMods.failures() == {}, (side, text)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
