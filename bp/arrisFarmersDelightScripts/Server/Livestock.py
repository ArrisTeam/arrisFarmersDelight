# -*- coding: utf-8 -*-
"""Livestock - 狼与马认狗粮 / 马饲料、喂食后的增益（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory
from .Helpers.Player import GiveOrDropItem
from ..Shared.Data.Mobs import horseComponentsDict, wolfComponentsDict

_COMPONENTS = {"minecraft:wolf": wolfComponentsDict, "minecraft:horse": horseComponentsDict}


@registerHandler("AddEntityServerEvent", match=("minecraft:wolf", "minecraft:horse"))
def InitWolfAndHorseComponents(args):
    # 给原版狼 / 马追加认本模组饲料的组件
    entityId = args["id"]
    eventComp = compFactory.CreateEntityEvent(entityId)
    for name, value in _COMPONENTS[args["engineTypeStr"]].items():
        eventComp.AddActorComponent(name, value)


@registerHandler("PlayerFeedEntityServerEvent", match=("arris:dog_food", "arris:horse_feed"))
def OnFeedAnimal(args):
    comp = compFactory.CreateEffect(args["entityId"])
    if args["itemDict"]["newItemName"] == "arris:dog_food":
        comp.AddEffectToEntity("speed", 300, 0, True)
        comp.AddEffectToEntity("strength", 300, 0, True)
        comp.AddEffectToEntity("resistance", 300, 0, True)
        GiveOrDropItem(args["playerId"], {"itemName": "minecraft:bowl", "count": 1})
    else:
        comp.AddEffectToEntity("speed", 300, 1, True)
        comp.AddEffectToEntity("jump_boost", 300, 0, True)
