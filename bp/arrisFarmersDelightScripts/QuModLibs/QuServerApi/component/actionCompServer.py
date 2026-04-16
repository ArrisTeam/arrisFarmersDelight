# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent

class ActionCompServer(BaseComponent):
    def SetAttackTarget(self, targetId):
        # type: (str) -> bool
        """
        设置仇恨目标
        """
        pass

    def ResetAttackTarget(self):
        # type: () -> bool
        """
        清除仇恨目标
        """
        pass

    def GetAttackTarget(self):
        # type: () -> str
        """
        获取仇恨目标
        """
        pass

    def SetMobKnockback(self, xd=0.1, zd=0.1, power=1.0, height=1.0, heightCap=1.0):
        # type: (float, float, float, float, float) -> None
        """
        设置击退的初始速度，需要考虑阻力的影响
        """
        pass

