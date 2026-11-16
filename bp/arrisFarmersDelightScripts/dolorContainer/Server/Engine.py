# -*- coding: utf-8 -*-
"""
服务端与引擎打交道的适配：物品种类信息、玩家背包读写、丢出物品、ExtraData 后端、手持物持久化。
只能在服务端线程调用（引擎接口在别的线程返回空）。
"""
import ast
import copy
import math
import random
import time
import uuid

import mod.server.extraServerApi as serverApi

from .. import HOST
from ..Common import Items, Shared
from . import Storage

_levelId = serverApi.GetLevelId()
_factory = serverApi.GetEngineCompFactory()
_INVENTORY = serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
_CARRIED = serverApi.GetMinecraftEnum().ItemPosType.CARRIED
_CREATIVE = serverApi.GetMinecraftEnum().GameType.Creative
_NBT_STRING = 8
_ORB_VALUES = (2477, 1237, 617, 307, 149, 73, 37, 17, 7, 3)   # 原版拆经验球的分法
_ORB_MANY = 12001       # 不少于这么多经验时平均拆成 13 个
_ORB_MANY_COUNT = 13
_INVENTORY_SIZE = 36
_CURSOR_KEY = "dolor_container:%s:cursor" % HOST   # 几个模组各带一份本库时各存各的
_HELD_KEY = "dolor_container:%s:held" % HOST       # 玩家临时格里的东西（工作台的合成格等），同上
THROW_SECONDS = 2.0   # 原版丢出的物品 2 秒内谁都捡不起来；脚本生成的掉落物只有 0.5 秒，余下的在拾取事件里挡

_basicInfo = {}
_unsaved = set()  # 写过自定义数据、还没交给引擎存档的实体（玩家、世界）：ExtraDataBackend.save 只存它们
writing = set()   # 正在由本框架写背包的玩家：这期间的背包变化事件是自己引起的，不当作外部改动
_thrown = {}      # 本框架丢出、还没过不可拾取期的掉落物：实体 ID -> 到期时刻
thrownHook = [None]   # 丢出了要挡拾取的东西时调用（服务挂上：这时才监听拾取事件）
_policies = Shared.table().policies


def setDropDisabled(disabled):
    """世界级的设置，几份库共用（见 Common.Shared）。"""
    _policies["dropDisabled"] = bool(disabled)


def setContainersDisabled(disabled):
    """世界级的设置，几份库共用（见 Common.Shared）。"""
    _policies["containersDisabled"] = bool(disabled)


def purgeThrown(now=None):
    """清掉过了不可拾取期的掉落物，返回还剩几个。"""
    now = time.time() if now is None else now
    for entityId, expiry in list(_thrown.items()):
        if expiry <= now:
            del _thrown[entityId]
    return len(_thrown)


def thrownPickupDelay(entityId, now=None):
    """
    刚丢出的掉落物还要等多久才能捡（拾取事件的单位：帧，每秒 30 帧），过了不可拾取期返回 0。
    """
    expiry = _thrown.get(entityId)
    if expiry is None:
        return 0
    left = expiry - (time.time() if now is None else now)
    if left <= 0:
        del _thrown[entityId]
        return 0
    return int(math.ceil(left * 30))


def basicInfo(name, aux):
    key = (name, aux)
    info = _basicInfo.get(key)
    if info is None:
        info = _factory.CreateItem(_levelId).GetItemBasicInfo(name, aux) or {}
        _basicInfo[key] = info
    return info


RULES = Items.ItemRules(lambda name, aux: basicInfo(name, aux).get("maxStackSize", 64),
                        lambda name, aux: basicInfo(name, aux).get("maxDurability", 0), basicInfo)


def heldItem(playerId):
    """玩家手上拿着的物品（主手，带附加数据），没有时为 None。"""
    return Items.normalize(_factory.CreateItem(playerId).GetPlayerItem(_CARRIED, 0, True))


def selectedSlot(playerId):
    """玩家主手对应的快捷栏格（0–8），取不到时为 -1。"""
    return _factory.CreateItem(playerId).GetSelectSlotId()


def inventorySlot(playerId, index):
    """玩家背包第 index 格（0–35，带附加数据），空格为 None。"""
    return Items.normalize(_factory.CreateItem(playerId).GetPlayerItem(_INVENTORY, index, True))


def tagHeld(playerId, stack, key):
    """给玩家手上的这件物品记上实例编号（附加数据的 key 写一个新的随机编号），返回编号；写不进去返回 None。"""
    uid = uuid.uuid4().hex
    user = dict(stack.get("userData") or {})
    user[key] = {"__type__": _NBT_STRING, "__value__": uid}
    if not _factory.CreateItem(playerId).SpawnItemToPlayerCarried(toEngine(dict(stack, userData=user)), playerId):
        return None
    return uid


