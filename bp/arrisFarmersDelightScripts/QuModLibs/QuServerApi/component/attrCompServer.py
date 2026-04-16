# -*- coding: utf-8 -*-
from common.component.baseComponent import BaseComponent

class AttrCompServer(BaseComponent):
    def SetAttrValue(self, attrType, value):
        # type: (int, float) -> bool
        """
        设置实体的引擎属性
        """
        pass

    def GetAttrValue(self, attrType):
        # type: (int) -> float
        """
        获取实体的引擎属性
        """
        pass

    def SetAttrMaxValue(self, type, value):
        # type: (int, float) -> bool
        """
        设置实体的引擎属性的最大值
        """
        pass

    def GetAttrMaxValue(self, type):
        # type: (int) -> float
        """
        获取实体的引擎属性的最大值
        """
        pass

    def IsEntityOnFire(self):
        # type: () -> bool
        """
        获取实体是否着火
        """
        pass

    def SetEntityOnFire(self, seconds, burn_damage=1):
        # type: (int, int) -> bool
        """
        设置实体着火
        """
        pass

    def SetStepHeight(self, stepHeight):
        # type: (float) -> bool
        """
        设置玩家前进非跳跃状态下能上的最大台阶高度, 默认值为0.5625，1的话表示能上一个台阶
        """
        pass

    def GetStepHeight(self):
        # type: () -> float
        """
        返回玩家前进非跳跃状态下能上的最大台阶高度
        """
        pass

    def ResetStepHeight(self):
        # type: () -> bool
        """
        恢复引擎默认玩家前进非跳跃状态下能上的最大台阶高度
        """
        pass

    def GetTypeFamily(self):
        # type: () -> list[str]
        """
        获取生物行为包字段 type_family
        """
        pass

    def SetPersistent(self, persistent):
        # type: (bool) -> bool
        """
        设置实体不会因为离玩家太远而被清除
        """
        pass

