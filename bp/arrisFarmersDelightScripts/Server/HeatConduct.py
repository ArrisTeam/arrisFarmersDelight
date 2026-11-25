# -*- coding: utf-8 -*-
"""HeatConduct - 漏斗传热：下面是漏斗的厨锅 / 煎锅，隔一会儿自己去看漏斗下面的热源还在不在（服务端）

锅和煎锅的"热不热"存在方块实体数据里（heatEnable），只在正下方那一格变了（BlockNeighborChangedServerEvent，邻居事件只来自相邻的方块）时重算。
正下方是漏斗时热源在两格以下（JE 的 heat_conductors，Helpers/Heat.IsHeated），那一格点着、熄灭、拆掉、放上都没有事件，所以这样的锅 / 煎锅
每 CHECK_SECONDS 秒（真实时间）重算一次；变了就当成"正下方那一格变了"交给原来的邻居事件处理函数（Server/CookingPot.OnCookingPotNeighborChanged、
Server/Skillet.OnSkilletNeighborChanged：存状态、同步客户端、煎锅断热时重置计时），不另抄一份。下面不是漏斗的锅什么都不查，只读一次正下方的方块名。
"""
import time

from .EventRegistry import dispatch, registerHandler
from .Helpers.Engine import GetBlockEntityData, GetBlockName
from .Helpers.Heat import IsHeated
from ..Shared.Rules import HeatSources
from ..Shared.Rules.Ticks import Pacer

HEATED_BLOCKS = ("arris:cooking_pot", "arris:skillet")
CHECK_SECONDS = 0.5
_pacer = Pacer(CHECK_SECONDS)


@registerHandler("ServerBlockEntityTickEvent", match=HEATED_BLOCKS)
def OnHeatedBlockTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    if not _pacer.due((dimensionId, blockPos), time.time()):
        return
    belowPos = (blockPos[0], blockPos[1] - 1, blockPos[2])
    belowName = GetBlockName(belowPos, dimensionId)
    if not HeatSources.conducts(belowName):           # 漏斗，或带 farmersdelight:heat_conductors 的方块
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData or IsHeated(belowPos, dimensionId, belowName) == (blockEntityData["heatEnable"] is True):
        return
    dispatch("BlockNeighborChangedServerEvent",
             {"dimensionId": dimensionId, "blockName": args["blockName"], "posX": blockPos[0], "posY": blockPos[1], "posZ": blockPos[2],
              "neighborPosX": belowPos[0], "neighborPosY": belowPos[1], "neighborPosZ": belowPos[2], "toBlockName": belowName},
             args["blockName"])


@registerHandler("BlockRemoveServerEvent", match=HEATED_BLOCKS)
def OnHeatedBlockRemove(args):
    _pacer.forget((args["dimension"], (args["x"], args["y"], args["z"])))
