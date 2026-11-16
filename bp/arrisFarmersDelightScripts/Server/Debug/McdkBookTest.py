# -*- coding: utf-8 -*-
"""McdkBookTest - 站点食谱书"放料"的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；前置包（场景交互 · 前置）没装时跳过。直接驱动前置包服务端的 Manager（与客户端点书同一条校验路径）：
在第一个玩家脚下往 +x 3 / +z 3 放一口厨锅（下面岩浆块）、往 -x 3 / +z 3 放一块砧板（下面石头），背包第 9、10 格放 40 个番茄、
第 11、12 格放 3 个面包和 6 个煎蛋 -> 开锅的站点、书里点番茄酱放 16 份（锅里 32 个番茄、背包少 32 个）、关站；
开砧板的站点、书里点夹蛋三明治放 16 份（面包只有 3 个：做 3 份，板上 3 个夹蛋三明治）、关站。会改玩家背包第 9～12 格。
    from arrisFarmersDelightScripts.Server.Debug import McdkBookTest as T
    return T.mcdk_test_book()
"""
import time

from ..Helpers import PotContainer
from ..Helpers.Engine import compFactory, levelId, serverApi, GetBlockEntityData, ItemPosType
from ..Helpers.Player import IsCreative
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList

SAUCE = "arris:tomato_sauce"
SANDWICH = "arris:egg_sandwich"


def _custom(name, data=None):
    return {"type": "custom", "name": name, "data": data or {}}


def _count(playerId, name):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    return sum(item["count"] for item in items if item and item.get("newItemName") == name)


def _place(pos, dim, block, below):
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": below}, 0, dim)
    blockInfo.SetBlockNew(pos, {"name": block}, 0, dim)


def _clear(pos, dim):
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:air"}, 0, dim)


def mcdk_test_book():
    """测试函数：照书给锅放 16 份番茄酱的料、给砧板摆夹蛋三明治；返回结构化结果。"""
    started = time.time()
    runtime = serverApi.ImportModule("arrisDiegesisScripts.Server.Runtime")
    manager = runtime.getManager() if runtime is not None else None
    players = serverApi.GetPlayerList()
    if manager is None or not players:
        return {"case": "station_book", "ok": True, "skipped": "diegesis not installed or no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    dim = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    potPos, boardPos = (int(x) + 3, int(y), int(z) + 3), (int(x) - 3, int(y), int(z) + 3)
    _place(potPos, dim, "arris:cooking_pot", "minecraft:magma")
    _place(boardPos, dim, "arris:cutting_board", "minecraft:stone")
    compFactory.CreateItem(playerId).SetPlayerAllItems({
        (ItemPosType.INVENTORY, 9): {"newItemName": "arris:tomato", "newAuxValue": 0, "count": 20},
        (ItemPosType.INVENTORY, 10): {"newItemName": "arris:tomato", "newAuxValue": 0, "count": 20},
        (ItemPosType.INVENTORY, 11): {"newItemName": "minecraft:bread", "newAuxValue": 0, "count": 3},
        (ItemPosType.INVENTORY, 12): {"newItemName": "arris:fried_egg", "newAuxValue": 0, "count": 6}})
    sauce = next(index for index, recipe in enumerate(CookingPotRecipeList) if recipe["CookResult"][0] == SAUCE)
    tomatoesBefore = _count(playerId, "arris:tomato")
    potOpened = manager.open(playerId, list(potPos))
    potFilled = manager.action(playerId, list(potPos), _custom("bookFill", {"key": sauce, "sets": 16}))
    inPot = sum(item.get("count", 0) for item in PotContainer.inputs(dim, potPos) if item.get("newItemName") == "arris:tomato")
    tomatoesTaken = tomatoesBefore - _count(playerId, "arris:tomato")
    potClosed = manager.close(playerId, "self test")
    boardOpened = manager.open(playerId, list(boardPos))
    boardFilled = manager.action(playerId, list(boardPos), _custom("bookFill", {"key": "d:" + SANDWICH, "sets": 16}))
    data = GetBlockEntityData(dim, boardPos)
    onBoard = data["dishDone"] if data else None
    boardClosed = manager.close(playerId, "self test")
    _clear(potPos, dim)
    _clear(boardPos, dim)
    result = {"case": "station_book", "pot": {"opened": potOpened, "filled": potFilled, "tomatoesInPot": inPot,
                                              "tomatoesTaken": tomatoesTaken, "closed": potClosed},
              "board": {"opened": boardOpened, "filled": boardFilled, "closed": boardClosed,
                        "onBoard": onBoard and (onBoard.get("newItemName"), onBoard.get("count"))},
              "duration_ms": int((time.time() - started) * 1000)}
    expectTaken = 0 if IsCreative(playerId) else 32         # 创造模式不扣背包
    result["ok"] = bool(potOpened and potFilled and inPot == 32 and tomatoesTaken == expectTaken and boardOpened and boardFilled
                        and result["board"]["onBoard"] == (SANDWICH, 3))
    return result
