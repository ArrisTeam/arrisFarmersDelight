# -*- coding: utf-8 -*-
# runner: both
"""没装沉浸式交互前置（或它太旧）时 Hands-On Delight 相关的东西一样也不跑：两个入口只挂 Presence，Compat/Diegesis 里除了两个入口、Presence、Steps、两张步骤表，
别的模块一个也不导入——所以它们的 @Listen / @AllowCall 也一个都不存在（原来入口在顶层导入全部站点模块，没装前置包时场景模块每帧的监听和端点照样挂着）。
装了、够新时站点模块由步骤导入、监听和端点才出现；客户端在"全部 Addon 脚本加载完成"之前什么也不碰。真的入口，引擎是 linkkit 里的假环境。只用本仓库的东西。"""
from __future__ import print_function

import fdtest
import linkkit as L

env = L.install()
Mode = L.Mode
PRESENCE, CLIENT_BOOT = L.DIEGESIS + ".Presence", L.DIEGESIS + ".ClientBoot"
SERVER_LISTENERS = [("LoadServerAddonScriptsAfter", PRESENCE, "onServerLoaded")]
CLIENT_LISTENERS = [("LoadClientAddonScriptsAfter", PRESENCE, "onClientLoaded"), ("OnLocalPlayerStopLoading", CLIENT_BOOT, "OnLocalPlayerStopLoading")]
SERVER_STATION_MODULES = {"BoardLogic", "PotLogic", "PanLogic", "GrillLogic", "DishCrafts"}
CLIENT_STATION_MODULES = {"BoardView", "PotView", "PanView", "GrillView", "PotScenes", "PanScenes", "StoveScenes", "BoardWatch"}
STATION_MODULES = SERVER_STATION_MODULES | CLIENT_STATION_MODULES
CLIENT_ENDPOINTS = [("PotScenes", "OnPotLook"), ("PanScenes", "OnPanLook"), ("StoveScenes", "OnStoveLook"), ("BoardWatch", "OnBoardLook")]


def apiOf(version=3, **flags):
    return type("Api", (object,), dict(flags, API_VERSION=version, Geometry="Geometry"))


def bootBoth(api=None, fire=True):
    """两端各启动一次（站点的 register 都是记账的）：返回 {端: [(站点, api)]}，没联动时一个也没调过。"""
    env.reset()
    env.apis["server"] = env.apis["client"] = api
    calls = {"server": [], "client": []}
    for side in calls:
        env.stubRegisters(side, calls[side])
    env.boot("server")
    env.boot("client", clean=False)
    if fire:
        env.fire("server")
        env.fire("client")
    return calls


def listeners(side):
    return [(event, func.__module__, func.__name__) for event, func in env.listened[side]]


def testWithoutThePrerequisiteBothSidesAreStandaloneAndOnlyTheEntryModulesAreImported():
    calls = bootBoth(None)
    assert Mode.mode("server") == Mode.STANDALONE and Mode.mode("client") == Mode.STANDALONE and Mode.linked() is False
    assert L.names() == sorted(L.ENTRY), "站点、场景、旁观声音的模块一个也没导入：%r" % (L.names(),)
    assert not set(L.names()) & STATION_MODULES and calls == {"server": [], "client": []}


def testWithoutThePrerequisiteNothingListensForTheStationsAndNoEndpointExists():
    bootBoth(None)
    assert listeners("server") == SERVER_LISTENERS, "服务端只有判定用的那一个监听"
    assert listeners("client") == CLIENT_LISTENERS, "客户端：判定用的，加上前置包太旧时提醒用的"
    assert env.endpoints == {"server": [], "client": []}, "OnPotLook / OnPanLook / OnStoveLook / OnBoardLook 都不存在"
    assert not [name for name, _ in env.listened["client"] if name in ("GameRenderTickEvent", "ModBlockEntityLoadedClientEvent")], \
        "没有每帧的监听、没有方块实体加载的监听"


def testAnOutdatedPrerequisiteImportsAndListensToNothingEither():
    for version in (0, 1, 2):
        calls = bootBoth(apiOf(version, FACING_HOOK=True))
        assert calls == {"server": [], "client": []}
        assert Mode.mode("server") == Mode.OUTDATED and Mode.mode("client") == Mode.OUTDATED and Mode.linked() is False
        assert L.names() == sorted(L.ENTRY), (version, L.names())
        assert listeners("server") == SERVER_LISTENERS and listeners("client") == CLIENT_LISTENERS
        assert env.endpoints == {"server": [], "client": []}


def testTheClientDoesNotEvenAskForTheApiBeforeTheEvent():
    calls = bootBoth(apiOf(3, FACING_HOOK=True), fire=False)
    assert env.asked["client"] == [], "客户端的接口模块会带进前置包自己的 QuModLibs：事件之前不碰它"
    assert Mode.mode("client") == Mode.PENDING and calls["client"] == []
    assert not set(L.names()) & CLIENT_STATION_MODULES
    assert env.asked["server"][0] == "arrisDiegesisScripts.Api.Server", "服务端导入时先找了一次"
    assert set(env.asked["server"][1:]) <= {L.TABLE_HOOKS}, "之后只有 table 那一步（和 board 那一步的否决）找前置包的原版工作台接口"
    assert Mode.mode("server") == Mode.LINKED and len(calls["server"]) == 4, "服务端导入时前置包的接口就在：马上联动"
    env.fire("client")
    assert env.asked["client"][0] == "arrisDiegesisScripts.Api.Client" and Mode.mode("client") == Mode.LINKED
    assert set(env.asked["client"][1:]) <= {L.BOOK_HOOKS}, "之后只有 table 那一步找前置包配方书的客户端登记口"
    assert [station for station, _ in calls["client"]] == ["board", "pot", "pan", "grill"]


def testWithAGoodPrerequisiteTheStepsImportTheStationModulesAndTheirListenersAndEndpointsAppear():
    # 反过来对照：不是什么都导入不了，是只有联动时才由步骤导入
    bootBoth(apiOf(3, FACING_HOOK=True), fire=False)
    assert SERVER_STATION_MODULES <= set(L.names()), "服务端导入时前置包的接口就在：步骤马上导入了站点模块"
    assert not set(L.names()) & CLIENT_STATION_MODULES, "客户端在事件之前什么也不导入"
    env.fire("client")
    assert STATION_MODULES <= set(L.names()), sorted(STATION_MODULES - set(L.names()))
    assert sorted(env.endpoints["client"]) == sorted((L.DIEGESIS + "." + module, name) for module, name in CLIENT_ENDPOINTS), env.endpoints
    sceneListeners = [(event, func.__module__[len(L.DIEGESIS) + 1:]) for event, func in env.listened["client"]
                      if func.__module__.startswith(L.DIEGESIS + ".")]
    for module in ("PotScenes", "PanScenes", "StoveScenes"):
        assert ("GameRenderTickEvent", module) in sceneListeners and ("ModBlockEntityLoadedClientEvent", module) in sceneListeners, module


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
