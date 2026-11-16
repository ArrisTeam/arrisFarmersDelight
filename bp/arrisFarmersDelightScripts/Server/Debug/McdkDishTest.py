# -*- coding: utf-8 -*-
"""McdkDishTest - 砧板摆盘的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；前置包（场景交互 · 前置）没装时跳过。直接驱动前置包服务端的 Manager（与客户端点击走同一条校验路径）：
在第一个玩家脚下往 +x 3 / -z 2 格放一块砧板（要在站点的 6 格交互距离里），快捷栏 0 号放 3 个面包、1 号放 6 个煎蛋 ->
开站 -> lay 面包打底 -> lay 煎蛋两次（第二层放下就自动做成）-> 板上是 3 个鸡蛋三明治 -> use 拿走 -> 关站；
再按工作台取出鸡蛋三明治派发一次 CraftItemOutputChangeServerEvent，应被取消。会改玩家快捷栏 0、1 号格。
    from arrisFarmersDelightScripts.Server.Debug import McdkDishTest as T
    return T.mcdk_test_dish()
"""
import time

from ..EventRegistry import dispatch
from ..Helpers.Engine import compFactory, levelId, serverApi, GetBlockEntityData, ItemPosType

SANDWICH = "arris:egg_sandwich"


def _custom(name, data=None):
    return {"type": "custom", "name": name, "data": data or {}}


def _count(playerId, name):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    return sum(item["count"] for item in items if item and item.get("newItemName") == name)


def mcdk_test_dish():
    """测试函数：开站摆一份鸡蛋三明治、拿走，再验工作台拦截；返回结构化结果。"""
    started = time.time()
    runtime = serverApi.ImportModule("arrisDiegesisScripts.Server.Runtime")
    manager = runtime.getManager() if runtime is not None else None
    players = serverApi.GetPlayerList()
    if manager is None or not players:
        return {"case": "board_dish", "ok": True, "skipped": "diegesis not installed or no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    pos, dim = (int(x) + 3, int(y), int(z) - 2), compFactory.CreateDimension(playerId).GetEntityDimensionId()
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:stone"}, 0, dim)
    blockInfo.SetBlockNew(pos, {"name": "arris:cutting_board"}, 0, dim)
    compFactory.CreateItem(playerId).SetPlayerAllItems({
        (ItemPosType.INVENTORY, 0): {"newItemName": "minecraft:bread", "newAuxValue": 0, "count": 3},
        (ItemPosType.INVENTORY, 1): {"newItemName": "arris:fried_egg", "newAuxValue": 0, "count": 6}})
    before = _count(playerId, SANDWICH)
    where = list(pos)
    opened = manager.open(playerId, where)
    laid = [manager.action(playerId, where, _custom("lay", {"slot": slot})) for slot in (0, 1, 1)]
    data = GetBlockEntityData(dim, pos)
    onBoard = data["dishDone"] if data else None
    took = manager.action(playerId, where, _custom("use", {"mark": 0}))
    gained = _count(playerId, SANDWICH) - before
    closed = manager.close(playerId, "self test")
    craft = {"playerId": playerId, "itemDict": {"newItemName": SANDWICH, "newAuxValue": 0, "count": 1},
             "screenContainerType": serverApi.GetMinecraftEnum().ContainerType.WORKBENCH, "cancel": False}
    dispatch("CraftItemOutputChangeServerEvent", craft, SANDWICH)
    blockInfo.SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:air"}, 0, dim)
    result = {"case": "board_dish", "opened": opened, "laid": laid,
              "onBoard": onBoard and (onBoard.get("newItemName"), onBoard.get("count")), "took": took, "gained": gained,
              "closed": closed, "craftCancelled": craft["cancel"], "duration_ms": int((time.time() - started) * 1000)}
    result["ok"] = bool(opened and all(laid) and result["onBoard"] == (SANDWICH, 3) and took and gained == 3 and closed
                        and craft["cancel"])
    return result
