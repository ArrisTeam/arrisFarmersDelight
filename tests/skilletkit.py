# -*- coding: utf-8 -*-
"""skilletkit - 煎锅服务端模块测试用的假引擎补丁（测试用的公共小工具，不是测试本身）

fakeengine.install() 只实现了各模块共用的那几个接口；煎锅这几个模块还要副手、潜行、液体层、会建方块实体数据的 SetBlockNew，
在这里按实例补上（不改 fakeengine.py）。extend(world) 要在导入 Server 下的玩法模块之前调用，因为 ItemPosType 是导入时取的。
"""
from __future__ import print_function

import sys

import fakeengine


class EngineData(dict):
    """像引擎的方块实体数据：缺键读出来是 None（不是 KeyError），对象本身总是真值（空的也是，玩法代码靠 `if not data` 判有没有方块实体）。"""

    def __missing__(self, key):
        return None

    def __bool__(self):
        return True

    __nonzero__ = __bool__


class ItemPos(object):
    """ModAPI 的 ItemPosType。"""
    INVENTORY = 0
    OFFHAND = 1
    CARRIED = 2
    ARMOR = 3


def extend(world):
    module = sys.modules[fakeengine.ENGINE_MODULE]
    module.ItemPosType = ItemPos
    world.offhand = {}               # 玩家 -> 副手物品
    world.sneaking = set()
    world.water = set()              # (维度, x, y, z)：液体层有水
    world.deferBlockEntity = False   # True：SetBlockNew 放煎锅后方块实体还没建好

    def reset():
        for name in ("entities", "players", "blocks", "itemEntities", "modAttr"):
            getattr(world, name).clear()
        for name in ("spawned", "destroyed", "sounds", "calls", "timers", "listened"):
            del getattr(world, name)[:]
        world.offhand.clear()
        world.sneaking.clear()
        world.water.clear()
        world.deferBlockEntity = False

    world.reset = reset
    baseItem, basePlayer, baseBlockInfo = world._Item, world._Player, world._BlockInfo

    def _Item(target):
        methods = dict(baseItem(target))
        mainGet, mainSet = methods["GetPlayerItem"], methods["SetEntityItem"]

        def getPlayerItem(posType, slot, getUserData=False):
            if posType == ItemPos.OFFHAND:
                item = world.offhand.get(target)
                return dict(item) if item else None
            return mainGet(posType, slot, getUserData)

        def setEntityItem(posType, itemDict, slot):
            if posType == ItemPos.OFFHAND:
                world.offhand[target] = dict(itemDict) if itemDict and itemDict.get("count", 0) > 0 else None
                return True
            return mainSet(posType, itemDict, slot)

        methods["GetPlayerItem"], methods["SetEntityItem"] = getPlayerItem, setEntityItem
        return methods

    def _Player(target):
        methods = dict(basePlayer(target))
        methods["isSneaking"] = lambda: target in world.sneaking
        return methods

    def _BlockInfo(target):
        methods = dict(baseBlockInfo(target))

        def setBlockNew(pos, blockDict, handling=0, dim=fakeengine.DIMENSION, *rest):
            data = EngineData() if blockDict["name"] == "arris:skillet" and not world.deferBlockEntity else None
            world.blocks[(dim,) + tuple(pos)] = {"name": blockDict["name"], "states": None, "data": data}
            return True

        methods["SetBlockNew"] = setBlockNew
        methods["GetLiquidBlock"] = lambda pos, dim=fakeengine.DIMENSION: {"name": "minecraft:water"} if (dim,) + tuple(pos) in world.water else None
        return methods

    world._Item, world._Player, world._BlockInfo = _Item, _Player, _BlockInfo
    return world
