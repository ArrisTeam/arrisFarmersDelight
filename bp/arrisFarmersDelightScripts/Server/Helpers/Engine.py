# -*- coding: utf-8 -*-
"""Engine - 服务端引擎入口的唯一出处（服务端）

玩法模块从这里按名字导入 compFactory / levelId / System 等，不再经星号导入链层层传递。
加固版 QuModLibs 不导出 compFactory，由本模组自己取。

方块实体数据（compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(维度, 坐标)）的两个坑：
- 返回的是引擎对象，不是 dict：没有 .get()，缺键时读出来是 None，用 ``data["k"] or 缺省值``；
- 读走的是 Python 侧缓存，只有赋值才会写进引擎、随存档落盘；缓存在区块卸载时丢弃。
  改了取回来的字典 / 列表之后一定要整体赋值回去，否则区块卸载后恢复原值。
  键必须是 str；列表里元素类型要一致；值不能是 unicode（不满足时引擎只打日志，不报错）。
"""
from ...QuModLibs.Server import serverApi, levelId, System, Call, DestroyEntity  # noqa: F401

compFactory = serverApi.GetEngineCompFactory()
ItemPosType = serverApi.GetMinecraftEnum().ItemPosType


def GetBlockEntityData(dimensionId, blockPos):
    """取方块实体数据对象；方块没有方块实体时返回 None。"""
    return compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dimensionId, blockPos)


def GetBlockName(blockPos, dimensionId):
    return compFactory.CreateBlockInfo(levelId).GetBlockNew(blockPos, dimensionId)["name"]


def GetEngineTypeStr(entityId):
    return compFactory.CreateEngineType(entityId).GetEngineTypeStr()


def GetCarriedItem(playerId, getUserData=False):
    """玩家主手物品（没有返回 None）。"""
    return compFactory.CreateItem(playerId).GetPlayerItem(ItemPosType.CARRIED, 0, getUserData)


def SetCarriedItem(playerId, itemDict):
    compFactory.CreateItem(playerId).SetEntityItem(ItemPosType.CARRIED, itemDict, 0)


def ShowTip(playerId, text):
    compFactory.CreateGame(playerId).SetOneTipMessage(playerId, text)


def GetLoadedEntities():
    """所有维度里已加载的非玩家实体：{实体 id: {"dimensionId": 维度, "identifier": 类型名}}。"""
    return serverApi.GetEngineActor()
