# -*- coding: utf-8 -*-
"""PlayerSession - 玩家进服：重置交互冷却、下发厨锅配方表；合成后返还空容器（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, System
from .Helpers.Player import ResetPlayerUsedCD
from ..Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ..Shared.Data.Food import shapedRecipeContainerDict

# 客户端厨锅界面从这个 ModAttr 读配方表（含附属包追加的配方）
RECIPE_LIST_ATTR = "arrisCookingPotRecipeList"


@registerHandler("ClientLoadAddonsFinishServerEvent")
def OnClientLoadAddonsFinish(args):
    playerId = args["playerId"]
    ResetPlayerUsedCD(playerId)
    compFactory.CreateModAttr(playerId).SetAttr(RECIPE_LIST_ATTR, CookingPotRecipeList)


@registerHandler("CraftItemOutputChangeServerEvent")
def OnCraftReturnContainer(args):
    # 合成后返还空容器（桶、玻璃瓶、碗）。以前由客户端调 RPC 通知服务端，服务端无从确认真的合成过，
    # 反复调用就能无限刷容器；现在只认服务端的合成产出事件。
    itemDict = args.get("itemDict") or {}
    containerTemplate = shapedRecipeContainerDict.get(itemDict.get("newItemName") or itemDict.get("itemName"))
    if not containerTemplate:
        return
    playerId = args["playerId"]
    # 一次取出可能是多份（例如蜂蜜曲奇一份 8 个）：按每份产出数折算，至少 1 个
    containerCount = max(1, itemDict.get("count", 1) // containerTemplate.get("perCraft", 1))
    returnDict = {"itemName": containerTemplate["itemName"], "count": containerCount,
                  "auxValue": containerTemplate.get("auxValue", 0)}
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    playerPos = compFactory.CreatePos(playerId).GetFootPos()
    if playerPos is not None:
        System.CreateEngineItemEntity(returnDict, dimensionId, playerPos)
