# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class TameComponentServer(BaseComponent):
    def GetOwnerId(self):
        # type: () -> str
        """
        获取驯服生物的主人id
        """
        pass

    def SetEntityTamed(self, playerId, tamedId):
        # type: (str, str) -> bool
        """
        设置生物驯服，需要配合 entityEvent组件使用。该类驯服不包含骑乘功能。
        """
        pass

