# -*- coding: utf-8 -*-
"""panclient - 煎锅客户端模块（Compat/Diegesis 的 PanScene / PanScenes / PanView / PanModel / PanFx）离线测试的假引擎（不是测试本身，跑器只收 test_*.py）

这些模块只通过 Client/Engine.py 拿引擎、通过 QuModLibs.Client 挂监听。这里把两个换成假的，再导入真正的 Compat 模块，
就能在没有引擎的开发机上塞广播、跑渲染帧、点指针，然后看：摆了几个客户端掉落物、各在世界的哪里、模型 molang 变量被推成了什么、
放了哪些粒子和声音。假引擎只记录调用，没有预设的接口一律报 AttributeError。
PanView 要前置包客户端的几个纯模块（Geometry / Pick / View.box / Registry），经 dgtest 用真的；视图本身（FakeView）在这里写个最小的。
"""
from __future__ import print_function

import math
import sys
import types

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgtest
import fdtest

PACKAGE = fdtest.SCRIPTS
POS = (10, 64, 10)


class NS(object):
    def __init__(self, **fields):
        self.__dict__.update(fields)


class World(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.drops = {}                 # 掉落物 id -> {"item", "dim", "at", "pivot", "euler", "scale"}
        self.shadows = {}               # 实体 id -> 影子开着吗（SetEntityShadowShow 设过的才有）
        self.deleted = []
        self.molang = {}                # (坐标, 变量名) -> 值
        self.armed = set()
        self.particles = []             # {"id", "pos", "vars"}
        self.sounds = []                # {"name", "pos", "volume", "pitch"}
        self.exData = {}                # 坐标 -> 方块实体的 exData（已经是 NBT 包过的形式）
        self.blocks = {POS: ("arris:skillet", 0)}
        self.biomes = {}                # 坐标 -> 群系名（客户端 GetBiomeName 的回答）；没写的坐标回 biomeAll
        self.biomeAll = None            # 其余坐标统一的群系名；None = 那里没答案（接口回 None）
        self.biomeAsked = []            # 每次 GetBiomeName 问的坐标，按顺序
        self.dimension = 0
        self.foot = (10.5, 64.0, 7.5)
        self.screen = (960.0, 540.0)
        self.listeners = {}
        self.endpoints = {}
        self.calls = []
        self.counts = {}                # 引擎组件的接口名 -> 被调了几次（数"没变的东西不碰引擎"用；要数一段就先 counts.clear()）
        self._next = 0

    def nextId(self):
        self._next += 1
        return "e%d" % self._next


world = World()


class Comp(object):
    def __init__(self, owner):
        self.owner = owner

    def __getattribute__(self, name):
        found = object.__getattribute__(self, name)
        if callable(found) and not name.startswith("_"):
            world.counts[name] = world.counts.get(name, 0) + 1          # 取出来就是要调：每次取记一次
        return found

    # ---- 物品 ----
    def AddDropItemToWorld(self, item, dim, pos, rx=0, ry=0):
        entityId = world.nextId()
        world.drops[entityId] = {"item": dict(item), "dim": dim, "at": tuple(pos), "pivot": None, "euler": None, "scale": None}
        return entityId

    def SetDropItemTransform(self, entityId, pivot, euler, scale):
        drop = world.drops[entityId]
        drop["pivot"], drop["euler"], drop["scale"] = tuple(pivot), tuple(euler), scale
        return True

    def SetEntityShadowShow(self, flag):
        world.shadows[self.owner] = bool(flag)

    def DeleteClientDropItemEntity(self, entityId):
        world.deleted.append(entityId)
        world.drops.pop(entityId, None)
        return True

    def GetItemBasicInfo(self, name, aux=0):
        return {"itemName": "name:" + name, "maxStackSize": 64}

    # ---- 方块 ----
    def GetBlock(self, pos):
        return world.blocks.get(tuple(pos))

    def GetBlockEntityData(self, pos):
        return {"exData": world.exData.get(tuple(pos), {})}

    def GetBiomeName(self, pos):
        """CreateBiome(levelId).GetBiomeName((x, y, z))：官方文档里参数是 tuple(int,int,int)，回群系名（不带命名空间），那里没加载回 None。"""
        assert isinstance(pos, tuple) and len(pos) == 3 and all(isinstance(value, int) for value in pos), "要三个整数的元组：%r" % (pos,)
        world.biomeAsked.append(pos)
        return world.biomes.get(pos, world.biomeAll)

    def SetEnableBlockEntityAnimations(self, pos, on):
        world.armed.add(tuple(pos))
        return True

    def SetBlockEntityMolangValue(self, pos, name, value):
        world.molang[(tuple(pos), name)] = value
        return True

    def GetBlockEntityMolangValue(self, pos, name):
        return world.molang.get((tuple(pos), name))

    # ---- 粒子、声音 ----
    def Create(self, identifier, pos):
        particleId = world.nextId()
        world.particles.append({"id": identifier, "pos": tuple(pos), "vars": {}, "particle": particleId})
        return particleId

    def SetVariable(self, particleId, name, value):
        for particle in world.particles:
            if particle["particle"] == particleId:
                particle["vars"][name] = value

    def PlayCustomMusic(self, name, pos, volume, pitch, loop, extra):
        world.sounds.append({"name": name, "pos": tuple(pos), "volume": volume, "pitch": pitch})
        return world.nextId()

    def StopCustomMusicById(self, musicId, fade):
        return True

    # ---- 游戏、位置 ----
    def GetScreenSize(self):
        return world.screen

    def GetCurrentDimension(self):
        return world.dimension

    def GetFootPos(self):
        return world.foot


class Factory(object):
    def __getattr__(self, name):
        if name.startswith("Create"):
            return lambda owner=None: Comp(owner)
        raise AttributeError(name)


def unwrapDeep(value):
    if isinstance(value, dict):
        if "__value__" in value and "__type__" in value:
            return unwrapDeep(value["__value__"])
        return dict((key, unwrapDeep(item)) for key, item in value.items())
    if isinstance(value, list):
        return [unwrapDeep(item) for item in value]
    return value


def _install():
    engine = types.ModuleType(PACKAGE + ".Client.Engine")
    engine.compFactory = Factory()
    engine.levelId = "level"
    engine.playerId = "player"
    engine.Call = lambda *args: world.calls.append(args)
    engine.clientApi = NS(ImportModule=lambda name: None, PushScreen=lambda *a: None, GetEngineCompFactory=lambda: Factory())
    engine.unwrapDeep = unwrapDeep
    engine.blockEntityExData = lambda pos: world.exData.get(tuple(pos), {})

    def addDropItem(item, dimensionId, pos):
        """Client/Engine.addDropItem 的替身：建掉落物、关影子。"""
        entityId = Comp(None).AddDropItemToWorld(item, dimensionId, pos)
        Comp(entityId).SetEntityShadowShow(False)
        return entityId

    engine.addDropItem = addDropItem
    sys.modules[PACKAGE + ".Client.Engine"] = engine
    qu = PACKAGE + ".QuModLibs"
    package = types.ModuleType(qu)
    package.__path__ = []
    client = types.ModuleType(qu + ".Client")

    def listen(name):
        def wrap(fn):
            world.listeners.setdefault(name, []).append(fn)
            return fn
        return wrap

    def allowCall(fn):
        world.endpoints[fn.__name__] = fn
        return fn

    client.Listen, client.AllowCall = listen, allowCall
    client.clientApi, client.levelId, client.playerId, client.Call = engine.clientApi, "level", "player", engine.Call
    sys.modules[qu], sys.modules[qu + ".Client"] = package, client


_installed = []


def install():
    """装假引擎（只装一次）并返回共享的世界；每个用例开头 world.reset()。"""
    if not _installed:
        _install()
        _installed.append(True)
    return world


def load(dotted):
    install()
    return fdtest.load(dotted)


# ---------------------------------------------------------------- 站点视图的替身（PanView 用）

class FakeView(object):
    """StationView 的最小替身：toWorld / toStation 用前置包真的几何（站点空间按 yaw 转），其余只记下被调用的。"""

    def __init__(self, pos=POS, yaw=0, hand=None):
        self.pos = pos
        self.dimensionId = 0
        self.yaw = yaw
        self.hand = hand
        self.actions = []
        self.shiftDown = False
        self.closed = False
        self.geometry = dgtest.load("Shared.Geometry")
        self.items = []
        self.state = NS(getItems=lambda group: list(self.items))
        self.booked = None
        self.rays = {}
        self.input, self.fitting = "mouse", 0             # 输入方式；fits() 的回答（放得进的那一格，放不进 None）
        self.buzzes = []                                  # view.buzz(种类) 要过的轻震

    def buzz(self, kind):
        self.buzzes.append(kind)

    def toWorld(self, x, y, z):
        return self.geometry.stationPointToWorld(self.yaw, x, y, z, self.pos[0], self.pos[1], self.pos[2])

    def toStation(self, wx, wy, wz):
        return self.geometry.worldPointToStation(self.yaw, wx, wy, wz, self.pos[0], self.pos[1], self.pos[2])

    def rayAt(self, screen):
        return self.rays.get(tuple(screen))

    def fits(self, group):
        return self.fitting

    def sendAction(self, name, data=None):
        self.actions.append((name, data))

    def close(self):
        self.closed = True

    def book(self, source):
        self.booked = source


def makeApi():
    """前置包客户端 Api 的替身：box / Geometry / StationBehavior 是真的。"""
    registry = dgtest.load("Client.Registry")
    pick = dgtest.load("Shared.Pick")
    geometry = dgtest.load("Shared.Geometry")

    def box(key, lo, hi, payload=None, visible=True):
        node = pick.Pickable(key, matrix=geometry.identity(), visible=visible, payload=payload)
        node.setBox(lo, hi)
        return node

    return NS(box=box, Geometry=geometry, StationBehavior=registry.StationBehavior, Pick=pick, API_VERSION=2, JAVA_FLIGHT=0.4, TOUCH="touch",
              Schema=dgtest.load("Shared.Schema"), registered=[], registerBehavior=lambda *args, **kwargs: None)


def ray(origin, target):
    """从 origin 射向 target 的站点射线（6 元组，方向单位化）。"""
    d = [target[i] - origin[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in d))
    return tuple(origin) + tuple(c / n for c in d)
