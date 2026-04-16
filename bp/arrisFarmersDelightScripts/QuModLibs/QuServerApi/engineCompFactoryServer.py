# -*- coding: utf-8 -*-
from component.effectCompServer import EffectComponentServer
from component.actorMotionCompServer import ActorMotionComponentServer
from component.engineTypeCompServer import EngineTypeComponentServer
from component.rideCompServer import RideCompServer
from component.blockInfoCompServer import BlockInfoComponentServer
from component.gameCompServer import GameComponentServer
from component.shareableCompServer import ShareableComponentServer
from component.actorPushableCompServer import ActorPushableCompServer
from component.bulletAttributesCompServer import BulletAttributesComponentServer
from component.timeCompServer import TimeComponentServer
from component.interactCompServer import InteractComponentServer
from component.httpToWebServerCompServer import HttpToWebServerCompServer
from component.blockCompServer import BlockCompServer
from component.projectileCompServer import ProjectileComponentServer
from component.scaleCompServer import ScaleComponentServer
from component.attrCompServer import AttrCompServer
from component.gravityCompServer import GravityComponentServer
from component.itemCompServer import ItemCompServer
from component.itemBannedCompServer import ItemBannedCompServer
from component.breathCompServer import BreathCompServer
from component.controlAiCompServer import ControlAiCompServer
from component.actorLootCompServer import ActorLootComponentServer
from component.exDataCompServer import ExDataCompServer
from component.playerCompServer import PlayerCompServer
from component.msgCompServer import MsgComponentServer
from component.posCompServer import PosComponentServer
from component.petCompServer import PetComponentServer
from component.expCompServer import ExpComponentServer
from component.tagCompServer import TagComponentServer
from component.flyCompServer import FlyComponentServer
from component.nameCompServer import NameComponentServer
from component.commandCompServer import CommandCompServer
from component.dimensionCompServer import DimensionCompServer
from component.hurtCompServer import HurtCompServer
from component.mobSpawnCompServer import MobSpawnComponentServer
from component.moveToCompServer import MoveToComponentServer
from component.redStoneCompServer import RedStoneComponentServer
from component.portalCompServer import PortalComponentServer
from component.levelCompServer import LevelComponentServer
from component.persistenceCompServer import PersistenceCompServer
from component.recipeCompServer import RecipeCompServer
from component.auxValueCompServer import AuxValueComponentServer
from component.chunkSourceComp import ChunkSourceCompServer
from component.biomeCompServer import BiomeCompServer
from component.chestContainerCompServer import ChestContainerCompServer
from component.tameCompServer import TameComponentServer
from component.entityEventCompServer import EntityEventComponentServer
from component.actionCompServer import ActionCompServer
from component.blockStateCompServer import BlockStateComponentServer
from component.actorOwnerCompServer import ActorOwnerComponentServer
from component.collisionBoxCompServer import CollisionBoxComponentServer
from component.featureCompServer import FeatureCompServer
from component.modAttrCompServer import ModAttrComponentServer
from component.rotCompServer import RotComponentServer
from component.modelCompServer import ModelComponentServer
from component.weatherCompServer import WeatherComponentServer
from component.blockUseEventWhiteListCompServer import BlockUseEventWhiteListComponentServer
from component.explosionCompServer import ExplosionComponentServer
from component.blockEntityExDataCompServer import BlockEntityExDataCompServer

