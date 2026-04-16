# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class HurtCompServer(BaseComponent):
    def ImmuneDamage(self, immune):
        # type: (bool) -> bool
        """
        设置实体是否免疫伤害（该属性存档）
        """
        pass

    def Hurt(self, damage, cause, attackerId=None, childAttackerId=None, knocked=True):
        # type: (int, str, str, str, bool) -> bool
        """
        设置实体伤害
        """
        pass

