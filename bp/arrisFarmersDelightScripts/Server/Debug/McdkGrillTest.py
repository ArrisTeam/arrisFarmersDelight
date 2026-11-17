# -*- coding: utf-8 -*-
"""McdkGrillTest - 炉灶手工烧烤的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；没装场景交互前置包（没联动，Shared/Rules/HandsOnMode）时亲手做菜不启用，这一项跳过。在第一个玩家脚下往 +x 15 / +z 9 格放一个点着的炉灶：0 号烤位手放一块生牛肉
（计时器替站点等贴灶台那面熟了就翻一次），1 号烤位按 FD 原样放一块（30 秒后自己弹出去，JE 的营火时间）。
一面 30 / 1.5 / 2 = 10 秒：约 20 秒后 0 号是熟牛肉、留在灶台上；31 秒后 1 号已经空了。
    from arrisFarmersDelightScripts.Server.Debug import McdkGrillTest as T
    return T.mcdk_test_grill_start()
    return T.mcdk_test_grill_collect()   # 约 32 秒后

炉灶朝向的自检（服务端一半，客户端一半在 Client/Debug/McdkGrillTest）：把炉灶用 SetBlockNew 放在第一个玩家脚下往 +x 15 / +z 13 格，转到 direction 状态 0 / 1 / 2 / 3，
返回服务端读到的：GetBlockStates 里的 direction、GetBlockNew 的 aux（和 Engine.GetBlockAux 的回答）、按 aux 读出来的 direction、站点朝向钩子（前置包里登记的
GrillOpen.facingOf，经 Api.getStationType("arris:stove").facing）的回答，和期望的站点朝向（0 南 180 / 1 西 270 / 2 北 0 / 3 东 90）。
普通世界 aux 就是 direction；假日创造者实验玩法的世界里是 0 / 4 / 8 / 12，aux_decodes_to 还是该等于 direction（Placement.directionOfAux）。
每转一个朝向，在客户端（execute_code 的 is_client 为 true）调一次 mcdk_test_grill_facing_client（要传这里返回的 pos），把三处的回答对起来：
direction 状态、两端读到的 aux、两端的钩子说的朝向要彼此一致。block 给 "arris:stove_extinguish" 测熄着的那个方块。用完调 mcdk_test_grill_facing_restore 还原那一格。
    return T.mcdk_test_grill_facing(0)                                   # 0 南；再 1、2、3
    return T.mcdk_test_grill_facing(2, "arris:stove_extinguish")
    return T.mcdk_test_grill_facing_restore()
"""
import time

from .. import HandGrill
from ..Helpers.Engine import GetBlockAux, compFactory, levelId, serverApi
from ..Stove import InitStoveData
from ...Shared.Rules.Placement import directionOfAux
from ...Shared.Rules import HandsOnMode

WATCH_STEP = 0.1
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}
FACING_OFFSET = (15, 13)                     # 离第一个玩家的位置：+x 15 / +z 13（和上面的烧烤自检的 +15 / +9 错开）
STATION_API = "arrisDiegesisScripts.Api.Server"
STOVE_STATION = "arris:stove"
EXPECTED_YAW = {0: 180, 1: 270, 2: 0, 3: 90}     # direction 状态 -> 站点朝向（度）：站点的北面转到炉灶的正面那一侧
_run = {}


def _watch():
    run = _run.get("grill")
    if not run:
        return
    hand = HandGrill.handOf(run["dim"], run["pos"])
    if hand.grill.down(0) >= 1.0 and hand.grill.up(0) < 1.0 and HandGrill.turn(hand, run["player"], 0, time.time(), BEEF):
        run["turns"].append(round(time.time() - run["started"], 1))


def mcdk_test_grill_start():
    """测试函数：放炉灶、摆两块牛肉（一块手放、一块 FD 原样），开始替厨师看着翻面。"""
    if not HandsOnMode.linked():               # 没装前置包：亲手做菜不启用，这一项没有东西可测
        return {"case": "grill_by_hand", "ok": True, "skipped": "hands-on delight is off: the prerequisite pack is not installed (or too old)"}
    players = serverApi.GetPlayerList()
    if not players or _run.get("grill"):
        return {"ok": False, "error": "no player" if not players else "already running"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    pos, dim = (int(x) + 15, int(y), int(z) + 9), compFactory.CreateDimension(playerId).GetEntityDimensionId()
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": "arris:stove"}, 0, dim)
    data = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dim, pos)
    InitStoveData(data)
    data["0"] = {"itemDict": dict(BEEF), "cookTimer": HandGrill.COOK_TIMER}
    data["1"] = {"itemDict": dict(BEEF), "cookTimer": HandGrill.COOK_TIMER}
    HandGrill.forget(dim, pos)
    HandGrill.handOf(dim, pos).grill.layByHand(0)
    timer = compFactory.CreateGame(levelId).AddRepeatedTimer(WATCH_STEP, _watch)
    _run["grill"] = {"pos": pos, "dim": dim, "player": playerId, "timer": timer, "started": time.time(), "turns": []}
    return {"case": "grill_start", "ok": True, "pos": pos, "collect_after_seconds": 32}


