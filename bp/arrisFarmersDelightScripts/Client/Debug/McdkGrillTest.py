# -*- coding: utf-8 -*-
"""McdkGrillTest - 炉灶朝向的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code（is_client 为 true）/ 开发调试调用

不会自动运行，没有 RPC 端点。配套服务端的 Server/Debug/McdkGrillTest 的 mcdk_test_grill_facing(direction, block)：服务端把一座炉灶转到某个朝向，
返回它读到的 direction 状态、aux、站点朝向钩子的回答和位置 pos。这里读本端：同一个位置的方块（GetBlock(pos) 的名字和 aux）、按 aux 读出来的 direction、
前置包里登记的炉灶站点朝向钩子（GrillView.facingOf，经 Api.getBehavior("arris:stove").facing）的回答，和期望的站点朝向：
服务端和客户端的 aux、两端钩子说的朝向要一致，客户端那一份才能和服务端的 Opened 里的 yaw 对上（站点的镜头、六件、世界里的展示都按它转）。
    from arrisFarmersDelightScripts.Client.Debug import McdkGrillTest as T
    return T.mcdk_test_grill_facing_client([x, y, z])          # 传服务端 mcdk_test_grill_facing 返回的 pos；每转一个朝向调一次
不传 pos 就用离本人 +x 15 / +z 13 的那一格（服务端自检的位置，本人没动过的话）。
"""
from ..Engine import clientApi, compFactory, levelId, playerId
from ...Shared.Rules.Placement import directionOfAux

FACING_OFFSET = (15, 13)                     # 和服务端自检一致（两端互不导入，各写一份）
STATION_API = "arrisDiegesisScripts.Api.Client"
STOVE_STATION = "arris:stove"
STOVES = ("arris:stove", "arris:stove_extinguish")
EXPECTED_YAW = {0: 180, 1: 270, 2: 0, 3: 90}     # direction 状态 -> 站点朝向（度）


def mcdk_test_grill_facing_client(pos=None):
    """测试函数：本端读到 pos 这座炉灶的 aux 和站点朝向钩子的回答，返回结构化结果。"""
    if pos is None:
        x, y, z = compFactory.CreatePos(playerId).GetFootPos()
        pos = (int(x) + FACING_OFFSET[0], int(y), int(z) + FACING_OFFSET[1])
    pos = (int(pos[0]), int(pos[1]), int(pos[2]))
    dim = compFactory.CreateGame(levelId).GetCurrentDimension()
    block = compFactory.CreateBlockInfo(levelId).GetBlock(pos)
    if not block or block[0] not in STOVES:
        return {"case": "grill_facing_client", "ok": False, "pos": pos, "block": block, "error": "那里不是炉灶（pos 传服务端返回的那个）"}
    api = clientApi.ImportModule(STATION_API)
    entry = api.getBehavior(STOVE_STATION) if api is not None else None
    hook = getattr(entry, "facing", None)
    direction = directionOfAux(block[1])
    result = {"case": "grill_facing_client", "pos": pos, "dim": dim, "block": block[0], "aux": block[1], "aux_decodes_to": direction,
              "client_facing": hook(pos, dim) if hook is not None else None, "expected_yaw": EXPECTED_YAW[direction]}
    result["ok"] = result["client_facing"] == EXPECTED_YAW[direction]
    if hook is None:
        result["note"] = "前置包没装或炉灶站点的表现没登记：client_facing 是 None，ok 不会是真"
    return result
