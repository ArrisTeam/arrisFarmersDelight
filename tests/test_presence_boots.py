# -*- coding: utf-8 -*-
# runner: both
"""两个联动入口（ServerBoot / ClientBoot）经 Presence 和步骤表联动：每个站点一步，顺序是原来登记的顺序（砧板、厨锅、煎锅、炉灶），
每一步做原来这个站点在入口里做的全部——登记站点、连带的世界外观广播 / 场景 / 旁观的声音 / 工作台拦截 / 炉灶让出灶上东西的烟；
HoD 配置里关了的站点（register 返回 None）这一步是 skipped、它连带的东西也不开；炉灶要接口的朝向钩子；前置包太旧一步不跑。
真的入口、真的步骤模块和站点模块，引擎是 linkkit 里的假环境，站点的 register 换成记账的（真的要前置包的接口类，这里没有它）。只用本仓库的东西。"""
from __future__ import print_function

import importlib
import itertools

import fdtest
import linkkit as L
from optkit import Config

env = L.install()
Mode = L.Mode
EventRegistry = fdtest.load("Server.EventRegistry")
LOOKS = {"pot": "PotLook", "pan": "PanLook", "stove": "StoveLook", "board": "BoardLook"}     # 服务端：世界外观广播
SCENES = {"pot": "PotScenes", "pan": "PanScenes", "stove": "StoveScenes", "board": "BoardWatch"}   # 客户端：场景 / 旁观的声音
STATION_LOOK = {"board": "board", "pot": "pot", "pan": "pan", "grill": "stove"}
DISH_CRAFTS = (L.DIEGESIS + ".DishCrafts", "onCraft")
SWITCH = {"board": "cutting_board", "pot": "cooking_pot", "pan": "skillet", "grill": "stove"}
ORDER = ["board", "pot", "pan", "grill"]
STEPS = ORDER + ["table"]                     # 步骤表：四个站点，最后是前置包原版工作台上的登记


class Hooks(object):
    """前置包的原版工作台接口（Vanilla/Server/TableHooks）的替身：记下登了什么。"""

    API_VERSION = 1

    def __init__(self):
        self.vetoes, self.remainders = [], []

    def addVeto(self, fn):
        self.vetoes.append(fn)

    def addRemainder(self, fn):
        self.remainders.append(fn)


class BookHooks(object):
    """前置包配方书的客户端登记口（Vanilla/Client/TableBookHooks）的替身：记下登了什么。"""

    API_VERSION = 1

    def __init__(self):
        self.hidden = []

    def addHidden(self, fn):
        self.hidden.append(fn)


def apiOf(version=3, **flags):
    return type("Api", (object,), dict(flags, API_VERSION=version, Geometry="Geometry"))       # 砧板的客户端步骤要接口上的 Geometry


def mod(name):
    """现在的（清过之后重新导入的）Compat/Diegesis 模块。"""
    return importlib.import_module(L.DIEGESIS + "." + name)


def serverLooks():
    return dict((name, fdtest.load("Server." + module).enabled()) for name, module in LOOKS.items())


def clientScenes():
    return dict((name, mod(module).enabled()) for name, module in SCENES.items())


def bootServer(api=apiOf(FACING_HOOK=True), off=(), fresh=True, hooks=True, **config):
    """服务端启动一次：返回 (登记的站点按顺序, 每一步的状态, 世界外观广播开了哪些, 工作台拦截登记了没有)。fresh 为假时不清另一端的状态。"""
    if fresh:
        env.reset()
    EventRegistry.clearAll()
    for module in LOOKS.values():
        fdtest.load("Server." + module).enable(False)
    calls = []
    env.apis["server"] = api
    if hooks:
        env.tableHooks["server"] = Hooks() if hooks is True else hooks
    env.stubRegisters("server", calls, off)
    with Config(**config):
        env.boot("server")
    report = mod("Presence").report("server")
    return [name for name, _ in calls], dict((name, status) for name, status, _ in report["steps"]), serverLooks(), \
        DISH_CRAFTS in EventRegistry.handlerNames("CraftItemOutputChangeServerEvent")


