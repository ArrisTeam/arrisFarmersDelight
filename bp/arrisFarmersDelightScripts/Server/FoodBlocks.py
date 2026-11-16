# -*- coding: utf-8 -*-
"""FoodBlocks - 放在地上的食物：派切块吃（手里拿刀则切下一片）、盘装食物用碗盛（服务端）"""
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, GetBlockEntityData, GetCarriedItem, ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound, ToAllPlayerBlockMolang
from .Helpers.Items import IsKnife
from .Helpers.Placement import FacingOfAux
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem, GiveOrDropItem
from ..Shared.Data.Food import pieList, platePackagedFoodDict
from ..Shared.Data.Slicing import PIE_BITES, SLICE_SOUND, pieSliceItems
from ..Shared.Rules.Eating import SATURATION, eatenFood

# 一个派 4 块；每吃一块等于吃一片派（JE 的 PIE_SLICE）：营养 3、饱和度修饰 0.3，速度 I 30 秒（不冒粒子）
PIE_NUTRITION = 3
PIE_SATURATION_MODIFIER = 0.3
PIE_SPEED_SECONDS = 30


def _takeBite(dimensionId, blockPos, blockEntityData):
    # 派少一块（吃掉或被刀切下）：记口数、同步画面，最后一块没了就拆掉方块
    blockEntityData["blockStatus"] = (blockEntityData["blockStatus"] or 0.0) + 1
    blockStatus = blockEntityData["blockStatus"]
    ToAllPlayerBlockMolang(blockPos, "variable.mod_pie", blockStatus)
    if blockStatus >= PIE_BITES:
        compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": "minecraft:air"}, 0, dimensionId)


def _feedPlayer(playerId):
    # 吃一片派的饥饿值与饱和度（Java 版 FoodData.eat 的算法）
    playerComp = compFactory.CreatePlayer(playerId)
    attrComp = compFactory.CreateAttr(playerId)
    hunger, saturation = eatenFood(playerComp.GetPlayerHunger(), attrComp.GetAttrValue(SATURATION),
                                   PIE_NUTRITION, PIE_SATURATION_MODIFIER)
    playerComp.SetPlayerHunger(hunger)
    attrComp.SetAttrValue(SATURATION, saturation)


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
    handItemDict = GetCarriedItem(playerId)
    sliceItem = pieSliceItems.get(args["blockName"])
    if sliceItem and handItemDict and IsKnife(handItemDict["newItemName"]):
        # 手里拿着刀：切下一片掉在派上，不吃、不耗刀（JE 的 PieBlock.cutSlice）
        _takeBite(dimensionId, blockPos, blockEntityData)
        System.CreateEngineItemEntity({"newItemName": sliceItem, "newAuxValue": 0, "count": 1}, dimensionId,
                                      (blockPos[0] + 0.5, blockPos[1] + 0.3, blockPos[2] + 0.5))
        ToAllPlayerPlaySound(dimensionId, blockPos, SLICE_SOUND)
        return
    ToAllPlayerPlaySound(dimensionId, blockPos, "random.eat")
    compFactory.CreateEffect(playerId).AddEffectToEntity("speed", PIE_SPEED_SECONDS, 0, False)
    _feedPlayer(playerId)
    _takeBite(dimensionId, blockPos, blockEntityData)


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
