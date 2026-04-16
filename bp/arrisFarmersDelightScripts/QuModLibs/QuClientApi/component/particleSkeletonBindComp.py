# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ParticleSkeletonBindComp(BaseComponent):
    def Bind(self, modelId, boneName, offset, rot):
        # type: (int, str, tuple[float,float,float], tuple[float,float,float]) -> bool
        """
        绑定骨骼模型
        """
        pass


