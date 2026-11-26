# -*- coding: utf-8 -*-
"""McdkHeatTest - 厨锅 / 煎锅下面热源的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。
mcdk_test_heat_probe(x, y, z)：读第一个玩家所在维度里 (x, y, z) 那一格，回答离线定不了的两件事：
1. 熔岩炼药锅在引擎里是什么样（Strata 知识库的方块表：minecraft:cauldron 的 cauldron_liquid = lava、fill_level 6，没有 lava_cauldron 方块）：
   用桶往炼药锅里倒一桶熔岩，读那一格：name、states 是不是 cauldron + lava + 6，heat_source 是不是真（Helpers/Heat.IsHeatSource），
   再用桶舀走、读一次：应是假（空了的不算）；
2. 漏斗传热的刷新（Server/HeatConduct）：自上而下摆 厨锅（或煎锅）、漏斗、点着的营火（炉灶、熔岩、岩浆块、熔岩炼药锅也行），读锅那一格：
   stored_heat（锅存着的 heatEnable）应是真、stored_shelf 是 0（漏斗上没有托盘）；浇灭营火 / 铲子熄炉灶，隔 1 秒再读：stored_heat 应变成假；再点着又是真。
   heated_by_helper 是 Heat.IsHeated 现算的，和 stored_heat 对不上的那一刻就是还没刷新（HeatConduct 每 0.5 秒一次）。
   厨锅那一格还给 stored_handle（吊把手的旗，Server/PotSupport 存的：挂着是 1.0，没有这个键是 None）：吊把手挂着时 stored_shelf 一定是 0。
    from arrisFarmersDelightScripts.Server.Debug import McdkHeatTest as T
    return T.mcdk_test_heat_probe(x, y, z)

炼药锅的四种样子（热源的状态条件 Shared/Data/Cooking.HeatSourceStateDict；客户端读不到状态，按服务端算好的 aux 判）：在第一个玩家脚下那一格
往东 3、7、11、15 格摆空的、盛水 6 级、熔岩 1 级、熔岩 6 级四个炼药锅（同 Client/Debug/McdkHeatTest.CAULDRONS；彼此隔 4 格，站在一个的西边一格时
3x3x3 里只有它）。站在平地上、往东 16 格以内空着再摆；摆之前那几格是什么，清的时候原样放回（方块名 + aux，方块实体不管）。先客户端、后服务端：
    服务端  return T.mcdk_test_heat_cauldron_place()    # 摆好；返回 origin、四格摆没摆上，GetBlockStatesFromAuxValue 对 aux 0..40 的原始返回（raw），
                                                        # 照它现算的满足条件的 aux（computed，不写表）、表里现在的（table）、HeatAux 上次算的（lastRefresh）
    客户端  from arrisFarmersDelightScripts.Client.Debug import McdkHeatTest as C
            return C.mcdk_test_heat_cauldron_client()   # 玩家动过了就传服务端返回的 origin：C.mcdk_test_heat_cauldron_client((x, y, z))
    服务端  return T.mcdk_test_heat_cauldron_read()     # 每格 GetBlockNew 的名字和 aux、GetBlockStates、IsHeatSource（当作锅下面那一格）、
                                                        # IsNearHeat（手持煎锅身边的这一格）、站在它西边一格时手持煎锅的 nearHeat
    服务端  return T.mcdk_test_heat_cauldron_clear()    # 四格放回原样
看什么：raw 里 aux 7、15、23（fill_level 的空号）和 24 以上（越界）引擎给的是什么（HeatStates.auxSet 当"没有方块"的只有 None、{}、不是字典、
和前面重复的状态）；computed["aux"] 是不是 [9, 10, 11, 12, 13, 14]、asked 问了几个；read 里熔岩两格 aux 是不是 9 / 14、heat_source / near_cell /
near_heat 是真，空的、盛水的是假；客户端那边 block 的 aux 和服务端一样、near_heat 一样。
3.10 实机（2026-11-26，单机）：raw 是 0–6 水 0–6 级、8–14 熔岩 0–6 级、16–22 细雪 0–6 级，空号 7、15 和越界的 23 以上（到 40）都是缺省状态
{"cauldron_liquid": "water", "fill_level": 0}（不是 None、不抛异常）；computed 是 [9..14]（asked 46、top 22）；四格的 aux 两端都是 0 / 6 / 9 / 14，
两端的判断四格一致（空的、盛水的不算，熔岩 1 级、6 级算），两边 ok。
"""
import math

