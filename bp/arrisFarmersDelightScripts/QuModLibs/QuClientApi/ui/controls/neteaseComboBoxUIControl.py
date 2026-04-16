# -*- coding: utf-8 -*-

class NeteaseComboBoxUIControl(object):
    def AddOption(self, showName, icon=None, userData=None):
        # type: (str, str, object) -> bool
        """
        添加下拉框项，若添加成功则返回True，否则返回False
        """
        pass

    def ClearOptions(self):
        # type: () -> None
        """
        清空下拉框
        """
        pass

    def ClearSelection(self):
        # type: () -> None
        """
        清除当前选中，使下拉框恢复未选中内容状态
        """
        pass

    def GetOptionIndexByShowName(self, name):
        # type: (str) -> int
        """
        根据展示文本查找对应下拉框项的索引位置，若找不到返回-1
        """
        pass

    def GetOptionShowNameByIndex(self, index):
        # type: (int) -> str
        """
        根据索引位置查找当前栈式文本，若找不到返回None
        """
        pass

    def GetOptionCount(self):
        # type: () -> int
        """
        获得选项数量
        """
        pass

    def GetSelectOptionIndex(self):
        # type: () -> int
        """
        获得当前选中项的索引，所无选中项则返回-1
        """
        pass

    def GetSelectOptionShowName(self):
        # type: () -> str
        """
        获得当前选中项的展示文本，所无选中项则返回None
        """
        pass

    def RemoveOptionByShowName(self, showName):
        # type: (str) -> bool
        """
        根据提供的展示文本移除对应下拉框项，移除成功则返回True，否则返回False
        """
        pass

    def RemoveOptionByIndex(self, index):
        # type: (int) -> bool
        """
        根据提供的索引移除对应下拉框项，移除成功则返回True，否则返回False
        """
        pass

    def SetSelectOptionByIndex(self, index):
        # type: (int) -> None
        """
        根据提供的索引选中对应下拉框项
        """
        pass

    def SetSelectOptionByShowName(self, name):
        # type: (str) -> None
        """
        根据提供的展示文本选中对应下拉框项
        """
        pass

    def RegisterOpenComboBoxCallback(self, callback):
        # type: (function) -> None
        """
        注册展开下拉框事件回调
        """
        pass

    def RegisterCloseComboBoxCallback(self, callback):
        # type: (function) -> None
        """
        注册关闭下拉框事件回调
        """
        pass

    def RegisterSelectItemCallback(self, callback):
        # type: (function) -> None
        """
        注册选中下拉框内容事件回调
        """
        pass

