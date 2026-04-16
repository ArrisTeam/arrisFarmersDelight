# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class EntityEventComponentServer(BaseComponent):
    def TriggerCustomEvent(self, entityId, eventName):
        # type: (str, str) -> bool
        """
        触发生物自定义事件
        """
        pass

