# -*- coding: utf-8 -*-
"""potfake - 厨锅站点离线测试用的假引擎和假世界（不是测试本身，跑器只收 test_*.py）

把 arrisFarmersDelightScripts.Server.Helpers.Engine（和 QuModLibs.Server）换成假的，再导入真的 HandCooking / PotContainer /
PotServe / PotLook / PotLogic / PotScoop / BookFill；前置包的 Manager、Registry、Station 也是真的（经 dgtest.FakeWorld）。
假世界只做这些测试要的：方块容器格（9 格）、方块实体数据（读写都拷贝，所以"改了嵌套字典忘了整体赋值"这类 bug 在这里会现形）、
玩家（背包 36 格、脚下位置、选中的快捷栏格、创造模式、ExtraData）、掉落物、经验球、Call / MultiClientsCall 的记录、计时器。
用法：fake = potfake.install(); fake.reset(); pot = fake.placePot((10, 64, 10)); ...
"""
from __future__ import print_function

import copy
import importlib
import sys
import types

import dgtest
import fdtest

PACKAGE = fdtest.SCRIPTS
POT_POS = (10, 64, 10)
DEFAULT_STACKS = {"minecraft:egg": 16, "arris:cookbeef_stew": 16, "minecraft:milk_bucket": 1, "minecraft:water_bucket": 1,
                  "minecraft:bucket": 16, "arris:hot_cocoa": 16, "minecraft:glass_bottle": 64}


class BEData(object):
    """方块实体数据：缺键读到 None；读写都拷贝（引擎的缓存只有整体赋值才会存档）。"""

    def __init__(self):
        self.d = {}

    def __getitem__(self, key):
        return copy.deepcopy(self.d.get(key))

    def __setitem__(self, key, value):
        self.d[key] = copy.deepcopy(value)


class PotWorld(dgtest.FakeWorld):
    def __init__(self, fake):
        super(PotWorld, self).__init__()
        self.fake = fake

    def maxStackOf(self, value):
        return self.fake.stackOf(value["newItemName"])


class Comp(object):
    def __init__(self, fake, owner):
        self.fake = fake
        self.owner = owner

    # ---- 物品 ----
    def GetContainerItem(self, pos, slot, dim=-1, getUserData=False):
        """和引擎一样：不要 userData 就不给（getUserData 缺省 False），要了才带。"""
        slots = self.fake.containers.get((dim, tuple(pos)))
        item = copy.deepcopy(slots[slot]) if slots and slots[slot] else None
        if item is not None and not getUserData:
            item.pop("userData", None)
        return item

    def SpawnItemToContainer(self, item, slot, pos, dim):
        slots = self.fake.containers.setdefault((dim, tuple(pos)), [None] * 9)
        slots[slot] = copy.deepcopy(item) if item and item.get("count", 0) > 0 else None
        return True

    def GetItemBasicInfo(self, name, aux=0):
        return {"maxStackSize": self.fake.stackOf(name), "itemName": "name:" + name, "itemType": "food"}

    def GetSelectSlotId(self):
        return self.fake.world.players[self.owner].get("selected", 0)

    def SpawnItemToPlayerInv(self, item, playerId):
        inv, size = self.fake.world.players[playerId]["inv"], self.fake.stackOf(item["newItemName"])
        probe, left = [copy.deepcopy(slot) for slot in inv], item["count"]
        for slot in probe:
            if slot and slot["newItemName"] == item["newItemName"] and slot["newAuxValue"] == item["newAuxValue"] and left > 0:
                moved = min(size - slot["count"], left)
                slot["count"] += moved
                left -= moved
        for index in range(len(probe)):
            if probe[index] is None and left > 0:
                moved = min(size, left)
                probe[index] = dict(item, count=moved)
                left -= moved
        if left > 0:
            return False
        inv[:] = probe
        return True

    # ---- 游戏、位置、维度 ----
    def GetPlayerGameType(self, playerId):
        return 1 if self.fake.world.players[playerId].get("creative") else 0

    def AddTimer(self, delay, fn, *args):
        self.fake.timers.append((delay, fn, args))
        return len(self.fake.timers)

    def GetFootPos(self):
        return self.fake.world.players[self.owner]["pos"]

    def GetEntityDimensionId(self):
        return self.fake.world.players[self.owner]["dim"]

    # ---- ExtraData / ModAttr / 经验球 ----
    def GetExtraData(self, key):
        return copy.deepcopy(self.fake.extra.get((self.owner, key)))

    def SetExtraData(self, key, value):
        self.fake.extra[(self.owner, key)] = copy.deepcopy(value)

    def GetAttr(self, key):
        return self.fake.attrs.get((self.owner, key))

    def SetAttr(self, key, value):
        self.fake.attrs[(self.owner, key)] = value

    def SetOrbExperience(self, value):
        self.fake.orbs[self.owner]["value"] = value

    def SetMotion(self, motion):
        """CreateActorMotion(实体).SetMotion：记下掉落物的初速（每刻几格）。"""
        self.fake.motions[self.owner] = tuple(motion)
        return True


class Factory(object):
    def __init__(self, fake):
        self.fake = fake

    def __getattr__(self, name):
        if name.startswith("Create"):
            return lambda owner=None: Comp(self.fake, owner)
        raise AttributeError(name)


