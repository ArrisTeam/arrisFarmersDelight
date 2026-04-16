# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class CameraComponentClient(BaseComponent):
    def GetFov(self):
        # type: () -> float
        """
        获取视野大小
        """
        pass

    def SetFov(self, fov):
        # type: (float) -> bool
        """
        设置视野大小
        """
        pass

    def LockCamera(self, lockPos, lockRot):
        # type: (tuple[float,float,float], tuple[float,float]) -> bool
        """
        锁定摄像机
        """
        pass

    def UnLockCamera(self):
        # type: () -> bool
        """
        解除摄像机锁定
        """
        pass

    def PickFacing(self):
        # type: () -> dict
        """
        获取准星选中的实体或者方块
        """
        pass

    def GetFpHeight(self):
        # type: () -> float
        """
        获取本地玩家当前状态下，第一人称视角时的摄像机高度偏移量。游泳时，滑翔时以及普通状态下会有所不同
        """
        pass

    def GetChosenEntity(self):
        # type: () -> str
        """
        获取屏幕点击位置的实体id，通常与GetEntityByCoordEvent配合使用
        """
        pass

    def GetChosen(self):
        # type: () -> dict
        """
        获取屏幕点击位置的实体或方块信息，通常与GetEntityByCoordEvent配合使用
        """
        pass

    def DepartCamera(self):
        # type: () -> None
        """
        分离玩家与摄像机
        """
        pass

    def UnDepartCamera(self):
        # type: () -> None
        """
        绑定玩家与摄像机
        """
        pass

    def SetCameraBindActorId(self, targetId):
        # type: (str) -> bool
        """
        将摄像机绑定到目标实体身上（调用者与目标必须在同一个dimension，同时需要在加载范围之内，若绑定后目标离开了范围或者死亡，则会自动解除绑定）
        """
        pass

    def ResetCameraBindActorId(self):
        # type: () -> bool
        """
        将摄像机重新绑定回主角身上
        """
        pass

    def GetForward(self):
        # type: () -> tuple[float,float,float]
        """
        返回相机向前的方向
        """
        pass

    def GetPosition(self):
        # type: () -> tuple[float,float,float]
        """
        返回相机中心
        """
        pass

    def SetCameraPos(self, pos):
        # type: (tuple[float,float,float]) -> bool
        """
        设置相机中心的位置
        """
        pass

    def SetCameraRot(self, rot):
        # type: (tuple[float,float]) -> bool
        """
        设定相机转向
        """
        pass

    def GetCameraRot(self):
        # type: () -> tuple[float,float]
        """
        获取相机转向
        """
        pass

    def SetCameraOffset(self, offset):
        # type: (tuple[float,float,float]) -> bool
        """
        设置摄像机偏移量
        """
        pass

    def GetCameraOffset(self):
        # type: () -> tuple[float,float,float]
        """
        获取摄像机偏移量
        """
        pass

    def SetCameraAnchor(self, offset):
        # type: (tuple[float,float,float]) -> bool
        """
        设置相机锚点,暂时只支持高度,其他维度无效
        """
        pass

    def GetCameraAnchor(self):
        # type: () -> tuple[float,float,float]
        """
        获取相机锚点
        """
        pass

    def LockModCameraPitch(self, enable):
        # type: (int) -> bool
        """
        锁定摄像机上下角度（第三人称下生效，锁定后不能上下调整视角）
        """
        pass

    def IsModCameraLockPitch(self):
        # type: () -> bool
        """
        是否锁定摄像机上下角度
        """
        pass

    def GetCameraPitchLimit(self):
        # type: () -> tuple[float,float]
        """
        获取摄像机上下角度限制值
        """
        pass

    def SetCameraPitchLimit(self, limit):
        # type: (tuple[float,float]) -> bool
        """
        设置摄像机上下角度限制值，默认是（-90，90）
        """
        pass

    def LockModCameraYaw(self, enable):
        # type: (int) -> bool
        """
        锁定摄像机左右角度（第三人称下生效，锁定后不能通过鼠标左右调整视角）
        """
        pass

    def IsModCameraLockYaw(self):
        # type: () -> bool
        """
        是否锁定摄像机左右角度
        """
        pass

    def SetSpeedFovLock(self, isLocked):
        # type: (bool) -> None
        """
        是否锁定相机视野fov，锁定后不随速度变化而变化
        """
        pass


