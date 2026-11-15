# -*- coding: utf-8 -*-
"""Tools - 刀的战利品加成、煎锅打人的音效、扔烂番茄（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetCarriedItem, GetEngineTypeStr
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import IsKnife
from .Helpers.Player import SetNotCreateItem
from ..Shared.Rules.Ticks import probability

# 用刀杀猪掉火腿的概率（%）
HAM_CHANCE = 80


@registerHandler("EntityDieLoottableServerEvent")
def OnKnifeKill(args):
    # 用刀杀死牛、鸡后掉落物翻倍，猪有概率掉火腿
    attackerId = args["attacker"]
    if GetEngineTypeStr(attackerId) != "minecraft:player":
        return
    handItemDict = GetCarriedItem(attackerId)
    if not handItemDict or not IsKnife(handItemDict["newItemName"]):
        return
    entityName = GetEngineTypeStr(args["dieEntityId"])
    itemList = args["itemList"]
    if entityName in ("minecraft:cow", "minecraft:chicken"):
        for itemDict in itemList:
            itemDict["count"] *= 2
        args["itemList"] = itemList
        args["dirty"] = True
    elif entityName == "minecraft:pig" and probability(HAM_CHANCE):
        itemList.append({"itemName": "arris:ham", "count": 1})
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
