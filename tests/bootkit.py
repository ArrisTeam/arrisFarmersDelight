# -*- coding: utf-8 -*-
"""bootkit - ServerBoot / ClientBoot（Compat/Diegesis 的两个联动入口）离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

两个入口经 Presence 和步骤表（ServerSteps / ClientSteps）导入四个站点两端的全部模块，要的引擎名字很多、各站点自己的假引擎又各不相同；
这里把两端的 Engine 和 QuModLibs 换成"什么名字都给一个无害替身"的模块（Loose），再导入真的入口和真的站点模块。服务端的前置包 Api 用真的
（登记进前置包的 Server/Registry，看登记了哪些站点），客户端的前置包 Api 用一个替身：真的 StationBehavior / 几何 / 声明模块，
registerBehavior 转给前置包真的 Client/Registry。前置包的接口由 _ServerApi / _ClientApi 的 ImportModule 回答（ABSENT 是没装）。
一次启动 = 入口模块重新导入一遍（它导入时就挂 Presence，前置包在场就联动）+ 发"全部 Addon 脚本加载完成"那个事件（Presence.onServerLoaded / onClientLoaded）。
Booted 是一次启动之后看得到的东西：两端各登记了哪些站点（按登记顺序）、世界外观广播和场景开没开、工作台拦截登记没有、这一端的运行模式和每一步的状态。
"""
from __future__ import print_function

import importlib

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest
import linkkit
import panclient
import potfake
from linkkit import loosen as _loosen

try:
    from importlib import reload      # py3
except ImportError:
    pass                              # py2：内建的 reload

PACKAGE = fdtest.SCRIPTS
ABSENT = object()                     # bootServer / bootClient 的参数：没装前置包（ImportModule 回答 None）；不给（None）是缺省的那份前置包接口


class _ServerApi(object):
    """serverApi 的替身：ImportModule 回答 api（前置包的服务端接口，没装是 None）；问前置包的原版工作台接口（Compat/Diegesis/TableHooksLink）时
    前置包在场就给它真的那个模块（Vanilla/Server/TableHooks），不在是 None。"""
    api = None

    @classmethod
    def ImportModule(cls, name):
        if name == linkkit.TABLE_HOOKS:
            return TableHooks if cls.api is not None else None
        return cls.api


class _ClientApi(object):
    """clientApi 的替身：同上。"""
    api = None

    @classmethod
    def ImportModule(cls, name):
        return cls.api


potfake.install()
panclient.install()
_loosen(PACKAGE + ".Server.Helpers.Engine")
_serverQu = _loosen(PACKAGE + ".QuModLibs.Server")
_serverQu.Listen = lambda *args, **kwargs: (lambda func: func)
_serverQu.AllowCall = lambda func: func
_serverQu.InjectHttpPlayerId = lambda func: func
_serverQu.serverApi = _ServerApi
_serverQu.ImportModule = importlib.import_module
_loosen(PACKAGE + ".Client.Engine")
_clientQu = _loosen(PACKAGE + ".QuModLibs.Client")
_clientQu.clientApi = _ClientApi
_clientQu.ImportModule = importlib.import_module

ServerBoot = fdtest.load("Compat.Diegesis.ServerBoot")
ClientBoot = fdtest.load("Compat.Diegesis.ClientBoot")
Presence = fdtest.load("Compat.Diegesis.Presence")
Mode = linkkit.Mode
EventRegistry = fdtest.load("Server.EventRegistry")
PotLook, PanLook, StoveLook, BoardLook = (fdtest.load("Server." + name) for name in ("PotLook", "PanLook", "StoveLook", "BoardLook"))
PotScenes, PanScenes, StoveScenes, BoardWatch = (fdtest.load("Compat.Diegesis." + name)
                                                 for name in ("PotScenes", "PanScenes", "StoveScenes", "BoardWatch"))
PotStation, PanStation, GrillStation, BoardStation = (fdtest.load("Shared.Rules." + name)
                                                      for name in ("PotStation", "PanStation", "GrillStation", "BoardStation"))
ServerRegistry = dgtest.load("Server.Registry")
ClientRegistry = dgtest.load("Client.Registry")
ServerApi = dgtest.load("Api.Server")
TableHooks = dgtest.load("Vanilla.Server.TableHooks")
Geometry = dgtest.load("Shared.Geometry")
Schema = dgtest.load("Shared.Schema")