from .. import HeatAux
from ..Helpers.Engine import GetBlockAux, GetBlockEntityData, GetBlockName, compFactory, levelId, serverApi
from ..Helpers.Heat import IsHeated, IsHeatSource, IsNearHeat
from ...Shared.Data.Cooking import HeatSourceAuxDict, HeatSourceStateDict
from ...Shared.Rules import HeatStates
from ...Shared.Rules.SkilletRules import nearHeat

CAULDRON = "minecraft:cauldron"
# (叫什么, 往东几格, 摆成什么状态, 该不该热)；同 Client/Debug/McdkHeatTest.CAULDRONS（两端互不导入，各写一份）
CAULDRONS = (("empty", 3, {"cauldron_liquid": "water", "fill_level": 0}, False),
             ("water6", 7, {"cauldron_liquid": "water", "fill_level": 6}, False),
             ("lava1", 11, {"cauldron_liquid": "lava", "fill_level": 1}, True),
             ("lava6", 15, {"cauldron_liquid": "lava", "fill_level": 6}, True))
RAW_UPTO = 40           # 原始返回列到 aux 40：炼药锅的位组合是 0–31，多看一段越界的
_placed = []            # [(格, 原来的方块名, 原来的 aux, 维度)]：清的时候放回去


def mcdk_test_heat_probe(x, y, z):
    """测试函数：读 (x, y, z) 那一格：方块名、状态、能不能给上面热、上面放锅热不热；那一格是厨锅 / 煎锅时还有它存着的热和托盘。"""
    players = serverApi.GetPlayerList()
    if not players:
        return {"case": "heat_probe", "ok": False, "error": "no player"}
    dim, pos = compFactory.CreateDimension(players[0]).GetEntityDimensionId(), (int(x), int(y), int(z))
    states = compFactory.CreateBlockState(levelId).GetBlockStates(pos, dim)
    result = {"case": "heat_probe", "ok": True, "pos": pos, "name": GetBlockName(pos, dim), "aux": GetBlockAux(pos, dim),
              "states": dict(states) if states else None, "heat_source": IsHeatSource(pos, dim), "heated_above": IsHeated(pos, dim)}
    data = GetBlockEntityData(dim, pos)
    if data and result["name"] in ("arris:cooking_pot", "arris:skillet"):
        below = (pos[0], pos[1] - 1, pos[2])
        result.update(stored_heat=data["heatEnable"], stored_shelf=data["shelfEnable"], stored_handle=data["handleEnable"],
                      below=GetBlockName(below, dim), heated_by_helper=IsHeated(below, dim))
    return result


# ---------------------------------------------------------------- 炼药锅的四种样子

def _origin(playerId):
    foot = compFactory.CreatePos(playerId).GetFootPos()
    return (int(math.floor(foot[0])), int(math.floor(foot[1] + 0.001)), int(math.floor(foot[2])))


def _raw(upto):
    """GetBlockStatesFromAuxValue(炼药锅, aux) 对 0..upto 每个 aux 的原始返回；抛了异常记成 "raise 类型: 消息"。"""
    comp = compFactory.CreateBlockState(levelId)
    found = []
    for aux in range(int(upto) + 1):
        try:
            value = comp.GetBlockStatesFromAuxValue(CAULDRON, aux)
        except Exception as error:  # noqa: BLE001 - 自检：引擎怎么答就记什么
            value = "raise %s: %s" % (type(error).__name__, error)
        found.append([aux, value if value is None or isinstance(value, (dict, str)) else repr(value)])
    return found


