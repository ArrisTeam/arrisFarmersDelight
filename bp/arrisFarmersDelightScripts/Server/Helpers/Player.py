# -*- coding: utf-8 -*-
"""Player - 玩家相关的小工具：交互冷却、扣物品、扣耐久、给物品（服务端）"""
from .Engine import compFactory, levelId, System, Call, ItemPosType, SetCarriedItem
from .Fx import ToAllPlayerPlaySound
from .Items import GetItemType

# 交互冷却（秒）：防止一次点击被多个事件 / 按住右键的连发重复处理
USE_COOLDOWN = 0.2
_CD_ATTR = "arrisUsedCD"


def IsCreative(playerId):
    return compFactory.CreateGame(levelId).GetPlayerGameType(playerId) == 1


def ResetPlayerUsedCD(playerId):
    compFactory.CreateModAttr(playerId).SetAttr(_CD_ATTR, False)


def SetPlayerUsedCD(playerId):
    """玩家还在交互冷却中返回 True（调用方应直接 return）；否则开始冷却、让玩家挥一下手并返回 False。

    所有交互处理共用一个冷却：同一次点击会同时触发 ServerItemUseOnEvent 与 ServerBlockUseEvent，
    按住右键时引擎每 tick 重发事件，先处理的一方认领这次点击，其余在冷却内直接返回。
    """
    cd = compFactory.CreateModAttr(playerId).GetAttr(_CD_ATTR)
    if cd:
        return True
    compFactory.CreateModAttr(playerId).SetAttr(_CD_ATTR, True)
    compFactory.CreateGame(levelId).AddTimer(USE_COOLDOWN, ResetPlayerUsedCD, playerId)
    Call(playerId, "PlayAttackAnimationCommon", None)
    return False


def SetNotCreateItem(playerId, itemDict):
    """非创造模式下扣掉手里物品 1 个（itemDict 就是手里那件物品，会被就地改 count）。"""
    if not IsCreative(playerId):
        itemDict["count"] -= 1
        SetCarriedItem(playerId, itemDict)


def SetCarriedDurability(playerId, itemDict, dimensionId, pos):
    """非创造模式下手持工具耐久 -1，用坏时播放破碎声并清空手。方块与无耐久的物品不处理。"""
    if IsCreative(playerId):
        return
    if GetItemType(itemDict) in ["", "block"]:
        return
    if itemDict.get("durability") is None:
        return
    itemDict["durability"] -= 1
    if itemDict["durability"] <= 0:
        ToAllPlayerPlaySound(dimensionId, pos, "random.break")
        SetCarriedItem(playerId, None)
    else:
        SetCarriedItem(playerId, itemDict)


def GiveOrDropItem(playerId, itemDict, dimensionId=None):
    """给玩家物品；背包放不下时掉在玩家脚下（SpawnItemToPlayerInv 失败时物品不会凭空消失）。"""
    if compFactory.CreateItem(playerId).SpawnItemToPlayerInv(itemDict, playerId):
        return True
    if dimensionId is None:
        dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    pos = compFactory.CreatePos(playerId).GetFootPos()
    if pos is not None:
        System.CreateEngineItemEntity(itemDict, dimensionId, pos)
    return False
