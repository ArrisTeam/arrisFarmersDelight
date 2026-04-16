# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class PetComponentServer(BaseComponent):
    def Disable(self):
        # type: () -> bool
        """
        关闭官方伙伴功能，单人游戏以及本地联机不支持该接口
        """
        pass

    def Enable(self):
        # type: () -> bool
        """
        启用官方伙伴功能，单人游戏以及本地联机不支持该接口
        """
        pass

