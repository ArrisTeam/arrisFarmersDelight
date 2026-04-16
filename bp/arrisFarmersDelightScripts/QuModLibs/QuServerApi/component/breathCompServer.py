# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class BreathCompServer(BaseComponent):
    def GetUnitBubbleAirSupply(self):
        # type: () -> int
        """
        单位气泡数对应的氧气储备值
        """
        pass

    def GetCurrentAirSupply(self):
        # type: () -> int
        """
        生物当前氧气储备值
        """
        pass

    def GetMaxAirSupply(self):
        # type: () -> int
        """
        获取生物最大氧气储备值
        """
        pass

    def SetCurrentAirSupply(self, data):
        # type: (int) -> bool
        """
        设置生物氧气储备值
        """
        pass

    def SetMaxAirSupply(self, data):
        # type: (int) -> bool
        """
        设置生物最大氧气储备值
        """
        pass

    def IsConsumingAirSupply(self):
        # type: () -> bool
        """
        获取生物当前是否在消耗氧气
        """
        pass

    def SetRecoverTotalAirSupplyTime(self, timeSec):
        # type: (float) -> bool
        """
        设置恢复最大氧气量的时间，单位秒
        """
        pass

