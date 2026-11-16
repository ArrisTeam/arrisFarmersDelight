# -*- coding: utf-8 -*-
"""HandFrying - 煎锅的手工煎制：手放的一批先煎贴锅面，熟了等厨师颠锅翻面，两面都熟后留在锅里等人取（服务端）

移植自 Hands-On Delight 的 station/SkilletCooking.java；两面进度的状态机在 Shared/Rules/HandsOn/Frying.py。
每个煎锅一份 PanHand，只活在内存里，站点关了它还在（锅里的东西接着煎、等着翻）；方块没了才删。
不是手放的（FD 自己的右键放进来的）照旧由 Server/Skillet.py 一件一件煎、弹出来；颠一下锅就从此归厨师，从生开始重算。
"""
from .Helpers.BlockItems import PublishSkillet
from .Helpers.Engine import System
from ..Shared.Rules import PanStation
from ..Shared.Rules.HandsOn import Frying


class PanHand(object):
    def __init__(self):
        self.frying = Frying.Frying()
        self.cook = None                 # 最后放料 / 颠锅的玩家
        self.fried = 0                   # 煎好的批数（站点看它变了就报"煎好了"）


_hands = {}


def handOf(dimensionId, blockPos):
    key = (dimensionId, tuple(blockPos))
    hand = _hands.get(key)
    if hand is None:
        hand = _hands[key] = PanHand()
    return hand


def peek(dimensionId, blockPos):
    return _hands.get((dimensionId, tuple(blockPos)))


def forget(dimensionId, blockPos):
    _hands.pop((dimensionId, tuple(blockPos)), None)


def byFarmersDelight(dimensionId, blockPos):
    """FD 自己的右键放料 / 取走：这锅回到 FD 原样（进度清零）。"""
    hand = peek(dimensionId, blockPos)
    if hand is not None:
        hand.frying.farmersDelightsWay()


def fry(hand, dimensionId, blockPos, blockEntityData, dt):
    """手放的一锅煎 dt 秒（煎锅烧着时由 Server/Skillet.py 的 tick 调用）。返回 False 表示这锅不归手工管，按 FD 原样煎。"""
    frying = hand.frying
    item = blockEntityData["cookingDict"]
    if not item or (item.get("count") or 0) <= 0:
        frying.farmersDelightsWay()
        return False
    if not frying.byHand:
        return False
    fried = PanStation.friedOf(item["newItemName"])
    if fried is None:
        return True                      # 已经煎好，留在锅里等人取
    frying.resize(min(item["count"], Frying.BATCH))
    if frying.step(dt, PanStation.sideSeconds(frying.batch), PanStation.isOneSided(item["newItemName"])):
        _finish(hand, dimensionId, blockPos, blockEntityData, item, fried)
    return True


def _finish(hand, dimensionId, blockPos, blockEntityData, item, fried):
    """两面都熟：这一批换成成品留在锅里；锅里比一批多（FD 右键放的一大叠又被颠过）时，成品照 FD 那样弹出来。"""
    count = min(hand.frying.batch, item["count"])
    done = {"newItemName": fried, "newAuxValue": item.get("newAuxValue", 0), "count": count}
    rest = item["count"] - count
    hand.frying.reset()
    if rest <= 0:
        blockEntityData["cookingDict"] = done
        PublishSkillet(dimensionId, blockPos, done)
    else:
        left = dict(item)
        left["count"] = rest
        blockEntityData["cookingDict"] = left
        PublishSkillet(dimensionId, blockPos, left)
        x, y, z = blockPos
        System.CreateEngineItemEntity(done, dimensionId, (x + 0.5, y + 0.3, z + 0.5))
    hand.fried += 1


def toss(hand, playerId, now, item):
    """playerId 颠锅：锅里是能煎的东西且离上次颠够久才算。FD 原样煎着的锅从此归厨师、从生开始算。"""
    hasFood = bool(item) and PanStation.canFry(item.get("newItemName"))
    if not hand.frying.toss(now, hasFood):
        return False
    hand.cook = playerId
    return True
