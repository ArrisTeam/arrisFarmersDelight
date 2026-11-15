# -*- coding: utf-8 -*-
"""Engine - 客户端引擎入口的唯一出处（客户端）

加固版 QuModLibs 不导出 compFactory，由本模组自己取。

客户端读方块实体数据（CreateBlockInfo(levelId).GetBlockEntityData(pos)）拿到的是 NBT 形式：
exData 下每个值包成 {"__type__": ..., "__value__": ...}，列表元素同样包着；用 unwrap 取值。
"""
from ..QuModLibs.Client import clientApi, levelId, playerId, Call  # noqa: F401

compFactory = clientApi.GetEngineCompFactory()


def unwrap(nbtValue, default=None):
    """{"__type__": t, "__value__": v} → v；None 或缺字段返回 default。"""
    if not nbtValue:
        return default
    if isinstance(nbtValue, dict) and "__value__" in nbtValue:
        return nbtValue["__value__"]
    return nbtValue


def blockEntityExData(blockPos):
    """客户端方块实体数据的 exData 字典（没有返回 {}）。"""
    blockEntityData = compFactory.CreateBlockInfo(levelId).GetBlockEntityData(blockPos)
    if not blockEntityData:
        return {}
    return blockEntityData.get("exData") or {}
