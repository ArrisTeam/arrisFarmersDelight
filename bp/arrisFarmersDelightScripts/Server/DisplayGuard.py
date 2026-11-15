# -*- coding: utf-8 -*-
"""DisplayGuard - 展示实体保护：不受伤害、不被传送、不吃药水效果；专用道具可以删掉它（服务端）

arris:item_display 是砧板 / 煎锅 / 炉灶上展示物品用的实体，被打死、传走或者吃了效果都会让展示错乱。
这几道守卫不要删。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, DestroyEntity, GetCarriedItem, SetCarriedItem, GetEngineTypeStr

DISPLAY_ENTITY = "arris:item_display"
_REMOVABLE = ("arris:item_display", "arris:corpse_display")
REMOVER_ITEM = "arris:item_display_destroy"


def _isDisplay(args):
    return GetEngineTypeStr(args["entityId"]) == DISPLAY_ENTITY


@registerHandler("HealthChangeBeforeServerEvent")
def OnDisplayHealthChange(args):
    if _isDisplay(args):
        args["cancel"] = True


@registerHandler("WillTeleportToServerEvent")
def OnDisplayTeleport(args):
    if _isDisplay(args):
        args["cancel"] = True


@registerHandler("WillAddEffectServerEvent")
def OnDisplayAddEffect(args):
    if _isDisplay(args):
        args["cancel"] = True


# 优先级 100：DamageEvent 里最先处理，与旧版模块加载顺序一致
@registerHandler("DamageEvent", priority=100)
def OnDamageDisplay(args):
    # 拿着"展示实体删除器"打展示实体：删掉它，删除器用掉
    entityId = args["entityId"]
    if GetEngineTypeStr(entityId) not in _REMOVABLE:
        return
    playerId = args["srcId"]
    carriedDict = GetCarriedItem(playerId)
    if carriedDict and carriedDict["newItemName"] == REMOVER_ITEM:
        DestroyEntity(entityId)
        compFactory.CreateGame(playerId).SetOneTipMessage(playerId, "§7物品展示实体 §a删除成功!")
        SetCarriedItem(playerId, {})
