# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class OperationCompClient(BaseComponent):
    def SetCanMove(self, move):
        # type: (bool) -> bool
        """
        设置是否响应移动
        """
        pass

    def SetCanJump(self, jump):
        # type: (bool) -> bool
        """
        设置是否响应跳跃（以及在水中浮起）
        """
        pass

    def SetCanAttack(self, attack):
        # type: (bool) -> bool
        """
        设置是否响应攻击
        """
        pass

    def SetCanWalkMode(self, walkmode):
        # type: (bool) -> bool
        """
        设置是否响应切换行走模式
        """
        pass

    def SetCanPerspective(self, persp):
        # type: (bool) -> bool
        """
        设置是否响应切换视角
        """
        pass

    def SetCanPause(self, pause):
        # type: (bool) -> bool
        """
        设置是否响应暂停按钮
        """
        pass

    def SetCanChat(self, chat):
        # type: (bool) -> bool
        """
        设置是否响应聊天按钮
        """
        pass

    def SetCanScreenShot(self, shot):
        # type: (bool) -> bool
        """
        设置是否响应截图按钮
        """
        pass

    def SetCanOpenInv(self, open):
        # type: (bool) -> bool
        """
        设置是否响应打开背包按钮
        """
        pass

    def SetCanDrag(self, drag):
        # type: (bool) -> bool
        """
        设置是否响应屏幕拖动
        """
        pass

    def SetCanInair(self, inair):
        # type: (bool) -> bool
        """
        设置是否响应上升下降按钮（飞在空中时右下角的三个按钮）
        """
        pass

    def SetCanAll(self, all):
        # type: (bool) -> bool
        """
        同时设置SetCanMove，SetCanJump，SetCanAttack，SetCanWalkMode，SetCanPerspective，SetCanPause，SetCanChat，SetCanScreenShot，SetCanOpenInv，SetCanDrag，SetCanInair
        """
        pass

    def SetMoveLock(self, movelock):
        # type: (bool) -> bool
        """
        设置是否锁住移动。实际上为是否响应十字键与遥感的操作。
        """
        pass

    def SetHoldTimeThreshold(self, time):
        # type: (int) -> bool
        """
        设置长按判定时间，即按着屏幕多长时间会触发长按操作
        """
        pass

    def GetHoldTimeThresholdInMs(self):
        # type: () -> int
        """
        获取长按判定时间，即按着屏幕多长时间会触发长按操作
        """
        pass


