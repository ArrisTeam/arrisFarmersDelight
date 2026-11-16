# -*- coding: utf-8 -*-
"""boardclient - 砧板站点客户端（Compat/Diegesis/BoardView 等）离线测试的假引擎和假视图（不是测试本身，跑器只收 test_*.py）

主包的 Client/Engine.py 经 QuModLibs.Client 拿引擎；这里先把 QuModLibs 换成假的（clientApi.GetEngineCompFactory() 给一个记账的假工厂），
再导入真的 BoardView / BoardDraw / BoardCutter / BoardFx。假视图（FakeView）有状态镜像、手上的东西、背包端口、道具（记下建了什么、挪到哪）、
sendAction 的记录、粒子的记录；站点坐标和世界坐标的换算用前置包真的 Shared/Geometry（朝北、玩家在北面时 yaw 0）。
"""
from __future__ import print_function

import copy
import math
import sys
import types

import dgtest
import fdtest

PACKAGE = fdtest.SCRIPTS
STATION_POS = (10, 64, 10)
TYPES = {"arris:iron_knife": "sword", "arris:flint_knife": "sword", "minecraft:iron_axe": "axe", "minecraft:cobblestone": "block",
         "minecraft:oak_log": "block"}


class FakeClientEngine(object):
    """记账的假引擎：背包、选中格、副手、物品信息、方块、声音。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.inventory = [None] * 36
        self.selected = 0
        self.offhand = None
        self.played = []
        self.playedAt = []                                # 每一声放在哪（和 played 一一对应）
        self.molang = {}                                  # 方块实体的 molang 变量（砧板的描边）
        self.block = ("arris:cutting_board", 2)          # direction 2 = 朝北
        self.dimension = 0
        self.particles = []                              # 主包自己放的粒子：{"id": 标识, "pos": 位置, "vars": {变量: 值}}

    # ---- 组件（工厂按需返回自己：下面这些方法就是组件的接口）
    def GetItemBasicInfo(self, name, aux=0):
        return {"itemType": TYPES.get(name, "food"), "maxStackSize": 64, "itemName": name.split(":")[-1]}

    def GetItemTags(self, name):
        return []

    def GetSlotId(self):
        """客户端物品组件的"当前手持的快捷栏格"（GetSelectSlotId 只有服务端有，这里故意不给，谁在客户端调它测试就炸）。"""
        return self.selected

    def GetOffhandItem(self, getUserData=False):
        return copy.deepcopy(self.offhand)

    def GetBlock(self, pos):
        return self.block

    def GetCurrentDimension(self):
        return self.dimension

    def SetEnableBlockEntityAnimations(self, pos, enable):
        return True

    def SetBlockEntityMolangValue(self, pos, name, value):
        self.molang[name] = value
        return True

    def Create(self, identifier, pos):
        self.particles.append({"id": identifier, "pos": tuple(pos), "vars": {}})
        return len(self.particles)

    def SetVariable(self, particleId, name, value):
        self.particles[particleId - 1]["vars"][name] = value
        return True

    def PlayCustomMusic(self, name, pos, volume, pitch, loop, entityId):
        self.played.append((name, volume, pitch))
        self.playedAt.append(tuple(pos))
        return "id"


class _Factory(object):
    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        if name.startswith("Create"):
            return lambda _id=None: self.engine
        raise AttributeError(name)


class _ClientApi(object):
    def __init__(self, engine):
        self.engine = engine

    def GetEngineCompFactory(self):
        return _Factory(self.engine)

    @staticmethod
    def ImportModule(name):
        return None


engine = FakeClientEngine()


def _install():
    quPackage = types.ModuleType(PACKAGE + ".QuModLibs")
    quPackage.__path__ = []
    quClient = types.ModuleType(PACKAGE + ".QuModLibs.Client")
    quClient.clientApi, quClient.levelId, quClient.playerId = _ClientApi(engine), "level", "me"
    quClient.Call = lambda *args: None
    quClient.Listen = lambda *args, **kwargs: (lambda fn: fn)
    quClient.AllowCall = lambda fn: fn
    sys.modules[PACKAGE + ".QuModLibs"], sys.modules[PACKAGE + ".QuModLibs.Client"] = quPackage, quClient


_install()
BoardView = fdtest.load("Compat.Diegesis.BoardView")
BoardDraw = fdtest.load("Compat.Diegesis.BoardDraw")
BoardFx = fdtest.load("Compat.Diegesis.BoardFx")
BoardWatch = fdtest.load("Compat.Diegesis.BoardWatch")
BlockItems = fdtest.load("Client.BlockItems")
Geometry = dgtest.load("Shared.Geometry")
KernelSchema = dgtest.load("Shared.Schema")
Items = dgtest.load("Shared.Items")


class FakeProp(object):
    def __init__(self, item, center, flat, along, facing, roll, scale, matrix, line=False):
        self.item, self.center, self.flat, self.along, self.facing, self.roll, self.scale, self.matrix = \
            item, tuple(center), flat, along, facing, roll, scale, matrix
        self.line, self.alive, self.moves = line, True, 0

    def move(self, center=None, along=None, facing=None, roll=None, scale=None, matrix=None):
        self.center = tuple(center) if center is not None else self.center
        self.along = along if along is not None else self.along
        self.facing = facing if facing is not None else self.facing
        self.roll = roll if roll is not None else self.roll
        self.scale = scale if scale is not None else self.scale
        self.moves += 1
        return True


class FakeProps(object):
    def __init__(self):
        self.made = []

    def item(self, item, center, flat=True, along=(1.0, 0.0), facing=(0.0, -1.0), roll=0.0, scale=1.0, matrix=None):
        prop = FakeProp(item, center, flat, along, facing, roll, scale, matrix)
        self.made.append(prop)
        return prop

    def line(self, a, b, hot=False):
        prop = FakeProp({"newItemName": "stroke_hot" if hot else "stroke"}, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), True,
                        (b[0] - a[0], b[2] - a[2]), None, 0.0, math.hypot(b[0] - a[0], b[2] - a[2]) / 8.0, None, line=True)
        self.made.append(prop)
        return prop

    def remove(self, prop):
        prop.alive = False

    def clear(self):
        for prop in self.made:
            prop.alive = False

    def live(self):
        return [prop for prop in self.made if prop.alive]


class FakeState(object):
    def __init__(self):
        self.board, self.layers = None, []

    def getItem(self, ref):
        return self.board if ref == ("board", 0) else None

    def getItems(self, group):
        return list(self.layers) + [None] * (9 - len(self.layers)) if group == "layers" else [self.board]


class FakePorts(object):
    def inventory(self):
        return [copy.deepcopy(item) for item in engine.inventory]

    def maxStack(self, item):
        return 64


class FakeView(object):
    def __init__(self):
        self.pos, self.yaw, self.dimensionId = STATION_POS, 0, 0
        self.state, self.data, self.hand = FakeState(), {}, None
        self.props, self.ports = FakeProps(), FakePorts()
        self.sent, self.dust = [], []
        self.input = "mouse"

    def sendAction(self, name, data=None):
        self.sent.append((name, data or {}))

    def overUi(self, pos):
        return False

    def toWorld(self, x, y, z):
        return Geometry.stationPointToWorld(self.yaw, x, y, z, self.pos[0], self.pos[1], self.pos[2])

    def toStation(self, wx, wy, wz):
        return Geometry.worldPointToStation(self.yaw, wx, wy, wz, self.pos[0], self.pos[1], self.pos[2])

    def particles(self, identifier, point, color=None, count=None):
        self.dust.append((identifier, tuple(point), color, count))


class StationBehavior(object):
    def __init__(self, view):
        self.view = view


class FakeApi(object):
    """前置包客户端 Api 里表现用得到的那几样。"""
    StationBehavior = StationBehavior
    Geometry = Geometry
    ITEM_SPAN = 8.0
    Schema = KernelSchema
    TOUCH = "touch"
    API_VERSION = 3

    def __init__(self):
        self.registered = None

    def registerBehavior(self, stationId, blocks, factory=None, schema=None, sneakFallback=True, canOpen=None):
        self.registered = (stationId, blocks, factory, schema, canOpen)

    @staticmethod
    def box(key, lo, hi, payload=None):
        return types.SimpleNamespace(key=key, lo=lo, hi=hi, payload=payload) if hasattr(types, "SimpleNamespace") \
            else type("Box", (), {"key": key, "lo": lo, "hi": hi, "payload": payload})()


class Hit(object):
    def __init__(self, key):
        self.node = type("Node", (), {"key": key, "payload": None})()


class Event(object):
    """PointerEvent 的假货。"""

    def __init__(self, kind, key=None, ray=None, button=0, quick=False, screen=(100.0, 100.0)):
        self.kind, self.hit, self.ray, self.button, self.quick, self.screen = kind, Hit(key) if key else None, ray, button, quick, screen
        self.point, self.pressed = None, kind == "down"


ORIGIN = (7.5, 35.5, -21.0)


def rayTo(point):
    """从机位射向站点里的 point 的射线（站点射线）。"""
    direction = (point[0] - ORIGIN[0], point[1] - ORIGIN[1], point[2] - ORIGIN[2])
    return Geometry.makeRay(ORIGIN, direction)


def item(name, count=1, aux=0, **extra):
    return dict({"newItemName": name, "newAuxValue": aux, "count": count}, **extra)


def station():
    """装好的表现：(行为对象, 视图)。engine 先清干净。"""
    engine.reset()
    BlockItems._hidden.clear()
    api = FakeApi()
    BoardView.register(api)
    view = FakeView()
    behavior = api.registered[2](view)
    return behavior, view, api
