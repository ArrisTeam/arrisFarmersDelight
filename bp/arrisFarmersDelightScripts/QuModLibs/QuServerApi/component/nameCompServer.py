# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class NameComponentServer(BaseComponent):
    def SetName(self, name):
        # type: (str) -> bool
        """
        用于设置生物的自定义名称，跟原版命名牌作用相同，玩家和新版流浪商人暂不支持
        """
        pass

    def GetName(self):
        # type: () -> str
        """
        获取生物的自定义名称，即使用命名牌或者SetName接口设置的名称
        """
        pass

    def SetPlayerPrefixAndSuffixName(self, prefix, prefixColor, suffix, suffixColor):
        # type: (str, str, str, str) -> bool
        """
        设置玩家前缀和后缀名字
        """
        pass

