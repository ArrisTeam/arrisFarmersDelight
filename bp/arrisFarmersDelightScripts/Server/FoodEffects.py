# -*- coding: utf-8 -*-
"""FoodEffects - 牛奶瓶 / 热可可 / 西瓜汁 / 冰棒 / 原版汤的追加结算，滋养与舒适效果（服务端）"""
import random
import traceback

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, serverApi
from ..Shared.Data.Effects import COMFORT, NOURISHMENT, NOURISHING_FOODS
from ..Shared.Rules import FoodEffects as Rules

REGENERATION = "regeneration"
_timers = {}


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
    # 滋养：饥饿值不下降（主要靠下面清消耗度；这里兜住消耗度以外的扣法）
    if args["hunger"] - args["hungerBefore"] <= 0 and compFactory.CreateEffect(args["playerId"]).HasEffect(NOURISHMENT) is True:
        args["cancel"] = True


def _naturalRegen(playerComp):
    rules = (compFactory.CreateGame(levelId).GetGameRulesInfoServer() or {}).get("option_info") or {}
    return rules.get("natural_regeneration", True) is not False and playerComp.IsPlayerNaturalRegen() is not False


def nourishmentTick():
    # 滋养（JE 1.3.4 NourishmentEffect）：不是"开着自然回血、受了伤、还有饱和度"就把消耗度清零，饱和度、饥饿值都不掉
    attrType = serverApi.GetMinecraftEnum().AttrType
    for playerId in serverApi.GetPlayerList() or ():
        if compFactory.CreateEffect(playerId).HasEffect(NOURISHMENT) is not True:
            continue
        playerComp = compFactory.CreatePlayer(playerId)
        attrComp = compFactory.CreateAttr(playerId)
        if Rules.nourishmentClears(_naturalRegen(playerComp), attrComp.GetAttrValue(attrType.HEALTH),
                                   attrComp.GetAttrMaxValue(attrType.HEALTH), attrComp.GetAttrValue(attrType.SATURATION)):
            playerComp.SetPlayerCurrentExhaustionValue(0.0)


def quietNourishment(playerId):
    # JE 的食物给的滋养不冒粒子：吃下后（下一刻，食物 JSON 的效果已经加上）把滋养按原来的时长、等级换成不冒粒子的
    effectComp = compFactory.CreateEffect(playerId)
    for effect in effectComp.GetAllEffects() or ():
        if effect["effectName"] == NOURISHMENT:
            effectComp.RemoveEffectFromEntity(NOURISHMENT)
            effectComp.AddEffectToEntity(NOURISHMENT, effect["duration"], effect["amplifier"], False)
            return


@registerHandler("PlayerEatFoodServerEvent", match=NOURISHING_FOODS)
def OnEatNourishingFood(args):
    compFactory.CreateGame(levelId).AddTimer(0.0, quietNourishment, args["playerId"])


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


def _guarded(tick, what):
    def run():
        try:
            tick()
        except Exception:  # noqa: BLE001 - 定时器边界：出错只打印，下一轮接着来
            print("[arrisFarmersDelight] %s出错" % what)
            traceback.print_exc()
    return run


@registerHandler("ClientLoadAddonsFinishServerEvent")
def OnEffectsPlayerJoin(args):
    # 舒适、滋养的定时器在第一个玩家进服时开（和篮子一样）
    game = compFactory.CreateGame(levelId)
    if "comfort" not in _timers:
        _timers["comfort"] = game.AddRepeatedTimer(Rules.COMFORT_SECONDS, _guarded(comfortTick, "舒适回血"))
    if "nourishment" not in _timers:
        _timers["nourishment"] = game.AddRepeatedTimer(Rules.NOURISHMENT_SECONDS, _guarded(nourishmentTick, "滋养清消耗度"))


@registerHandler("PlayerDieEvent")
def OnPlayerDieRemoveEffects(args):
    effectComp = compFactory.CreateEffect(args["id"])
    for effect in (COMFORT, NOURISHMENT):
        effectComp.RemoveEffectFromEntity(effect)
