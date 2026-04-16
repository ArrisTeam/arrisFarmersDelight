# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class ItemBannedCompServer(BaseComponent):
    def AddBannedItem(self, itemName):
        # type: (str) -> bool
        """
        增加禁用物品
        """
        pass

    def GetBannedItemList(self):
        # type: () -> object
        """
        获取禁用物品列表
        """
        pass

    def RemoveBannedItem(self, itemName):
        # type: (str) -> bool
        """
        移除禁用物品
        """
        pass

    def ClearBannedItems(self):
        # type: () -> bool
        """
        清空禁用物品
        """
        pass

