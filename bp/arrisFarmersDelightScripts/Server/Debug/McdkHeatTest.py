# -*- coding: utf-8 -*-
"""McdkHeatTest - 厨锅 / 煎锅下面热源的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。读第一个玩家所在维度里 (x, y, z) 那一格，回答离线定不了的两件事：
1. 熔岩炼药锅在引擎里是什么样（Strata 知识库的方块表：minecraft:cauldron 的 cauldron_liquid = lava、fill_level 6，没有 lava_cauldron 方块）：
   用桶往炼药锅里倒一桶熔岩，读那一格：name、states 是不是 cauldron + lava + 6，heat_source 是不是真（Helpers/Heat.IsHeatSource），
   再用桶舀走、读一次：应是假（空了的不算）；
2. 漏斗传热的刷新（Server/HeatConduct）：自上而下摆 厨锅（或煎锅）、漏斗、点着的营火（炉灶、熔岩、岩浆块、熔岩炼药锅也行），读锅那一格：
   stored_heat（锅存着的 heatEnable）应是真、stored_shelf 是 0（漏斗上没有托盘）；浇灭营火 / 铲子熄炉灶，隔 1 秒再读：stored_heat 应变成假；再点着又是真。
   heated_by_helper 是 Heat.IsHeated 现算的，和 stored_heat 对不上的那一刻就是还没刷新（HeatConduct 每 0.5 秒一次）。
   厨锅那一格还给 stored_handle（吊把手的旗，Server/PotSupport 存的：挂着是 1.0，没有这个键是 None）：吊把手挂着时 stored_shelf 一定是 0。
    from arrisFarmersDelightScripts.Server.Debug import McdkHeatTest as T
    return T.mcdk_test_heat_probe(x, y, z)
"""
from ..Helpers.Engine import GetBlockAux, GetBlockEntityData, GetBlockName, compFactory, levelId, serverApi
from ..Helpers.Heat import IsHeated, IsHeatSource


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
