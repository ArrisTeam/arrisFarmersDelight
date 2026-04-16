# -*- coding: utf-8 -*-
from ....Client import clientApi, levelId, playerId
from Globals import (
    _ItemBasicInfo,
    _ItemData,
    _InventoryData,
    EnchNBTView,
    EnchantType
)
lambda: "物品服务模块 By Zero123"

class ItemBasicInfo(_ItemBasicInfo):
    """ 基础物品信息 """
    def getArgs(self, itemName, auxValue, isEnchanted):
        # type: (str, int, bool) -> dict
        comp = clientApi.GetEngineCompFactory().CreateItem(levelId)
        return comp.GetItemBasicInfo(itemName, auxValue, isEnchanted)

class ItemData(_ItemData):
    """ 物品参数 """
    def getItemBasicInfo(self):
        # type: () -> _ItemBasicInfo
        """ 获取物品基础信息 """
        return ItemBasicInfo(self.newItemName, self.newAuxValue)

class InventoryData(_InventoryData):
    """ 背包物品信息 """
    USE_ITEM_CLS = ItemData

def GET_PLAYER_INVENTORY():
    """ 获取玩家当前背包数据 """
    comp = clientApi.GetEngineCompFactory().CreateItem(playerId)
    dataList = comp.GetPlayerAllItems(0, True) or []
    return InventoryData.loadItemDictList(dataList)