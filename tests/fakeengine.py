# -*- coding: utf-8 -*-
"""fakeengine - 离线测试服务端"胶水"模块的假引擎（不是测试本身，跑器只收 test_*.py）

Server/ 下的玩法模块只通过 Server/Helpers/Engine.py 拿引擎（compFactory、levelId、System……），
Helpers 里别的模块（Fx、Items、Player、Placement）也只依赖它。这里先把 Engine 换成假的，再导入真正的 Helpers 和玩法模块，
就能在没有引擎的开发机上用事件参数字典驱动它们，检查：条件判断、取消标志、消耗物品、生成的掉落物、记下的音效。

假引擎只记录调用、按测试预设返回，不模拟游戏规则；没有预设的接口一律报 AttributeError，免得悄悄放过拼错的 API 名。
用法：
    world = fakeengine.install()
    Livestock = fdtest.load("Server.Livestock")      # 之后才能导入 Server 里的玩法模块
    world.addPlayer("p1", hand={"newItemName": "arris:horse_feed", "newAuxValue": 0, "count": 3})
    Registry.dispatch("PlayerInteractServerEvent", args, "arris:horse_feed")
"""
from __future__ import print_function

import sys
import types

import fdtest

ENGINE_MODULE = fdtest.SCRIPTS + ".Server.Helpers.Engine"
LEVEL_ID = "level"
DIMENSION = 0


class _Comp(object):
    """一个实体 / 世界的组件：方法名 → 世界里的实现；没有的方法报 AttributeError。"""

    def __init__(self, methods):
        self._methods = methods

    def __getattr__(self, name):
        try:
            return self._methods[name]
        except KeyError:
            raise AttributeError("假引擎没有实现 %s（用到它的测试请在 fakeengine.py 里补上）" % name)


class FakeWorld(object):
    def __init__(self):
        self.entities = {}      # id -> {"type", "tamed", "health", "maxHealth", "fire", "owner", "effects"}
        self.players = {}       # id -> {"hand", "creative", "pos", "hunger", "given"}
        self.blocks = {}        # (dim, x, y, z) -> {"name", "states", "data"}
        self.itemEntities = {}  # id -> itemDict
        self.spawned = []       # [(itemDict, dim, pos)]
        self.destroyed = []     # 被 DestroyEntity 删掉的实体 id
        self.sounds = []        # [(声音名, 位置)]
        self.calls = []         # [(目标, 端点, 参数)]
        self.timers = []        # [(秒, 函数, 参数)]
        self.modAttr = {}
        self.listened = []      # AddBlockItemListenForUseEvent 的方块名
        self.components = {}    # 实体 id -> {组件名: JSON 串}
        self.tags = {"arris:iron_knife": ["arris:knife"]}
        self._nextId = [1000]

    # ---- 预设 ----
    def addEntity(self, entityId, entityType, **fields):
        entity = {"type": entityType, "tamed": False, "health": 10.0, "maxHealth": 20.0, "fire": False, "owner": None,
                  "effects": []}
        entity.update(fields)
        self.entities[entityId] = entity
        return entity

    def addPlayer(self, playerId, hand=None, creative=False, pos=(0.5, 64.0, 0.5)):
        self.players[playerId] = {"hand": hand, "creative": creative, "pos": pos, "hunger": 10, "given": []}
        self.entities[playerId] = {"type": "minecraft:player", "tamed": False, "health": 20.0, "maxHealth": 20.0,
                                   "fire": False, "owner": None, "effects": []}
        return self.players[playerId]

    def setBlock(self, x, y, z, name, states=None, data=None, dim=DIMENSION):
        self.blocks[(dim, x, y, z)] = {"name": name, "states": states, "data": data}

    def blockName(self, x, y, z, dim=DIMENSION):
        return self.blocks.get((dim, x, y, z), {"name": "minecraft:air"})["name"]

    def runTimers(self):
        timers, self.timers = self.timers, []
        for seconds, func, params in timers:
            func(*params)

    def spawnedNames(self):
        return [(itemDict.get("newItemName") or itemDict.get("itemName"), itemDict["count"]) for itemDict, dim, pos in self.spawned]

    # ---- 假组件 ----
    def comp(self, kind, target):
        return _Comp(getattr(self, "_" + kind)(target))

    def _EngineType(self, target):
        return {"GetEngineTypeStr": lambda: (self.entities.get(target) or {}).get("type")}

    def _Item(self, target):
        def getPlayerItem(posType, slot, getUserData=False):
            hand = self.players[target]["hand"]
            return dict(hand) if hand else None

        def setEntityItem(posType, itemDict, slot):
            self.players[target]["hand"] = dict(itemDict) if itemDict and itemDict.get("count", 0) > 0 else None
            return True

        def spawnToInv(itemDict, playerId):
            self.players[playerId]["given"].append(dict(itemDict))
            return True

        return {"GetPlayerItem": getPlayerItem, "SetEntityItem": setEntityItem, "SpawnItemToPlayerInv": spawnToInv,
                "GetItemTags": lambda name: self.tags.get(name, []),
                "GetDroppedItem": lambda entityId, getUserData=False: self.itemEntities.get(entityId),
                "GetItemBasicInfo": lambda name: {"itemType": "food", "maxDurability": 0}}

    def _Game(self, target):
        return {"GetPlayerGameType": lambda playerId: 1 if self.players[playerId]["creative"] else 0,
                "AddTimer": lambda seconds, func, *params: self.timers.append((seconds, func, params)),
                "GetGameRulesInfoServer": lambda: {"option_info": {}}}

    def _ModAttr(self, target):
        return {"GetAttr": lambda key: self.modAttr.get((target, key)),
                "SetAttr": lambda key, value: self.modAttr.__setitem__((target, key), value)}

    def _Effect(self, target):
        def add(name, duration, amplifier, showParticles=True):
            self.entities[target]["effects"].append((name, duration, amplifier))
            return True
        return {"AddEffectToEntity": add}

    def _Attr(self, target):
        def resetToMax(attrType):
            self.entities[target]["health"] = self.entities[target]["maxHealth"]
            return True
        return {"IsEntityOnFire": lambda: self.entities[target]["fire"], "ResetToMaxValue": resetToMax}

    def _EntityDefinitions(self, target):
        return {"IsTamed": lambda: self.entities[target]["tamed"]}

    def _ActorOwner(self, target):
        return {"GetEntityOwner": lambda: self.entities[target]["owner"]}

    def _EntityEvent(self, target):
        return {"AddActorComponent": lambda name, value: self.components.setdefault(target, {}).__setitem__(name, value) or True}

    def _Pos(self, target):
        return {"GetFootPos": lambda: self.players[target]["pos"] if target in self.players else self.entities[target].get("pos", (5.5, 64.0, 5.5))}

    def _Dimension(self, target):
        return {"GetEntityDimensionId": lambda: DIMENSION}

    def _Player(self, target):
        def setHunger(value):
            self.players[target]["hunger"] = value
            return True
        return {"GetPlayerHunger": lambda: self.players[target]["hunger"], "SetPlayerHunger": setHunger}

    def _BlockInfo(self, target):
        def setBlockNew(pos, blockDict, handling=0, dim=DIMENSION, *rest):
            self.blocks[(dim,) + tuple(pos)] = {"name": blockDict["name"], "states": None, "data": None}
            return True
        return {"SetBlockNew": setBlockNew,
                "GetBlockNew": lambda pos, dim=DIMENSION: {"name": self.blockName(pos[0], pos[1], pos[2], dim), "aux": 0}}

    def _BlockState(self, target):
        def getStates(pos, dim=DIMENSION):
            block = self.blocks.get((dim,) + tuple(pos))
            return dict(block["states"]) if block and block["states"] is not None else None

        def setStates(pos, states, dim=DIMENSION):
            self.blocks[(dim,) + tuple(pos)]["states"] = dict(states)
            return True
        return {"GetBlockStates": getStates, "SetBlockStates": setStates}

    def _BlockEntityData(self, target):
        return {"GetBlockEntityData": lambda dim, pos: (self.blocks.get((dim,) + tuple(pos)) or {}).get("data")}

    def _BlockUseEventWhiteList(self, target):
        return {"AddBlockItemListenForUseEvent": lambda name: self.listened.append(name) or True}


