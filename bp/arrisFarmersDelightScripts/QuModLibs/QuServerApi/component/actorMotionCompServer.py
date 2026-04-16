# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent

class ActorMotionComponentServer(BaseComponent):
    def SetMotion(self, motion):
        # type: (tuple[float,float,float]) -> bool
        """
        设置生物（不含玩家）的瞬时移动方向向量
        """
        pass

    def SetPlayerMotion(self, motion):
        # type: (tuple[float,float,float]) -> bool
        """
        设置玩家的瞬时移动方向向量
        在damageEvent事件里面使用该接口时，需把damageEvent事件回调的knock参数设置为Fals
        """
        pass

    def GetMotion(self):
        # type: () -> tuple[int,int,int]
        """
        获取生物（含玩家）的瞬时移动方向向量
        """
        pass

    def ResetMotion(self):
        # type: () -> bool
        """
        重置生物（不含玩家）的瞬时移动方向向量
        """
        pass

