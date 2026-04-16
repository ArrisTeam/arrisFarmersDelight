# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ParticleTransComp(BaseComponent):
    def GetPos(self):
        # type: () -> tuple[float,float,float]
        """
        获取粒子发射器的世界坐标位置
        """
        pass

    def SetPos(self, pos):
        # type: (tuple[float,float,float]) -> bool
        """
        设置粒子发射器的世界坐标位置
        """
        pass

    def GetRot(self):
        # type: () -> tuple[float,float,float]
        """
        获取粒子发射器的旋转角度
        """
        pass

    def SetRotUseZXY(self, rot):
        # type: (tuple[float,float,float]) -> bool
        """
        设置粒子发射器的旋转，旋转顺序按照绕z,x,y轴旋转
        """
        pass


