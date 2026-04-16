# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ConfigCompClient(BaseComponent):
    def GetConfigData(self, configName, isGlobal=False):
        # type: (str, bool) -> dict
        """
        获取本地配置文件中存储的数据
        """
        pass

    def SetConfigData(self, configName, value, isGlobal=False):
        # type: (str, dict, bool) -> bool
        """
        以本地配置文件的方式存储数据
        """
        pass


