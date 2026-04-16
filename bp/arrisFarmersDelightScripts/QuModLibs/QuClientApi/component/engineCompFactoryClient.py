# -*- coding: utf-8 -*-
from skyRenderCompClient import SkyRenderCompClient
from frameAniTransComp import FrameAniTransComp
from cameraCompClient import CameraComponentClient
from itemCompClient import ItemCompClient
from blockGeometryCompClient import BlockGeometryCompClient
from attrCompClient import AttrCompClient
from chunkSourceCompClient import ChunkSourceCompClient
from particleSkeletonBindComp import ParticleSkeletonBindComp
from playerViewCompClient import PlayerViewCompClient
from queryVariableCompClient import QueryVariableComponentClient
from particleEntityBindComp import ParticleEntityBindComp
from virtualWorldCompClient import VirtualWorldCompClient
from engineTypeCompClient import EngineTypeComponentClient
from frameAniControlComp import FrameAniControlComp
from actorMotionCompClient import ActorMotionComponentClient
from frameAniSkeletonBindComp import FrameAniSkeletonBindComp
from healthCompClient import HealthComponentClient
from audioCustomCompClient import AudioCustomComponentClient
from posCompClient import PosComponentClient
from blockCompClient import BlockCompClient
from blockInfoCompClient import BlockInfoComponentClient
from engineEffectBindControlComp import EngineEffectBindControlComp
from recipeCompClient import RecipeCompClient
from modelCompClient import ModelComponentClient
from nameCompClient import NameComponentClient
from gameCompClient import GameComponentClient
from particleTransComp import ParticleTransComp
from configCompClient import ConfigCompClient
from playerCompClient import PlayerCompClient
from fogCompClient import FogCompClient
from textBoardCompClient import TextBoardComponentClient
from actorCollidableCompClient import ActorCollidableCompClient
from postProcessControlComp import PostProcessComponent
from auxValueCompClient import AuxValueComponentClient
from brightnessCompClient import BrightnessCompClient
from deviceCompClient import DeviceCompClient
from playerAnimCompClient import PlayerAnimCompClient
from operationCompClient import OperationCompClient
from textNotifyCompClient import TextNotifyComponet
from rotCompClient import RotComponentClient
from particleControlComp import ParticleControlComp
from actorRenderCompClient import ActorRenderCompClient
from modAttrCompClient import ModAttrComponentClient
from frameAniEntityBindComp import FrameAniEntityBindComp

