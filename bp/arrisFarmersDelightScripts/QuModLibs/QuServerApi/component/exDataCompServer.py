# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent

class ExDataCompServer(BaseComponent):
    def SetExtraData(self, key, value, autoSave=True):
        # type: (str, object, bool) -> bool
        """
        用于设置实体的自定义数据或者世界的自定义数据，数据以键值对的形式保存。设置实体数据时使用对应实体id创建组件，设置世界数据时使用levelId创建组件
        """
        pass

    def SaveExtraData(self):
        # type: () -> bool
        """
        用于保存实体的自定义数据或者世界的自定义数据
        """
        pass

    def CleanExtraData(self, key):
        # type: (str) -> bool
        """
        清除实体的自定义数据或者世界的自定义数据，清除实体数据时使用对应实体id创建组件，清除世界数据时使用levelId创建组件
        """
        pass

    def GetExtraData(self, key):
        # type: (str) -> object
        """
        获取实体的自定义数据或者世界的自定义数据，某个键所对应的值。获取实体数据时使用对应实体id创建组件，获取世界数据时使用levelId创建组件
        """
        pass

    def GetWholeExtraData(self):
        # type: () -> object
        """
        获取完整的实体的自定义数据或者世界的自定义数据，获取实体数据时使用对应实体id创建组件，获取世界数据时使用levelId创建组件
        """
        pass

