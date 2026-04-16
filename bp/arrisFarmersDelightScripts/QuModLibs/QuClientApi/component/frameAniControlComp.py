# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class FrameAniControlComp(BaseComponent):
    def Play(self):
        # type: () -> bool
        """
        播放序列帧
        """
        pass

    def Pause(self):
        # type: () -> bool
        """
        暂停播放，序列帧定格在当前时刻，再次调用Play时继续播放
        """
        pass

    def Stop(self):
        # type: () -> bool
        """
        停止序列帧（不是暂停）
        """
        pass

    def SetFaceCamera(self, face):
        # type: (bool) -> bool
        """
        设置序列帧是否始终朝向摄像机，默认为是
        """
        pass

    def SetLoop(self, loop):
        # type: (bool) -> bool
        """
        设置序列帧是否循环播放，默认为否
        """
        pass

    def SetDeepTest(self, deepTest):
        # type: (bool) -> bool
        """
        设置序列帧是否透视，默认为否
        """
        pass

    def SetLayer(self, layer):
        # type: (int) -> bool
        """
        设置序列帧渲染层级，默认层级为1，当层级不为1时表示该特效开启特效分层渲染功能。特效（粒子和帧动画）分层渲染时，层级越高渲染越靠后，层级大的会遮挡层级低的，且同一层级的特效会根据特效的相对位置产生正确的相互遮挡关系。
        """
        pass

    def SetMixColor(self, color):
        # type: (tuple[float,float,float,float]) -> bool
        """
        设置序列帧混合颜色
        """
        pass

    def SetFadeDistance(self, fadeDistance):
        # type: (float) -> bool
        """
        设置序列帧开始自动调整透明度的距离。序列帧与摄像机之间的距离小于该值时会自动调整序列帧的透明度，距离摄像机越近，序列帧越透明
        """
        pass

    def SetUsePointFiltering(self, use):
        # type: (bool) -> bool
        """
        设置序列帧是否使用点滤波
        """
        pass


