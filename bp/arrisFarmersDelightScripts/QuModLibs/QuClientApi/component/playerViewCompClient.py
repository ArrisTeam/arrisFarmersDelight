# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class PlayerViewCompClient(BaseComponent):
    def GetPerspective(self):
        # type: () -> int
        """
        获取当前的视角模式
        """
        pass

    def SetPerspective(self, persp):
        # type: (int) -> bool
        """
        设置视角模式
        """
        pass

    def LockPerspective(self, lock):
        # type: (int) -> bool
        """
        锁定玩家的视角模式
        """
        pass

    def GetUIProfile(self):
        # type: () -> int
        """
        获取"UI 档案"模式
        """
        pass

    def SetUIProfile(self, profileType):
        # type: (int) -> bool
        """
        设置"UI 档案"模式
        """
        pass

    def SetToggleOption(self, optionId, isOn):
        # type: (str, bool) -> bool
        """
        修改开关型设置的接口
        """
        pass

    def SetSplitControlCanChange(self, canChange):
        # type: (bool) -> bool
        """
        设置是否允许使用准星瞄准按钮
        """
        pass

    def GetToggleOption(self, optionId):
        # type: (str) -> int
        """
        获得某个开关设置值的接口
        """
        pass

    def HighlightBoxSelection(self, isHighlight):
        # type: (bool) -> None
        """
        镜头移动时高亮当前视角中心所指的方块
        """
        pass


