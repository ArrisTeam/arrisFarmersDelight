# -*- coding: utf-8 -*-
"""McdkDishTest - 砧板摆盘的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；前置包（沉浸式交互前置）没装时跳过。直接驱动前置包服务端的 Manager（与客户端点击走同一条校验路径）：
在第一个玩家脚下往 +x 3 / -z 2 格放一块砧板（要在站点的 6 格交互距离里），往快捷栏 0、1 号放料 -> 开站 -> 一层层 place {from: 格号}
（Shift 点托盘的那条路）-> 最后一层放下就自动做成 -> 板上（cuttingDict，和 HoD 一样成品躺在板的槽里）是成品 -> take 拿走 -> 关站。
会改玩家快捷栏 0、1 号格。
    from arrisFarmersDelightScripts.Server.Debug import McdkDishTest as T
    return T.mcdk_test_dish()          面包 3 + 煎蛋 6 -> 3 个夹蛋三明治
    return T.mcdk_test_dish_dough()    小麦 5 + 水桶 1 -> 5 个面团，水桶原样还给厨师（HoD：水桶每轮都放回去，不限份数）
工作台拦不拦砧板菜要读真的合成格，见 McdkCraftTest 的 sandwich / dough / slices 用例。
"""
import time

from ..Helpers.Engine import compFactory, levelId, serverApi, GetBlockEntityData, ItemPosType

SANDWICH = "arris:egg_sandwich"


def _custom(name, data=None):
    return {"type": "custom", "name": name, "data": data or {}}


def _count(playerId, name):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    return sum(item["count"] for item in items if item and item.get("newItemName") == name)


def _stack(name, count):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def _run(case, hotbar, lays, dish, made, back=None):
    """hotbar：快捷栏 0、1 号放的 (物品名, 个数)；lays：依次 lay 的格子；dish / made：板上该是什么、几个；
    back：做成后还给厨师的 (物品名, 个数)——放上砧板时扣掉了（HoD 创造模式也扣），还回来正好和放之前一样多。"""
    started = time.time()
    runtime = serverApi.ImportModule("arrisDiegesisScripts.Server.Runtime")
    manager = runtime.getManager() if runtime is not None else None
    players = serverApi.GetPlayerList()
    if manager is None or not players:
        return {"case": case, "ok": True, "skipped": "diegesis not installed or no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    pos, dim = (int(x) + 3, int(y), int(z) - 2), compFactory.CreateDimension(playerId).GetEntityDimensionId()
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:stone"}, 0, dim)
    blockInfo.SetBlockNew(pos, {"name": "arris:cutting_board"}, 0, dim)
    compFactory.CreateItem(playerId).SetPlayerAllItems(dict(
        ((ItemPosType.INVENTORY, slot), _stack(name, count)) for slot, (name, count) in enumerate(hotbar)))
    before = _count(playerId, dish)
    backBefore = _count(playerId, back[0]) if back else 0
    where = list(pos)
    opened = manager.open(playerId, where)
    laid = [manager.action(playerId, where, _custom("place", {"from": slot})) for slot in lays]
    data = GetBlockEntityData(dim, pos)
    onBoard = data["cuttingDict"] if data else None
    returned = _count(playerId, back[0]) - backBefore if back else 0
    took = manager.action(playerId, where, _custom("take"))
    gained = _count(playerId, dish) - before
    closed = manager.close(playerId, "self test")
    blockInfo.SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:air"}, 0, dim)
    result = {"case": case, "opened": opened, "laid": laid,
              "onBoard": onBoard and (onBoard.get("newItemName"), onBoard.get("count")), "took": took, "gained": gained,
              "returned": returned, "closed": closed, "duration_ms": int((time.time() - started) * 1000)}
    result["ok"] = bool(opened and all(laid) and result["onBoard"] == (dish, made) and took and gained == made and closed
                        and (not back or returned == 0))
    return result


def mcdk_test_dish():
    """测试函数：开站摆一份夹蛋三明治、拿走；返回结构化结果。"""
    return _run("board_dish", [("minecraft:bread", 3), ("arris:fried_egg", 6)], (0, 1, 1), SANDWICH, 3)


def mcdk_test_dish_dough():
    """测试函数：5 个小麦 + 1 桶水揉成 5 个面团，水桶原样还回来；返回结构化结果。"""
    return _run("board_dough", [("minecraft:wheat", 5), ("minecraft:water_bucket", 1)], (0, 1), "arris:wheat_dough", 5,
                back=("minecraft:water_bucket", 1))
