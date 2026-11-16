# -*- coding: utf-8 -*-
"""McdkPotTest - 厨锅手工烹饪的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。在第一个玩家脚下往 +x 9 / +z 9 格（避开 McdkSelfTest 的方块）放一口烧着的厨锅、两格各 2 个番茄（番茄酱，一批 2 份），
假装这位玩家做过 40 份番茄酱（开满 3 颗星），用计时器替站点每 0.05 秒 attend 并按宽圈稳速搅一下（一秒一圈）。
2 份的一批要 10 / (1.5 / sqrt(2)) ≈ 9.4 秒，星星 4 秒涨满：出锅时 3 星，2 套料出 3 份（多送 1 份）。
    from arrisFarmersDelightScripts.Server.Debug import McdkPotTest as T
    return T.mcdk_test_pot_start()       # 放锅、开始搅
    return T.mcdk_test_pot_collect()     # 约 12 秒后：停手，取结果，清理方块、还原"做过几份"
"""
import math
import time

from .. import HandCooking
from ..Helpers import PotContainer
from ..Helpers.Engine import compFactory, levelId, serverApi
from ...Shared.Rules.HandsOn import PotCooking

DISH = "arris:tomato_sauce"
STIR_STEP = 0.05
_run = {}


def _stirOnce():
    run = _run.get("pot")
    if not run:
        return
    now = time.time()
    hand = HandCooking.handOf(run["dim"], run["pos"])
    hand.clock.attend(now)
    if hand.served > run["served"]:
        if run["servedAfter"] is None:
            run["servedAfter"] = now - run["started"]
        return
    angle = 2.0 * math.pi * (now - run["started"])
    if HandCooking.stir(hand, run["player"], now, 0.9 * math.cos(angle), 0.9 * math.sin(angle), now - run["started"]):
        run["stirs"] += 1
    run["modes"].add(hand.mode)
    run["peak"] = max(run["peak"], hand.clock.skill.stars(now))


def mcdk_test_pot_start():
    """测试函数：放锅、放料、开始替站点搅拌。"""
    players = serverApi.GetPlayerList()
    if not players or _run.get("pot"):
        return {"ok": False, "error": "no player" if not players else "already running"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    pos, dim = (int(x) + 9, int(y), int(z) + 9), compFactory.CreateDimension(playerId).GetEntityDimensionId()
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:magma"}, 0, dim)
    blockInfo.SetBlockNew(pos, {"name": "arris:cooking_pot"}, 0, dim)
    itemComp = compFactory.CreateItem(levelId)
    for slot in (0, 1):
        itemComp.SpawnItemToContainer({"newItemName": "arris:tomato", "newAuxValue": 0, "count": 2}, slot, pos, dim)
    HandCooking.forget(dim, pos)
    made = HandCooking.madeOf(playerId, DISH)
    HandCooking._made[playerId][DISH] = 40          # 只改内存里的缓存，collect 时还原；不写存档
    hand = HandCooking.handOf(dim, pos)
    timer = compFactory.CreateGame(levelId).AddRepeatedTimer(STIR_STEP, _stirOnce)
    _run["pot"] = {"pos": pos, "dim": dim, "player": playerId, "made": made, "timer": timer, "started": time.time(),
                   "served": hand.served, "stirs": 0, "modes": set(), "peak": 0.0, "servedAfter": None}
    return {"case": "pot_stir_start", "ok": True, "pos": pos, "collect_after_seconds": 12}


def mcdk_test_pot_collect():
    """测试函数：停止搅拌，检查这一批出了几份、几星，然后清理。"""
    run = _run.pop("pot", None)
    if not run:
        return {"ok": False, "error": "not started"}
    compFactory.CreateGame(levelId).CancelTimer(run["timer"])
    pos, dim = run["pos"], run["dim"]
    data = compFactory.CreateBlockEntityData(levelId).GetBlockEntityData(dim, pos)
    ready = PotContainer.preview(data) if data else {}
    left = [PotContainer.inputs(dim, pos)[slot].get("count", 0) for slot in (0, 1)]
    hand = HandCooking.handOf(dim, pos)
    result = {"case": "pot_stirred_batch", "meals": ready.get("count", 0) if ready.get("newItemName") == DISH else 0,
              "inputs_left": left, "grade": hand.clock.grade, "bonus": hand.clock.bonus, "stirs": run["stirs"],
              "peak_stars": round(run["peak"], 2), "served_after": run["servedAfter"] and round(run["servedAfter"], 1),
              "stirred_mode_seen": PotCooking.STIRRED in run["modes"]}
    result["ok"] = result["meals"] == 3 and left == [0, 0] and hand.clock.grade == 3 and hand.clock.bonus == 1
    HandCooking._made[run["player"]][DISH] = run["made"]
    HandCooking.forget(dim, pos)
    if data:
        PotContainer.setPreview(data, None)          # 不然拆锅时煮好的番茄酱会掉出来
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:air"}, 0, dim)
    return result
