# -*- coding: utf-8 -*-
"""Tools - 刀与洋葱的战利品、煎锅打人的音效、扔烂番茄（服务端）

刀的额外掉落和洋葱掉落照 JE 的战利品修饰器，概率与掉落表在 Shared/Data/MobLoot.py，结算在 Shared/Rules/MobLoot.py。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetCarriedItem, GetEngineTypeStr
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import IsKnife
from .Helpers.Player import SetNotCreateItem
from ..Shared.Data.MobLoot import KNIFE_HAM, PROJECTILES
from ..Shared.Rules import MobLoot

PLAYER = "minecraft:player"


def _killerPlayer(attackerId):
    # 击杀者是玩家（含玩家射出的箭、三叉戟）时返回玩家 ID，否则 None
    if not attackerId:
        return None
    attackerType = GetEngineTypeStr(attackerId)
    if attackerType == PLAYER:
        return attackerId
    if attackerType in PROJECTILES:
        ownerId = compFactory.CreateActorOwner(attackerId).GetEntityOwner()
        if ownerId and GetEngineTypeStr(ownerId) == PLAYER:
            return ownerId
    return None


@registerHandler("EntityDieLoottableServerEvent")
def OnMobLoot(args):
    # 手里拿着刀杀死生物额外掉落（皮革、羽毛、火腿……）；玩家杀死僵尸、灾厄村民有概率掉洋葱（用什么武器都行）
    playerId = _killerPlayer(args.get("attacker"))
    if playerId is None:
        return
    dieEntityId = args["dieEntityId"]
    entityName = GetEngineTypeStr(dieEntityId)
    handItemDict = GetCarriedItem(playerId, True)
    looting = MobLoot.enchantLevel(handItemDict, MobLoot.LOOTING)
    drops = []
    if handItemDict and IsKnife(handItemDict["newItemName"]):
        burning = entityName in KNIFE_HAM and bool(compFactory.CreateAttr(dieEntityId).IsEntityOnFire())
        drops.extend(MobLoot.knifeDrops(entityName, burning, looting))
    drops.extend(MobLoot.onionDrops(entityName, looting))
    if drops:
        itemList = args["itemList"]
        itemList.extend(MobLoot.lootEntries(drops))
        args["itemList"] = itemList
        args["dirty"] = True


@registerHandler("PlayerAttackEntityEvent")
def OnSkilletAttack(args):
    playerId = args["playerId"]
    itemDict = GetCarriedItem(playerId)
    if itemDict and itemDict["newItemName"] == "arris:skillet_item":
        dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
        ToAllPlayerPlaySound(dimensionId, compFactory.CreatePos(playerId).GetFootPos(), "ambient.skillet.attack_strong")


@registerHandler("ItemUseAfterServerEvent", match="arris:rotten_tomato")
def OnThrowRottenTomato(args):
    playerId = args["entityId"]
    SetNotCreateItem(playerId, args["itemDict"])
    compFactory.CreateProjectile(levelId).CreateProjectileEntity(playerId, "arris:rotten_tomato")
