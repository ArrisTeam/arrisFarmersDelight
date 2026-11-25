# -*- coding: utf-8 -*-
"""ModServer - 服务端入口：导入各玩法模块（导入即登记），每个引擎事件只在这里挂一次监听（服务端）

处理函数在各玩法模块里用 EventRegistry.registerHandler 登记；这里只把事件转给注册表，
并给出按方块 / 物品 / 实体分派用的匹配键。

ServerItemUseOnEvent 是唯一靠执行顺序区分处理者的事件（同一次点击可能同时满足几个模块的条件，
由共用的交互冷却决定谁认领）。各处理函数的 priority 按旧版模块加载顺序给出：
    100 放下的煎锅 / 砧板 / 成熟作物取消物品使用（煎锅、砧板不潜行时：JE 的 use 吃掉这一下）    99 野生作物放置检查    98.5 煎锅物品（只有潜行才放，ItemToBlock 看不到它）
     98 物品放成方块（派）、长 / 短榻榻米垫
     50 种水稻 / 骨粉 / 蘑菇菌落        11 炉灶点火 / 灭火（用上了认领，不再往下走）    10 炉灶放食物
DamageEvent 同理：100 展示实体删除器、60 爬绳免摔、0 背刺魔咒加伤害（不认领，后面的照常）。
"""
from ..QuModLibs.Server import Listen
from .EventRegistry import dispatch

# 导入即登记（顺序不影响执行顺序，执行顺序只看 priority）
from . import LegacyApi  # noqa: F401
from . import PlayerSession  # noqa: F401
from . import TableSync  # noqa: F401
from . import CraftReturns  # noqa: F401
from . import CookingPot  # noqa: F401
from . import CookingPotHost  # noqa: F401
from . import Skillet  # noqa: F401
from . import HeatConduct  # noqa: F401
from . import SkilletHold  # noqa: F401
from . import Stove  # noqa: F401
from . import StoveFire  # noqa: F401
from . import CuttingBoard  # noqa: F401
from . import ItemToBlock  # noqa: F401
from . import Crops  # noqa: F401
from . import BoneMeal  # noqa: F401
from . import RichSoil  # noqa: F401
from . import WildCrops  # noqa: F401
from . import FoodBlocks  # noqa: F401
from . import Storage  # noqa: F401
from . import RopeAndNet  # noqa: F401
from . import TatamiMats  # noqa: F401
from . import TatamiPairs  # noqa: F401
from . import RopeFences  # noqa: F401
from . import FoodEffects  # noqa: F401
from . import Livestock  # noqa: F401
from . import Tools  # noqa: F401
from . import Backstabbing  # noqa: F401
from . import KnifeSlicing  # noqa: F401
from . import ChestLoot  # noqa: F401
from . import DisplayGuard  # noqa: F401


def _itemName(args):
    itemDict = args.get("itemDict") or {}
    return itemDict.get("newItemName")


# ---- 方块：匹配键是方块名 ----

@Listen("ServerBlockUseEvent")
def _onServerBlockUse(args):
    dispatch("ServerBlockUseEvent", args, args.get("blockName"))


@Listen("ServerItemUseOnEvent")
def _onServerItemUseOn(args):
    dispatch("ServerItemUseOnEvent", args, args.get("blockName"))


@Listen("ItemUseOnAfterServerEvent")
def _onItemUseOnAfter(args):
    dispatch("ItemUseOnAfterServerEvent", args, args.get("blockName"))


@Listen("BlockNeighborChangedServerEvent")
def _onBlockNeighborChanged(args):
    dispatch("BlockNeighborChangedServerEvent", args, args.get("blockName"))


@Listen("BlockRandomTickServerEvent")
def _onBlockRandomTick(args):
    dispatch("BlockRandomTickServerEvent", args, args.get("fullName"))


@Listen("ServerBlockEntityTickEvent")
def _onServerBlockEntityTick(args):
    dispatch("ServerBlockEntityTickEvent", args, args.get("blockName"))


@Listen("ServerPlaceBlockEntityEvent")
def _onServerPlaceBlockEntity(args):
    dispatch("ServerPlaceBlockEntityEvent", args, args.get("blockName"))


@Listen("BlockRemoveServerEvent")
def _onBlockRemove(args):
    dispatch("BlockRemoveServerEvent", args, args.get("fullName"))


@Listen("DestroyBlockEvent")
def _onDestroyBlock(args):
    dispatch("DestroyBlockEvent", args, args.get("fullName"))


