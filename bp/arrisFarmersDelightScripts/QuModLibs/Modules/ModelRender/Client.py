# -*- coding: utf-8 -*-
from ...Client import clientApi, levelId, Entity
from ...Util import TRY_EXEC_FUN
lambda: "By Zero123"

class QFreeModelPool:
    """ 自由模型管理池 """
    def __init__(self, modelName=""):
        self.modelName = modelName
        self.freeModel = []
        """ 待使用的模型 """
        self.usingModel = []
        """ 使用中的模型 """

    def malloc(self, showNow=True):
        # type: (bool) -> str
        """ 尝试性分配单个模型 """
        comp = clientApi.GetEngineCompFactory().CreateModel(levelId)
        init = False
        if len(self.freeModel) <= 0:
            # 没有足以分配的模型了 构造新的模型
            self.freeModel.append(comp.CreateFreeModel(self.modelName))
            init = True
        useModel = self.freeModel[-1]
        del self.freeModel[-1]
        self.usingModel.append(useModel)
        if not init and showNow:
            comp.ShowModel(useModel)
        return useModel

    def free(self, modeId, delModel=False):
        # type: (str, bool) -> None
        """ 释放单个模型 当delModel为False时仅回收起来 待下次复用 """
        try:
            if len(self.usingModel) != 0:
                self.usingModel.remove(modeId)
        except:
            pass
        comp = clientApi.GetEngineCompFactory().CreateModel(levelId)
        if not delModel:
            # 非真实性销毁 仅回收到池中
            self.freeModel.append(modeId)
            comp.HideModel(modeId)
            return
        comp.RemoveFreeModel(modeId)

    def freeAllModel(self):
        # type: () -> None
        """ 真正的释放所有模型(而不是回收起来) """
        comp = clientApi.GetEngineCompFactory().CreateModel(levelId)
        for modeId in self.freeModel + self.usingModel:
            TRY_EXEC_FUN(comp.RemoveFreeModel, modeId)
        self.freeModel = []
        self.usingModel = []

def CREATE_FREE_MODEL(modelName, createPos=None):
    # type: (str, tuple[float] | None) -> int
    """ 创建自由模型 createPos不指定时将不会设置到任何位置 """
    comp = clientApi.GetEngineCompFactory().CreateModel(levelId)
    modelId = comp.CreateFreeModel(modelName)
    if createPos != None:
        comp.SetFreeModelPos(modelId, createPos[0], createPos[1], createPos[2])
    return modelId

def SET_FREE_MODEL_POS(modelId, newPos=(0, 0, 0)):
    # type: (int, tuple[float]) -> bool
    """ 设置自由模型位置 """
    comp = clientApi.GetEngineCompFactory().CreateModel(levelId)
    return comp.SetFreeModelPos(modelId, newPos[0], newPos[1], newPos[2])

def GET_EXTRA_UNIFORM_VALUE(modelId, uniformIndex=1):
    # type: (str, int) -> tuple[float, float, float, float] | None
    """ 获取自由模型的Uniform值 uniformIndex为自定义变量的下标 值范围为1~4 """
    comp = clientApi.GetEngineCompFactory().CreateModel(modelId)
    return comp.GetExtraUniformValue(modelId, uniformIndex)

def SET_EXTRA_UNIFORM_VALUE(modelId, uniformIndex=1, vec4data=(0, 0, 0, 0)):
    # type: (str, int, tuple[float, float, float, float]) -> bool
    """ 设置自由模型的Uniform值 uniformIndex为自定义变量的下标 值范围为1~4
        - GLSL中使用
        #include "uniformExtraVectorConstants.h"
        EXTRA_VECTOR1
    """
    comp = clientApi.GetEngineCompFactory().CreateModel(modelId)
    return comp.SetExtraUniformValue(modelId, uniformIndex, vec4data)

class QBlockRender:
    """ 方块模型渲染管理 """
    _cacheBlockModel = {}

    @staticmethod
    def mallocBlockModel(blockName="", aux=0):
        # type: (str, int) -> str | None
        """ 分配方块模型ID """
        saveKey = "{}:{}".format(blockName, aux)
        if not blockName or blockName == "minecraft:air":
            return None
        if saveKey in QBlockRender._cacheBlockModel:
            return QBlockRender._cacheBlockModel[saveKey]
        joData = {'extra': {}, 'void': False, 'actor': {}, 'volume': (1, 1, 1), 'common': {(blockName, aux): [0]}, 'eliminateAir': True}
        comp = clientApi.GetEngineCompFactory().CreateBlock(levelId)
        newPalette = comp.GetBlankBlockPalette()
        newPalette.DeserializeBlockPalette(joData)
        blockId = "QBlock_{}".format(id(newPalette))
        blockGeometryComp = clientApi.GetEngineCompFactory().CreateBlockGeometry(levelId)
        blockGeometryComp.CombineBlockPaletteToGeometry(newPalette, blockId)
        QBlockRender._cacheBlockModel[saveKey] = blockId
        return blockId

    @staticmethod
    def addEntityBlockModel(entityId, blockModelId, offset=(0, 0, 0), rotation=(0, 0, 0)):
        # type: (str, str, tuple[float], tuple[float]) -> bool
        """ 为特定实体添加方块模型渲染 (可通过mallocBlockModel分配) """
        actorRenderComp = clientApi.GetEngineCompFactory().CreateActorRender(entityId)
        return actorRenderComp.AddActorBlockGeometry(blockModelId, offset, rotation)

class QNativeEntityModel:
    """ 原生实体模型管理 """
    class MinecraftBone:
        def __init__(self, bindEntity, boneName=""):
            # type: (str, str) -> None
            self.comp = clientApi.GetEngineCompFactory().CreateModel(bindEntity)
            self.bindEntity = bindEntity
            self.boneName = boneName
            self.entityObj = Entity(bindEntity)

        def getWorldPos(self):
            # type: () -> tuple[float, float, float] | None
            """ 基于网易API的获取Bone当前的世界空间位置(截至3.0版本该API性能较低 因此有另外一种实现方案) """
            return self.comp.GetBonePositionFromMinecraftObject(self.boneName)

        def getTestWorldPos(self):
            # type: () -> tuple[float, float, float] | None
            """ 基于网易API的获取Bone当前的世界空间位置 该方法经过判断当获取失败时返回当前实体的pos而不是None 如若实体不存在才会抛出None """
            bonePos = self.getWorldPos()
            if not bonePos:
                return self.entityObj.Pos
            return bonePos

        def getParWorldPos(self, usePar="netease:tutorial_particle"):
            # type: (str) -> tuple[float, float, float]
            """ 基于粒子测试法获取指定Bone当前的世界空间位置 如若不存在则返回实体当前位置(截至3.0版本该方案性能远大于网易官方API实现但在低帧数下精准度不如官方实现) """
            comp = clientApi.GetEngineCompFactory().CreateParticleSystem(None)
            pId = comp.CreateBindEntityNew(usePar, self.bindEntity, self.boneName, (0, 0, 0), (0, 0, 0))
            pos = comp.GetPos(pId, False)
            comp.Remove(pId)
            if pos != (0, 0, 0):
                return pos
            return self.entityObj.Pos