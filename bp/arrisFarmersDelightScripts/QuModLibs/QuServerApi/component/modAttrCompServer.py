# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class ModAttrComponentServer(BaseComponent):
    def SetAttr(self, paramName, paramValue, needRestore=False):
        # type: (str, object, bool) -> None
        """
        设置属性值
        """
        pass

    def GetAttr(self, paramName, defaultValue=None):
        # type: (str, object) -> object
        """
        获取属性值
        """
        pass

