# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class TimeComponentServer(BaseComponent):
    def SetTime(self, time):
        # type: (int) -> bool
        """
        设置当前世界时间
        """
        pass

    def SetTimeOfDay(self, timeOfDay):
        # type: (int) -> bool
        """
        设置当前世界在一天内所在的时间
        """
        pass

    def GetTime(self):
        # type: () -> int
        """
        获取当前世界时间
        """
        pass