POT, BOARD, SKILLET, STOVE = PotStation.STATION_ID, BoardStation.STATION_ID, PanStation.STATION_ID, GrillStation.STATION_ID
POT_BLOCK, BOARD_BLOCK, SKILLET_BLOCK = PotStation.POT_BLOCKS[0], BoardStation.BOARD_BLOCKS[0], PanStation.PAN_BLOCKS[0]
STOVE_BLOCK = GrillStation.STOVE_BLOCKS[0]
DISH_CRAFTS = (PACKAGE + ".Compat.Diegesis.DishCrafts", "onCraft")


class Booted(object):
    """一次启动之后：stations 是登记的站点编号（按登记顺序），looks 是世界外观广播 / 场景开没开，dishCrafts 是工作台拦截登记了没有，
    mode 是这一端的运行模式（Shared/Rules/HandsOnMode），steps 是每一步的状态 {步骤名: ok / skipped / failed}，
    tableHooks 是前置包真的原版工作台接口上登了什么 {"vetoes": 个数, "remainders": 个数}（客户端是 None）。"""

    def __init__(self, stations, looks, dishCrafts, mode=None, steps=None, tableHooks=None):
        self.stations = stations
        self.looks = looks                # {"pot": 世界外观广播开没开……}（服务端是 PotLook 这些，客户端是 PotScenes 这些）
        self.dishCrafts = dishCrafts
        self.mode = mode
        self.steps = steps or {}
        self.tableHooks = tableHooks

    def has(self, stationId):
        return stationId in self.stations


def _answer(api, default):
    return None if api is ABSENT else (default if api is None else api)


def _stepsOf(side):
    return dict((name, status) for name, status, _ in Presence.report(side)["steps"])


def bootServer(api=None):
    """ServerBoot 重新启动一次：入口重新导入（前置包的服务端 Api 是 api，缺省真的那份，ABSENT 是没装），再发 LoadServerAddonScriptsAfter。"""
    ServerRegistry.clearAll()
    EventRegistry.clearAll()
    TableHooks.clear()
    for look in (PotLook, PanLook, StoveLook, BoardLook):
        look.enable(False)
    linkkit.unlink("server")
    _ServerApi.api = _answer(api, ServerApi)
    reload(ServerBoot)
    Presence.onServerLoaded()
    looks = {"pot": PotLook.enabled(), "pan": PanLook.enabled(), "stove": StoveLook.enabled(), "board": BoardLook.enabled()}
    hooks = {"vetoes": len(TableHooks._vetoes), "remainders": len(TableHooks._remainders)}
    return Booted(ServerRegistry.stationIds(), looks, DISH_CRAFTS in EventRegistry.handlerNames("CraftItemOutputChangeServerEvent"),
                  Mode.mode("server"), _stepsOf("server"), hooks)


class ClientApi(object):
    """前置包客户端 Api 的替身：登记转给前置包真的 Client/Registry（站点认不认方块就看它）。"""
    API_VERSION = 3
    FACING_HOOK = True
    TOUCH = "touch"
    Geometry = Geometry
    Schema = Schema
    StationBehavior = ClientRegistry.StationBehavior

    @staticmethod
    def registerBehavior(stationId, blocks, factory=None, schema=None, sneakFallback=True, canOpen=None, facing=None):
        return ClientRegistry.registerBehavior(stationId, blocks, factory or ClientRegistry.StationBehavior, schema, sneakFallback,
                                               canOpen, facing)


def bootClient(api=None):
    """ClientBoot 重新来一次：入口重新导入（前置包的客户端 Api 是 api，缺省上面的替身，ABSENT 是没装），再发 LoadClientAddonScriptsAfter。"""
    ClientRegistry.clearAll()
    for scenes in (PotScenes, PanScenes, StoveScenes, BoardWatch):
        scenes._state["on"] = False
    linkkit.unlink("client")
    _ClientApi.api = _answer(api, ClientApi)
    reload(ClientBoot)
    Presence.onClientLoaded()
    looks = {"pot": PotScenes.enabled(), "pan": PanScenes.enabled(), "stove": StoveScenes.enabled(), "board": BoardWatch.enabled()}
    return Booted(list(ClientRegistry._order), looks, None, Mode.mode("client"), _stepsOf("client"))