def orbValues(amount):
    """照原版把经验拆成几个经验球的值：少时按递减的一串值拆，多时平均拆成 13 个。"""
    if amount >= _ORB_MANY:
        each = amount // _ORB_MANY_COUNT
        return [each] * (_ORB_MANY_COUNT - 1) + [each + amount % _ORB_MANY_COUNT]
    values = []
    while amount > 0:
        value = next((v for v in _ORB_VALUES if amount >= v), 1)
        values.append(value)
        amount -= value
    return values


def spawnExperience(playerId, amount):
    """照原版熔炉给经验：在玩家的位置生成经验球，只有这位玩家捡得起来。"""
    if amount <= 0:
        return
    position = _factory.CreatePos(playerId).GetPos()
    if not position:
        return
    comp = _factory.CreateExp(playerId)
    for value in orbValues(int(amount)):
        comp.CreateExperienceOrb(value, tuple(position), True)


def keepInventoryRule():
    """全局游戏规则"保留物品栏"是否开启。"""
    rules = _factory.CreateGame(_levelId).GetGameRulesInfoServer() or {}
    return bool((rules.get("cheat_info") or {}).get("keep_inventory"))


def toEngine(stack, count=None):
    """规整的物品堆 -> 交给引擎接口的字典（深拷贝，引擎接口会改传进去的字典）。"""
    return {
        "newItemName": stack["newItemName"],
        "newAuxValue": stack["newAuxValue"],
        "count": stack["count"] if count is None else count,
        "userData": copy.deepcopy(stack.get("userData")) or {},
    }


class PlayerInventory(object):
    """一位玩家的 36 格背包。"""

    def __init__(self, playerId):
        self.playerId = playerId
        self._comp = _factory.CreateItem(playerId)

    def read(self):
        items = self._comp.GetPlayerAllItems(_INVENTORY, True) or [None] * _INVENTORY_SIZE
        return [Items.normalize(stack) for stack in items]

    def readSlot(self, index):
        return Items.normalize(self._comp.GetPlayerItem(_INVENTORY, index, True))

    def write(self, changes):
        """按格写入，写完重读，返回 {下标: 实际物品堆}。"""
        writing.add(self.playerId)
        try:
            for index, stack in sorted(changes.items()):
                self._writeSlot(index, Items.normalize(stack))
        finally:
            writing.discard(self.playerId)
        return dict((index, self.readSlot(index)) for index in changes)

    def _writeSlot(self, index, stack):
        current = self.readSlot(index)
        if stack is None:
            if current is not None:
                self._comp.SetInvItemNum(index, 0)
            return
        if current is not None and Items.sameKind(current, stack):
            if Items.count(current) != Items.count(stack):
                self._comp.SetInvItemNum(index, Items.count(stack))
            return
        # 按字典生成物品时数量先按种类的堆叠数截断，userData 里更大的堆叠数要生成后再改数量
        base = RULES.baseMaxStack(stack)
        self._comp.SpawnItemToPlayerInv(toEngine(stack, min(Items.count(stack), base)), self.playerId, index)
        if Items.count(stack) > base:
            self._comp.SetInvItemNum(index, Items.count(stack))

    def spawnExperience(self, amount):
        spawnExperience(self.playerId, amount)

    def creative(self):
        """这位玩家现在是不是创造模式。"""
        return _factory.CreateGame(_levelId).GetPlayerGameType(self.playerId) == _CREATIVE

    def mayOpenContainers(self):
        return mayOpenContainers(self.playerId)

    def canDrop(self):
        """
        这位玩家现在能不能往世界里丢东西，照原版容器界面：没有"使用门和开关"能力（访客）不能丢，
        世界禁止丢弃物品（Api.setDropDisabled）时也不能丢。
        """
        if _policies.get("dropDisabled"):
            return False
        abilities = _factory.CreatePlayer(self.playerId).GetPlayerAbilities()
        return not abilities or bool(abilities.get("doorsandswitches", True))

    def drop(self, stack):
        """
        照原版玩家丢东西：从眼睛往下 0.5 格处朝视线方向抛出（每刻 0.3 格，水平再随机偏一点点），
        THROW_SECONDS 之内谁都捡不起来。
        """
        stack = Items.normalize(stack)
        if stack is None:
            return
        dimension = _factory.CreateDimension(self.playerId).GetEntityDimensionId()
        eye = _factory.CreatePos(self.playerId).GetPos()
        rot = _factory.CreateRot(self.playerId).GetRot()
        direction = serverApi.GetDirFromRot(rot) if rot else (0.0, 0.0, 0.0)
        position = (eye[0], eye[1] - 0.5, eye[2])
        system = serverApi.GetSystem("Minecraft", "game")
        now = time.time()
        purgeThrown(now)
        remaining = Items.count(stack)
        limit = RULES.baseMaxStack(stack)
        while remaining > 0:
            amount = min(remaining, limit)
            entityId = system.CreateEngineItemEntity(toEngine(stack, amount), dimension, position)
            if entityId:
                angle = random.random() * 2.0 * math.pi
                spread = 0.02 * random.random()
                _factory.CreateActorMotion(entityId).SetMotion((direction[0] * 0.3 + math.cos(angle) * spread,
                                                                direction[1] * 0.3,
                                                                direction[2] * 0.3 + math.sin(angle) * spread))
                _thrown[entityId] = now + THROW_SECONDS
            remaining -= amount
        if _thrown and thrownHook[0] is not None:
            thrownHook[0]()


