# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class ControlAiCompServer(BaseComponent):
    def SetBlockControlAi(self, isBlock, freezeAnim=False):
        # type: (bool, bool) -> bool
        """
        设置屏蔽生物原生AI
        """
        pass

    def GetBlockControlAi(self):
        # type: () -> bool
        """
        获取生物原生AI是否被屏蔽
        """
        pass

