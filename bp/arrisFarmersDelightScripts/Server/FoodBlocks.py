# -*- coding: utf-8 -*-
"""FoodBlocks - 放在地上的食物：派切块吃、盘装食物用碗盛（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetCarriedItem, ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound, ToAllPlayerBlockMolang
from .Helpers.Placement import FacingOfAux
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem, GiveOrDropItem
from ..Shared.Data.Food import pieList, platePackagedFoodDict

# 一个派 4 块；每吃一块：速度效果 30 秒、饥饿值 +3
PIE_SLICES = 4.0
PIE_HUNGER = 3


@registerHandler("ServerBlockUseEvent", match=pieList)
def OnEatPie(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    blockEntityData["blockStatus"] = (blockEntityData["blockStatus"] or 0.0) + 1
    blockStatus = blockEntityData["blockStatus"]
    ToAllPlayerPlaySound(dimensionId, blockPos, "random.eat")
    compFactory.CreateEffect(playerId).AddEffectToEntity("speed", 30, 1, False)
    playerComp = compFactory.CreatePlayer(playerId)
    playerComp.SetPlayerHunger(playerComp.GetPlayerHunger() + PIE_HUNGER)
    ToAllPlayerBlockMolang(blockPos, "variable.mod_pie", blockStatus)
    if blockStatus == PIE_SLICES:
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 0, dimensionId)


@registerHandler("ServerBlockUseEvent", match=platePackagedFoodDict)
def OnServePlatedFood(args):
    # 盘装食物：拿碗右键盛一份（饭卷拼盘不用碗）。盛完最后一份：有空盘的菜留下空盘、再点一下收走，
    # 没有空盘的菜（南瓜盅）整道消失，最后一份也盛给玩家（JE 的 FeastBlock：hasLeftovers 为假时拿走最后一份就拆掉）
    blockName = args["blockName"]
    x, y, z = args["x"], args["y"], args["z"]
    blockPos = (x, y, z)
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    handItemDict = GetCarriedItem(playerId) or {}
    packagedFoodDict = platePackagedFoodDict[blockName]
    name = packagedFoodDict.get("target")
    if packagedFoodDict.get("item") is None:
        # 吃剩的空盘：收走（掉落物按方块的战利品表）
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)
        return
    itemDict = {"itemName": packagedFoodDict.get("item"), "count": 1}
    needsBowl = blockName[0:28] != "arris:rice_roll_medley_block"
    if needsBowl and handItemDict.get("newItemName") != "minecraft:bowl":
        ShowTip(playerId, "你需要一个碗以食用它。")
        return
    if name is None:
        # 没有空盘可留的菜：最后一份盛出，整道菜消失
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 1, dimensionId)
    else:
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": name}, 0, dimensionId)
        blockStates = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
        if blockStates:
            blockStates["direction"] = FacingOfAux(args["aux"])
            compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, blockStates, dimensionId)
    ToAllPlayerPlaySound(dimensionId, blockPos, "armor.equip_leather")
    if needsBowl:
        SetNotCreateItem(playerId, handItemDict)
    GiveOrDropItem(playerId, itemDict, dimensionId)
