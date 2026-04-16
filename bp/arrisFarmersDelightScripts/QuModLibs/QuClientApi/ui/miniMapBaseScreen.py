# -*- coding: utf-8 -*-

from screenNode import ScreenNode


class MiniMapBaseScreen(ScreenNode):
    def AddEntityMarker(self, entityId, texturePath, size=(4, 4), enableRotation=False):
        # type: (str, str, tuple[float,float], bool) -> bool
        """
        增加实体位置标记
        """
        pass

    def RemoveEntityMarker(self, entityId):
        # type: (str) -> bool
        """
        删除实体位置标记
        """
        pass

    def AddStaticMarker(self, key, vec2, texturePath, size=(4, 4)):
        # type: (str, tuple[float,float], str, tuple[float,float]) -> bool
        """
        增加地图上静态位置的标记
        """
        pass

    def RemoveStaticMarker(self, key):
        # type: (str) -> bool
        """
        删除静态位置标记
        """
        pass

    def ZoomIn(self, value=0.05):
        # type: (float) -> bool
        """
        放大地图
        """
        pass

    def ZoomOut(self, value=0.05):
        # type: (float) -> bool
        """
        缩小地图
        """
        pass

    def ZoomReset(self):
        # type: () -> bool
        """
        恢复地图放缩大小为默认值
        """
        pass

    def SetHighestY(self, highestY):
        # type: (int) -> bool
        """
        设置绘制地图的最大高度
        """
        pass