@Listen("ServerEntityTryPlaceBlockEvent")
def _onServerEntityTryPlaceBlock(args):
    dispatch("ServerEntityTryPlaceBlockEvent", args, args.get("fullName"))


@Listen("EntityPlaceBlockAfterServerEvent")
def _onEntityPlaceBlockAfter(args):
    dispatch("EntityPlaceBlockAfterServerEvent", args, args.get("fullName"))


@Listen("ServerPlayerTryDestroyBlockEvent")
def _onServerPlayerTryDestroyBlock(args):
    dispatch("ServerPlayerTryDestroyBlockEvent", args, args.get("fullName"))


@Listen("OnEntityInsideBlockServerEvent")
def _onEntityInsideBlock(args):
    dispatch("OnEntityInsideBlockServerEvent", args, args.get("blockName"))


@Listen("OnBeforeFallOnBlockServerEvent")
def _onBeforeFallOnBlock(args):
    dispatch("OnBeforeFallOnBlockServerEvent", args, args.get("blockName"))


@Listen("OnStandOnBlockServerEvent")
def _onStandOnBlock(args):
    dispatch("OnStandOnBlockServerEvent", args, args.get("blockName"))


@Listen("MobGriefingBlockServerEvent")
def _onMobGriefingBlock(args):
    dispatch("MobGriefingBlockServerEvent", args, args.get("blockName"))


# ---- 物品：匹配键是物品名 ----

@Listen("ItemUseAfterServerEvent")
def _onItemUseAfter(args):
    dispatch("ItemUseAfterServerEvent", args, _itemName(args))


@Listen("PlayerFeedEntityServerEvent")
def _onPlayerFeedEntity(args):
    dispatch("PlayerFeedEntityServerEvent", args, _itemName(args))


@Listen("PlayerEatFoodServerEvent")
def _onPlayerEatFood(args):
    dispatch("PlayerEatFoodServerEvent", args, _itemName(args))


@Listen("ItemDurabilityChangedServerEvent")
def _onItemDurabilityChanged(args):
    dispatch("ItemDurabilityChangedServerEvent", args, _itemName(args))


@Listen("CraftItemOutputChangeServerEvent")
def _onCraftItemOutputChange(args):
    dispatch("CraftItemOutputChangeServerEvent", args, _itemName(args))


# ---- 实体 / 玩家 ----

@Listen("AddEntityServerEvent")
def _onAddEntity(args):
    dispatch("AddEntityServerEvent", args, args.get("engineTypeStr"))


@Listen("EntityDieLoottableServerEvent")
def _onEntityDieLoottable(args):
    dispatch("EntityDieLoottableServerEvent", args)


@Listen("OnContainerFillLoottableServerEvent")
def _onContainerFillLoottable(args):
    # 战利品箱第一次被打开、按战利品表生成物品时；匹配键由处理函数从 args["loottable"] 里取
    dispatch("OnContainerFillLoottableServerEvent", args)


@Listen("PlayerAttackEntityEvent")
def _onPlayerAttackEntity(args):
    dispatch("PlayerAttackEntityEvent", args)


@Listen("PlayerInteractServerEvent")
def _onPlayerInteract(args):
    # 玩家右键实体（读回 cancel 可取消）；匹配键是手里的物品名
    dispatch("PlayerInteractServerEvent", args, _itemName(args))


@Listen("DamageEvent")
def _onDamage(args):
    dispatch("DamageEvent", args)


@Listen("HealthChangeBeforeServerEvent")
def _onHealthChangeBefore(args):
    dispatch("HealthChangeBeforeServerEvent", args)


@Listen("WillTeleportToServerEvent")
def _onWillTeleportTo(args):
    dispatch("WillTeleportToServerEvent", args)


@Listen("WillAddEffectServerEvent")
def _onWillAddEffect(args):
    dispatch("WillAddEffectServerEvent", args)


@Listen("AddEffectServerEvent")
def _onAddEffect(args):
    dispatch("AddEffectServerEvent", args)


@Listen("PlayerHungerChangeServerEvent")
def _onPlayerHungerChange(args):
    dispatch("PlayerHungerChangeServerEvent", args)


@Listen("PlayerDieEvent")
def _onPlayerDie(args):
    dispatch("PlayerDieEvent", args)


@Listen("ClientLoadAddonsFinishServerEvent")
def _onClientLoadAddonsFinish(args):
    dispatch("ClientLoadAddonsFinishServerEvent", args)


@Listen("DelServerPlayerEvent")
def _onDelServerPlayer(args):
    dispatch("DelServerPlayerEvent", args)
