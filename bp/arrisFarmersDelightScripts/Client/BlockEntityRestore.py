# -*- coding: utf-8 -*-
"""BlockEntityRestore - 方块实体在本端加载时按存档数据恢复 molang（客户端）

厨锅 / 煎锅的"支架""加热"、派吃到第几块都由服务端在变化时广播；
区块重新加载或玩家刚进服时，客户端按方块实体数据自己补一次。
"""
from ..QuModLibs.Client import Listen
from .Engine import compFactory, levelId, unwrap, blockEntityExData

_HEATED = ("arris:skillet", "arris:cooking_pot")
_PIES = ("arris:apple_pie", "arris:chocolate_pie", "arris:sweet_berry_cheesecake")


@Listen("ModBlockEntityLoadedClientEvent")
def OnBlockEntityLoaded(args):
    blockName = args["blockName"]
    if blockName not in _HEATED and blockName not in _PIES:
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    blockInfo = compFactory.CreateBlockInfo(levelId)
    if not blockInfo.GetBlockEntityData(blockPos):
        return
    # /setblock、结构放出的方块可能缺键，逐个判空
    exData = blockEntityExData(blockPos)
    blockInfo.SetEnableBlockEntityAnimations(blockPos, True)
    if blockName in _HEATED:
        heat = unwrap(exData.get("heatParticleEnable"))
        if heat is not None:
            blockInfo.SetBlockEntityMolangValue(blockPos, "variable.mod_heat", heat)
        shelf = unwrap(exData.get("shelfEnable"))
        if shelf is not None:
            blockInfo.SetBlockEntityMolangValue(blockPos, "variable.mod_shelf", shelf)
    else:
        blockInfo.SetBlockEntityMolangValue(blockPos, "variable.mod_pie", unwrap(exData.get("blockStatus"), 0.0))
