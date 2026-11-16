# -*- coding: utf-8 -*-
"""FoodEffects - 牛奶瓶 / 热可可清除效果、滋养与舒适效果（服务端）"""
import random

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory
from ..Shared.Data.Effects import negativeEffect, COMFORT, NOURISHMENT
from ..Shared.Rules import FoodEffects as Rules


@registerHandler("PlayerEatFoodServerEvent", match=Rules.HANDLED)
def OnPlayerEatFood(args):
    # 牛奶瓶、热可可、原版汤的追加结算：做什么由 Shared/Rules/FoodEffects.py 决定，这里只执行
    effectComp = compFactory.CreateEffect(args["playerId"])
    active = [effectDict["effectName"] for effectDict in effectComp.GetAllEffects() or []]
    for action in Rules.eatActions(args["itemDict"]["newItemName"], active, random):
        if action[0] == Rules.REMOVE:
            effectComp.RemoveEffectFromEntity(action[1])
        elif action[0] == Rules.ADD:
            effectComp.AddEffectToEntity(action[1], action[2], action[3], action[4])


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
