# -*- coding: utf-8 -*-

class ImageUIControl(object):
    def SetSprite(self, texturePath):
        # type: (str) -> None
        """
        给图片控件换指定贴图
        """
        pass

    def SetSpriteColor(self, color):
        # type: (tuple[float,float,float]) -> None
        """
        设置图片颜色
        """
        pass

    def SetSpriteGray(self, gray):
        # type: (bool) -> None
        """
        给图片控件置灰，比直接SetSprite一张灰图片效率要高
        """
        pass

    def SetSpriteUV(self, uv):
        # type: (tuple[float,float]) -> None
        """
        设置图片的起始uv，与json中的"uv"属性作用一致
        """
        pass

    def SetSpriteUVSize(self, uvSize):
        # type: (tuple[float,float]) -> None
        """
        设置图片的uv大小，与json中的"uv_size"属性作用一致
        """
        pass

    def SetSpriteClipRatio(self, clipRatio):
        # type: (float) -> None
        """
        设置图片的裁剪区域比例（不改变控件尺寸）。可以配合image控件的clip_ratio属性控制方向。
        """
        pass

    def SetSpritePlatformHead(self):
        # type: () -> None
        """
        设置图片为我的世界移动端启动器当前帐号的头像
        """
        pass

    def SetSpritePlatformFrame(self):
        # type: () -> None
        """
        设置图片为我的世界移动端启动器当前帐号的头像框
        """
        pass

    def SetClipDirection(self, clipDirection):
        # type: (str) -> bool
        """
        设置图片控件的裁剪方向
        """
        pass

    def GetClipDirection(self):
        # type: () -> str
        """
        获取图片控件的裁剪方向
        """
        pass

    def SetImageAdaptionType(self, imageAdaptionType, imageAdaptionData=None):
        # type: (str, tuple[float,float,float,float]) -> bool
        """
        设置图片控件的图片适配方式以及信息
        """
        pass

