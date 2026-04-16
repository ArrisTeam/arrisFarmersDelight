# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class AttrCompClient(BaseComponent):
    def isEntityInLava(self):
        # type: () -> bool
        """
        实体是否在岩浆中
        """
        pass

    def isEntityOnGround(self):
        # type: () -> bool
        """
        实体是否触地
        """
        pass

    def GetAttrValue(self, attrType):
        # type: (int) -> float
        """
        获取属性值，包括生命值，饥饿度，移速
        """
        pass

    def GetAttrMaxValue(self, type):
        # type: (int) -> float
        """
        获取属性最大值，包括生命值，饥饿度，移速等
        """
        pass


