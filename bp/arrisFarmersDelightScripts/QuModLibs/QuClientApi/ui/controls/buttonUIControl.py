# -*- coding: utf-8 -*-

class ButtonUIControl(object):
    def AddTouchEventParams(self, args=None):
        # type: (dict) -> None
        """
        开启按钮回调功能，不调用该函数则按钮无回调
        """
        pass

    def SetButtonTouchDownCallback(self, callbackFunc):
        # type: (function) -> None
        """
        设置按钮按下时触发的回调函数
        """
        pass

    def SetButtonTouchUpCallback(self, callbackFunc):
        # type: (function) -> None
        """
        设置触控在按钮范围内弹起时的回调函数
        """
        pass

    def SetButtonTouchCancelCallback(self, callbackFunc):
        # type: (function) -> None
        """
        设置触控在按钮范围外弹起时触发的回调函数
        """
        pass

    def SetButtonTouchMoveCallback(self, callbackFunc):
        # type: (function) -> None
        """
        设置按下后触控移动时触发的回调函数
        """
        pass

    def SetButtonTouchMoveInCallback(self, callbackFunc):
        # type: (function) -> None
        """
        设置按下按钮后进入控件时触发的回调函数
        """
        pass

    def SetButtonTouchMoveOutCallback(self, callbackFunc):
        # type: (function) -> None
        """
        设置按下按钮后退出控件时触发的回调函数
        """
        pass

