# -*- coding: utf-8 -*-
"""BoardDish - 砧板摆盘的存档：板上叠着的层、做好的那叠（服务端）

只在场景交互 · 前置在场时由砧板站点（Compat/Diegesis/BoardDish.py）往里放；经典玩法也认它：右键砧板把它们全还给玩家，
拆砧板时掉出来。存在方块实体数据 dishLayers（物品字典的列表，底座在前）和 dishDone（做好的那叠或 None），
整件存：名字、aux、数量和附魔 / 耐久 / 改名 / extraId / userData（Shared/Rules/HandsOn/ItemData.py），读出来换回物品字典，还给玩家 / 掉出来都原样；
变了就广播给各客户端画（Helpers/BlockItems.PublishBoardDish）。
"""
from .BlockItems import PublishBoardDish
from .Engine import System
from .Fx import ToAllPlayerPlaySound
from .Player import GiveOrDropItem
from ...Shared.Rules.HandsOn import ItemData

LAYERS_KEY = "dishLayers"
DONE_KEY = "dishDone"


def stack(item, count=None):
    """存档用的一叠：名字（str）、aux、数量和全部数据。"""
    return ItemData.stored(item, count)


def layersOf(blockEntityData):
    """层（底座在前），读出来是物品字典（附魔换回元组）。"""
    layers = blockEntityData[LAYERS_KEY] or []
    return [ItemData.restored(layer) for layer in layers if layer and layer.get("newItemName") and (layer.get("count") or 0) > 0]


def dishOf(blockEntityData):
    dish = blockEntityData[DONE_KEY]
    return ItemData.restored(dish) if dish and dish.get("newItemName") and (dish.get("count") or 0) > 0 else None


def hasAny(blockEntityData):
    return bool(layersOf(blockEntityData)) or dishOf(blockEntityData) is not None


def save(dimensionId, blockPos, blockEntityData, layers, dish=None):
    """整体回写（改了嵌套列表必须回写）并广播。"""
    blockEntityData[LAYERS_KEY] = [stack(layer) for layer in layers] if layers else None
    blockEntityData[DONE_KEY] = stack(dish) if dish else None
    PublishBoardDish(dimensionId, blockPos, layers, dish)


def giveBack(playerId, dimensionId, blockPos, blockEntityData):
    """层和做好的菜全还给玩家（背包满了掉在脚下）。板上没有返回 False。"""
    things = ([dishOf(blockEntityData)] if dishOf(blockEntityData) else []) + layersOf(blockEntityData)
    if not things:
        return False
    for item in things:
        GiveOrDropItem(playerId, item, dimensionId)
    save(dimensionId, blockPos, blockEntityData, None)
    ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
    return True


def spill(dimensionId, blockPos, blockEntityData):
    """拆砧板：层和做好的菜掉在原地。"""
    x, y, z = blockPos
    for item in ([dishOf(blockEntityData)] if dishOf(blockEntityData) else []) + layersOf(blockEntityData):
        System.CreateEngineItemEntity(item, dimensionId, (x + 0.5, y + 0.5, z + 0.5))
    blockEntityData[LAYERS_KEY] = None
    blockEntityData[DONE_KEY] = None
