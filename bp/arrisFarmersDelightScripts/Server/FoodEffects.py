# -*- coding: utf-8 -*-
"""FoodEffects - 牛奶瓶 / 热可可清除效果、滋养与舒适效果（服务端）"""
import random

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, GetEngineTypeStr
from ..Shared.Data.Effects import negativeEffect

COMFORT = "arris:comfort"
NOURISHMENT = "arris:nourishment"


@registerHandler("PlayerEatFoodServerEvent")
def OnPlayerEatFood(args):
    playerId = args["playerId"]
    itemName = args["itemDict"]["newItemName"]
    effectComp = compFactory.CreateEffect(playerId)
    effectDictList = effectComp.GetAllEffects()
    if not effectDictList:
        return
    if itemName == "arris:milk_bottle":
        # 牛奶瓶：随机清除一个效果
        effectComp.RemoveEffectFromEntity(effectDictList[random.randint(0, len(effectDictList) - 1)]["effectName"])
    elif itemName == "arris:hot_cocoa":
        # 热可可：清除一个负面效果
        for effectDict in effectDictList:
            if effectDict["effectName"] in negativeEffect:
                effectComp.RemoveEffectFromEntity(effectDict["effectName"])
                break


@registerHandler("PlayerHungerChangeServerEvent")
def OnPlayerHungerChange(args):
    # 滋养：饥饿值不下降
    if args["hunger"] - args["hungerBefore"] <= 0 and compFactory.CreateEffect(args["playerId"]).HasEffect(NOURISHMENT) is True:
        args["cancel"] = True


@registerHandler("AddEffectServerEvent")
def OnAddEffect(args):
    # 舒适：免疫负面效果；获得舒适时清掉身上已有的负面效果
    entityId = args["entityId"]
    effectName = args["effectName"]
    effectComp = compFactory.CreateEffect(entityId)
    if effectName in negativeEffect:
        if effectComp.HasEffect(COMFORT) is True:
            effectComp.RemoveEffectFromEntity(effectName)
    elif effectName == COMFORT:
        for effectDict in effectComp.GetAllEffects() or []:
            if effectDict["effectName"] in negativeEffect:
                effectComp.RemoveEffectFromEntity(effectDict["effectName"])


@registerHandler("PlayerDieEvent")
def OnPlayerDieRemoveEffects(args):
    effectComp = compFactory.CreateEffect(args["id"])
    for effect in (COMFORT, NOURISHMENT):
        effectComp.RemoveEffectFromEntity(effect)


# 优先级 70：DamageEvent 里排在展示实体（100）之后、爬绳免摔（60）之前，与旧版模块加载顺序一致
@registerHandler("DamageEvent", priority=70)
def OnPlayerDamageRemoveEffects(args):
    # 玩家受到伤害时失去舒适与滋养
    entityId = args["entityId"]
    if GetEngineTypeStr(entityId) == "minecraft:player":
        effectComp = compFactory.CreateEffect(entityId)
        for effect in (COMFORT, NOURISHMENT):
            effectComp.RemoveEffectFromEntity(effect)
