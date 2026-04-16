# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class RedStoneComponentServer(BaseComponent):
    def GetStrength(self, pos, dimensionId=-1):
        # type: (tuple[float,float,float], int) -> int
        """
        获取某个坐标的红石信号强度
        """
        pass

    def GetBlockPoweredState(self, pos, dimensionId):
        # type: (tuple[float,float,float], int) -> int
        """
        获取某个坐标方块的充能状态
        """
        pass

