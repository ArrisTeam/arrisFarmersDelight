# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class SkyRenderCompClient(BaseComponent):
    def SetSkyColor(self, color):
        # type: (tuple[float,float,float,float]) -> bool
        """
        设置天空颜色
        """
        pass

    def ResetSkyColor(self):
        # type: () -> bool
        """
        重置天空颜色
        """
        pass

    def GetSkyColor(self):
        # type: () -> tuple[float,float,float,float]
        """
        获取天空颜色
        """
        pass

    def GetUseSkyColor(self):
        # type: () -> bool
        """
        判断是否在mod设置了天空颜色
        """
        pass

    def SetSunRot(self, rot):
        # type: (tuple[float,float,float]) -> bool
        """
        设置太阳所在角度
        """
        pass

    def ResetSunRot(self):
        # type: () -> bool
        """
        重置太阳角度
        """
        pass

    def GetSunRot(self):
        # type: () -> tuple[float,float,float]
        """
        获取太阳角度
        """
        pass

    def GetUseSunRot(self):
        # type: () -> bool
        """
        判断是否在mod设置了太阳角度
        """
        pass

    def SetMoonRot(self, rot):
        # type: (tuple[float,float,float]) -> bool
        """
        设置月亮所在角度
        """
        pass

    def ResetMoonRot(self):
        # type: () -> bool
        """
        重置月亮角度
        """
        pass

    def GetMoonRot(self):
        # type: () -> tuple[float,float,float]
        """
        获取月亮角度
        """
        pass

    def GetUseMoonRot(self):
        # type: () -> bool
        """
        判断是否在mod设置了月亮角度
        """
        pass

    def SetAmbientBrightness(self, brightness):
        # type: (float) -> bool
        """
        设置环境光亮度，影响天空亮度，不影响实体与方块光照
        """
        pass

    def ResetAmbientBrightness(self):
        # type: () -> bool
        """
        重置环境光亮度
        """
        pass

    def GetAmbientBrightness(self):
        # type: () -> float
        """
        获取环境光亮度，影响天空亮度，不影响实体与方块光照
        """
        pass

    def GetUseAmbientBrightness(self):
        # type: () -> bool
        """
        判断是否在mod设置了环境光亮度
        """
        pass

    def SetStarBrightness(self, brightness):
        # type: (float) -> bool
        """
        设置星星亮度，白天也可以显示星星
        """
        pass

    def ResetStarBrightness(self):
        # type: () -> bool
        """
        重置星星亮度
        """
        pass

    def GetStarBrightness(self):
        # type: () -> float
        """
        获取星星亮度
        """
        pass

    def GetUseStarBrightness(self):
        # type: () -> bool
        """
        判断是否在mod设置了星星亮度
        """
        pass

    def SetSkyTextures(self, texturelist):
        # type: (list[str]) -> bool
        """
        设置当前维度天空盒贴图，天空盒需要6张贴图
        """
        pass

    def GetSkyTextures(self):
        # type: () -> list[str]
        """
        获取当前维度天空盒贴图，天空盒共6张贴图
        """
        pass

    def ResetSkyTextures(self):
        # type: () -> bool
        """
        重置当前维度天空盒贴图。如果有使用addon配置贴图则会使用配置的贴图，否则为游戏内默认无贴图的情况
        """
        pass

    def SkyTextures(self):
        # type: () -> None
        """
        修改太阳、月亮、云层分布、天空盒的贴图。使用addon配置，非python接口。
        """
        pass


