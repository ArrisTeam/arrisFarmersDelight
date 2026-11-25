# -*- coding: utf-8 -*-
# runner: both
"""四个站点的玩家开关登进前置包的设置界面（Compat/Diegesis/SettingsClientLink，客户端最后一步 settings，条件 SETTINGS）：
- 接口没有 SETTINGS（老的前置包）：这一步 skipped，什么都不登、什么都不报；
- 登的组：总开关 + 这一端登记成功的站点各一项（关了的、没登上的不出现；四个都没登上不登这一组，skipped），每项管着那个站点登记用的站点 id；
- 登记时内核不调 onChange（前置包 Client/SettingsKeep._changed），所以登记完自己报一次；之后总开关、砧板那一项改了再报，别的项不报；
  本地玩家进了世界（OnLocalPlayerStopLoading）再报一次同样的值；砧板没登上就什么都不报；
- "砧板站点对我开不开" = 总开关 and 砧板那一项；关着时前置包工作台的配方书照列（TableClientLink.hidden），开着照旧藏。
服务端收到以后怎么办由 test_board_switch.py 管。真的入口、真的步骤模块，引擎是 linkkit 里的假环境，前置包的接口是下面的替身
（照前置包 Client/SettingsKeep 的规矩：登记不调回调，改一项调一次）。只用本仓库的东西。"""
from __future__ import print_function

import importlib
import sys

import fdtest
import linkkit as L
from optkit import Config

env = L.install()
Rules = fdtest.load("Shared.Rules.StationSwitches")
GROUP, MASTER, BOARD = Rules.GROUP, Rules.MASTER, Rules.BOARD
REPORT = "BoardSwitchReport"
SANDWICH = [[("arris:fried_egg", 0)], [("arris:fried_egg", 0)], [("minecraft:bread", 0)]]     # 蛋三明治在砧板上的配方，配方书的写法
sent = []
sys.modules[L.PACKAGE + ".QuModLibs.Client"].Call = lambda name, data: sent.append((name, data))       # 客户端发给服务端的


class Kernel(object):
    """前置包客户端接口的替身（站点的 register 由 env.stubRegisters 换成记账的）：设置照 Client/SettingsKeep——
    registerSettings 只记下来、不调 onChange；settingValue 是存着的值或缺省（开关缺省开），没登记的项 None；change 是玩家改了一项。"""

    API_VERSION = 3
    FACING_HOOK = True
    Geometry = "Geometry"

    def __init__(self, settings=True, saved=None):
        self.SETTINGS = settings
        self.groups = {}
        self.saved = dict(saved or {})

    def registerSettings(self, groupId, title, items, onChange=None):
        self.groups[groupId] = (title, list(items), onChange)

    def settingValue(self, groupId, key):
        group = self.groups.get(groupId)
        if group is None or key not in [item["key"] for item in group[1]]:
            return None
        return self.saved.get(key, True)

    def change(self, key, value):
        self.saved[key] = value
        self.groups[GROUP][2](key, value)


class BookHooks(object):
    """前置包配方书的客户端登记口（Vanilla/Client/TableBookHooks）的替身。"""

    API_VERSION = 1

    def __init__(self):
        self.hidden = []

    def addHidden(self, fn):
        self.hidden.append(fn)


def mod(name):
    return importlib.import_module(L.DIEGESIS + "." + name)


def bootClient(kernel, off=(), **config):
    """客户端启动一次：返回每一步的状态。"""
    env.reset()
    env.tableHooks["client"] = BookHooks()
    env.apis["client"] = kernel
    env.stubRegisters("client", [], off)
    del sent[:]
    with Config(**config):
        env.boot("client")
        env.fire("client")
    return dict((name, status) for name, status, _ in mod("Presence").report("client")["steps"])


def keys(kernel):
    return [item["key"] for item in kernel.groups[GROUP][1]]


def testAnOldPrerequisiteWithoutSettingsSkipsTheStepAndRegistersAndReportsNothing():
    kernel = Kernel(settings=False)
    steps = bootClient(kernel)
    assert steps["settings"] == "skipped" and kernel.groups == {} and sent == []
    assert mod("SettingsClientLink").boardOnForMe() is True, "缺省开着：书照旧藏砧板菜"