def mcdk_test_grill_collect():
    """测试函数：停表，检查手放的那块两面烤好留在灶台上、FD 原样那块已经弹走，然后清理。"""
    run = _run.pop("grill", None)
    if not run and not HandsOnMode.linked():
        return {"case": "grill_by_hand", "ok": True, "skipped": "hands-on delight is off: the prerequisite pack is not installed (or too old)"}
    if not run:
        return {"ok": False, "error": "not started"}
    compFactory.CreateGame(levelId).CancelTimer(run["timer"])
    pos, dim = run["pos"], run["dim"]
    data = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dim, pos)
    first, second = (HandGrill.slotItem(data, 0), HandGrill.slotItem(data, 1)) if data else (None, None)
    hand = HandGrill.handOf(dim, pos)
    result = {"case": "grill_by_hand", "place0": first and first["newItemName"], "place1": second and second["newItemName"],
              "turns": run["turns"], "finished": hand.finished, "seconds": round(time.time() - run["started"], 1)}
    result["ok"] = (result["place0"] == "minecraft:cooked_beef" and result["place1"] is None and len(run["turns"]) == 1
                    and hand.finished == 1)
    if data:
        InitStoveData(data)                          # 不然拆炉灶时烤好的牛肉会掉出来
    HandGrill.forget(dim, pos)
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    return result


def mcdk_test_grill_facing(direction=0, block="arris:stove"):
    """测试函数：把炉灶（第一次调用时放在玩家脚下往 +x 15 / +z 13 格，原来那一格记下来）转到 direction 状态 0..3，返回服务端读到的各样朝向，对着期望的站点朝向。"""
    players = serverApi.GetPlayerList()
    if not players or direction not in EXPECTED_YAW:
        return {"case": "grill_facing", "ok": False, "error": "no player" if not players else "direction 要是 0..3"}
    playerId = players[0]
    info, stateComp = compFactory.CreateBlockInfo(levelId), compFactory.CreateBlockState(levelId)
    if "facing" not in _run:
        x, y, z = compFactory.CreatePos(playerId).GetFootPos()
        pos, dim = (int(x) + FACING_OFFSET[0], int(y), int(z) + FACING_OFFSET[1]), compFactory.CreateDimension(playerId).GetEntityDimensionId()
        _run["facing"] = {"pos": pos, "dim": dim, "name": (info.GetBlockNew(pos, dim) or {}).get("name") or "minecraft:air",
                          "states": stateComp.GetBlockStates(pos, dim)}
    pos, dim = _run["facing"]["pos"], _run["facing"]["dim"]
    info.SetBlockNew(pos, {"name": block}, 0, dim)
    states = stateComp.GetBlockStates(pos, dim) or {}
    states["direction"] = direction
    stateComp.SetBlockStates(pos, states, dim)
    aux = (info.GetBlockNew(pos, dim) or {}).get("aux")
    api = serverApi.ImportModule(STATION_API)
    stationType = api.getStationType(STOVE_STATION) if api is not None else None
    hook = getattr(stationType, "facing", None)
    result = {"case": "grill_facing", "block": block, "pos": pos, "dim": dim, "direction_set": direction,
              "state_direction": (stateComp.GetBlockStates(pos, dim) or {}).get("direction"), "aux": aux, "get_block_aux": GetBlockAux(pos, dim),
              "aux_decodes_to": directionOfAux(aux), "server_facing": hook(dim, pos) if hook is not None else None,
              "expected_yaw": EXPECTED_YAW[direction]}
    result["ok"] = (result["state_direction"] == direction and result["get_block_aux"] == (aux or 0) and result["aux_decodes_to"] == direction
                    and result["server_facing"] == EXPECTED_YAW[direction])
    if hook is None:
        result["note"] = "前置包没装或炉灶站点没登记：server_facing 是 None，ok 不会是真"
    return result


def mcdk_test_grill_facing_restore():
    """测试函数：把朝向自检用的那一格还原成原来的方块（名字、朝向），清掉记录。"""
    run = _run.pop("facing", None)
    if not run:
        return {"case": "grill_facing_restore", "ok": False, "error": "not started"}
    pos, dim = run["pos"], run["dim"]
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": run["name"]}, 0, dim)
    if run["states"]:
        compFactory.CreateBlockState(levelId).SetBlockStates(pos, run["states"], dim)
    now = (compFactory.CreateBlockInfo(levelId).GetBlockNew(pos, dim) or {}).get("name")
    return {"case": "grill_facing_restore", "ok": now == run["name"], "restored": run["name"], "now": now, "pos": pos}
