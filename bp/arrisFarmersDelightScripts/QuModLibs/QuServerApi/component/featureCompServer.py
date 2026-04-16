# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent

class FeatureCompServer(BaseComponent):
    def AddNeteaseFeatureWhiteList(self, structureName):
        # type: (str) -> bool
        """
        添加结构对PlaceNeteaseStructureFeatureEvent事件的脚本层监听
        """
        pass

    def RemoveNeteaseFeatureWhiteList(self, structureName):
        # type: (str) -> bool
        """
        移除structureName对PlaceNeteaseStructureFeatureEvent事件的脚本层监听
        """
        pass

    def ClearAllNeteaseFeatureWhiteList(self):
        # type: () -> bool
        """
        清空所有已添加Netease Structure Feature对PlaceNeteaseStructureFeatureEvent事件的脚本层监听
        """
        pass

    def LocateStructureFeature(self, featureType, dimensionId, pos):
        # type: (int, int, tuple[int,int,int]) -> object
        """
        与/locate指令相似，用于定位原版的部分结构，如海底神殿、末地城等。
        """
        pass

    def LocateNeteaseFeatureRule(self, ruleName, dimensionId, pos):
        # type: (str, int, tuple[int,int,int]) -> object
        """
        与/locate指令相似，用于定位网易自定义特征规则
        """
        pass