class System(object):
    fake = None

    @classmethod
    def CreateEngineItemEntity(cls, item, dim, pos):
        cls.fake.spawned.append((copy.deepcopy(item), dim, tuple(pos)))
        return "item%d" % len(cls.fake.spawned)

    @classmethod
    def CreateEngineEntityByTypeStr(cls, typeName, pos, rot, dim):
        entityId = "orb%d" % len(cls.fake.orbs)
        cls.fake.orbs[entityId] = {"type": typeName, "pos": tuple(pos), "dim": dim, "value": 0}
        return entityId


class ItemPosType(object):
    INVENTORY, CARRIED, ARMOR, OFFHAND = 0, 1, 2, 3


class Fake(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.world = PotWorld(self)
        self.containers = {}
        self.blockEntities = {}
        self.spawned = []
        self.motions = {}                 # 实体 id -> SetMotion 给的初速（掉落物的 id 是 CreateEngineItemEntity 返回的 item1、item2……）
        self.orbs = {}
        self.calls = []
        self.multi = []
        self.timers = []
        self.extra = {}
        self.attrs = {}
        self.stacks = dict(DEFAULT_STACKS)
        self.blockAux = {}                # (维度, 坐标) -> 方块的 aux（GetBlockNew 给的；没有的是 0）
        return self

    def stackOf(self, name):
        return self.stacks.get(name, 64)

    def placePot(self, pos=POT_POS, heated=True, dim=0):
        pos = tuple(pos)
        self.world.blocks[(dim, pos)] = "arris:cooking_pot"
        self.containers[(dim, pos)] = [None] * 9
        data = self.blockEntities[(dim, pos)] = BEData()
        data["previewItemSlot"] = [{}]
        data["timer"] = 10.0
        data["heatEnable"] = heated
        return data

    def addPlayer(self, playerId, pos, dim=0, creative=False):
        player = self.world.addPlayer(playerId, pos, dim)
        player["selected"], player["creative"] = 0, creative
        return player

    def give(self, playerId, slot, name, count, aux=0, userData=None):
        item = self.world.players[playerId]["inv"][slot] = {"newItemName": name, "newAuxValue": aux, "count": count}
        if userData is not None:
            item["userData"] = userData

    def count(self, playerId, name):
        return sum(item["count"] for item in self.world.players[playerId]["inv"] if item and item["newItemName"] == name)

    def container(self, pos, slot, dim=0):
        return self.containers[(dim, tuple(pos))][slot]

    def setContainer(self, pos, slot, name, count, aux=0, dim=0, userData=None):
        item = self.containers[(dim, tuple(pos))][slot] = {"newItemName": name, "newAuxValue": aux, "count": count}
        if userData is not None:
            item["userData"] = userData


_installed = {}


def install():
    """装假引擎并返回共享的 Fake（只装一次；之后每个用例先 fake.reset()）。"""
    if "fake" in _installed:
        return _installed["fake"]
    fake = _installed["fake"] = Fake()
    System.fake = fake
    helpers = PACKAGE + ".Server.Helpers"
    importlib.import_module(helpers)
    engine = types.ModuleType(helpers + ".Engine")
    engine.compFactory = Factory(fake)
    engine.levelId = "level"
    engine.System = System
    engine.ItemPosType = ItemPosType
    engine.serverApi = types.SimpleNamespace(GetPlayerList=lambda: list(fake.world.players)) if hasattr(types, "SimpleNamespace") \
        else type("Api", (), {"GetPlayerList": staticmethod(lambda: list(fake.world.players))})()
    engine.Call = lambda playerId, name, *args: fake.calls.append((playerId, name, args))
    engine.DestroyEntity = lambda entityId: None
    engine.GetBlockEntityData = lambda dim, pos: fake.blockEntities.get((dim, tuple(pos)))
    engine.GetBlockName = lambda pos, dim: fake.world.blocks.get((dim, tuple(pos)), "minecraft:air")
    engine.GetBlockAux = lambda pos, dim: fake.blockAux.get((dim, tuple(pos)), 0)
    engine.GetCarriedItem = lambda playerId, getUserData=False: _carried(fake, playerId)
    engine.SetCarriedItem = lambda playerId, item: _setCarried(fake, playerId, item)
    sys.modules[helpers + ".Engine"] = engine
    qu = PACKAGE + ".QuModLibs"
    quPackage = types.ModuleType(qu)
    quPackage.__path__ = []
    quServer = types.ModuleType(qu + ".Server")
    quServer.MultiClientsCall = lambda players, key, *args: fake.multi.append((list(players), key, args))
    quServer.AllowCall = quServer.InjectHttpPlayerId = lambda func: func        # Server/CookingPot.py 的端点装饰器
    sys.modules[qu], sys.modules[qu + ".Server"] = quPackage, quServer
    return fake


def _carried(fake, playerId):
    player = fake.world.players[playerId]
    return copy.deepcopy(player["inv"][player.get("selected", 0)])


def _setCarried(fake, playerId, item):
    player = fake.world.players[playerId]
    player["inv"][player.get("selected", 0)] = copy.deepcopy(item) if item and item.get("count", 0) > 0 else None


def load(dotted):
    """导入主包脚本根下的模块（要先 install）：load("Compat.Diegesis.PotLogic")。"""
    return fdtest.load(dotted)


class Clock(object):
    """顶替模块里的 time：time() 读假世界的钟。"""

    def __init__(self, world):
        self.world = world

    def time(self):
        return self.world.time