def mcdk_test_heat_cauldron_place(upto=RAW_UPTO):
    """测试函数：在第一个玩家脚下那一格往东摆四个炼药锅（见模块说明），返回摆在哪、引擎的原始返回、现算的和表里的满足条件的 aux。
    这里不读那四格（先让客户端读，再调 mcdk_test_heat_cauldron_read）。"""
    players = serverApi.GetPlayerList()
    if not players:
        return {"case": "heat_cauldron_place", "ok": False, "error": "no player"}
    if _placed:
        return {"case": "heat_cauldron_place", "ok": False, "error": "已经摆着一组：先 mcdk_test_heat_cauldron_clear()"}
    dim, origin = compFactory.CreateDimension(players[0]).GetEntityDimensionId(), _origin(players[0])
    blockInfo, blockState = compFactory.CreateBlockInfo(levelId), compFactory.CreateBlockState(levelId)
    placed = {}
    for name, east, states, _hot in CAULDRONS:
        cell = (origin[0] + east, origin[1], origin[2])
        before = blockInfo.GetBlockNew(cell, dim) or {}
        _placed.append((cell, before.get("name") or "minecraft:air", before.get("aux") or 0, dim))
        put = blockInfo.SetBlockNew(cell, {"name": CAULDRON, "aux": 0}, 0, dim)
        changed = blockState.SetBlockStates(cell, dict(states), dim)
        placed[name] = {"pos": cell, "was": before.get("name"), "setBlock": put, "setStates": changed}
    conditions = HeatSourceStateDict.get(CAULDRON)
    return {"case": "heat_cauldron_place", "ok": all(row["setBlock"] and row["setStates"] for row in placed.values()),
            "origin": origin, "dimension": dim, "placed": placed, "raw": _raw(upto), "conditions": conditions,
            "computed": HeatStates.auxSet(HeatAux.reader(CAULDRON), conditions), "table": list(HeatSourceAuxDict.get(CAULDRON) or []),
            "lastRefresh": HeatAux.report().get(CAULDRON)}


def _nearAt(foot, dimensionId):
    return nearHeat(foot, lambda pos: IsNearHeat(pos, dimensionId))


def mcdk_test_heat_cauldron_read():
    """测试函数：服务端读摆好的四格（见模块说明）；每格 ok：三处判的都和该不该热一样，aux 在不在表里也一样。"""
    if not _placed:
        return {"case": "heat_cauldron_read", "ok": False, "error": "还没摆：先 mcdk_test_heat_cauldron_place()"}
    blockInfo, blockState = compFactory.CreateBlockInfo(levelId), compFactory.CreateBlockState(levelId)
    table = list(HeatSourceAuxDict.get(CAULDRON) or [])
    cells = {}
    for (name, _east, _states, hot), (cell, _was, _aux, dim) in zip(CAULDRONS, _placed):
        info = blockInfo.GetBlockNew(cell, dim) or {}
        states = blockState.GetBlockStates(cell, dim)
        row = {"pos": cell, "name": info.get("name"), "aux": info.get("aux"), "states": dict(states) if states else states,
               "heat_source": IsHeatSource(cell, dim), "near_cell": IsNearHeat(cell, dim),
               "near_heat": _nearAt((cell[0] - 0.5, cell[1], cell[2] + 0.5), dim), "expected": hot}
        row["ok"] = row["heat_source"] is hot and row["near_cell"] is hot and row["near_heat"] is hot and (row["aux"] in table) is hot
        cells[name] = row
    return {"case": "heat_cauldron_read", "ok": all(row["ok"] for row in cells.values()), "cells": cells, "table": table,
            "lastRefresh": HeatAux.report().get(CAULDRON)}


def mcdk_test_heat_cauldron_clear():
    """测试函数：摆过的格放回摆之前的方块（方块名 + aux）。"""
    blockInfo = compFactory.CreateBlockInfo(levelId)
    restored = []
    while _placed:
        cell, name, aux, dim = _placed.pop()
        restored.append({"pos": cell, "block": name, "aux": aux, "ok": blockInfo.SetBlockNew(cell, {"name": name, "aux": aux}, 0, dim)})
    return {"case": "heat_cauldron_clear", "ok": all(row["ok"] for row in restored), "restored": restored}
