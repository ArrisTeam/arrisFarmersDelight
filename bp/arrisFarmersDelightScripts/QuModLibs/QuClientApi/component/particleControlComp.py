# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ParticleControlComp(BaseComponent):
    def Play(self):
        # type: () -> bool
        """
        播放粒子特效
        """
        pass

    def Pause(self):
        # type: () -> bool
        """
        暂停播放，粒子定格在当前时刻，再次调用Play时继续播放
        """
        pass

    def Stop(self):
        # type: () -> bool
        """
        停止粒子播放
        """
        pass

    def SetRelative(self, relative):
        # type: (bool) -> bool
        """
        当粒子绑定了entity或骨骼模型时，发射出的粒子使用entity坐标系还是世界坐标系。与mcstudio特效编辑器中粒子的“相对挂点运动”选项功能相同。
        """
        pass

    def SetLayer(self, layer):
        # type: (int) -> bool
        """
        粒子默认层级为1，当层级不为1时表示该特效开启特效分层渲染功能。特效（粒子和帧动画）分层渲染时，层级越高渲染越靠后，层级大的会遮挡层级低的，且同一层级的特效会根据特效的相对位置产生正确的相互遮挡关系。
        """
        pass

    def SetFadeDistance(self, fadeDistance):
        # type: (float) -> bool
        """
        设置粒子开始自动调整透明度的距离。粒子与摄像机之间的距离小于该值时会自动调整粒子的透明度，距离摄像机越近，粒子越透明
        """
        pass

    def SetUsePointFiltering(self, enable):
        # type: (bool) -> bool
        """
        设置粒子材质的纹理滤波是否使用点滤波方法。默认为使用双线性滤波
        """
        pass

    def SetParticleSize(self, minSize, maxSize):
        # type: (tuple[float,float], tuple[float,float]) -> bool
        """
        设置粒子特效中粒子大小的最小值及最大值。
        """
        pass

    def GetParticleMaxSize(self):
        # type: () -> tuple[float,float]
        """
        获取粒子特效中粒子大小的最大值。
        """
        pass

    def GetParticleMinSize(self):
        # type: () -> tuple[float,float]
        """
        获取粒子特效中粒子大小的最小值。
        """
        pass

    def SetParticleVolumeSize(self, scale):
        # type: (tuple[float,float,float]) -> bool
        """
        设置粒子发射器的体积大小缩放，不影响单个粒子的尺寸。粒子发射器的体积越大，则粒子的发射范围越大。
        """
        pass

    def GetParticleVolumeSize(self):
        # type: () -> tuple[float,float,float]
        """
        获取粒子发射器的体积大小缩放值。
        """
        pass

    def SetParticleMaxNum(self, num):
        # type: (int) -> bool
        """
        设置粒子发射器的粒子容量，即粒子发射器所包含的最大粒子数量。该数量并不代表目前粒子发射器所发射的粒子数量，如需要增加发射的粒子数量，需同时改变粒子的发射频率。
        """
        pass

    def GetParticleMaxNum(self):
        # type: () -> int
        """
        获取粒子发射器包含的最大粒子数量。
        """
        pass

    def SetParticleEmissionRate(self, minRate, maxRate):
        # type: (float, float) -> bool
        """
        设置粒子发射器每帧发射粒子的频率，频率越大则每帧发射的粒子数量越多，但粒子数量不会超过粒子发射器的粒子容量，同时由于性能考虑，每帧发射的粒子数量也不会超过100个。
        """
        pass

    def GetParticleEmissionRate(self):
        # type: () -> tuple[float,float]
        """
        获取粒子发射器每帧发射粒子的频率。
        """
        pass


