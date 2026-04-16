# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class EffectComponentServer(BaseComponent):
    def AddEffectToEntity(self, effectName, duration, amplifier, showParticles):
        # type: (str, int, int, bool) -> bool
        """
        为实体添加指定状态效果，如果添加的状态已存在则有以下集中情况：1、等级大于已存在则更新状态等级及持续时间；2、状态等级相等且剩余时间duration大于已存在则刷新剩余时间；3、等级小于已存在则不做修改；4、粒子效果以新的为准
        """
        pass

    def RemoveEffectFromEntity(self, effectName):
        # type: (str) -> bool
        """
        为实体删除指定状态效果
        """
        pass

    def GetAllEffects(self):
        # type: () -> list[dict]
        """
        获取实体当前所有状态效果
        """
        pass

