# -*- coding: utf-8 -*-
# runner: both
"""场景交互前置的联动判定（Compat/Diegesis/Presence.attach）：每端判定一次，找到前置包的接口、API_VERSION 够（REQUIRED_API_VERSION，一个数）就先把模式拨到 LINKED 再跑步骤表，
找到但太旧是 OUTDATED、一步不跑，到了"全部 Addon 脚本加载完成"那个事件还没有就是 STANDALONE。服务端导入时先找一次，客户端只在事件里找。
前置包、引擎、步骤模块都是假的（直接调 Presence.attach，不经入口模块），只用本仓库的东西。"""
from __future__ import print_function

import types

import fdtest
import linkkit as L

Mode = L.Mode
Presence = fdtest.load("Compat.Diegesis.Presence")
Steps = fdtest.load("Compat.Diegesis.Steps")
SERVER_API, CLIENT_API = "arrisDiegesisScripts.Api.Server", "arrisDiegesisScripts.Api.Client"
SERVER_EVENT, CLIENT_EVENT = "LoadServerAddonScriptsAfter", "LoadClientAddonScriptsAfter"
TABLE = [("first", "Fake.First:link", None), ("second", "Fake.Second:link", None), ("hooked", "Fake.Hooked:link", "SOME_HOOK")]


def apiOf(version, **flags):
    return type("Api", (object,), dict(flags, API_VERSION=version))


class World(object):
    """假引擎和假步骤模块：listen 记下挂了什么监听，find 是 ImportModule（回答 api，没装是 None），load 导入假的步骤模块；
    步骤函数把"被调了"记进 ran（连同当时的模式）。"""

    def __init__(self, api=None):
        self.api = api
        self.asked, self.listened, self.ran = [], [], []
        self.modules = {}
        for name in ("First", "Second", "Hooked"):
            self.modules[fdtest.SCRIPTS + ".Fake." + name] = self._module(name.lower())

    def _module(self, name):
        def link(ctx):
            self.ran.append((name, ctx.side, ctx.api, ctx.apiVersion, Mode.mode(ctx.side)))
        return type("FakeStepModule", (object,), {"link": staticmethod(link)})

    def listen(self, event):
        def decorate(func):
            self.listened.append((event, func))
            return func
        return decorate

    def find(self, name):
        self.asked.append(name)
        if isinstance(self.api, Exception):
            raise self.api
        return self.api

    def load(self, path):
        if path not in self.modules:
            raise ImportError("No module named %s" % path)
        return self.modules[path]

    def attach(self, side, steps=TABLE):
        Presence.attach(side, steps, listen=self.listen, find=self.find, load=self.load)

    def fire(self, side):
        event = SERVER_EVENT if side == "server" else CLIENT_EVENT
        for name, func in list(self.listened):
            if name == event:
                func({})

    def names(self):
        return [entry[0] for entry in self.ran]


def _fresh():
    L.unlink()
    Presence._sides.clear()


def testTheServerLooksAtImportAndRunsTheStepsOnceWhenTheApiIsAlreadyThere():
    _fresh()
    world = World(apiOf(3, SOME_HOOK=True))
    world.attach("server")
    assert Mode.mode("server") == Mode.LINKED, "导入时前置包的接口就在：马上联动"
    assert world.names() == ["first", "second", "hooked"], "按表的顺序一站一站"
    assert world.asked == [SERVER_API]
    world.fire("server")
    assert world.names() == ["first", "second", "hooked"], "事件到了不再跑一遍"
    assert world.asked == [SERVER_API], "判定过了，事件里也不再找"


def testTheServerFindsTheApiAtTheEventWhenItWasNotThereAtImport():
    _fresh()
    world = World()
    world.attach("server")
    assert Mode.mode("server") == Mode.PENDING and world.ran == [] and Mode.linked() is False, "导入时没有：还不能说它没装"
    world.api = apiOf(3, SOME_HOOK=True)           # 前置包比本包后加载
    world.fire("server")
    assert Mode.mode("server") == Mode.LINKED and world.names() == ["first", "second", "hooked"]
    world.fire("server")
    assert world.names() == ["first", "second", "hooked"], "只跑一次"


def testTheServerIsStandaloneWhenTheEventComesAndTheApiIsStillMissing():
    _fresh()
    world = World()
    world.attach("server")
    assert Mode.mode("server") == Mode.PENDING
    world.fire("server")
    assert Mode.mode("server") == Mode.STANDALONE and world.ran == [] and Mode.linked() is False
    assert world.asked == [SERVER_API, SERVER_API], "导入时一次、事件里一次"
    world.api = apiOf(3)
    world.fire("server")
    assert Mode.mode("server") == Mode.STANDALONE and world.ran == [], "判定只做一次"


def testAnOutdatedApiAtImportIsOutdatedAtOnceAndNothingRuns():
    _fresh()
    world = World(apiOf(2, SOME_HOOK=True))
    world.attach("server")
    assert Mode.mode("server") == Mode.OUTDATED and world.ran == [] and Mode.linked() is False
    world.api = apiOf(3, SOME_HOOK=True)
    world.fire("server")
    assert Mode.mode("server") == Mode.OUTDATED and world.ran == [], "判定只做一次：事件到了也不改口"
    assert Presence.report("server")["apiVersion"] == 2


