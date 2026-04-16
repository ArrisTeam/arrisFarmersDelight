# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class EngineTypeComponentServer(BaseComponent):
    def GetEngineType(self):
        # type: () -> int
        """
        获取实体类型，主要用于判断实体是否属于某一类型的生物。
        """
        pass

    def GetEngineTypeStr(self):
        # type: () -> str
        """
        获取实体的类型名称
        """
        pass

