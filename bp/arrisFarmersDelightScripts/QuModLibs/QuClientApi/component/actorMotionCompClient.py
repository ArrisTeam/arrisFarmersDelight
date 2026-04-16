# -*- coding: utf-8 -*-
from component.baseComponent import BaseComponent

class ActorMotionComponentClient(BaseComponent):
    def GetInputVector(self):
        # type: () -> tuple[float,float]
        """
        获取方向键（移动轮盘）的输入
        """
        pass

    def LockInputVector(self, inputVector):
        # type: (tuple[float,float]) -> bool
        """
        锁定本地玩家方向键（移动轮盘）的输入，可使本地玩家持续向指定方向前行，且不会再受玩家输入影响
        """
        pass

    def UnlockInputVector(self):
        # type: () -> bool
        """
        解锁本地玩家方向键（移动轮盘）的输入
        """
        pass

    def SetMotion(self, motion):
        # type: (tuple[float,float,float]) -> bool
        """
        设置瞬时的移动方向向量，用于本地玩家
        """
        pass

    def GetMotion(self):
        # type: () -> tuple[int,int,int]
        """
        获取生物的瞬时移动方向向量
        """
        pass

    def BeginSprinting(self):
        # type: () -> None
        """
        使本地玩家进入并保持向前冲刺状态
        """
        pass

    def EndSprinting(self):
        # type: () -> None
        """
        使本地玩家结束向前冲刺状态
        """
        pass


