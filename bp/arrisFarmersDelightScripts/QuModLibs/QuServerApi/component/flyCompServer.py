# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class FlyComponentServer(BaseComponent):
    def IsPlayerFlying(self):
        # type: () -> bool
        """
        获取玩家是否在飞行
        """
        pass

    def ChangePlayerFlyState(self, isFly):
        # type: (bool) -> bool
        """
        给予/取消飞行能力，并且进入飞行/非飞行状态
        """
        pass