class _Factory(object):
    def __init__(self, world):
        self._world = world

    def __getattr__(self, name):
        if not name.startswith("Create"):
            raise AttributeError(name)
        kind = name[len("Create"):]
        if not hasattr(self._world, "_" + kind):
            raise AttributeError("假引擎没有实现 %s（用到它的测试请在 fakeengine.py 里补上）" % name)
        return lambda target=None: self._world.comp(kind, target)


class _System(object):
    def __init__(self, world):
        self._world = world

    def CreateEngineItemEntity(self, itemDict, dimensionId, pos):
        entityId = "item%d" % self._world._nextId[0]
        self._world._nextId[0] += 1
        self._world.spawned.append((dict(itemDict), dimensionId, tuple(pos)))
        self._world.itemEntities[entityId] = dict(itemDict)
        return entityId


def install():
    """换上假的 Server/Helpers/Engine，返回 FakeWorld。必须在导入 Server 下的任何玩法模块之前调用。"""
    world = FakeWorld()
    module = types.ModuleType(ENGINE_MODULE)
    module.compFactory = _Factory(world)
    module.levelId = LEVEL_ID
    module.System = _System(world)
    module.Call = lambda target, endpoint, data=None: world.calls.append((target, endpoint, data))

    def destroyEntity(entityId):
        world.destroyed.append(entityId)
        return True

    module.DestroyEntity = destroyEntity
    module.GetBlockEntityData = lambda dim, pos: (world.blocks.get((dim,) + tuple(pos)) or {}).get("data")
    module.GetBlockName = lambda pos, dim: world.blockName(pos[0], pos[1], pos[2], dim)
    module.GetEngineTypeStr = lambda entityId: (world.entities.get(entityId) or {}).get("type")
    module.GetCarriedItem = lambda playerId, getUserData=False: world.comp("Item", playerId).GetPlayerItem(0, 0, getUserData)
    module.SetCarriedItem = lambda playerId, itemDict: world.comp("Item", playerId).SetEntityItem(0, itemDict, 0)
    module.ShowTip = lambda playerId, text: world.calls.append((playerId, "ShowTip", text))
    sys.modules[ENGINE_MODULE] = module
    # 声音广播走 Call("*", "OnPlaySound", ...)：把它翻成 sounds 清单，测试读起来直接
    realCall = module.Call

    def call(target, endpoint, data=None):
        if endpoint == "OnPlaySound":
            world.sounds.append((data["soundName"], data["pos"]))
        else:
            realCall(target, endpoint, data)

    module.Call = call
    return world
