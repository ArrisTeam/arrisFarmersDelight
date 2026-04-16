# -*- coding: utf-8 -*-


class PosComponentServer(object):
    def SetPos(self, pos):
        # type: (tuple[int,int,int]) -> bool
        """
        设置实体位置
        """
        pass

    def GetPos(self):
        # type: () -> tuple[float,float,float]
        """
        获取实体位置
        """
        pass

    def GetFootPos(self):
        # type: () -> tuple[float,float,float]
        """
        获取实体脚所在的位置
        """
        pass

    def SetFootPos(self, footPos):
        # type: (tuple[float,float,float]) -> bool
        """
        设置实体脚底所在的位置
        """
        pass

