# -*- coding: utf-8 -*-
"""PlayerSession - 玩家进服：重置交互冷却、下发厨锅配方表（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory
from .Helpers.Player import ResetPlayerUsedCD
from ..Shared.Data.CookingPotRecipes import CookingPotRecipeList

# 客户端厨锅界面从这个 ModAttr 读配方表（含附属包追加的配方）
RECIPE_LIST_ATTR = "arrisCookingPotRecipeList"


@registerHandler("ClientLoadAddonsFinishServerEvent")
def OnClientLoadAddonsFinish(args):
    playerId = args["playerId"]
    ResetPlayerUsedCD(playerId)
    compFactory.CreateModAttr(playerId).SetAttr(RECIPE_LIST_ATTR, CookingPotRecipeList)

