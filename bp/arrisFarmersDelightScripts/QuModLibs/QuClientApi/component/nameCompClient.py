# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class NameComponentClient(BaseComponent):
    def SetShowName(self, show):
        # type: (bool) -> bool
        """
        设置生物名字是否按照默认游戏逻辑显示
        """
        pass

    def SetAlwaysShowName(self, show):
        # type: (bool) -> bool
        """
        设置生物名字是否一直显示，瞄准点不指向生物时也能显示
        """
        pass


