# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ItemCompClient(BaseComponent):
    def GetOffhandItem(self, getUserData=False):
        # type: (bool) -> dict
        """
        获取左手物品的信息
        """
        pass

    def GetCarriedItem(self, getUserData=False):
        # type: (bool) -> dict
        """
        获取右手物品的信息
        """
        pass

    def GetSlotId(self):
        # type: () -> int
        """
        获取当前手持的快捷栏的槽id
        """
        pass

    def GetItemBasicInfo(self, itemName, auxValue=0, isEnchanted=False):
        # type: (str, int, bool) -> dict
        """
        获取物品的基础信息
        """
        pass

    def GetItemFormattedHoverText(self, itemName, auxValue=0, showCategory=False, userData=None):
        # type: (str, int, bool, dict) -> str
        """
        获取物品的格式化hover文本，如：§f灾厄旗帜§r
        """
        pass

    def GetItemHoverName(self, itemName, auxValue=0, userData=None):
        # type: (str, int, dict) -> str
        """
        获取物品的hover名称，如：灾厄旗帜§r
        """
        pass

    def GetItemEffectName(self, itemName, auxValue=0, userData=None):
        # type: (str, int, dict) -> str
        """
        获取物品的状态描述，如：§7保护 0§r
        """
        pass

    def GetUserDataInEvent(self, eventName):
        # type: (str) -> bool
        """
        使物品相关客户端事件的物品信息字典参数带有userData。在mod初始化时调用即可
        """
        pass

    def ChangeItemTexture(self, identifier, texturePath):
        # type: (str, str) -> bool
        """
        替换物品的贴图，修改后所有用到该贴图的物品都会被改变，后续创建的此类物品也会被改变。会同时修改物品在UI界面上的显示，手持时候的显示与场景掉落的显示。
        """
        pass


