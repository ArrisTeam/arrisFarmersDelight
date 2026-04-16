# -*- coding: utf-8 -*-
from serverUtils.serverUtils import *
import random

@Listen("PlayerEatFoodServerEvent")
def OnPlayerEatFoodServer(args):
    playerId = args["playerId"]
    itemDict = args["itemDict"]
    itemName = itemDict["newItemName"]
    effectDictList = compFactory.CreateEffect(playerId).GetAllEffects()
    if effectDictList:
        if itemName == "arris:milk_bottle":
            # 喝下牛奶瓶后随机清除一个效果
            index = random.randint(0, len(effectDictList) - 1)
            effectName = effectDictList[index]["effectName"]
            compFactory.CreateEffect(playerId).RemoveEffectFromEntity(effectName)
        elif itemName == "arris:hot_cocoa":
            # 喝下热可可后随机清除一个负面效果
            for index in range(0, len(effectDictList)):
                effectName = effectDictList[index]["effectName"]
                if effectName in negativeEffect:
                    compFactory.CreateEffect(playerId).RemoveEffectFromEntity(effectName)
                    break

@Listen("PlayerHungerChangeServerEvent")
def OnPlayerHungerChange(args):
    playerId = args["playerId"]
    hungerBefore = args["hungerBefore"]
    hunger = args["hunger"]
    if hunger - hungerBefore <= 0:
        effectRes = compFactory.CreateEffect(playerId).HasEffect("arris:nourishment")
        if effectRes is True:
            args["cancel"] = True

@Listen("AddEffectServerEvent")
def OnAddEffectServer(args):
    entityId = args["entityId"]
    effectName = args["effectName"]
    if effectName in negativeEffect:
        effectRes = compFactory.CreateEffect(entityId).HasEffect("arris:comfort")
        if effectRes is True:
            compFactory.CreateEffect(entityId).RemoveEffectFromEntity(effectName)
    elif effectName == "arris:comfort":
        effectDictList = compFactory.CreateEffect(entityId).GetAllEffects()
        for effectDict in effectDictList:
            name = effectDict["effectName"]
            if name in negativeEffect:
                compFactory.CreateEffect(entityId).RemoveEffectFromEntity(name)

@Listen("PlayerDieEvent")
def OnPlayerDieDelEffect(args):
    playerId = args["id"]
    for effect in ["arris:comfort", "arris:nourishment"]:
        compFactory.CreateEffect(playerId).RemoveEffectFromEntity(effect)

@Listen("DamageEvent")
def OnPlayerDamageDelEffect(args):
    entityId = args["entityId"]
    identifier = compFactory.CreateEngineType(entityId).GetEngineTypeStr()
    if identifier == "minecraft:player":
        for effect in ["arris:comfort", "arris:nourishment"]:
            compFactory.CreateEffect(entityId).RemoveEffectFromEntity(effect)
