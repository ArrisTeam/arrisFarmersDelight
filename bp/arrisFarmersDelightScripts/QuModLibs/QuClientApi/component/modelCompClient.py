# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class ModelComponentClient(BaseComponent):
    def SetModel(self, modelName):
        # type: (str) -> int
        """
        替换实体的骨骼模型
        """
        pass

    def GetModelId(self):
        # type: () -> int
        """
        获取骨骼模型的Id，主要用于特效绑定骨骼模型
        """
        pass

    def ResetModel(self):
        # type: () -> bool
        """
        恢复实体为原版模型
        """
        pass

    def PlayAnim(self, aniName, isLoop):
        # type: (str, bool) -> bool
        """
        播放骨骼动画
        """
        pass

    def GetPlayingAnimlist(self, modelId):
        # type: (int) -> list[str]
        """
        获取指定的骨骼模型中正处于播放状态的骨骼动画名称列表
        """
        pass

    def GetAnimLength(self, aniName):
        # type: (str) -> float
        """
        获取某个骨骼动画的长度，单位为秒
        """
        pass

    def SetAnimSpeed(self, aniName, speed):
        # type: (str, float) -> bool
        """
        设置某个骨骼动画的播放速度
        """
        pass

    def BindModelToModel(self, boneName, modelName):
        # type: (str, str) -> int
        """
        在骨骼模型上挂接其他骨骼模型
        """
        pass

    def UnBindModelToModel(self, modelId):
        # type: (int) -> bool
        """
        取消骨骼模型上挂接的某个骨骼模型。取消挂接后，这个modelId的模型便会销毁，无法再使用，如果是临时隐藏可以使用HideModel
        """
        pass

    def BindModelToEntity(self, boneName, modelName, offset=(0, 0, 0), rot=(0, 0, 0)):
        # type: (str, str, tuple[float,float,float], tuple[float,float,float]) -> int
        """
        实体替换骨骼模型后，再往上其他挂接骨骼模型。
        """
        pass

    def UnBindModelToEntity(self, modelId):
        # type: (int) -> bool
        """
        取消实体上挂接的某个骨骼模型。取消挂接后，这个modelId的模型便会销毁，无法再使用，如果是临时隐藏可以使用HideModel
        """
        pass

    def GetAllBindModelToEntity(self, boneName):
        # type: (str) -> list[int]
        """
        获取实体上某个骨骼上挂接的所有骨骼模型的id
        """
        pass

    def SetTexture(self, texture):
        # type: (str) -> bool
        """
        设置骨骼模型的贴图，该接口与SetModelTexture功能相同，但属于客户端接口。
        """
        pass

    def GetTexture(self):
        # type: () -> str
        """
        获取骨骼模型的贴图路径
        """
        pass

    def SetSkin(self, skin):
        # type: (str) -> bool
        """
        更换原版自定义皮肤
        """
        pass

    def SetLegacyBindRot(self, enable):
        # type: (bool) -> bool
        """
        用于修复特效挂接到骨骼时的方向
        """
        pass

    def GetBoneWorldPos(self, boneName):
        # type: (str) -> tuple[int,int,int]
        """
        获取骨骼的坐标
        """
        pass

    def GetEntityBoneWorldPos(self, entityId, boneName):
        # type: (str, str) -> tuple[int,int,int]
        """
        获取换了骨骼模型的实体的骨骼坐标
        """
        pass

    def CreateFreeModel(self, modelName):
        # type: (str) -> int
        """
        创建自由的模型（无需绑定Entity）
        """
        pass

    def RemoveFreeModel(self, modelId):
        # type: (int) -> bool
        """
        移除自由模型
        """
        pass

    def SetFreeModelPos(self, modelId, x, y, z):
        # type: (int, float, float, float) -> bool
        """
        设置自由模型的位置
        """
        pass

    def SetFreeModelRot(self, modelId, x, y, z):
        # type: (int, float, float, float) -> bool
        """
        设置自由模型的方向
        """
        pass

    def SetFreeModelAniSpeed(self, modelId, aniName, speed):
        # type: (int, str, float) -> bool
        """
        设置自由模型动画的播放速度
        """
        pass

    def SetFreeModelScale(self, modelId, x, y, z):
        # type: (int, float, float, float) -> bool
        """
        设置自由模型的大小
        """
        pass

    def ModelPlayAni(self, modelId, aniName, isLoop=False, isBlended=False, layer=0):
        # type: (int, str, bool, bool, int) -> bool
        """
        纯骨骼播放动作。 支持骨骼动画混合，可参考SetAnimationBoneMask接口以及RegisterAnim1DControlParam接口说明。
        """
        pass

    def HideModel(self, modelId):
        # type: (int) -> None
        """
        隐藏纯模型
        """
        pass

    def ShowModel(self, modelId):
        # type: (int) -> None
        """
        显示纯模型
        """
        pass

    def SetFreeModelBoundingBox(self, modelId, min, max):
        # type: (int, tuple[float,float,float], tuple[float,float,float]) -> bool
        """
        设置自由模型的包围盒
        """
        pass

    def BindEntityToEntity(self, bindEntityId):
        # type: (str) -> bool
        """
        绑定骨骼模型跟随其他entity,摄像机也跟随其他entity
        """
        pass

    def ResetBindEntity(self):
        # type: () -> bool
        """
        取消目标entity的绑定实体，取消后不再跟随任何其他entity
        """
        pass

    def SetModelOffset(self, offset):
        # type: (tuple[float,float,float]) -> None
        """
        模型增加偏移量
        """
        pass

    def SetModelPerspectiveEffect(self, isPerspective, color):
        # type: (bool, tuple[float,float,float,float]) -> None
        """
        设置模型透视效果。注：只对自定义骨骼模型生效
        """
        pass

    def SetEntityOpacity(self, opacity):
        # type: (float) -> None
        """
        设置骨骼模型的透明度，只能对骨骼模型生效，如果设置的是原版模型，则模型的影子会被隐藏。
        """
        pass

    def ShowCommonHurtColor(self, show):
        # type: (bool) -> bool
        """
        设置挂接骨骼模型的实体是否显示通用的受伤变红效果
        """
        pass

    def SetShowArmModel(self, modelId, show):
        # type: (int, bool) -> bool
        """
        设置使用骨骼模型后切换至第一人称时是否显示手部模型。需要先为骨骼模型定义arm_model，arm_model的定义可参考demo示例-AwesomeMod中的resourcePack/models/netease_models.json中的大天狗模型定义
        """
        pass

    def SetExtraUniformValue(self, modelId, uniformIndex, vec4data):
        # type: (int, int, tuple[float,float,float,float]) -> bool
        """
        设置shader中特定Uniform的值
        """
        pass

    def ModelStopAni(self, modelId, aniName):
        # type: (int, str) -> bool
        """
        暂停指定的骨骼动画
        """
        pass

    def SetAnimationBoneMask(self, modelId, aniName, boneNameslist, enable, applyToChild=True):
        # type: (int, str, list[str], bool, bool) -> bool
        """
        设置是否屏蔽动画中指定的骨骼的动画，若开启骨骼屏蔽后，该骨骼将不再播放该动画中的动作。通过屏蔽指定骨骼的动画可实现同一个骨骼模型同时在不同骨骼上播放不同的动作动画，从而实现快捷的动作融合。
        """
        pass

    def SetAnimationAllBoneMask(self, modelId, aniName, ignoreBoneslist, enable, applyToChild=True):
        # type: (int, str, list[str], bool, bool) -> bool
        """
        设置是否屏蔽动画中所有骨骼的动画，若开启骨骼屏蔽后，该骨骼将不再播放该动画中的动作。该接口会对该动画中所有骨骼生效，可通过参数ignoreBonelist来指定不受影响的骨骼名称。通过屏蔽指定骨骼的动画可实现同一个骨骼模型同时在不同骨骼上播放不同的动作动画，从而实现快捷的动作融合。
        """
        pass

    def CancelAllBoneMask(self, modelId, aniName):
        # type: (int, str) -> bool
        """
        取消动画中的所有骨骼屏蔽。
        """
        pass

    def SetAnimLayer(self, modelId, aniName, layer):
        # type: (int, str, int) -> bool
        """
        设置骨骼动画的层级，动画层级越大，则优先度越高，骨骼模型的骨骼优先播放优先度最高的动画，相同层级的动画则优先播放率先播放的动画。
        """
        pass

    def RegisterAnim1DControlParam(self, modelId, leftAniName, rightAniName, paramName):
        # type: (int, str, str, str) -> bool
        """
        当同时播放多个骨骼动画时，新建用于控制动画进行1D线性混合的参数。目前线性混合仅支持对两个动画进行混合。新建的参数值范围为[0,1]。指定的骨骼将会按照这个参数的值对两个动画进行线性混合。
        """
        pass

    def SetAnim1DControlParam(self, modelId, paramName, value):
        # type: (int, str, float) -> bool
        """
        新建动画的1D控制参数后，使用该接口对相应的参数进行控制。
        """
        pass

    def SetEntityShadowShow(self, flag):
        # type: (bool) -> None
        """
        设置实体打开/关闭影子渲染
        """
        pass


