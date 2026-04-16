# -*- coding: utf-8 -*-
from ....Server import serverApi, levelId, _loaderSystem
from ..Server import BaseService
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
        comp = serverApi.GetEngineCompFactory().CreateItem(levelId)
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

class BaseItemService(BaseService):
    """ 基本物品服务 """
    @staticmethod
    def spawnInventoryItems(_inventoryData, pos, dm):
        # type: (InventoryData, tuple[float], int) -> None
        """ 将一个背包中的所有物品生成到世界 """
        for itemData in _inventoryData.walk():
            if itemData.empty:
                continue
            _loaderSystem.CreateEngineItemEntity(itemData.getDict(), dm, tuple(pos))

    @staticmethod
    def getPlayerInventoryData(playerId, getUserData = False, itemPosType = 0):
        """ 获取玩家背包物品信息 itemPosType默认为背包 getUserData启用后将拿到userData字段 """
        comp = serverApi.GetEngineCompFactory().CreateItem(playerId)
        return InventoryData.loadItemDictList(comp.GetPlayerAllItems(itemPosType, getUserData), playerId)

    @staticmethod
    def setPlayerInventoryData(playerId, inventoryData, itemPosType = 0, leaveBlankValues = False):
        # type: (str, InventoryData, int, bool) -> None
        """ 设置玩家背包物品信息 itemPosType默认为背包 leaveBlankValues启用后将会保留空物品对象 """
        comp = serverApi.GetEngineCompFactory().CreateItem(playerId)
        comp.SetPlayerAllItems(inventoryData.getItemsDictMap(itemPosType, leaveBlankValues))

    @staticmethod
    def setEntityInventoryData(entityId, data, itemPosType = 0, leaveBlankValues = False):
        # type: (str, InventoryData | ItemData, int, bool) -> None
        """ 设置实体背包物品信息 itemPosType默认为背包 leaveBlankValues启用后将会保留空物品对象 """
        comp = serverApi.GetEngineCompFactory().CreateItem(entityId)
        if isinstance(data, InventoryData):
            for itemData in data.walk():
                if not leaveBlankValues and itemData.empty:
                    continue
                comp.SetEntityItem(itemPosType, itemData.getDict(), itemData.index)
        elif isinstance(data, ItemData):
            if not leaveBlankValues and data.empty:
                return
            comp.SetEntityItem(itemPosType, data.getDict(), 0)

    @staticmethod
    def setPlayerHandItem(playerId, handItemData):
        # type: (str, ItemData) -> None
        """ 设置玩家手持物品 """
        comp = serverApi.GetEngineCompFactory().CreateItem(playerId)
        comp.SpawnItemToPlayerCarried(handItemData.getDict(), playerId)

    @staticmethod
    def getPlayerHandItem(playerId, getUserData = False):
        # type: (str, bool) -> ItemData
        """ 获取玩家手持物品 """
        comp = serverApi.GetEngineCompFactory().CreateItem(playerId)
        return ItemData(comp.GetPlayerItem(2, 0, getUserData), playerId)

    def __init__(self):
        BaseService.__init__(self)
        if self.__class__ is BaseItemService:
            raise RuntimeError("请勿实例化基类服务")