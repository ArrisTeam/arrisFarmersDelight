# -*- coding: utf-8 -*-


class RotComponentClient(object):
    def GetRot(self):
        # type: () -> tuple[float,float]
        """
        获取实体头与水平方向的俯仰角度和竖直方向的旋转角度，获得角度后可用GetDirFromRot接口转换为朝向的单位向量 MC坐标系说明
        """
        pass

    def SetRot(self, rot):
        # type: (tuple[float,float]) -> bool
        """
        设置实体头与水平方向的俯仰角度和竖直方向的旋转角度 MC坐标系说明
        """
        pass

    def GetBodyRot(self):
        # type: () -> float
        """
        获取实体的身体的角度
        """
        pass

    def LockLocalPlayerRot(self, lock):
        # type: (bool) -> bool
        """
        在分离摄像机时，锁定本地玩家的头部角度
        """
        pass

    def SetPlayerLookAtPos(self, targetPos, pitchStep, yawStep, blockInput=True):
        # type: (tuple[float,float,float], float, float, bool) -> bool
        """
        设置本地玩家看向某个位置
        """
        pass


