# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent

class ActorOwnerComponentServer(BaseComponent):
    def SetEntityOwner(self, targetId):
        # type: (str) -> bool
        """
        设置实体的属主
        """
        pass

    def GetEntityOwner(self):
        # type: () -> str
        """
        获取实体的属主
        """
        pass

