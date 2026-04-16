# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent


class DimensionCompServer(BaseComponent):
    def ChangePlayerDimension(self, dimensionId, pos):
        # type: (int, tuple[int,int,int]) -> bool
        """
        传送玩家
        """
        pass

    def GetEntityDimensionId(self):
        # type: () -> int
        """
        获取实体所在维度
        """
        pass

    def ChangeEntityDimension(self, dimensionId, pos=None):
        # type: (int, tuple[int,int,int]) -> bool
        """
        传送实体
        """
        pass

    def MirrorDimension(self, fromId, toId):
        # type: (int, int) -> bool
        """
        复制不同dimension的地形
        """
        pass

    def CreateDimension(self, dimensionId):
        # type: (int) -> bool
        """
        创建新的dimension
        """
        pass

    def RegisterEntityAOIEvent(self, dimension, name, aabb, ignoredEntities, entityType=1):
        # type: (int, str, tuple[float,float,float,float,float,float], list[str], int) -> bool
        """
        注册感应区域，有实体进入时和离开时会有消息通知
        """
        pass

    def UnRegisterEntityAOIEvent(self, dimension, name):
        # type: (int, str) -> bool
        """
        反注册感应区域
        """
        pass

    def SetUseLocalTime(self, dimension, value):
        # type: (int, bool) -> bool
        """
        让某个维度拥有自己的局部时间规则，开启后该维度可以拥有与其他维度不同的时间与是否昼夜更替的规则
        """
        pass

    def GetUseLocalTime(self, dimension):
        # type: (int) -> bool
        """
        获取某个维度是否设置了使用局部时间规则
        """
        pass

    def SetLocalTime(self, dimension, time):
        # type: (int, int) -> bool
        """
        设置使用局部时间规则维度的时间
        """
        pass

    def SetLocalTimeOfDay(self, dimension, timeOfDay):
        # type: (int, int) -> bool
        """
        设置使用局部时间规则维度在一天内所在的时间
        """
        pass

    def GetLocalTime(self, dimension):
        # type: (int) -> int
        """
        获取维度的时间
        """
        pass

    def SetLocalDoDayNightCycle(self, dimension, value):
        # type: (int, bool) -> bool
        """
        设置使用局部时间规则的维度是否打开昼夜更替
        """
        pass

    def GetLocalDoDayNightCycle(self, dimension):
        # type: (int) -> bool
        """
        获取维度是否打开昼夜更替
        """
        pass

