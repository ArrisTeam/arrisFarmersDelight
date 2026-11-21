# -*- coding: utf-8 -*-
"""McdkPanTest - 煎锅手工煎制的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；没装沉浸式交互前置包（没联动，Shared/Rules/HandsOnMode）时亲手做菜不启用，这一项跳过。在第一个玩家脚下往 +x 12 / +z 9 格放一口烧着的煎锅、手放 2 块生牛肉，
用计时器替站点等贴锅面熟了就颠一次锅。2 块一面要 6 * sqrt(2) / 3 ≈ 2.8 秒，两面约 5.7 秒：之后锅里应是 2 块熟牛肉。
    from arrisFarmersDelightScripts.Server.Debug import McdkPanTest as T
    return T.mcdk_test_pan_start()       # 放锅、放料
    return T.mcdk_test_pan_collect()     # 约 8 秒后：看锅里，清理方块
"""
import time

from .. import HandFrying
from ..Helpers.Engine import compFactory, levelId, serverApi
from ...Shared.Rules import HandsOnMode

WATCH_STEP = 0.1
_run = {}


def _watch():
    run = _run.get("pan")
    if not run:
        return
    frying = HandFrying.handOf(run["dim"], run["pos"]).frying
    if frying.down >= 1.0 and frying.up < 1.0 and HandFrying.toss(HandFrying.handOf(run["dim"], run["pos"]), run["player"],
                                                                   time.time(), {"newItemName": "minecraft:beef"}):
        run["tosses"].append(round(time.time() - run["started"], 1))


def mcdk_test_pan_start():
    """测试函数：放煎锅、手放 2 块生牛肉，开始替厨师看着颠锅。"""
    if not HandsOnMode.linked():               # 没装前置包：亲手做菜不启用，这一项没有东西可测
        return {"case": "pan_fried_by_hand", "ok": True, "skipped": "hands-on delight is off: the prerequisite pack is not installed (or too old)"}
    players = serverApi.GetPlayerList()
    if not players or _run.get("pan"):
        return {"ok": False, "error": "no player" if not players else "already running"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    pos, dim = (int(x) + 12, int(y), int(z) + 9), compFactory.CreateDimension(playerId).GetEntityDimensionId()
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:magma"}, 0, dim)
    blockInfo.SetBlockNew(pos, {"name": "arris:skillet"}, 0, dim)
    data = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dim, pos)
    data["heatEnable"] = True
    data["cookTimer"] = 7
    data["cookingDict"] = {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}
    HandFrying.forget(dim, pos)
    HandFrying.handOf(dim, pos).frying.layByHand()
    timer = compFactory.CreateGame(levelId).AddRepeatedTimer(WATCH_STEP, _watch)
    _run["pan"] = {"pos": pos, "dim": dim, "player": playerId, "timer": timer, "started": time.time(), "tosses": []}
    return {"case": "pan_fry_start", "ok": True, "pos": pos, "collect_after_seconds": 8}


def mcdk_test_pan_collect():
    """测试函数：停表，检查两面都煎好、留在锅里，然后清理。"""
    run = _run.pop("pan", None)
    if not run and not HandsOnMode.linked():
        return {"case": "pan_fried_by_hand", "ok": True, "skipped": "hands-on delight is off: the prerequisite pack is not installed (or too old)"}
    if not run:
        return {"ok": False, "error": "not started"}
    compFactory.CreateGame(levelId).CancelTimer(run["timer"])
    pos, dim = run["pos"], run["dim"]
    data = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dim, pos)
    inPan = data["cookingDict"] if data else None
    hand = HandFrying.handOf(dim, pos)
    result = {"case": "pan_fried_by_hand", "in_pan": inPan and (inPan.get("newItemName"), inPan.get("count")),
              "tosses": run["tosses"], "fried": hand.fried, "seconds": round(time.time() - run["started"], 1)}
    result["ok"] = result["in_pan"] == ("minecraft:cooked_beef", 2) and len(run["tosses"]) == 1 and hand.fried == 1
    if data:
        data["cookingDict"] = None                   # 不然拆锅时煎好的牛肉会掉出来
    HandFrying.forget(dim, pos)
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:air"}, 0, dim)
    return result
