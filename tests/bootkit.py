# -*- coding: utf-8 -*-
"""bootkit - ServerBoot / ClientBoot（Compat/Diegesis 的两个联动入口）离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

两个入口导入四个站点两端的全部模块，要的引擎名字很多、各站点自己的假引擎又各不相同；这里把两端的 Engine 和 QuModLibs 换成
"什么名字都给一个无害替身"的模块（Loose），再导入真的入口和真的站点模块。服务端的前置包 Api 用真的（登记进前置包的 Server/Registry，
看登记了哪些站点），客户端的前置包 Api 用一个替身：真的 StationBehavior / 几何 / 声明模块，registerBehavior 转给前置包真的 Client/Registry。
Booted 是一次启动之后看得到的东西：两端各登记了哪些站点（按登记顺序）、世界外观广播和场景开没开、工作台拦截登记没有。
"""
from __future__ import print_function

import sys
import types

import dgtest
import fdtest
import panclient
import potfake

PACKAGE = fdtest.SCRIPTS


class _Stub(object):
    """没有预设的名字：能调、能取属性、能迭代，什么也不做。"""

    def __init__(self, name):
        self._name = name

    def __call__(self, *args, **kwargs):
        return _Stub(self._name + "()")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Stub(self._name + "." + name)

    def __iter__(self):
        return iter(())


class Loose(types.ModuleType):
    """缺的名字补一个 _Stub（from X import 名字 就能导入）。"""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = _Stub(name)
        setattr(self, name, value)
        return value


def _loosen(name):
    module = sys.modules[name]
    loose = Loose(name)
    loose.__dict__.update(module.__dict__)
    sys.modules[name] = loose
    return loose


class _ServerApi(object):
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
_loosen(PACKAGE + ".Client.Engine")
_loosen(PACKAGE + ".QuModLibs.Client")

ServerBoot = fdtest.load("Compat.Diegesis.ServerBoot")
ClientBoot = fdtest.load("Compat.Diegesis.ClientBoot")
EventRegistry = fdtest.load("Server.EventRegistry")
PotLook, PanLook, StoveLook, BoardLook = (fdtest.load("Server." + name) for name in ("PotLook", "PanLook", "StoveLook", "BoardLook"))
PotScenes, PanScenes, StoveScenes, BoardWatch = (fdtest.load("Compat.Diegesis." + name)
                                                 for name in ("PotScenes", "PanScenes", "StoveScenes", "BoardWatch"))
PotStation, PanStation, GrillStation, BoardStation = (fdtest.load("Shared.Rules." + name)
                                                      for name in ("PotStation", "PanStation", "GrillStation", "BoardStation"))
ServerRegistry = dgtest.load("Server.Registry")
ClientRegistry = dgtest.load("Client.Registry")
ServerApi = dgtest.load("Api.Server")
Geometry = dgtest.load("Shared.Geometry")
Schema = dgtest.load("Shared.Schema")

POT, BOARD, SKILLET, STOVE = PotStation.STATION_ID, BoardStation.STATION_ID, PanStation.STATION_ID, GrillStation.STATION_ID
POT_BLOCK, BOARD_BLOCK, SKILLET_BLOCK = PotStation.POT_BLOCKS[0], BoardStation.BOARD_BLOCKS[0], PanStation.PAN_BLOCKS[0]
STOVE_BLOCK = GrillStation.STOVE_BLOCKS[0]
DISH_CRAFTS = (PACKAGE + ".Compat.Diegesis.DishCrafts", "onCraft")


class Booted(object):
    """一次启动之后：stations 是登记的站点编号（按登记顺序），blocks 是每个站点绑的方块里第一个能不能被前置包认出来。"""

    def __init__(self, stations, looks, dishCrafts):
        self.stations = stations
        self.looks = looks                # {"pot": 世界外观广播开没开……}（服务端是 PotLook 这些，客户端是 PotScenes 这些）
        self.dishCrafts = dishCrafts

    def has(self, stationId):
        return stationId in self.stations


def bootServer(api=None):
    """ServerBoot 重新启动一次（前置包的服务端 Api 是 api，缺省真的那份）。"""
    ServerRegistry.clearAll()
    EventRegistry.clearAll()
    for look in (PotLook, PanLook, StoveLook, BoardLook):
        look.enable(False)
    ServerBoot._state["registered"] = False
    _ServerApi.api = api if api is not None else ServerApi
    assert ServerBoot.tryRegister() is True
    looks = {"pot": PotLook.enabled(), "pan": PanLook.enabled(), "stove": StoveLook.enabled(), "board": BoardLook.enabled()}
    return Booted(ServerRegistry.stationIds(), looks, DISH_CRAFTS in EventRegistry.handlerNames("CraftItemOutputChangeServerEvent"))


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
    """ClientBoot 重新来一次（LoadClientAddonScriptsAfter，前置包的客户端 Api 是 api，缺省上面的替身）。"""
    ClientRegistry.clearAll()
    for scenes in (PotScenes, PanScenes, StoveScenes, BoardWatch):
        scenes._state["on"] = False
    ClientBoot.clientApi.ImportModule = lambda name: api if api is not None else ClientApi
    ClientBoot.OnLoadClientAddonScriptsAfter()
    looks = {"pot": PotScenes.enabled(), "pan": PanScenes.enabled(), "stove": StoveScenes.enabled(), "board": BoardWatch.enabled()}
    return Booted(list(ClientRegistry._order), looks, None)
