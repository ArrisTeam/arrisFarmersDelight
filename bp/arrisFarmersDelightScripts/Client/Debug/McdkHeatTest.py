# -*- coding: utf-8 -*-
"""McdkHeatTest - 热源的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code（is_client 为 true）/ 开发调试调用

不会自动运行，没有 RPC 端点。读服务端 Server/Debug/McdkHeatTest.mcdk_test_heat_cauldron_place 摆好的四个炼药锅（同一份 CAULDRONS 的位置，
两端互不导入，各写一份）：每一格客户端 GetBlock 给的 (名字, aux)、这一格按 aux 判算不算热源（Client/Input._isHeat：HeatSources.heatsByAux）、
站在它西边一格时手持煎锅的 nearHeat（Client/Input._nearHeat：右键"煎还是吃"走的就是它），以及客户端这一份状态条件表 / aux 集合里
炼药锅那一条（单机时两端共用一份表；联机的客户端是表同步发来的）。先在客户端线程调这个，再在服务端线程调 mcdk_test_heat_cauldron_read：
    from arrisFarmersDelightScripts.Client.Debug import McdkHeatTest as C
    return C.mcdk_test_heat_cauldron_client()             # 玩家没动过：按自己脚下那一格算四格的位置
    return C.mcdk_test_heat_cauldron_client((x, y, z))    # 动过了：传服务端 mcdk_test_heat_cauldron_place 返回的 origin
怎么摆、怎么清、看什么：服务端那个文件的说明。
"""
import math

from .. import Input
from ..Engine import compFactory, levelId, playerId
from ...Shared.Data.Cooking import HeatSourceAuxDict, HeatSourceStateDict

CAULDRON = "minecraft:cauldron"
# (叫什么, 往东几格, 该不该热)：同服务端 Server/Debug/McdkHeatTest.CAULDRONS
CAULDRONS = (("empty", 3, False), ("water6", 7, False), ("lava1", 11, True), ("lava6", 15, True))


def _origin():
    foot = compFactory.CreatePos(playerId).GetFootPos()
    return (int(math.floor(foot[0])), int(math.floor(foot[1] + 0.001)), int(math.floor(foot[2])))


def mcdk_test_heat_cauldron_client(origin=None):
    """测试函数：客户端读四个炼药锅；每格 ok：按 aux 判的和站在旁边的 nearHeat 都和该不该热一样。"""
    origin = tuple(int(value) for value in origin) if origin else _origin()
    blockInfo = compFactory.CreateBlockInfo(levelId)
    table = list(HeatSourceAuxDict.get(CAULDRON) or [])
    cells = {}
    for name, east, hot in CAULDRONS:
        cell = (origin[0] + east, origin[1], origin[2])
        block = blockInfo.GetBlock(cell)
        row = {"pos": cell, "block": list(block) if isinstance(block, (list, tuple)) else block,
               "heats_by_aux": Input._isHeat(blockInfo, cell), "near_heat": Input._nearHeat((cell[0] - 0.5, cell[1], cell[2] + 0.5)),
               "expected": hot}
        row["ok"] = row["heats_by_aux"] is hot and row["near_heat"] is hot
        cells[name] = row
    return {"case": "heat_cauldron_client", "thread": "client", "ok": all(row["ok"] for row in cells.values()), "origin": origin,
            "cells": cells, "conditions": HeatSourceStateDict.get(CAULDRON), "table": table}
