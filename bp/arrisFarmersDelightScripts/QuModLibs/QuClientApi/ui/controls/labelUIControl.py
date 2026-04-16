# -*- coding: utf-8 -*-

class LabelUIControl(object):
    def SetText(self, text, syncSize=False):
        # type: (str, bool) -> None
        """
        设置Label的文本信息
        """
        pass

    def GetText(self):
        # type: () -> str
        """
        获取Label的文本信息，获取失败会返回None
        """
        pass

    def SetTextColor(self, color):
        # type: (tuple[float,float,float]) -> None
        """
        设置Label文本的颜色
        """
        pass

    def GetTextColor(self):
        # type: () -> tuple[float,float,float,float]
        """
        获取Label文本颜色
        """
        pass

    def SetTextFontSize(self, componentPath, scale):
        # type: (str, float) -> None
        """
        设置Label中文本字体的大小
        """
        pass

    def SetTextAlignment(self, textAlignment):
        # type: (str) -> bool
        """
        设置文本控件的文本对齐方式
        """
        pass

    def GetTextAlignment(self):
        # type: () -> str
        """
        获取文本控件的文本对齐方式
        """
        pass

    def SetTextLinePadding(self, textLinePadding):
        # type: (float) -> bool
        """
        设置文本控件的行间距
        """
        pass

    def GetTextLinePadding(self):
        # type: () -> float
        """
        获取文本控件的行间距
        """
        pass

    def EnableTextShadow(self):
        # type: () -> bool
        """
        使文本控件显示阴影
        """
        pass

    def DisableTextShadow(self):
        # type: () -> bool
        """
        关闭文本控件显示阴影
        """
        pass

    def IsTextShadowEnabled(self):
        # type: () -> bool
        """
        判断文本控件是否显示阴影
        """
        pass

