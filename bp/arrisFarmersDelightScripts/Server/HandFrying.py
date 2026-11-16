# -*- coding: utf-8 -*-
"""HandFrying - 煎锅的手工煎制：手放的一批先煎贴锅面，熟了等厨师颠锅翻面，两面都熟后留在锅里等人取（服务端）

移植自 Hands-On Delight 的 station/SkilletCooking.java；两面进度的状态机在 Shared/Rules/HandsOn/Frying.py。
每个煎锅一份 PanHand，站点关了它还在（锅里的东西接着煎、等着翻），方块没了才删。和 HoD 一样存进方块实体数据（键 panFrying，
Frying.save / load）：服务器重启、区块卸载再加载之后接着煎。
不是手放的（FD 自己的右键放进来的）照旧由 Server/Skillet.py 一件一件煎、弹出来；颠一下锅就从此归厨师，从生开始重算。
一面多久按方块里那件煎锅的火焰附加算（PanStation.sideSeconds）。两面都熟时这一批换成成品留在锅里，并广播 fried 事件（PanLook）。
"""
from . import PanLook
from .Helpers.BlockItems import PublishSkillet
from .Helpers.Engine import System
from ..Shared.Rules import PanStation
from ..Shared.Rules.HandsOn import Frying

SAVE_KEY = "panFrying"


class PanHand(object):
    def __init__(self):
        self.frying = Frying.Frying()
        self.cook = None                 # 最后放料 / 颠锅的玩家
        self.fried = 0                   # 煎好的批数（站点看它变了就报"煎好了"）
        self.tosses = 0                  # 颠成功的次数（广播看它变了就马上发）
        self.loaded = False              # 方块实体里存的两面进度读过没有


_hands = {}


def handOf(dimensionId, blockPos, blockEntityData=None):
    """这口锅的手工煎制状态；给了方块实体数据且还没读过存档，顺手读回来。"""
    key = (dimensionId, tuple(blockPos))
    hand = _hands.get(key)
    if hand is None:
        hand = _hands[key] = PanHand()
    if not hand.loaded and blockEntityData is not None:
        hand.loaded = True
        saved = blockEntityData[SAVE_KEY]
        if saved:
            hand.frying.load(saved)
    return hand


def peek(dimensionId, blockPos):
    return _hands.get((dimensionId, tuple(blockPos)))


def forget(dimensionId, blockPos):
    _hands.pop((dimensionId, tuple(blockPos)), None)
    PanLook.forget(dimensionId, blockPos)


def save(hand, blockEntityData):
    """两面进度写回方块实体数据（整个 dict 重新赋值才会存档）；没东西可存就清掉键。"""
    if blockEntityData is not None:
        blockEntityData[SAVE_KEY] = hand.frying.save()


def byFarmersDelight(dimensionId, blockPos, blockEntityData=None):
    """FD 自己的右键放料 / 取走：这锅回到 FD 原样（进度清零）。"""
    hand = peek(dimensionId, blockPos)
    if hand is not None:
        hand.frying.farmersDelightsWay()
        save(hand, blockEntityData)


def fry(hand, dimensionId, blockPos, blockEntityData, dt, fireAspect=0):
    """手放的一锅煎 dt 秒（煎锅烧着时由 Server/Skillet.py 的 tick 调用）。返回 False 表示这锅不归手工管，按 FD 原样煎。"""
    frying = hand.frying
    item = blockEntityData["cookingDict"]
    if not item or (item.get("count") or 0) <= 0:
        if frying.byHand or frying.down > 0.0 or frying.up > 0.0:
            frying.farmersDelightsWay()
            save(hand, blockEntityData)
        return False
    if not frying.byHand:
        return False
    fried = PanStation.friedOf(item["newItemName"])
    if fried is None:
        return True                      # 已经煎好，留在锅里等人取
    frying.resize(min(item["count"], Frying.BATCH))
    done = frying.step(dt, PanStation.sideSeconds(frying.batch, fireAspect), PanStation.isOneSided(item["newItemName"]))
    if done:
        _finish(hand, dimensionId, blockPos, blockEntityData, item, fried)
    if done or frying.dueToSend():
        save(hand, blockEntityData)
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
    PanLook.event(dimensionId, blockPos, "fried", {"stack": done, "in_pan": rest <= 0, "to_cook": False})


def toss(hand, playerId, now, item):
    """playerId 颠锅：锅里是能煎的东西且离上次颠够久才算。FD 原样煎着的锅从此归厨师、从生开始算。"""
    hasFood = bool(item) and PanStation.canFry(item.get("newItemName"))
    if not hand.frying.toss(now, hasFood):
        return False
    hand.cook = playerId
    hand.tosses += 1
    return True
