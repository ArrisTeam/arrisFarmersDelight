# -*- coding: utf-8 -*-

from component.baseComponent import BaseComponent

class BlockInfoComponentClient(BaseComponent):
    def GetBlockClip(self, pos):
        # type: (tuple[int,int,int]) -> dict
        """
        获取指定位置方块当前clip的aabb
        """
        pass

    def GetBlockCollision(self, pos):
        # type: (tuple[int,int,int]) -> dict
        """
        获取指定位置方块当前collision的aabb
        """
        pass

    def GetBlock(self, pos):
        # type: (tuple[float,float,float]) -> tuple[str,int]
        """
        获取某一位置的block
        """
        pass

    def GetTopBlockHeight(self, pos):
        # type: (tuple[int,int]) -> object
        """
        获取当前维度某一位置最高的非空气方块的高度
        """
        pass

    def ChangeBlockTextures(self, blockName, tileName, texturePath):
        # type: (str, str, str) -> bool
        """
        替换方块贴图
        """
        pass

    def GetDestroyTotalTime(self, blockName, itemName=None):
        # type: (str, str) -> float
        """
        获取使用物品破坏方块需要的时间
        """
        pass

    def SetBlockEntityMolangValue(self, pos, variableName, value):
        # type: (tuple[int,int,int], str, float) -> bool
        """
        设置自定义方块实体的Molang变量，与实体的molang变量作用相同。目前主要用于控制自定义实体的动画状态转变。Molang变量的定义方式与原版实体的Molang变量定义方法相同。详细可参考自定义方块实体动画的教学文档。
        """
        pass

    def GetBlockEntityMolangValue(self, pos, variableName):
        # type: (tuple[int,int,int], str) -> float
        """
        获取自定义方块实体的Molang变量的值。
        """
        pass

    def SetEnableBlockEntityAnimations(self, pos, enable):
        # type: (tuple[int,int,int], bool) -> bool
        """
        设置是否开启自定义方块实体的动画效果，开启之后，自定义实体方块会按照实体文件中animation_controller所定义的动画状态机进行动画播放。关闭之后，则会停止所有动画播放。
        """
        pass

    def CreateParticleEffectForBlockEntity(self, pos, path, particleKeyName, effectPos):
        # type: (tuple[int,int,int], str, str, tuple[float,float,float]) -> object
        """
        在自定义方块实体上创建粒子特效，创建后该接口返回粒子特效的Id，利用该Id可以使用特效/粒子中的接口对该粒子特效进行播放、设置位置、大小等操作。与实体的粒子特效创建方式类似。若自定义方块实体已存在键值名称相同的特效，则不会创建新的特效，接口返回已有的特效Id。
        """
        pass

    def GetParticleEffectIdInBlockEntity(self, pos, particleKeyName):
        # type: (tuple[int,int,int], str) -> object
        """
        获取在自定义方块实体中已创建的指定粒子特效的Id，已创建的特效分为两种：一是通过resource_pack/entity/下的实体json文件中使用“netease_particle_effects”所定义的特效；二是使用接口CreateParticleEffectForBlockEntity创建的特效。 返回的特效Id可以使用特效/粒子中的接口对该粒子特效进行播放、设置位置、大小等操作。与实体的粒子特效创建方式类似。
        """
        pass

    def RemoveParticleEffectInBlockEntity(self, pos, particleKeyName):
        # type: (tuple[int,int,int], str) -> bool
        """
        移除在自定义方块实体上创建的粒子特效。移除后的特效Id将会失效。
        """
        pass

    def CreateFrameEffectForBlockEntity(self, pos, path, frameKeyName, effectPos):
        # type: (tuple[int,int,int], str, str, tuple[float,float,float]) -> object
        """
        在自定义方块实体上创建序列帧特效，创建后该接口返回序列帧特效的Id，利用该Id可以使用特效/序列帧中的接口对该序列帧特效进行播放、设置位置、大小等操作。与实体的序列帧特效创建方式类似。
        """
        pass

    def GetFrameEffectIdInBlockEntity(self, pos, frameKeyName):
        # type: (tuple[int,int,int], str) -> object
        """
        获取在自定义方块实体中已创建的指定序列帧特效的Id，已创建的特效分为两种：一是通过resource_pack/entity/下的实体json文件中使用“netease_frame_effects”所定义的特效；二是使用接口CreateFrameEffectForBlockEntity创建的特效。 返回的特效Id可以使用特效/序列帧中的接口对该序列帧特效进行播放、设置位置、大小等操作。与实体的序列帧特效创建方式类似。
        """
        pass

    def RemoveFrameEffectInBlockEntity(self, pos, frameKeyName):
        # type: (tuple[int,int,int], str) -> bool
        """
        移除在自定义方块实体上创建的序列帧特效。移除后的特效Id将会失效。
        """
        pass

    def SetBlockEntityParticlePosOffset(self, pos, particleKeyName, effectPosOffset):
        # type: (tuple[int,int,int], str, tuple[int,int,int]) -> bool
        """
        设置自定义方块实体中粒子特效位置偏移值，用于调整粒子特效相对于方块位置的偏移。与特效/粒子/SetPos接口不同，该接口调整的是相对于方块位置的位置偏移值，而不是世界坐标。
        """
        pass

    def SetBlockEntityFramePosOffset(self, pos, frameKeyName, effectPosOffset):
        # type: (tuple[int,int,int], str, tuple[int,int,int]) -> bool
        """
        设置自定义方块实体中序列帧特效位置偏移值，用于调整序列帧特效相对于方块位置的偏移。与特效/序列帧/SetPos接口不同，该接口调整的是相对于方块位置的位置偏移值，而不是世界坐标。
        """
        pass

    def SetBlockEntityModelPosOffset(self, pos, modelPosOffset):
        # type: (tuple[int,int,int], tuple[int,int,int]) -> bool
        """
        设置自定义方块实体的实体模型位置偏移值，用于调整实体模型相对于方块位置的偏移。可通过该接口来调整自定义方块实体的实体模型的位置。只有自定义方块实体定义实体模型才生效，实体模型在resource_pack/entity/下定义，详细可参考自定义方块实体动画的教学文档。
        """
        pass

    def SetBlockEntityModelScale(self, pos, scale):
        # type: (tuple[int,int,int], tuple[int,int,int]) -> bool
        """
        设置自定义方块实体的实体模型大小的缩放值，可通过该接口来调整自定义方块实体的实体模型的大小。只有自定义方块实体定义实体模型才生效，实体模型在resource_pack/entity/下定义，详细可参考自定义方块实体动画的教学文档。
        """
        pass

    def SetBlockEntityModelRotation(self, pos, angles, rotateAxis):
        # type: (tuple[int,int,int], float, str) -> bool
        """
        设置自定义方块实体的实体模型在各个轴上的旋转值，可通过该接口来调整自定义方块实体的实体模型的旋转。只有自定义方块实体定义实体模型才生效，实体模型在resource_pack/entity/下定义，详细可参考自定义方块实体动画的教学文档。
        """
        pass

    def RegisterOnStandOn(self, blockName, sendPythonEvent):
        # type: (str, bool) -> bool
        """
        可以动态注册与修改netease:on_stand_on组件
        """
        pass

    def UnRegisterOnStandOn(self, blockName):
        # type: (str) -> bool
        """
        可以动态删除netease:on_stand_on组件
        """
        pass

    def RegisterOnStepOn(self, blockName, sendPythonEvent):
        # type: (str, bool) -> bool
        """
        可以动态注册与修改netease:on_step_on组件
        """
        pass

    def UnRegisterOnStepOn(self, blockName):
        # type: (str) -> bool
        """
        可以动态删除netease:on_step_on组件
        """
        pass

    def RegisterOnStepOff(self, blockName, sendPythonEvent):
        # type: (str, bool) -> bool
        """
        可以动态注册与修改netease:on_step_off组件
        """
        pass

    def UnRegisterOnStepOff(self, blockName):
        # type: (str) -> bool
        """
        可以动态删除netease:on_step_off组件
        """
        pass

    def RegisterOnEntityInside(self, blockName, sendPythonEvent):
        # type: (str, bool) -> bool
        """
        可以动态注册与修改netease:on_entity_inside组件
        """
        pass

    def UnRegisterOnEntityInside(self, blockName):
        # type: (str) -> bool
        """
        可以动态删除netease:on_entity_inside组件
        """
        pass

    def SetCrackFrame(self, dimensionId, blockPos, frame):
        # type: (int, tuple[int,int,int], int) -> bool
        """
        仅客户端的破坏纹理的渲染，可自定义破坏阶段在第几帧。
        Args:
            dimensionId: 方块所在维度
            blockPos: 目标方块的坐标
            frame: 第几张纹理（取值范围0-9）
        Returns:
            是否执行成功（不代表必定能显示裂纹）
        备注:
            目前自定义方块实体外观，不支持裂纹的显示（client_entity、netease_model）
        """
        pass

    def DestroyCrackFrame(self, dimensionId, blockPos):
        # type: (int, tuple[int,int,int]) -> bool
        """
        销毁特定方块位置上的破坏纹理（仅能销毁SetCrackFrame接口创建的破坏纹理）
        Args:
            dimensionId: 方块所在维度
            blockPos: 目标方块的坐标
        Returns:
            是否执行成功
        备注:
            如果方块被替换，需开发者主动销毁裂纹
        """
        pass


