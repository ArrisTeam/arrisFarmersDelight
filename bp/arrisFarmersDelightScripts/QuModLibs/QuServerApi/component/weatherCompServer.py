# -*- coding: utf-8 -*-

from common.component.baseComponent import BaseComponent

class WeatherComponentServer(BaseComponent):
    def IsRaining(self):
        # type: () -> bool
        """
        获取是否下雨
        """
        pass

    def SetRaining(self, level, time):
        # type: (float, int) -> bool
        """
        设置是否下雨
        """
        pass

    def SetThunder(self, level, time):
        # type: (float, int) -> bool
        """
        设置是否打雷
        """
        pass

    def IsThunder(self):
        # type: () -> bool
        """
        获取是否打雷
        """
        pass

    def SetDimensionUseLocalWeather(self, dimension, value):
        # type: (int, bool) -> bool
        """
        设置某个维度拥有自己的天气规则，开启后该维度可以拥有与其他维度不同的天气和天气更替的规则
        """
        pass

    def GetDimensionUseLocalWeather(self, dimension):
        # type: (int) -> bool
        """
        获取某个维度是否拥有自己的天气规则
        """
        pass

    def SetDimensionLocalRain(self, dimension, rainLevel, rainTime):
        # type: (int, float, int) -> bool
        """
        设置某个维度下雨(必须先使用SetDimensionUseLocalWeather接口设置此维度拥有自己的独立天气)
        """
        pass

    def SetDimensionLocalThunder(self, dimension, thunderLevel, thunderTime):
        # type: (int, float, int) -> bool
        """
        设置某个维度打雷(必须先使用SetDimensionUseLocalWeather接口设置此维度拥有自己的独立天气)
        """
        pass

    def SetDimensionLocalDoWeatherCycle(self, dimension, value):
        # type: (int, bool) -> bool
        """
        设置某个维度是否开启天气循环(必须先使用SetDimensionUseLocalWeather接口设置此维度拥有自己的独立天气)
        """
        pass

    def GetDimensionLocalWeatherInfo(self, dimension):
        # type: (int) -> dict
        """
        获取独立维度天气信息(必须先使用SetDimensionUseLocalWeather接口设置此维度拥有自己的独立天气)
        """
        pass

