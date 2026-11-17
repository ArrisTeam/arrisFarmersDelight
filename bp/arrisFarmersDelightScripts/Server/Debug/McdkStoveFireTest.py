# -*- coding: utf-8 -*-
"""McdkStoveFireTest - 炉灶点火 / 灭火换方块的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。要核对的是引擎对 SetBlockNew 换炉灶方块的反应（离线只能照官方文档写，事件先后、方块实体什么时候在都是推断）：
在第一个玩家脚下往 +x 15 / +z 17 格放一座朝北的炉灶（toUnlit 为真放点着的、为假放熄着的），摆上三件东西（0 号 FD 原样烤了一半的牛肉、2 号手放的贴灶面烤了一半的鸡肉、
5 号熟牛肉），给 StoveSwap.claims / apply 套上记录，再直接调 StoveSwap.swap 换成对面的方块（不用打火石、铲子：要看的是引擎的反应，手上的工具另有清单）。
返回里的 log 是事件到的先后：("claims", 旧 / 新方块名, 认没认) 是引擎给旧方块发的 BlockRemoveServerEvent 来了、StoveSwap 把它当换方块挡住了没有，
("apply", 写成了没有) 是快照写进新方块实体（swap 里当场写、放置事件里写、炉灶的下一步里写，谁先到谁写），("swap_returned",) 是 swap 返回的那一刻——
它前面的是 SetBlockNew 里同步到的，后面的是晚到的。约 3 秒后调 collect：核对东西一件不少、位置没变、手放的标记和朝向还在，还原那一格。
    from arrisFarmersDelightScripts.Server.Debug import McdkStoveFireTest as T
    return T.mcdk_test_stove_swap_start()                   # 点着 -> 熄着；T.mcdk_test_stove_swap_start(False) 是熄着 -> 点着
    return T.mcdk_test_stove_swap_collect()                 # 约 3 秒后
别和 McdkGrillTest 的烧烤自检同时跑（共用玩家脚边的位置，错开了 +z 8 格）。
"""
import time

from .. import HandGrill, StoveSwap
from ..Helpers.Engine import GetBlockEntityData, compFactory, levelId, serverApi
from ..Stove import InitStoveData

OFFSET = (15, 17)
LIT, UNLIT = "arris:stove", "arris:stove_extinguish"
NORTH = 2                                    # direction 状态：0 南 1 西 2 北 3 东
_run = {}


def _item(name):
    return {"newItemName": name, "newAuxValue": 0, "count": 1}


def _logged(log):
    """给 StoveSwap.claims / apply 套上记录（Stove.py 和 swap 自己都经模块属性调它们）；返回要还原的原函数。"""
    originals = {"claims": StoveSwap.claims, "apply": StoveSwap.apply}

    def claims(dimensionId, blockPos, fullName, now):
        result = originals["claims"](dimensionId, blockPos, fullName, now)
        log.append(("claims", fullName, result))
        return result

    def apply(dimensionId, blockPos):
        result = originals["apply"](dimensionId, blockPos)
        log.append(("apply", result))
        return result

    StoveSwap.claims, StoveSwap.apply = claims, apply
    return originals


def _direction(pos, dim):
    return (compFactory.CreateBlockState(levelId).GetBlockStates(pos, dim) or {}).get("direction")


def mcdk_test_stove_swap_start(toUnlit=True):
    """测试函数：放炉灶、摆东西、换方块（点着 -> 熄着，或反过来），记下引擎事件到的先后。"""
    players = serverApi.GetPlayerList()
    if not players or "swap" in _run:
        return {"case": "stove_swap", "ok": False, "error": "no player" if not players else "already running"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    pos, dim = (int(x) + OFFSET[0], int(y), int(z) + OFFSET[1]), compFactory.CreateDimension(playerId).GetEntityDimensionId()
    start, goal = (LIT, UNLIT) if toUnlit else (UNLIT, LIT)
    info, states = compFactory.CreateBlockInfo(levelId), compFactory.CreateBlockState(levelId)
    info.SetBlockNew(pos, {"name": start}, 0, dim)
    states.SetBlockStates(pos, dict(states.GetBlockStates(pos, dim) or {}, direction=NORTH), dim)
    data = GetBlockEntityData(dim, pos)
    if not data:
        return {"case": "stove_swap", "ok": False, "error": "放下的炉灶没有方块实体数据（SetBlockNew 之后还不在？）", "pos": pos}
    InitStoveData(data)
    data["0"] = {"itemDict": _item("minecraft:beef"), "cookTimer": 12.5}
    data["2"] = {"itemDict": _item("minecraft:chicken"), "cookTimer": 30}
    data["5"] = {"itemDict": _item("minecraft:cooked_beef"), "cookTimer": 30}
    HandGrill.forget(dim, pos)
    hand = HandGrill.handOf(dim, pos)
    hand.grill.layByHand(2)
    hand.grill.grill(2, 0.4)
    HandGrill.save(hand, data)
    before, log = StoveSwap.snapshot(data), []
    originals = _logged(log)
    swapped = StoveSwap.swap(dim, pos, goal)
    log.append(("swap_returned",))
    record = StoveSwap._swaps.get((dim, pos))
    _run["swap"] = {"pos": pos, "dim": dim, "goal": goal, "before": before, "log": log, "originals": originals, "started": time.time()}
    return {"case": "stove_swap_start", "ok": bool(swapped), "pos": pos, "from": start, "to": goal, "swap_returned": swapped, "log": list(log),
            "block_now": (info.GetBlockNew(pos, dim) or {}).get("name"), "entity_there_right_after": bool(GetBlockEntityData(dim, pos)),
            "data_pending_right_after": bool(record and record.data is not None), "direction_right_after": _direction(pos, dim),
            "collect_after_seconds": 3}


def mcdk_test_stove_swap_collect():
    """测试函数：核对换完之后东西、手放的标记、朝向，还原那一格。"""
    run = _run.pop("swap", None)
    if not run:
        return {"case": "stove_swap_collect", "ok": False, "error": "not started"}
    StoveSwap.claims, StoveSwap.apply = run["originals"]["claims"], run["originals"]["apply"]
    pos, dim, before = run["pos"], run["dim"], run["before"]
    data = GetBlockEntityData(dim, pos)
    after = StoveSwap.snapshot(data) if data else {}
    same = dict((key, (after.get(key) or {}).get("itemDict") == (before.get(key) or {}).get("itemDict")) for key in ("0", "1", "2", "3", "4", "5"))
    name = (compFactory.CreateBlockInfo(levelId).GetBlockNew(pos, dim) or {}).get("name")
    hand = (after.get(HandGrill.SAVE_KEY) or {}).get("byHand")
    checks = {"block_is_goal": name == run["goal"], "items_all_there_and_in_place": all(same.values()),
              "hand_laid_flag_kept": hand is not None and hand[2] == 1 and hand[0] == 0, "direction_kept": _direction(pos, dim) == NORTH,
              "swap_record_gone_or_applied": StoveSwap._swaps.get((dim, pos)) is None or StoveSwap._swaps[(dim, pos)].data is None}
    result = {"case": "stove_swap_collect", "ok": all(checks.values()), "checks": checks, "items_same": same, "block": name, "log": run["log"],
              "removal_events_claimed": [entry[2] for entry in run["log"] if entry[0] == "claims"], "seconds": round(time.time() - run["started"], 1)}
    if data:
        InitStoveData(data)                          # 不然拆炉灶时烤位上的东西会掉出来
    HandGrill.forget(dim, pos)
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    return result