def testTheClientDoesNothingBeforeTheEvent():
    _fresh()
    world = World(apiOf(3, SOME_HOOK=True))
    world.attach("client")
    assert world.asked == [], "客户端的接口模块会带进前置包自己的 QuModLibs：事件之前不碰它"
    assert Mode.mode("client") == Mode.PENDING and world.ran == []
    assert [event for event, _ in world.listened] == [CLIENT_EVENT]
    world.fire("client")
    assert world.asked == [CLIENT_API]
    assert Mode.mode("client") == Mode.LINKED and world.names() == ["first", "second", "hooked"]
    assert Mode.mode("server") == Mode.PENDING, "两端各判各的"


def testTheClientIsStandaloneOrOutdatedAtTheEventAccordingToTheApi():
    for api, expected in ((None, Mode.STANDALONE), (apiOf(2), Mode.OUTDATED), (apiOf(0), Mode.OUTDATED), (apiOf(3), Mode.LINKED)):
        _fresh()
        world = World(api)
        world.attach("client")
        world.fire("client")
        assert Mode.mode("client") == expected, (api, Mode.mode("client"))
        assert (world.names() == []) is (expected != Mode.LINKED)


def testOneRequiredApiVersionReplacesTheThreeOldThresholds():
    assert Presence.REQUIRED_API_VERSION == 3
    for side in ("server", "client"):
        for version, expected in ((0, Mode.OUTDATED), (1, Mode.OUTDATED), (2, Mode.OUTDATED), (3, Mode.LINKED), (4, Mode.LINKED), (10, Mode.LINKED)):
            _fresh()
            world = World(apiOf(version))
            world.attach(side)
            world.fire(side)
            assert Mode.mode(side) == expected, (side, version)
    _fresh()
    world = World(types.ModuleType("noVersion"))           # 没有 API_VERSION 的接口模块当 0
    world.attach("server")
    assert Mode.mode("server") == Mode.OUTDATED


def testTheModeIsAlreadyLinkedWhileTheStepsRun():
    # 站点的 register 问 HandsOnOptions（没联动时它说 HoD 不在、站点开关是假，见 test_handson_options_gate）：模式要先于步骤拨到 LINKED
    _fresh()
    world = World(apiOf(3, SOME_HOOK=True))
    assert Mode.mode("server") == Mode.PENDING
    world.attach("server")
    assert [entry[4] for entry in world.ran] == [Mode.LINKED] * 3, world.ran
    assert Mode.linked() is True


def testTheStepsGetTheSideTheHandshakenApiAndItsVersion():
    _fresh()
    api = apiOf(4, SOME_HOOK=True)
    world = World(api)
    world.attach("client")
    world.fire("client")
    assert [entry[1:4] for entry in world.ran] == [("client", api, 4)] * 3


def testAConditionalStepNeedsTheFeatureFlagOnTheApi():
    _fresh()
    world = World(apiOf(3))
    world.attach("server")
    assert world.names() == ["first", "second"], "接口没有 SOME_HOOK：这一步不跑"
    statuses = [(name, status) for name, status, _ in Presence.report("server")["steps"]]
    assert statuses == [("first", "ok"), ("second", "ok"), ("hooked", "skipped")]


def testAnApiThatCannotBeImportedIsTreatedAsAbsentAndAttachDoesNotRaise():
    _fresh()
    world = World(ImportError("前置包的接口导入出错"))
    world.attach("server")              # 导入时出错：记下来，当它没装；入口模块的导入不能因此失败
    assert Mode.mode("server") == Mode.PENDING and world.ran == []
    world.fire("server")
    assert Mode.mode("server") == Mode.STANDALONE and world.ran == []


def testTheEventHandlersAreOnePerSideAndNamedSoTheQuModLoaderKeepsBoth():
    # QuModLibs 的 Listen 按"模块.函数名"去重：两端的处理函数不能同名
    _fresh()
    server, client = World(), World()
    server.attach("server")
    client.attach("client")
    assert [event for event, _ in server.listened] == [SERVER_EVENT] and [event for event, _ in client.listened] == [CLIENT_EVENT]
    funcs = (server.listened[0][1], client.listened[0][1])
    assert funcs == (Presence.onServerLoaded, Presence.onClientLoaded)
    assert funcs[0].__name__ != funcs[1].__name__ and funcs[0].__module__ == funcs[1].__module__ == Presence.__name__


def testReportShowsTheModeTheApiVersionAndEveryStepForTheInGameCheck():
    _fresh()
    assert Presence.report("server") == {"mode": "pending", "linked": False, "apiVersion": None, "steps": []}
    world = World(apiOf(3))
    world.attach("server")
    report = Presence.report("server")
    assert report["mode"] == "linked" and report["linked"] is True and report["apiVersion"] == 3
    assert [step[:2] for step in report["steps"]] == [["first", "ok"], ["second", "ok"], ["hooked", "skipped"]]
    assert Presence.report("client") == {"mode": "pending", "linked": True, "apiVersion": None, "steps": []}, "linked 问的是整个进程"


def testWhenDecidedHearsThePresenceDecision():
    _fresh()
    seen = []
    Mode.whenDecided("client", seen.append)
    world = World(apiOf(2))
    world.attach("client")
    assert seen == []
    world.fire("client")
    assert seen == [Mode.OUTDATED]


def testAttachingAgainStartsThatSideOverWithAFreshState():
    # 热重载 / 测试里再导入一次入口：那一端从头来
    _fresh()
    World().attach("server")
    world = World(apiOf(3, SOME_HOOK=True))
    Mode.decide("server", Mode.PENDING)
    world.attach("server")
    assert Mode.mode("server") == Mode.LINKED and world.names() == ["first", "second", "hooked"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
