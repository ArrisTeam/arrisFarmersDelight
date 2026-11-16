# -*- coding: utf-8 -*-
"""FoodEffects - 牛奶瓶 / 热可可 / 西瓜汁 / 冰棒 / 原版汤的追加结算，滋养与舒适效果（服务端）"""
import random

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, serverApi
from ..Shared.Data.Effects import negativeEffect, COMFORT, NOURISHMENT
from ..Shared.Rules import FoodEffects as Rules


def _heal(playerId, amount):
    attrComp = compFactory.CreateAttr(playerId)
    health = serverApi.GetMinecraftEnum().AttrType.HEALTH
    value = Rules.healedValue(attrComp.GetAttrValue(health), attrComp.GetAttrMaxValue(health), amount)
    if value is not None:
        # 第三个参数 0：只改当前值，不动属性的默认值（重生时按默认值起算）
        attrComp.SetAttrValue(health, value, 0)


@registerHandler("PlayerEatFoodServerEvent", match=Rules.HANDLED)
def OnPlayerEatFood(args):
    # 牛奶瓶、热可可、西瓜汁、冰棒、原版汤的追加结算：做什么由 Shared/Rules/FoodEffects.py 决定，这里只执行
    playerId = args["playerId"]
    effectComp = compFactory.CreateEffect(playerId)
    active = [effectDict["effectName"] for effectDict in effectComp.GetAllEffects() or []]
    for action in Rules.eatActions(args["itemDict"]["newItemName"], active, random):
        if action[0] == Rules.REMOVE:
            effectComp.RemoveEffectFromEntity(action[1])
        elif action[0] == Rules.ADD:
            effectComp.AddEffectToEntity(action[1], action[2], action[3], action[4])
        elif action[0] == Rules.HEAL:
            _heal(playerId, action[1])
        elif action[0] == Rules.EXTINGUISH:
            compFactory.CreateAttr(playerId).SetEntityOnFire(0)  # 秒数 <= 0 即灭火


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
