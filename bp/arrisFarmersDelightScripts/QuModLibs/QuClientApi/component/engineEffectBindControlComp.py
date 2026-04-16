# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class EngineEffectBindControlComp(BaseComponent):
    def Pause(self):
        # type: () -> bool
        """
        暂停模型特效（即使用CreateEngineEffectBind创建的特效）
        """
        pass

    def Resume(self):
        # type: () -> bool
        """
        继续播放模型特效（即使用CreateEngineEffectBind创建的特效）
        """
        pass