class EngineCompFactoryServer():
    def CreateAction(self, entityId):
        # type: (object) -> ActionCompServer
        """
        创建action组件
        """
        pass

    def CreateActorLoot(self, entityId):
        # type: (object) -> ActorLootComponentServer
        """
        创建actorLoot组件
        """
        pass

    def CreateActorMotion(self, entityId):
        # type: (object) -> ActorMotionComponentServer
        """
        创建actorMotion组件
        """
        pass

    def CreateActorOwner(self, entityId):
        # type: (object) -> ActorOwnerComponentServer
        """
        创建actorOwner组件
        """
        pass

    def CreateActorPushable(self, entityId):
        # type: (object) -> ActorPushableCompServer
        """
        创建actorPushable组件
        """
        pass

    def CreateAttr(self, entityId):
        # type: (object) -> AttrCompServer
        """
        创建attr组件
        """
        pass

    def CreateAuxValue(self, entityId):
        # type: (object) -> AuxValueComponentServer
        """
        创建auxValue组件
        """
        pass

    def CreateBiome(self, entityId):
        # type: (object) -> BiomeCompServer
        """
        创建biome组件
        """
        pass

    def CreateBlock(self, entityId):
        # type: (object) -> BlockCompServer
        """
        创建block组件
        """
        pass

    def CreateBlockEntityData(self, entityId):
        # type: (object) -> BlockEntityExDataCompServer
        """
        创建blockEntityData组件
        """
        pass

    def CreateBlockInfo(self, entityId):
        # type: (object) -> BlockInfoComponentServer
        """
        创建blockInfo组件
        """
        pass

    def CreateBlockState(self, entityId):
        # type: (object) -> BlockStateComponentServer
        """
        创建blockState组件
        """
        pass

    def CreateBlockUseEventWhiteList(self, entityId):
        # type: (object) -> BlockUseEventWhiteListComponentServer
        """
        创建blockUseEventWhiteList组件
        """
        pass

    def CreateBreath(self, entityId):
        # type: (object) -> BreathCompServer
        """
        创建breath组件
        """
        pass

    def CreateBulletAttributes(self, entityId):
        # type: (object) -> BulletAttributesComponentServer
        """
        创建bulletAttributes组件
        """
        pass

    def CreateChestBlock(self, entityId):
        # type: (object) -> ChestContainerCompServer
        """
        创建chestBlock组件
        """
        pass

    def CreateChunkSource(self, entityId):
        # type: (object) -> ChunkSourceCompServer
        """
        创建chunkSource组件
        """
        pass

    def CreateCollisionBox(self, entityId):
        # type: (object) -> CollisionBoxComponentServer
        """
        创建collisionBox组件
        """
        pass

    def CreateCommand(self, entityId):
        # type: (object) -> CommandCompServer
        """
        创建command组件
        """
        pass

    def CreateControlAi(self, entityId):
        # type: (object) -> ControlAiCompServer
        """
        创建controlAi组件
        """
        pass

    def CreateDimension(self, entityId):
        # type: (object) -> DimensionCompServer
        """
        创建dimension组件
        """
        pass

    def CreateEffect(self, entityId):
        # type: (object) -> EffectComponentServer
        """
        创建effect组件
        """
        pass

    def CreateEngineType(self, entityId):
        # type: (object) -> EngineTypeComponentServer
        """
        创建engineType组件
        """
        pass

    def CreateEntityEvent(self, entityId):
        # type: (object) -> EntityEventComponentServer
        """
        创建entityEvent组件
        """
        pass

    def CreateExp(self, entityId):
        # type: (object) -> ExpComponentServer
        """
        创建exp组件
        """
        pass

    def CreateExplosion(self, entityId):
        # type: (object) -> ExplosionComponentServer
        """
        创建explosion组件
        """
        pass

    def CreateExtraData(self, entityId):
        # type: (object) -> ExDataCompServer
        """
        创建extraData组件
        """
        pass

    def CreateFeature(self, entityId):
        # type: (object) -> FeatureCompServer
        """
        创建feature组件
        """
        pass

    def CreateFly(self, entityId):
        # type: (object) -> FlyComponentServer
        """
        创建fly组件
        """
        pass

    def CreateGame(self, entityId):
        # type: (object) -> GameComponentServer
        """
        创建game组件
        """
        pass

    def CreateGravity(self, entityId):
        # type: (object) -> GravityComponentServer
        """
        创建gravity组件
        """
        pass

    def CreateHttp(self, entityId):
        # type: (object) -> HttpToWebServerCompServer
        """
        创建http组件
        """
        pass

    def CreateHurt(self, entityId):
        # type: (object) -> HurtCompServer
        """
        创建hurt组件
        """
        pass

    def CreateInteract(self, entityId):
        # type: (str) -> InteractComponentServer
        """
        创建实体交互组件
        """
        pass

    def CreateItem(self, entityId):
        # type: (object) -> ItemCompServer
        """
        创建item组件
        """
        pass

    def CreateItemBanned(self, entityId):
        # type: (object) -> ItemBannedCompServer
        """
        创建itembanned组件
        """
        pass

    def CreateLv(self, entityId):
        # type: (object) -> LevelComponentServer
        """
        创建lv组件
        """
        pass

    def CreateMobSpawn(self, entityId):
        # type: (object) -> MobSpawnComponentServer
        """
        创建mobSpawn组件
        """
        pass

    def CreateModAttr(self, entityId):
        # type: (object) -> ModAttrComponentServer
        """
        创建modAttr组件
        """
        pass

    def CreateModel(self, entityId):
        # type: (object) -> ModelComponentServer
        """
        创建model组件
        """
        pass

    def CreateMoveTo(self, entityId):
        # type: (object) -> MoveToComponentServer
        """
        创建moveTo组件
        """
        pass

    def CreateMsg(self, entityId):
        # type: (object) -> MsgComponentServer
        """
        创建msg组件
        """
        pass

    def CreateName(self, entityId):
        # type: (object) -> NameComponentServer
        """
        创建name组件
        """
        pass

    def CreatePersistence(self, entityId):
        # type: (object) -> PersistenceCompServer
        """
        创建persistence组件
        """
        pass

    def CreatePet(self, entityId):
        # type: (object) -> PetComponentServer
        """
        创建pet组件
        """
        pass

    def CreatePlayer(self, entityId):
        # type: (object) -> PlayerCompServer
        """
        创建player组件
        """
        pass

    def CreatePortal(self, entityId):
        # type: (object) -> PortalComponentServer
        """
        创建portal组件
        """
        pass

    def CreatePos(self, entityId):
        # type: (object) -> PosComponentServer
        """
        创建pos组件
        """
        pass

    def CreateProjectile(self, entityId):
        # type: (object) -> ProjectileComponentServer
        """
        创建projectile组件
        """
        pass

    def CreateRecipe(self, entityId):
        # type: (object) -> RecipeCompServer
        """
        创建recipe组件
        """
        pass

    def CreateRedStone(self, entityId):
        # type: (object) -> RedStoneComponentServer
        """
        创建redStone组件
        """
        pass

    def CreateRide(self, entityId):
        # type: (object) -> RideCompServer
        """
        创建ride组件
        """
        pass

    def CreateRot(self, entityId):
        # type: (object) -> RotComponentServer
        """
        创建rot组件
        """
        pass

    def CreateScale(self, entityId):
        # type: (object) -> ScaleComponentServer
        """
        创建scale组件
        """
        pass

    def CreateShareables(self, entityId):
        # type: (str) -> ShareableComponentServer
        """
        创建实体拾取组件
        """
        pass

    def CreateTag(self, entityId):
        # type: (object) -> TagComponentServer
        """
        创建tag组件
        """
        pass

    def CreateTame(self, entityId):
        # type: (object) -> TameComponentServer
        """
        创建tame组件
        """
        pass

    def CreateTime(self, entityId):
        # type: (object) -> TimeComponentServer
        """
        创建time组件
        """
        pass

    def CreateWeather(self, entityId):
        # type: (object) -> WeatherComponentServer
        """
        创建weather组件
        """
        pass

