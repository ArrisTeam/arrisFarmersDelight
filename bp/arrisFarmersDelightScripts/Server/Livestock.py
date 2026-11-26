# -*- coding: utf-8 -*-
"""Livestock - 狗粮 / 马饲料喂给驯服的狼、马类的增益，马驴骡被马饲料吸引、狼向本包的肉讨食（服务端）

喂食照 JE 的 DogFoodItem / HorseFeedItem：右键驯服的生物，回满血并得到状态效果，吃掉手里一份（狗粮还给一个碗，创造模式不耗）。
JE 是在"玩家右键实体"的事件里直接处理并取消，这里同样用 PlayerInteractServerEvent，不再借原版的治疗 / 繁殖组件
（那条路只在生物满血时才触发喂食事件，也只认马和狼）。右键事件只在目标对手里的物品有交互时才来，
所以马、狼身上加了 bribeable 记号（见 Shared/Data/Mobs.py 开头的说明），否则能吃的狗粮会被玩家吃掉、马饲料没有任何反应。
喂食规则与吸引 / 讨食的组件都在 Shared/Data/Mobs.py。猫、鸡、猪、兔子、鹦鹉、狼认本包的食物（吸引、繁殖、喂小崽、驯服、治疗）是 Server/AnimalFood.py。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, GetCarriedItem, GetEngineTypeStr
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import GiveOrDropItem, IsCreative, SetNotCreateItem, SetPlayerUsedCD
from ..Shared.Data.Mobs import FEED_USERS, livestockComponents
from ..Shared.Rules.Livestock import HEALTH, feedFor, isTamed


@registerHandler("AddEntityServerEvent", match=livestockComponents)
def InitLivestockComponents(args):
    # 给原版马、驴、骡追加吸引组件、狼追加讨食组件（加上本模组的物品），马类和狼加喂食记号
    eventComp = compFactory.CreateEntityEvent(args["id"])
    for name, value in livestockComponents[args["engineTypeStr"]].items():
        eventComp.AddActorComponent(name, value)


def _isTamed(entityId):
    tamedFlag = compFactory.CreateEntityDefinitions(entityId).IsTamed()
    ownerId = compFactory.CreateActorOwner(entityId).GetEntityOwner() if tamedFlag is None else None
    return isTamed(tamedFlag, ownerId)


@registerHandler("PlayerInteractServerEvent", match=FEED_USERS)
def OnFeedTamedAnimal(args):
    # 右键驯服的目标：回满血、加状态效果、吃掉一份，并取消原版对这次右键的处理（JE 同样取消，不骑也不开背包）。
    # 这种物品对这种生物的右键一律由这里接管：没驯服的什么都不发生（JE 也是），也不让 bribeable 记号白白吃掉物品
    playerId = args["playerId"]
    victimId = args["victimId"]
    feed = feedFor(args["itemDict"]["newItemName"], GetEngineTypeStr(victimId))
    if feed is None:
        return
    args["cancel"] = True
    if not _isTamed(victimId) or SetPlayerUsedCD(playerId) is True:
        return
    compFactory.CreateAttr(victimId).ResetToMaxValue(HEALTH)
    effectComp = compFactory.CreateEffect(victimId)
    for effectName, seconds, amplifier in feed["effects"]:
        effectComp.AddEffectToEntity(effectName, seconds, amplifier, True)
    dimensionId = compFactory.CreateDimension(victimId).GetEntityDimensionId()
    ToAllPlayerPlaySound(dimensionId, compFactory.CreatePos(victimId).GetFootPos(), feed["sound"])
    SetNotCreateItem(playerId, GetCarriedItem(playerId))
    if feed["returns"] and not IsCreative(playerId):
        GiveOrDropItem(playerId, {"itemName": feed["returns"], "count": 1}, dimensionId)
