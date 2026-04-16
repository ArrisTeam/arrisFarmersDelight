# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class LevelComponentServer(BaseComponent):
    def GetPlayerLevel(self):
        # type: () -> int
        """
        获取玩家等级
        """
        pass

    def AddPlayerLevel(self, level):
        # type: (int) -> bool
        """
        修改玩家等级
        """
        pass

