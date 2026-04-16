# -*- coding: utf-8 -*-

class NeteasePaperDollUIControl(object):
    def GetModelId(self):
        # type: () -> int
        """
        获取渲染的骨骼模型Id
        """
        pass

    def RenderEntity(self, params):
        # type: (dict) -> bool
        """
        渲染实体
        """
        pass

    def RenderSkeletonModel(self, params):
        # type: (dict) -> bool
        """
        渲染骨骼模型（不依赖实体）
        """
        pass

