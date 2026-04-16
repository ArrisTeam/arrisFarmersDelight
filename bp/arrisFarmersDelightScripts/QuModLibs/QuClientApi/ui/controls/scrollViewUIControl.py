# -*- coding: utf-8 -*-

class ScrollViewUIControl(object):
    def SetScrollViewPos(self, pos):
        # type: (float) -> None
        """
        设置当前scroll_view内容的位置
        """
        pass

    def GetScrollViewPos(self):
        # type: () -> float
        """
        获得当前scroll_view最上方内容的位置
        """
        pass

    def SetScrollViewPercentValue(self, percent_value):
        # type: (int) -> None
        """
        设置当前scroll_view内容的百分比位置
        """
        pass

    def GetScrollViewContentPath(self):
        # type: () -> str
        """
        返回该scroll_view内容的路径
        """
        pass

    def GetScrollViewContentControl(self):
        # type: () -> object
        """
        返回该scroll_view内容的BaseUIControl实例
        """
        pass