def testTheGroupHasTheMasterAndEveryStationRegisteredOnThisSide():
    kernel = Kernel()
    assert bootClient(kernel)["settings"] == "ok"
    title, items, onChange = kernel.groups[GROUP]
    assert title["key"] == "arris_fd.settings.group" and keys(kernel) == ["enabled", "cooking_pot", "cutting_board", "skillet", "stove"]
    stations = dict((item["key"], item.get("stations")) for item in items)
    assert stations == {"enabled": None, "cooking_pot": (fdtest.load("Shared.Rules.PotStation").STATION_ID,),
                        "cutting_board": (fdtest.load("Shared.Rules.BoardStation").STATION_ID,),
                        "skillet": (fdtest.load("Shared.Rules.PanStation").STATION_ID,),
                        "stove": (fdtest.load("Shared.Rules.GrillStation").STATION_ID,)}, "每项管着那个站点登记用的站点 id"


def testStationsThatDidNotRegisterGetNoItemAndNoStationsMeansNoGroup():
    kernel = Kernel()
    bootClient(kernel, off=("pot",))
    assert keys(kernel) == ["enabled", "cutting_board", "skillet", "stove"], "配置里关了厨锅：没有厨锅那一项"
    kernel = Kernel()
    kernel.FACING_HOOK = False
    bootClient(kernel)
    assert keys(kernel) == ["enabled", "cooking_pot", "cutting_board", "skillet"], "炉灶那一步没跑：没有炉灶那一项"
    kernel = Kernel()
    steps = bootClient(kernel, off=("board", "pot", "pan", "grill"))
    assert steps["settings"] == "skipped" and kernel.groups == {} and sent == [], "四个都没登上：不登这一组"


def testRegisteringReportsTheBoardOnceBecauseTheKernelDoesNotCallBack():
    kernel = Kernel()
    bootClient(kernel)
    assert sent == [(REPORT, {"on": True})], "登记完自己算一遍、报一次"
    kernel = Kernel(saved={BOARD: False})
    bootClient(kernel)
    assert sent == [(REPORT, {"on": False})], "设置存在本机：进世界时砧板就是关着的，也要报"
    assert mod("SettingsClientLink").boardOnForMe() is False
    kernel = Kernel()
    bootClient(kernel, off=("board",))
    assert keys(kernel) == ["enabled", "cooking_pot", "skillet", "stove"] and sent == [], "砧板没登上：服务端也没有否决，什么都不报"


def testTheMasterAndTheBoardSwitchDecideAndAreReportedOtherSwitchesAreNot():
    kernel = Kernel()
    bootClient(kernel)
    link = mod("SettingsClientLink")
    del sent[:]
    kernel.change("cooking_pot", False)
    assert sent == [] and link.boardOnForMe() is True, "厨锅那一项和砧板无关：不报"
    kernel.change(BOARD, False)
    assert sent == [(REPORT, {"on": False})] and link.boardOnForMe() is False
    kernel.change(MASTER, False)
    kernel.change(BOARD, True)
    assert sent[1:] == [(REPORT, {"on": False}), (REPORT, {"on": False})] and link.boardOnForMe() is False, "总开关关着：砧板那一项开了也还是关"
    kernel.change(MASTER, True)
    assert sent[-1] == (REPORT, {"on": True}) and link.boardOnForMe() is True, "总开关变了也重报"


def testThePlayerStoppingLoadingSendsTheSameValueAgain():
    kernel = Kernel(saved={MASTER: False})
    bootClient(kernel)
    del sent[:]
    for event, func in env.listened["client"]:
        if event == "OnLocalPlayerStopLoading" and func.__module__ == L.DIEGESIS + ".SettingsClientLink":
            func({})
    assert sent == [(REPORT, {"on": False})]


def testTheBookHidesTheBoardDishesOnlyWhileTheBoardIsOnForMe():
    kernel = Kernel()
    bootClient(kernel)
    hidden = mod("TableClientLink").hidden
    product = {"newItemName": "arris:egg_sandwich", "newAuxValue": 0, "count": 1}
    assert hidden(product, SANDWICH), "开着：照旧不列"
    kernel.change(BOARD, False)
    assert not hidden(product, SANDWICH), "关了砧板：他开不了砧板站点，书里照列（每次现读，不用重进世界）"
    kernel.change(BOARD, True)
    kernel.change(MASTER, False)
    assert not hidden(product, SANDWICH), "总开关关了也一样"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
