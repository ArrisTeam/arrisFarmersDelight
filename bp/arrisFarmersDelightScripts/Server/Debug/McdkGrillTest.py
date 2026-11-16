# -*- coding: utf-8 -*-
"""McdkGrillTest - 炉灶手工烧烤的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。在第一个玩家脚下往 +x 15 / +z 9 格放一个点着的炉灶：0 号烤位手放一块生牛肉
（计时器替站点等贴灶台那面熟了就翻一次），1 号烤位按 FD 原样放一块（7 秒后自己弹出去）。
一面 7 / 1.5 / 2 ≈ 2.35 秒：约 4.7 秒后 0 号是熟牛肉、留在灶台上；8 秒后 1 号已经空了。
    from arrisFarmersDelightScripts.Server.Debug import McdkGrillTest as T
    return T.mcdk_test_grill_start()
    return T.mcdk_test_grill_collect()   # 约 9 秒后
"""
import time

from .. import HandGrill
from ..Helpers.Engine import compFactory, levelId, serverApi
from ..Stove import InitStoveData

WATCH_STEP = 0.1
BEEF = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 1}
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
    return {"case": "grill_start", "ok": True, "pos": pos, "collect_after_seconds": 9}


def mcdk_test_grill_collect():
    """测试函数：停表，检查手放的那块两面烤好留在灶台上、FD 原样那块已经弹走，然后清理。"""
    run = _run.pop("grill", None)
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
