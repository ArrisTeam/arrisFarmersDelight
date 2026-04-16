# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class PostProcessComponent(BaseComponent):
    def SetEnableVignette(self, enable):
        # type: (bool) -> bool
        """
        设置是否开启屏幕渐晕（Vignette）效果，开启后玩家屏幕周围将出现渐晕，可通过Vignette其他接口设置效果参数。
        """
        pass

    def CheckVignetteEnabled(self):
        # type: () -> bool
        """
        检测是否开启了屏幕渐晕（Vignette）效果。
        """
        pass

    def SetVignetteRGB(self, color):
        # type: (tuple[float,float,float]) -> bool
        """
        设置渐晕（Vignette）的渐晕颜色，可改变屏幕渐晕的颜色。
        """
        pass

    def SetVignetteCenter(self, center):
        # type: (tuple[float,float]) -> bool
        """
        设置渐晕（Vignette）的渐晕中心位置，可改变屏幕渐晕的位置。
        """
        pass

    def SetVignetteRadius(self, radius):
        # type: (float) -> bool
        """
        设置渐晕（Vignette）的渐晕半径，半径越大，渐晕越小，玩家的视野范围越大。
        """
        pass

    def SetVignetteSmoothness(self, radius):
        # type: (float) -> bool
        """
        设置渐晕（Vignette）的渐晕模糊系数，模糊系数越大，则渐晕边缘越模糊，模糊的范围也越大
        """
        pass

    def SetEnableGaussianBlur(self, enable):
        # type: (bool) -> bool
        """
        设置是否开启高斯模糊效果，开启后玩家屏幕周围被模糊，可通过高斯模糊其他接口设置效果参数。
        """
        pass

    def CheckGaussianBlurEnabled(self):
        # type: () -> bool
        """
        检测是否开启了高斯模糊效果。
        """
        pass

    def SetGaussianBlurRadius(self, radius):
        # type: (float) -> bool
        """
        设置高斯模糊效果的模糊半径，半径越大，模糊程度越大，反之则模糊程度越小。
        """
        pass

    def SetEnableColorAdjustment(self, enable):
        # type: (bool) -> bool
        """
        设置是否开启色彩校正效果，开启后可进行屏幕色彩调整，可通过色彩校正效果其他接口设置效果参数。
        """
        pass

    def CheckColorAdjustmentEnabled(self):
        # type: () -> bool
        """
        检测是否开启了色彩校正效果。
        """
        pass

    def SetColorAdjustmentBrightness(self, brightness):
        # type: (float) -> bool
        """
        调整屏幕色彩亮度，亮度值越大，屏幕越亮，反之则越暗。
        """
        pass

    def SetColorAdjustmentSaturation(self, saturation):
        # type: (float) -> bool
        """
        调整屏幕色彩饱和度，屏幕饱和度值越大，色彩则越明显，反之则越灰暗。
        """
        pass

    def SetColorAdjustmentContrast(self, contrast):
        # type: (float) -> bool
        """
        调整屏幕色彩对比度，屏幕对比度值越大，色彩差异则越明显，反之则色彩差异越小。
        """
        pass

    def SetColorAdjustmentTint(self, intensity, color):
        # type: (float, tuple[float,float,float]) -> bool
        """
        调整屏幕色彩的色调，根据输入的色调和强度来调整屏幕色彩，当强度越大时，屏幕整体颜色越偏向输入的色调。
        """
        pass

    def SetEnableLensStain(self, enable):
        # type: (bool) -> bool
        """
        设置是否开启镜头污迹效果，开启后镜头出现污迹效果，可改变使用的污迹贴图及污迹颜色。
        """
        pass

    def CheckLensStainEnabled(self):
        # type: () -> bool
        """
        检测是否开启了镜头污迹效果。
        """
        pass

    def SetLensStainTexture(self, texturePath):
        # type: (str) -> bool
        """
        开启镜头污迹效果后，污迹效果使用的为系统默认贴图。该接口可改变镜头污迹所使用的贴图。注意贴图最好使用透明背景，否则屏幕将被贴图覆盖。
        """
        pass

    def ResetLensStainTexture(self):
        # type: () -> bool
        """
        重置污迹效果使用的贴图为系统默认贴图。
        """
        pass

    def SetLensStainIntensity(self, intensity):
        # type: (float) -> bool
        """
        调整镜头污迹强度，强度越大，污迹越明显，反之则越透明。
        """
        pass

    def SetLensStainColor(self, intensity, color):
        # type: (float, tuple[float,float,float]) -> bool
        """
        调整镜头污迹颜色，根据输入的颜色和强度来调整污迹色彩，当强度越大时，污迹颜色越偏向输入的颜色。
        """
        pass

    def SetEnableDepthOfField(self, enable):
        # type: (bool) -> bool
        """
        设置是否开启景深效果，开启后屏幕出现景深效果，根据焦点距离呈现远处模糊近处清晰或者近处模糊远处清晰的效果。
        """
        pass

    def CheckDepthOfFieldEnabled(self):
        # type: () -> bool
        """
        检测是否开启了景深效果。
        """
        pass

    def SetDepthOfFieldFocusDistance(self, distance):
        # type: (float) -> bool
        """
        调整景深效果焦点距离，距离越小，则远处模糊，近处清晰；距离越大，则远处清晰，近处模糊。该距离为实际距离，即以玩家相机为起点的世界坐标距离。
        """
        pass

    def SetDepthOfFieldBlurRadius(self, radius):
        # type: (float) -> bool
        """
        调整景深效果模糊半径，模糊半径越大，模糊程度越大，反之则越小。
        """
        pass

    def SetDepthOfFieldNearBlurScale(self, scale):
        # type: (float) -> bool
        """
        调整景深效果近景模糊大小，近景模糊大小越大，近景的模糊程度越大，反之则越小。注意，近景模糊程度的调节依赖于焦点距离，如果焦点处于较近的距离，那么此时近景处于较清晰的状态，模糊程度大小调节不会很明显。
        """
        pass

    def SetDepthOfFieldFarBlurScale(self, scale):
        # type: (float) -> bool
        """
        调整景深效果远景模糊大小，远景模糊大小越大，远景的模糊程度越大，反之则越小。注意，远景模糊程度的调节依赖于焦点距离，如果焦点处于较近的距离，那么此时远景处于较清晰的状态，模糊程度大小调节不会很明显。
        """
        pass

    def SetDepthOfFieldUseCenterFocus(self, enable):
        # type: (bool) -> bool
        """
        设置景深效果是否开启屏幕中心聚焦模式，开启后聚焦距离将被自动设置为屏幕中心所对应的物体所在的距离。在第一人称视角下，聚焦距离将被自动设置为屏幕准心所对应的物体与相机的距离，即自动聚焦准心所对应的物体。在第三人称视角下，由于屏幕中心总是对应着玩家，因此聚焦距离将被自动设置为玩家与相机的距离，即自动聚焦在玩家自己。
        """
        pass


