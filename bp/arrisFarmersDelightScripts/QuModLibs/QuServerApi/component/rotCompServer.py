# -*- coding: utf-8 -*-


class RotComponentServer(object):
    def SetRot(self, rot):
        # type: (tuple[float,float]) -> bool
        """
        设置实体头与水平方向的俯仰角度和竖直方向的旋转角度 MC坐标系说明
        """
        pass

    def GetRot(self):
        # type: () -> tuple[float,float]
        """
        获取实体头与水平方向的俯仰角度和竖直方向的旋转角度，获得角度后可用GetDirFromRot接口转换为朝向的单位向量 MC坐标系说明
        """
        pass

    def SetEntityLookAtPos(self, targetPos, minTime, maxTime, reject):
        # type: (tuple[float,float,float], float, float, bool) -> bool
        """
        设置非玩家的实体看向某个位置
        """
        pass