def bootClient(api=apiOf(FACING_HOOK=True), off=(), fresh=True, hooks=True, **config):
    """客户端启动一次：返回 (登记的站点按顺序, 每一步的状态, 场景 / 旁观的声音开了哪些, 灶上东西的烟让出去了没有)。fresh 为假时不清另一端的状态。"""
    if fresh:
        env.reset()
    if hooks:
        env.tableHooks["client"] = BookHooks() if hooks is True else hooks
    StoveFlame = fdtest.load("Client.StoveFlame")
    StoveFlame._state["muted"] = False
    calls = []
    env.apis["client"] = api
    env.stubRegisters("client", calls, off)
    with Config(**config):
        env.boot("client")
        env.fire("client")
    report = mod("Presence").report("client")
    return [name for name, _ in calls], dict((name, status) for name, status, _ in report["steps"]), clientScenes(), StoveFlame.muted()


def testTheServerLinksTheFourStationsInTheirOldOrderAndTurnsOnEverythingThatHangsOnThem():
    calls, steps, looks, dishCrafts = bootServer()
    assert calls == ORDER and steps == dict((name, "ok") for name in STEPS), (calls, steps)
    assert looks == {"pot": True, "pan": True, "stove": True, "board": True}
    assert dishCrafts is True, "工作台拦截登记了"
    assert Mode.mode("server") == Mode.LINKED


def testTheClientLinksTheFourStationsInTheirOldOrderAndTurnsOnTheScenesTheSoundsAndTheSmokeHandOver():
    calls, steps, scenes, muted = bootClient()
    assert calls == ORDER and steps == dict((name, "ok") for name in STEPS), (calls, steps)
    assert scenes == {"pot": True, "pan": True, "stove": True, "board": True}
    assert muted is True, "炉灶站点登记了：灶上东西的烟交给站点"
    assert Mode.mode("client") == Mode.LINKED


def testTheStepsGetTheSameApiObjectTheBootFound():
    api = apiOf(4, FACING_HOOK=True)
    env.reset()
    got = []
    env.apis["server"] = api
    env.stubRegisters("server", got)
    env.boot("server")
    assert len(got) == 4 and all(seen is api for _, seen in got)


def testASwitchedOffStationIsSkippedOnBothSidesAndTakesOnlyItsOwnExtrasWithIt():
    for station in ORDER:
        calls, steps, looks, dishCrafts = bootServer(off=(station,))
        assert steps == dict((name, "skipped" if name == station else "ok") for name in STEPS), (station, steps)
        assert looks == dict((name, name != STATION_LOOK[station]) for name in LOOKS), (station, looks)
        assert dishCrafts is (station != "board"), "工作台拦截跟着砧板站点走"
        calls, steps, scenes, muted = bootClient(off=(station,))
        assert steps == dict((name, "skipped" if name == station else "ok") for name in STEPS), (station, steps)
        assert scenes == dict((name, name != STATION_LOOK[station]) for name in SCENES), (station, scenes)
        assert muted is (station != "grill"), "炉灶站点没登记：灶上东西的烟照放"
        assert calls == ORDER, "关了的也问过它（register 自己说不）：登记顺序不变"


def testServerAndClientAgreeOnEveryCombinationOfTheStationSwitches():
    for flags in itertools.product((True, False), repeat=4):
        off = tuple(station for station, on in zip(ORDER, flags) if not on)
        server = bootServer(off=off)
        client = bootClient(off=off)
        assert server[1] == client[1], (off, server[1], client[1])
        assert [server[2][STATION_LOOK[name]] for name in ORDER] == [client[2][STATION_LOOK[name]] for name in ORDER] == list(flags), off


def testTheCraftingGridSwitchOnlyTakesTheTableInterceptionAway():
    calls, steps, looks, dishCrafts = bootServer(remove_crafting_recipes=False)
    assert steps == dict((name, "ok") for name in STEPS) and looks["board"] is True, "站点都在，砧板的旁观声音也开着"
    assert dishCrafts is False, "工作台照旧出这些菜"
    assert bootServer()[3] is True


