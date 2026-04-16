# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class ModelComponentServer(BaseComponent):
    def SetModel(self, modelName):
        # type: (str) -> bool
        """
        设置骨骼模型
        """
        pass

    def SetModelTexture(self, texture):
        # type: (str) -> bool
        """
        设置骨骼模型贴图，该接口与SetTexture功能相同，但属于服务端接口。
        """
        pass

    def SetModelOffset(self, offset):
        # type: (tuple[float,float,float]) -> None
        """
        设置骨骼模型相对于局部坐标系的偏移量，初始值为(0, 0, 0)
        """
        pass

    def GetModelName(self):
        # type: () -> str
        """
        获取实体的模型名称
        """
        pass

    def ShowCommonHurtColor(self, show):
        # type: (bool) -> bool
        """
        设置挂接骨骼模型的实体是否显示通用的受伤变红效果
        """
        pass

