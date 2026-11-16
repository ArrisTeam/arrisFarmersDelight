# -*- coding: utf-8 -*-
"""Slicing - 刀切派、蛋糕、南瓜：还剩几片、插着哪支蜡烛、等着结算的切片单（双端，纯规则）"""
from ..Data import Slicing as Data

# 开始破坏到方块真正没了之间最多等多久（秒）；切片单过期作废，防止放弃的破坏留下旧单子
TICKET_SECONDS = 5.0
_TICKET_LIMIT = 64


def pieSlicesLeft(bitesTaken):
    """派被吃了 bitesTaken 口（OnEatPie 里存的 blockStatus 是浮点数）后还剩几块。"""
    return max(0, Data.PIE_BITES - int(bitesTaken or 0))


def cakeSlicesLeft(biteCounter):
    """蛋糕的 bite_counter（已吃口数，0 到 6）对应还剩几片。"""
    return max(0, Data.CAKE_BITES - int(biteCounter or 0))


def cakeAfterCut(biteCounter):
    """刀切一片之后蛋糕的 bite_counter；最后一片（bite_counter 已是 6）切下后没有蛋糕了，返回 None。"""
    biteCounter = int(biteCounter or 0)
    return biteCounter + 1 if biteCounter < Data.CAKE_BITES - 1 else None


def candleOf(candleCakeName):
    """"minecraft:red_candle_cake" -> "minecraft:red_candle"；不是插蜡烛的蛋糕返回 None。"""
    if candleCakeName not in Data.CANDLE_CAKES:
        return None
    return candleCakeName[:-len("_cake")]


def sliceDrops(blockName, count):
    """切 / 拆 blockName 得到的 count 片 -> [(物品, 数量)]（派给各自的一片，蛋糕给蛋糕片）。"""
    sliceItem = Data.pieSliceItems.get(blockName, Data.CAKE_SLICE)
    return [(sliceItem, count)] if count > 0 else []


class SliceTickets(object):
    """玩家用刀开始拆派 / 蛋糕时记下该给几片，方块真的没了才兑现。

    引擎先发"玩家即将破坏方块"（这时还能读到派的口数 / 蛋糕的 bite_counter），破坏完成后才发"方块已被破坏"。
    只有后一个事件到了才掉切片，所以破坏被取消时不会白掉东西；单子按 (维度, 坐标) 记，认玩家、会过期。
    """

    def __init__(self):
        self._tickets = {}

    def put(self, key, drops, playerId, now):
        if len(self._tickets) >= _TICKET_LIMIT:
            for oldKey in [k for k, v in self._tickets.items() if v[2] < now]:
                del self._tickets[oldKey]
        self._tickets[key] = (drops, playerId, now + TICKET_SECONDS)

    def take(self, key, playerId, now):
        ticket = self._tickets.pop(key, None)
        if ticket is None or ticket[1] != playerId or ticket[2] < now:
            return []
        return ticket[0]

    def __len__(self):
        return len(self._tickets)
