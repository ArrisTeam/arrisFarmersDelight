# -*- coding: utf-8 -*-
"""FoodEffects - 牛奶瓶 / 热可可 / 西瓜汁 / 冰棒 / 原版汤的追加结算，滋养与舒适效果（服务端）"""
import random
import traceback

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, serverApi
from ..Shared.Data.Effects import COMFORT, NOURISHMENT
from ..Shared.Rules import FoodEffects as Rules

REGENERATION = "regeneration"
_timer = []


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


def comfortTick():
    # 舒适（JE 1.3.4 的 ComfortEffect）：每 4 秒看一遍身上有舒适的玩家（JE 的生物也吃这个效果；它只能用指令给，这边只管玩家）
    attrType = serverApi.GetMinecraftEnum().AttrType
    for playerId in serverApi.GetPlayerList() or ():
        effectComp = compFactory.CreateEffect(playerId)
        if effectComp.HasEffect(COMFORT) is not True:
            continue
        attrComp = compFactory.CreateAttr(playerId)
        if Rules.comfortHeals(effectComp.HasEffect(REGENERATION) is True, attrComp.GetAttrValue(attrType.SATURATION),
                              attrComp.GetAttrValue(attrType.HEALTH), attrComp.GetAttrMaxValue(attrType.HEALTH)):
            _heal(playerId, Rules.COMFORT_HEAL)


def _comfortTick():
    try:
        comfortTick()
    except Exception:  # noqa: BLE001 - 定时器边界：出错只打印，下一轮接着来
        print("[arrisFarmersDelight] 舒适回血出错")
        traceback.print_exc()


@registerHandler("ClientLoadAddonsFinishServerEvent")
def OnComfortPlayerJoin(args):
    if not _timer:
        _timer.append(compFactory.CreateGame(levelId).AddRepeatedTimer(Rules.COMFORT_SECONDS, _comfortTick))


@registerHandler("PlayerDieEvent")
def OnPlayerDieRemoveEffects(args):
    effectComp = compFactory.CreateEffect(args["id"])
    for effect in (COMFORT, NOURISHMENT):
        effectComp.RemoveEffectFromEntity(effect)