class EngineCompFactoryClient():
    def CreateActorCollidable(self, entityId):
        # type: (object) -> ActorCollidableCompClient
        """
        创建actorCollidable组件
        """
        pass

    def CreateActorMotion(self, entityId):
        # type: (object) -> ActorMotionComponentClient
        """
        创建actorMotion组件
        """
        pass

    def CreateActorRender(self, entityId):
        # type: (object) -> ActorRenderCompClient
        """
        创建actorRender组件
        """
        pass

    def CreateAttr(self, entityId):
        # type: (str) -> AttrCompClient
        """
        创建实体属性组件
        """
        pass

    def CreateAuxValue(self, entityId):
        # type: (object) -> AuxValueComponentClient
        """
        创建auxValue组件
        """
        pass

    def CreateBlock(self, entityId):
        # type: (object) -> BlockCompClient
        """
        创建block组件
        """
        pass

    def CreateBlockGeometry(self, entityId):
        # type: (object) -> BlockGeometryCompClient
        """
        创建block组件
        """
        pass

    def CreateBlockInfo(self, entityId):
        # type: (object) -> BlockInfoComponentClient
        """
        创建blockInfo组件
        """
        pass

    def CreateBlockUseEventWhitelist(self, entityId):
        """
        创建blockUseEventWhitelist组件
        """
        pass

    def CreateBrightness(self, entityId):
        # type: (object) -> BrightnessCompClient
        """
        创建brightness组件
        """
        pass

    def CreateCamera(self, entityId):
        # type: (object) -> CameraComponentClient
        """
        创建camera组件
        """
        pass

    def CreateChunkSource(self, entityId):
        # type: (object) -> ChunkSourceCompClient
        """
        创建chunkSource组件
        """
        pass

    def CreateConfigClient(self, levelId):
        # type: (str) -> ConfigCompClient
        """
        创建config组件
        """
        pass

    def CreateCustomAudio(self, entityId):
        # type: (object) -> AudioCustomComponentClient
        """
        创建customAudio组件
        """
        pass

    def CreateDevice(self, entityId):
        # type: (object) -> DeviceCompClient
        """
        创建device组件
        """
        pass

    def CreateEngineEffectBindControl(self, entityId):
        # type: (object) -> EngineEffectBindControlComp
        """
        创建particleSkeletonBind组件
        """
        pass

    def CreateEngineType(self, entityId):
        # type: (object) -> EngineTypeComponentClient
        """
        创建engineType组件
        """
        pass

    def CreateFog(self, entityId):
        # type: (object) -> FogCompClient
        """
        创建fog组件
        """
        pass

    def CreateFrameAniControl(self, entityId):
        # type: (object) -> FrameAniControlComp
        """
        创建frameAniControl组件
        """
        pass

    def CreateFrameAniEntityBind(self, entityId):
        # type: (object) -> FrameAniEntityBindComp
        """
        创建frameAniEntityBind组件
        """
        pass

    def CreateFrameAniSkeletonBind(self, entityId):
        # type: (object) -> FrameAniSkeletonBindComp
        """
        创建frameAniSkeletonBind组件
        """
        pass

    def CreateFrameAniTrans(self, entityId):
        # type: (object) -> FrameAniTransComp
        """
        创建frameAniTrans组件
        """
        pass

    def CreateGame(self, entityId):
        # type: (object) -> GameComponentClient
        """
        创建game组件
        """
        pass

    def CreateHealth(self, entityId):
        # type: (object) -> HealthComponentClient
        """
        创建health组件
        """
        pass

    def CreateItem(self, entityId):
        # type: (object) -> ItemCompClient
        """
        创建item组件
        """
        pass

    def CreateModAttr(self, entityId):
        # type: (object) -> ModAttrComponentClient
        """
        创建modAttr组件
        """
        pass

    def CreateModel(self, entityId):
        # type: (object) -> ModelComponentClient
        """
        创建model组件
        """
        pass

    def CreateName(self, entityId):
        # type: (object) -> NameComponentClient
        """
        创建name组件
        """
        pass

    def CreateOperation(self, entityId):
        # type: (object) -> OperationCompClient
        """
        创建operation组件
        """
        pass

    def CreateParticleControl(self, entityId):
        # type: (object) -> ParticleControlComp
        """
        创建particleControl组件
        """
        pass

    def CreateParticleEntityBind(self, entityId):
        # type: (object) -> ParticleEntityBindComp
        """
        创建particleEntityBind组件
        """
        pass

    def CreateParticleSkeletonBind(self, entityId):
        # type: (object) -> ParticleSkeletonBindComp
        """
        创建particleSkeletonBind组件
        """
        pass

    def CreateParticleTrans(self, entityId):
        # type: (object) -> ParticleTransComp
        """
        创建particleTrans组件
        """
        pass

    def CreatePlayer(self, entityId):
        # type: (object) -> PlayerCompClient
        """
        创建player组件
        """
        pass

    def CreatePlayerAnim(self, playerId):
        # type: (str) -> PlayerAnimCompClient
        """
        创建玩家动画组件
        """
        pass

    def CreatePlayerView(self, entityId):
        # type: (object) -> PlayerViewCompClient
        """
        创建playerView组件
        """
        pass

    def CreatePos(self, entityId):
        # type: (object) -> PosComponentClient
        """
        创建pos组件
        """
        pass

    def CreatePostProcess(self, entityId):
        # type: (str) -> PostProcessComponent
        """
        创建屏幕后处理效果组件
        """
        pass

    def CreateQueryVariable(self, entityId):
        # type: (object) -> QueryVariableComponentClient
        """
        创建queryVariable组件
        """
        pass

    def CreateRecipe(self, entityId):
        # type: (object) -> RecipeCompClient
        """
        创建recipe组件
        """
        pass

    def CreateRot(self, entityId):
        # type: (object) -> RotComponentClient
        """
        创建rot组件
        """
        pass

    def CreateSkyRender(self, entityId):
        # type: (object) -> SkyRenderCompClient
        """
        创建skyRender组件
        """
        pass

    def CreateTextBoard(self, entityId):
        # type: (object) -> TextBoardComponentClient
        """
        创建textBoard组件
        """
        pass

    def CreateTextNotifyClient(self, entityId):
        # type: (object) -> TextNotifyComponet
        """
        创建textNotifyClient组件
        """
        pass

    def CreateVirtualWorld(self, levelId):
        # type: (str) -> VirtualWorldCompClient
        """
        创建virtualWorld组件实例组件
        """
        pass


