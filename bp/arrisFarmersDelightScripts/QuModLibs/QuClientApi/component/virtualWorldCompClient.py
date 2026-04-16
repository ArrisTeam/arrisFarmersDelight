# -*- coding: utf-8 -*-
from component.baseComponent import BaseComponent
class VirtualWorldCompClient(BaseComponent):
    def VirtualWorldCreate(self):
        # type: () -> bool
        """
        创建虚拟世界，虚拟世界只允许存在一个，已经存在虚拟世界的情况下再调用此方法则无效
        """
        pass

    def VirtualWorldDestroy(self):
        # type: () -> bool
        """
        销毁虚拟世界
        """
        pass

    def VirtualWorldToggleVisibility(self, isVisible):
        # type: (bool) -> bool
        """
        设置虚拟世界是否显示
        """
        pass

    def VirtualWorldSetCollidersVisible(self, isVisible):
        # type: (bool) -> bool
        """
        设置虚拟世界中模型的包围盒是否显示,主要用于调试,默认为不显示
        """
        pass

    def VirtualWorldSetSkyTexture(self, texturePath, mode):
        # type: (str, int) -> bool
        """
        设置虚拟世界中天空的贴图
        """
        pass

    def VirtualWorldSetSkyBgColor(self, color):
        # type: (tuple[float,float,float]) -> bool
        """
        设置虚拟世界中天空背景的颜色
        """
        pass

    def CameraSetPos(self, pos):
        # type: (tuple[float,float,float]) -> bool
        """
        设置相机位置
        """
        pass

    def CameraGetPos(self):
        # type: () -> tuple[float,float,float]
        """
        返回相机位置
        """
        pass

    def CameraSetFov(self, fov):
        # type: (float) -> bool
        """
        设置相机视野大小
        """
        pass

    def CameraGetFov(self):
        # type: () -> float
        """
        获取相机视野大小
        """
        pass

    def CameraSetZoom(self, zoom):
        # type: (float) -> bool
        """
        设置相机缩放
        """
        pass

    def CameraLookAt(self, targetPos, upVector):
        # type: (tuple[float,float,float], tuple[float,float,float]) -> bool
        """
        修改相机朝向
        """
        pass

    def CameraMoveTo(self, pos, targetPos, upVector, zoom, time, ease='linear'):
        # type: (tuple[float,float,float], tuple[float,float,float], tuple[float,float,float], float, float, object) -> bool
        """
        设置相机移动动画, 会根据当前相机状态与传入参数按时间进行插值显示
        """
        pass

    def CameraStopActions(self):
        # type: () -> bool
        """
        停止相机移动动画
        """
        pass

    def CameraGetZoom(self):
        # type: () -> float
        """
        获取相机的缩放值
        """
        pass

    def CameraGetClickModel(self):
        # type: () -> int
        """
        获取相机当前指向的模型的id，会返回离相机最近的，通常与GetEntityByCoordEvent配合使用
        """
        pass

    def ModelCreateObject(self, modelName, animationName):
        # type: (str, str) -> int
        """
        在虚拟世界中创建网易骨骼模型
        """
        pass

    def ModelCreateMinecraftObject(self, identifier):
        # type: (str) -> int
        """
        在虚拟世界中创建微软原版模型
        """
        pass

    def ModelSetVisible(self, objId, isVisible):
        # type: (int, bool) -> bool
        """
        设置模型可见性
        """
        pass

    def ModelIsVisible(self, objId):
        # type: (int) -> bool
        """
        返回模型可见性
        """
        pass

    def ModelUpdateAnimationMolangVariable(self, objId, molangdict):
        # type: (int, dict) -> bool
        """
        更新微软原版模型表达式变量，可控制动作的改变
        """
        pass

    def ModelPlayAnimation(self, objId, animationName, loop, isBlended=False, layer=0):
        # type: (int, str, bool, bool, int) -> bool
        """
        模型播放动画，支持动作融合，其功能与模型接口ModelPlayAni相同。
        """
        pass

    def ModelStopAnimation(self, objId, animationName):
        # type: (int, str) -> bool
        """
        停止播放指定的模型动画。
        """
        pass

    def ModelSetAnimBoneMask(self, objId, animationName, boneNameslist, enable, applyToChild=True):
        # type: (int, str, list[str], bool, bool) -> bool
        """
        设置是否屏蔽动画中指定的骨骼的动画，若开启骨骼屏蔽后，该骨骼将不再播放该动画中的动作。通过屏蔽指定骨骼的动画可实现同一个骨骼模型同时在不同骨骼上播放不同的动作动画，从而实现快捷的动作融合。
        """
        pass

    def ModelSetAnimAllBoneMask(self, objId, animationName, ignoreBoneslist, enable, applyToChild=True):
        # type: (int, str, list[str], bool, bool) -> bool
        """
        设置是否屏蔽动画中所有骨骼的动画，若开启骨骼屏蔽后，该骨骼将不再播放该动画中的动作。该接口会对该动画中所有骨骼生效，可通过参数ignoreBonelist来指定不受影响的骨骼名称。通过屏蔽指定骨骼的动画可实现同一个骨骼模型同时在不同骨骼上播放不同的动作动画，从而实现快捷的动作融合。
        """
        pass

    def ModelCancelAllBoneMask(self, objId, animationName):
        # type: (int, str) -> bool
        """
        取消动画中的所有骨骼屏蔽。
        """
        pass

    def ModelSetAnimLayer(self, objId, animationName, layer):
        # type: (int, str, int) -> bool
        """
        设置骨骼动画的层级，动画层级越大，则优先度越高，骨骼模型的骨骼优先播放优先度最高的动画，相同层级的动画则优先播放率先播放的动画。
        """
        pass

    def ModelRegisterAnim1DControlParam(self, objId, leftAniName, rightAniName, paramName):
        # type: (int, str, str, str) -> bool
        """
        当同时播放多个骨骼动画时，新建用于控制动画进行1D线性混合的参数。目前线性混合仅支持对两个动画进行混合。新建的参数值范围为[0,1]。指定的骨骼将会按照这个参数的值对两个动画进行线性混合。
        """
        pass

    def ModelSetAnim1DControlParam(self, objId, paramName, value):
        # type: (int, str, float) -> bool
        """
        新建动画的1D控制参数后，使用该接口对相应的参数进行控制。
        """
        pass

    def ModelSetBoxCollider(self, objId, lengths, offset=(0.0, 0.0, 0.0)):
        # type: (int, tuple[float,float,float], tuple[float,float,float]) -> bool
        """
        设置模型的包围盒
        """
        pass

    def ModelRemove(self, objId):
        # type: (int) -> bool
        """
        销毁虚拟世界中的模型
        """
        pass

    def ModelRotate(self, objId, degreeAngle, axis):
        # type: (int, float, tuple[float,float,float]) -> bool
        """
        模型绕某个轴旋转多少度
        """
        pass

    def ModelSetPos(self, objId, pos):
        # type: (int, tuple[float,float,float]) -> bool
        """
        设置模型坐标
        """
        pass

    def ModelGetPos(self, objId):
        # type: (int) -> tuple[float,float,float]
        """
        获取模型的坐标
        """
        pass

    def ModelSetRot(self, objId, rot):
        # type: (int, tuple[float,float,float]) -> bool
        """
        设置模型的旋转角度
        """
        pass

    def ModelGetRot(self, objId):
        # type: (int) -> tuple[float,float,float]
        """
        返回模型的旋转角度
        """
        pass

    def ModelSetScale(self, objId, scales):
        # type: (int, tuple[float,float,float]) -> bool
        """
        设置模型的缩放值
        """
        pass

    def ModelMoveTo(self, objId, pos, time, ease='linear'):
        # type: (int, tuple[float,float,float], float, object) -> bool
        """
        设置模型平移运动
        """
        pass

    def ModelRotateTo(self, objId, rot, time, ease='linear'):
        # type: (int, tuple[float,float,float], float, object) -> bool
        """
        设置模型旋转运动
        """
        pass

    def ModelStopActions(self, objId):
        # type: (int) -> bool
        """
        停止模型的移动和旋转运动
        """
        pass

    def MoveToVirtualWorld(self, virtualWorldObjectType, objId):
        # type: (int, int) -> bool
        """
        把对象从主世界移到虚拟世界, 非绑定的序列帧，文本，粒子需要调用该方法后才会出现在虚拟世界中，绑定的可以省略调用该方法。
        """
        pass

    def BindModel(self, virtualWorldObjectType, objId, targetId, posOffset, rotOffset, boneName='root'):
        # type: (int, int, int, tuple[float,float,float], tuple[float,float,float], str) -> bool
        """
        把对象绑定到模型上, 支持绑定序列帧，粒子，文本和其它模型
        """
        pass