class ExtraDataBackend(Storage.Backend):
    """
    实体（玩家）或世界的 ExtraData。值只存 str。存档（save）只在这个实体写过东西时才交给引擎（同一个实体的几个后端对象共用
    这个记录）：引擎存实体的数据时把它的自定义数据整份打包。删除时引擎当场存档，所以没有这一项时不删。
    """

    def __init__(self, entityId):
        self._id = entityId
        self._comp = _factory.CreateExtraData(entityId)

    def get(self, key):
        value = self._comp.GetExtraData(key)
        return value if isinstance(value, str) else None

    def set(self, key, value):
        self._comp.SetExtraData(key, value, False)
        _unsaved.add(self._id)

    def delete(self, key):
        if self._comp.GetExtraData(key) is None:
            return
        self._comp.CleanExtraData(key)
        _unsaved.discard(self._id)   # 引擎删的时候已经把这个实体（世界）的数据存了档

    def save(self):
        if self._id in _unsaved:
            _unsaved.discard(self._id)
            self._comp.SaveExtraData()


def mayOpenContainers(playerId):
    """
    照游戏的规矩这位玩家现在能不能用容器：玩家的"打开容器"能力（访客、旁观模式、自定义权限里关掉的、正在加载画面里的
    都没有），原版容器在打开与容器里的动作（合成器切换格子、讲台翻页）时查的就是它，读不到时当作不能；世界禁止打开容器时
    （Api.setContainersDisabled）谁都不能。
    """
    if _policies.get("containersDisabled"):
        return False
    abilities = _factory.CreatePlayer(playerId).GetPlayerAbilities()
    return bool(abilities and abilities.get("opencontainers"))


def addRepeatedTimer(seconds, func):
    """每 seconds 秒（现实时间）调用一次 func。"""
    return _factory.CreateGame(_levelId).AddRepeatedTimer(seconds, func)


def chunkLoaded(dimension, pos):
    """那个位置所在的区块加载着没有（没加载的区块里读到的都是空气，只有这里分得出来）。"""
    return bool(_factory.CreateChunkSource(_levelId).CheckChunkState(dimension, tuple(pos)))


def levelBackend():
    """世界上的后端（ExtraData 存在世界上，玩家离线时也能读写）。"""
    return ExtraDataBackend(_levelId)


class CursorStore(object):
    """手持物存在玩家 ExtraData 里，与背包同一条存档，服务器崩溃后下次进游戏能退回。"""

    def __init__(self, playerId):
        self._backend = ExtraDataBackend(playerId)

    def get(self):
        text = self._backend.get(_CURSOR_KEY)
        if not text:
            return None
        name, aux, count, userData = ast.literal_eval(text)
        return {"newItemName": name, "newAuxValue": aux, "count": count, "userData": userData}

    def set(self, stack):
        if Items.isEmpty(stack):
            self._backend.delete(_CURSOR_KEY)
        else:
            self._backend.set(_CURSOR_KEY, repr((stack["newItemName"], stack["newAuxValue"], stack["count"],
                                                 stack.get("userData"))))

    def save(self):
        self._backend.save()


class HeldStore(object):
    """
    玩家临时格里的东西（工作台的合成格、铁砧的输入）存在玩家 ExtraData 里，与背包同一条存档：
    服务器在界面开着时崩溃，下次进游戏退回背包。只在有东西时占一个键。
    """

    def __init__(self, playerId):
        self._backend = ExtraDataBackend(playerId)

    def get(self):
        text = self._backend.get(_HELD_KEY)
        if not text:
            return []
        return [{"newItemName": name, "newAuxValue": aux, "count": count, "userData": userData}
                for name, aux, count, userData in ast.literal_eval(text)]

    def set(self, stacks):
        rows = [(stack["newItemName"], stack["newAuxValue"], stack["count"], stack.get("userData"))
                for stack in stacks if not Items.isEmpty(stack)]
        if rows:
            self._backend.set(_HELD_KEY, repr(rows))
        else:
            self._backend.delete(_HELD_KEY)