def testTheGrillStepNeedsTheFacingHookOnTheApiOnBothSides():
    server = bootServer(api=apiOf(3))
    assert server[0] == ["board", "pot", "pan"], "炉灶的 register 没被调"
    assert server[1] == {"board": "ok", "pot": "ok", "pan": "ok", "grill": "skipped", "table": "ok"} and server[2]["stove"] is False
    client = bootClient(api=apiOf(3))
    assert client[0] == ["board", "pot", "pan"] and client[1]["grill"] == "skipped"
    assert client[2]["stove"] is False and client[3] is False, "炉灶站点没登记：灶上东西的烟照放"


def testAnApiBelowTheRequiredVersionRunsNoStepOnEitherSide():
    for version in (0, 1, 2):
        server = bootServer(api=apiOf(version, FACING_HOOK=True))
        client = bootClient(api=apiOf(version, FACING_HOOK=True), fresh=False)
        assert Mode.mode("server") == Mode.OUTDATED and Mode.mode("client") == Mode.OUTDATED
        assert server[:2] == ([], {}) and client[:2] == ([], {}), (version, server, client)
        assert server[2] == dict((name, False) for name in LOOKS) and server[3] is False
        assert client[2] == dict((name, False) for name in SCENES) and client[3] is False


def testTheTableStepRegistersTheReturnsAndTheBoardStepTheDishVeto():
    """前置包的原版工作台（Vanilla/Server/TableHooks）：table 一步登还容器，砧板菜的否决跟着砧板站点和 remove_crafting_recipes 在 board 那一步登；
    接口不在（前置包太旧、没装它的内容包）：table 记成 skipped、什么都不登。"""
    TableHooksLink = lambda: mod("TableHooksLink")      # noqa: E731 - 每次开机后模块是新导入的
    hooks = Hooks()
    calls, steps, looks, dishCrafts = bootServer(hooks=hooks)
    assert steps["table"] == "ok" and hooks.remainders == [TableHooksLink().returns] and hooks.vetoes == [TableHooksLink().dishVeto]
    hooks = Hooks()
    bootServer(hooks=hooks, remove_crafting_recipes=False)
    assert hooks.remainders and hooks.vetoes == [], "配置里关了 remove_crafting_recipes：工作台照旧出砧板菜"
    hooks = Hooks()
    bootServer(hooks=hooks, off=("board",))
    assert hooks.remainders and hooks.vetoes == [], "砧板站点没登上：不拦"
    calls, steps, looks, dishCrafts = bootServer(hooks=False)
    assert steps["table"] == "skipped" and dishCrafts is True, "接口不在：table 跳过；原版合成格的拦截照旧"


def testTheClientTableStepHidesTheBoardDishesFromTheBookUnderTheVetosCondition():
    """前置包配方书的客户端登记口（Vanilla/Client/TableBookHooks）：和服务端登否决同一个条件（这一端 board 那一步登上了、
    remove_crafting_recipes 开着）在 table 那一步登"砧板菜不进书"；条件不满足什么都不登、记 ok（和服务端 table 一步一样）；登记口不在：skipped。"""
    TableClientLink = lambda: mod("TableClientLink")    # noqa: E731 - 每次开机后模块是新导入的
    hooks = BookHooks()
    calls, steps, scenes, muted = bootClient(hooks=hooks)
    assert steps["table"] == "ok" and hooks.hidden == [TableClientLink().hidden]
    hooks = BookHooks()
    assert bootClient(hooks=hooks, remove_crafting_recipes=False)[1]["table"] == "ok" and hooks.hidden == [], "配置关了：书照旧全列"
    hooks = BookHooks()
    assert bootClient(hooks=hooks, off=("board",))[1]["table"] == "ok" and hooks.hidden == [], "砧板站点没登上：不挡"
    assert bootClient(hooks=False)[1]["table"] == "skipped", "前置包没有这个登记口"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
