# -*- coding: utf-8 -*-
"""PanContents - 煎锅里的东西：方块实体数据里的 cookingDict 那一格，给场景交互前置的站点当槽组绑（服务端）

前置包的 bindSlots 要的存储（size / get / set）：站点读写它就是读写方块自己的数据——FD 原样的右键放料、煎锅自己一件件煎、
手工煎制的两面进度（HandFrying）、没人开站点时路过的人看到的，都是同一份。HoD 的 SkilletLogic 对 FD 煎锅的 getStoredStack / setItem
也是这么绑的。set 同时广播给没装场景的客户端（BlockItems 的老办法）；方块实体不在就抛（前置包把这个动作作废、东西还给玩家，不能悄悄吞）。
"""
import copy

from .BlockItems import PublishSkillet
from .Engine import compFactory, levelId, GetBlockEntityData
from ...Shared.Rules import SkilletRules

_WATER = ("minecraft:water", "minecraft:flowing_water")
KEY = "cookingDict"


def isWaterlogged(dimensionId, blockPos):
    """液体层里有水：JE 的 WATERLOGGED，含水的煎锅不能煎、不收东西。"""
    liquid = compFactory.CreateBlockInfo(levelId).GetLiquidBlock(blockPos, dimensionId)
    return bool(liquid) and liquid.get("name") in _WATER


def itemOf(dimensionId, blockPos):
    """锅里的东西（物品字典的拷贝），空锅 None。"""
    data = GetBlockEntityData(dimensionId, blockPos)
    item = data[KEY] if data else None
    return copy.deepcopy(item) if item and item.get("newItemName") and (item.get("count") or 0) > 0 else None


class PanSlots(object):
    """一格，窗口在 cookingDict 上。"""

    def __init__(self, dimensionId, blockPos):
        self.dimensionId = dimensionId
        self.blockPos = tuple(blockPos)

    def size(self):
        return 1

    def get(self, index):
        return itemOf(self.dimensionId, self.blockPos)

    def set(self, index, item):
        data = GetBlockEntityData(self.dimensionId, self.blockPos)
        if data is None:                         # 方块实体不在：悄悄返回的话放进锅的东西就没存下、手上却扣了：抛，动作作废、东西还给玩家（和 StoveSlots 一样）
            raise RuntimeError("skillet block entity missing at %s: contents not written" % (self.blockPos,))
        stored = copy.deepcopy(item) if item and (item.get("count") or 0) > 0 else None
        data[KEY] = stored                       # 整个字典重新赋值才会存档
        PublishSkillet(self.dimensionId, self.blockPos, stored)


def restartTimer(data):
    """FD 原样煎的倒计时回到起点（和 Server/Skillet._timerStart 同一个算法：配方秒数按火焰附加换算再加 1）。"""
    aspect = SkilletRules.fireAspectLevel(data["skilletItem"])
    data["cookTimer"] = SkilletRules.cookingSeconds(SkilletRules.CAMPFIRE_TICKS, aspect) + 1.0
