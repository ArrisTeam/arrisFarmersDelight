# -*- coding: utf-8 -*-
"""Drops - 把东西从方块里抛出来：落在方块里随机一点（Containers.dropItemStack）、从一个点弹出去（ItemUtils.spawnItemEntity）、
砧板切出来 / 煎锅煎好的从方块侧面弹出去（服务端）

JE 的掉落物生成时带着初速；基岩版 CreateEngineItemEntity 只给位置，初速要再用 CreateActorMotion(实体).SetMotion 设（单位同 JE：每刻几格，
和 dolorContainer 抛东西、箱子掉东西同一个做法：dolorContainer/Server/Engine.py、Std/Block/Server.py）。位置和初速的数在 Shared/Rules/ItemDrops.py。
"""
import random

from .Engine import compFactory, System, GetBlockAux
from ...Shared.Rules import ItemDrops
from ...Shared.Rules.Placement import directionOfAux


def PopItem(dimensionId, pos, item, motion):
    """在 pos 生成一个掉落物，给它初速 motion（每刻几格）。"""
    entityId = System.CreateEngineItemEntity(item, dimensionId, pos)
    if entityId:
        compFactory.CreateActorMotion(entityId).SetMotion(motion)
    return entityId


def PopOut(dimensionId, pos, item):
    """FD 的 ItemUtils.spawnItemEntity 烤好弹出：从 pos 往上带一点点随机的横向初速弹出去。"""
    return PopItem(dimensionId, pos, item, ItemDrops.popMotion(random))


def ScatterItem(dimensionId, blockPos, item):
    """FD 的 ItemUtils.dropItems 对一格里的一叠：从 blockPos 这个方块里随机一点掉出来，数量多的分成每个 10..30 个，各带一点随机的初速。"""
    x, y, z = blockPos
    for amount, (fx, fy, fz), motion in ItemDrops.scatter(item.get("count") or 1, random):
        drop = dict(item)
        drop["count"] = amount
        PopItem(dimensionId, (x + fx, y + fy, z + fz), drop, motion)


def _popFrom(dimensionId, blockPos, item, placed):
    offset, motion = placed
    return PopItem(dimensionId, tuple(corner + shift for corner, shift in zip(blockPos, offset)), item, motion)


def PopFromBoard(dimensionId, blockPos, item):
    """FD 的砧板切出一件（CuttingBoardBlockEntity.processStoredItemUsingTool:89-92）：从板的侧面带着初速弹出去，朝板的朝向逆时针那一边。"""
    return _popFrom(dimensionId, blockPos, item, ItemDrops.boardPop(directionOfAux(GetBlockAux(blockPos, dimensionId))))


def PopFromPan(dimensionId, blockPos, item):
    """FD 的煎锅煎好一件（SkilletBlockEntity.cookAndOutputItems:102-105）：从锅心往上、往侧面带着初速弹出去，朝锅柄的逆时针那一边。"""
    return _popFrom(dimensionId, blockPos, item, ItemDrops.panPop(directionOfAux(GetBlockAux(blockPos, dimensionId))))
