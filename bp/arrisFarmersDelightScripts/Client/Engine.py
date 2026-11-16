# -*- coding: utf-8 -*-
"""Engine - 客户端引擎入口的唯一出处（客户端）

加固版 QuModLibs 不导出 compFactory，由本模组自己取。

客户端读方块实体数据（CreateBlockInfo(levelId).GetBlockEntityData(pos)）拿到的是 NBT 形式：
exData 下每个值包成 {"__type__": ..., "__value__": ...}，列表元素同样包着；用 unwrap 取值。
"""
from ..QuModLibs.Client import clientApi, levelId, playerId, Call  # noqa: F401

compFactory = clientApi.GetEngineCompFactory()


def addDropItem(item, dimensionId, pos):
    """在世界里放一件只有本端看得见的掉落物（站点和方块上摆着的东西都是它），返回实体 id，没建成 None。
    掉落物脚下有一团影子，落在实体的位置上而不是画出来的位置上，摆着看就是旁边多出一块黑：建好就关掉。"""
    entityId = compFactory.CreateItem(levelId).AddDropItemToWorld(item, dimensionId, pos, 0, 0)
    if not entityId:
        return None
    compFactory.CreateModel(entityId).SetEntityShadowShow(False)
    return entityId


def unwrap(nbtValue, default=None):
    """{"__type__": t, "__value__": v} → v；None 或缺字段返回 default。"""
    if not nbtValue:
        return default
    if isinstance(nbtValue, dict) and "__value__" in nbtValue:
        return nbtValue["__value__"]
    return nbtValue


def unwrapDeep(nbtValue):
    """整棵 NBT 形式的值逐层解包（字典、列表里的值也包着）。"""
    if isinstance(nbtValue, dict):
        if "__value__" in nbtValue and "__type__" in nbtValue:
            return unwrapDeep(nbtValue["__value__"])
        return dict((key, unwrapDeep(value)) for key, value in nbtValue.items())
    if isinstance(nbtValue, list):
        return [unwrapDeep(value) for value in nbtValue]
    return nbtValue


def blockEntityExData(blockPos):
    """客户端方块实体数据的 exData 字典（没有返回 {}）。"""
    blockEntityData = compFactory.CreateBlockInfo(levelId).GetBlockEntityData(blockPos)
    if not blockEntityData:
        return {}
    return blockEntityData.get("exData") or {}
