# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class FrameAniTransComp(BaseComponent):
    def GetPos(self):
        # type: () -> tuple[float,float,float]
        """
        获取序列帧特效的位置
        """
        pass

    def SetPos(self, pos):
        # type: (tuple[float,float,float]) -> bool
        """
        设置序列帧的位置
        """
        pass

    def GetRot(self):
        # type: () -> tuple[float,float,float]
        """
        获取序列帧特效的旋转角度
        """
        pass

    def SetRot(self, rot):
        # type: (tuple[float,float,float]) -> bool
        """
        设置序列帧的旋转
        """
        pass

    def SetRotUseZXY(self, rot):
        # type: (tuple[float,float,float]) -> bool
        """
        设置序列帧的旋转，旋转顺序按照绕z,x,y轴旋转
        """
        pass

    def GetScale(self):
        # type: () -> tuple[float,float,float]
        """
        获取序列帧特效的缩放值
        """
        pass

    def SetScale(self, scale):
        # type: (tuple[float,float,float]) -> bool
        """
        设置序列帧的缩放
        """
        pass


