# -*- coding: utf-8 -*-
"""farmengine - 种植服务端模块的假引擎（测试用的公共小工具，不是测试本身）

install() 把 Server/Helpers 里碰引擎的四个模块（Engine / Fx / Items / Player）换成假的，
之后就能离线导入 Server/Crops、CropTicks、BoneMeal、RichSoil、OrganicCompost、MushroomColony、Straw，
对着一个字典做的世界跑它们的事件处理函数。假引擎只实现这些模块用到的那几个接口，签名照 ModAPI 文档。
"""
from __future__ import print_function

import sys
import types

import fdtest

PACKAGE = fdtest.SCRIPTS + ".Server.Helpers"
AIR = "minecraft:air"
_DEFAULT_STATES = {
    "minecraft:farmland": {"moisturized_amount": 0},
    "arris:brown_mushroom_colony": {"arris:growth": 0},
    "arris:red_mushroom_colony": {"arris:growth": 0},
}


class Level(object):
    def __init__(self):
        self.blocks = {}
        self.states = {}
        self.water = set()
        self.raining = False
        self.entities = []          # CreateEngineItemEntity 掉出来的 (itemDict, dim, pos)
        self.sounds = []
        self.particles = []
        self.hands = {}
        self.creative = set()
        self.destroyed = []
        self.setCalls = []
        self.tips = []

    # ---- 摆世界 ----
    def put(self, pos, name, dim=0, **states):
        self.blocks[(dim,) + tuple(pos)] = name
        base = dict(_DEFAULT_STATES.get(name, {}))
        base.update(states)
        if base:
            self.states[(dim,) + tuple(pos)] = base
        else:
            self.states.pop((dim,) + tuple(pos), None)
        return self

    def fill(self, name, low, high, dim=0, **states):
        for x in range(low[0], high[0] + 1):
            for y in range(low[1], high[1] + 1):
                for z in range(low[2], high[2] + 1):
                    self.put((x, y, z), name, dim, **states)
        return self

    def nameAt(self, pos, dim=0):
        return self.blocks.get((dim,) + tuple(pos), AIR)

    def statesAt(self, pos, dim=0):
        return self.states.get((dim,) + tuple(pos))

    # ---- 引擎接口 ----
    def top(self, x, z, dim):
        ys = [key[2] for key, name in self.blocks.items() if key[0] == dim and key[1] == x and key[3] == z and name != AIR]
        return max(ys) if ys else 0


class _BlockInfo(object):
    def __init__(self, level):
        self.level = level

    def GetBlockNew(self, pos, dim):
        return {"name": self.level.nameAt(pos, dim), "aux": 0}

    def SetBlockNew(self, pos, blockDict, handling=0, dimensionId=0, isLegacy=False, updateNeighbors=True):
        self.level.setCalls.append((tuple(pos), blockDict["name"], dimensionId, handling, updateNeighbors))
        self.level.put(pos, blockDict["name"], dimensionId)
        return True

    def GetLiquidBlock(self, pos, dim):
        return {"name": "minecraft:water"} if (dim,) + tuple(pos) in self.level.water else None

    def GetTopBlockHeight(self, pos, dim=0):
        return self.level.top(pos[0], pos[1], dim)


class _BlockState(object):
    def __init__(self, level):
        self.level = level

    def GetBlockStates(self, pos, dim):
        states = self.level.statesAt(pos, dim)
        return dict(states) if states is not None else None

    def SetBlockStates(self, pos, states, dim):
        self.level.states[(dim,) + tuple(pos)] = dict(states)
        return True


class _Weather(object):
    def __init__(self, level):
        self.level = level

    def IsRaining(self):
        return self.level.raining


class _Game(object):
    def __init__(self, level):
        self.level = level

    def GetPlayerGameType(self, playerId):
        return 1 if playerId in self.level.creative else 0


class _CompFactory(object):
    def __init__(self, level):
        self.level = level

    def CreateBlockInfo(self, levelId):
        return _BlockInfo(self.level)

    def CreateBlockState(self, levelId):
        return _BlockState(self.level)

    def CreateWeather(self, levelId):
        return _Weather(self.level)

    def CreateGame(self, levelId):
        return _Game(self.level)


def install(level):
    """把假的 Helpers 模块放进 sys.modules（要在导入 Server 模块之前调）；返回各假模块。"""
    for key in [k for k in sys.modules if k.startswith(fdtest.SCRIPTS + ".Server.")]:
        del sys.modules[key]
    factory = _CompFactory(level)

    engine = types.ModuleType(PACKAGE + ".Engine")
    engine.compFactory = factory
    engine.levelId = "level"

    class System(object):
        @staticmethod
        def CreateEngineItemEntity(itemDict, dimensionId, pos):
            level.entities.append((dict(itemDict), dimensionId, tuple(pos)))
            return "entity%d" % len(level.entities)

    engine.System = System
    engine.GetBlockName = lambda pos, dim: level.nameAt(pos, dim)
    engine.GetCarriedItem = lambda playerId, getUserData=False: level.hands.get(playerId)
    engine.ShowTip = lambda playerId, text: level.tips.append((playerId, text))
    engine.DestroyEntity = lambda entityId: level.destroyed.append(entityId)

    fx = types.ModuleType(PACKAGE + ".Fx")
    fx.ToAllPlayerPlaySound = lambda dim, pos, name: level.sounds.append((dim, tuple(pos), name))
    fx.ToAllPlayerGrowthParticle = lambda pos: level.particles.append(tuple(pos))

    items = types.ModuleType(PACKAGE + ".Items")
    items.GetItemType = lambda itemDict: "hoe" if itemDict and itemDict["newItemName"].endswith("_hoe") else "item"
    items.IsKnife = lambda name: name.endswith("_knife")

    player = types.ModuleType(PACKAGE + ".Player")
    player.IsCreative = lambda playerId: playerId in level.creative
    player.SetPlayerUsedCD = lambda playerId: False

    def setNotCreate(playerId, itemDict):
        if playerId not in level.creative:
            itemDict["count"] -= 1

    player.SetNotCreateItem = setNotCreate
    player.SetCarriedDurability = lambda *args: None

    for module in (engine, fx, items, player):
        sys.modules[module.__name__] = module
    return engine, fx, items, player
