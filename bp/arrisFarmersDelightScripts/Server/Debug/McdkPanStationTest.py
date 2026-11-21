# -*- coding: utf-8 -*-
"""McdkPanStationTest - 煎锅站点（JE 对齐后）的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；前置包（沉浸式交互前置）没装时跳过。直接驱动前置包服务端的 Manager（与客户端点击走同一条校验路径），
走真引擎的方块实体、背包和广播：在第一个玩家脚下往 +x 3 / +z 2 放一口烧着的煎锅（下面岩浆块），背包第 9、10 格放 5 块生牛肉和 4 个生鸡肉：
开站 -> 光标栈拿起牛肉（PICKUP）-> place 右键放一个、place 左键放余下的 -> 放猪排被拒（光标栈上的鸡肉不变）-> 托盘 Shift 点鸡肉被拒（锅里是牛肉）
-> 颠锅（toss，第二下在 0.4 秒内被拒）-> take（5 块牛肉回背包）-> 再放牛肉、看方块实体里存了 panFrying -> 关站、清理。会改玩家背包第 9、10 格。
    from arrisFarmersDelightScripts.Server.Debug import McdkPanStationTest as T
    return T.mcdk_test_pan_station()
"""
import time

from .. import HandFrying, PanLook
from ..Helpers.Engine import compFactory, levelId, serverApi, GetBlockEntityData, ItemPosType

BEEF, CHICKEN = "minecraft:beef", "minecraft:chicken"


def _custom(name, data=None):
    return {"type": "custom", "name": name, "data": data or {}}


def _click(kind, index=0, button=0, click="PICKUP", group=None):
    target = {"kind": kind, "index": index}
    if group:
        target["group"] = group
    return {"type": "click", "target": target, "button": button, "click": click}


def _count(playerId, name):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    return sum(item["count"] for item in items if item and item.get("newItemName") == name)


def _slotOf(playerId, name):
    """背包里第一格装着这种东西的格号（take 放回背包的位置不一定是原来的格），没有返回 -1。"""
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    return next((index for index, item in enumerate(items) if item and item.get("newItemName") == name), -1)


def _inPan(dim, pos):
    data = GetBlockEntityData(dim, pos)
    item = data["cookingDict"] if data else None
    return (item.get("newItemName"), item.get("count")) if item else None


def mcdk_test_pan_station():
    """测试函数：放、拒、颠、取、存档；返回结构化结果。"""
    started = time.time()
    runtime = serverApi.ImportModule("arrisDiegesisScripts.Server.Runtime")
    manager = runtime.getManager() if runtime is not None else None
    players = serverApi.GetPlayerList()
    if manager is None or not players:
        return {"case": "pan_station", "ok": True, "skipped": "diegesis not installed or no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    dim = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    pos = (int(x) + 3, int(y), int(z) + 2)
    blockInfo = compFactory.CreateBlockInfo(levelId)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:magma"}, 0, dim)
    blockInfo.SetBlockNew(pos, {"name": "arris:skillet"}, 0, dim)
    data = GetBlockEntityData(dim, pos)
    if not data:
        return {"case": "pan_station", "ok": False, "error": "no block entity for the skillet"}
    data["heatEnable"] = True
    data["cookingDict"] = None
    HandFrying.forget(dim, pos)
    PanLook.enable(True)
    compFactory.CreateItem(playerId).SetPlayerAllItems({
        (ItemPosType.INVENTORY, 9): {"newItemName": BEEF, "newAuxValue": 0, "count": 5},
        (ItemPosType.INVENTORY, 10): {"newItemName": CHICKEN, "newAuxValue": 0, "count": 4}})
    checks = {}
    checks["opened"] = bool(manager.open(playerId, list(pos)))
    if not checks["opened"]:
        return {"case": "pan_station", "checks": checks, "ok": False, "error": "station did not open (too far? prerequisite too old?)"}
    checks["picked_up"] = bool(manager.action(playerId, list(pos), _click("inventory", 9)))
    manager.action(playerId, list(pos), _custom("place", {"one": True}))
    checks["one_in"] = _inPan(dim, pos) == (BEEF, 1)
    manager.action(playerId, list(pos), _custom("place", {"one": False}))
    checks["rest_in"] = _inPan(dim, pos) == (BEEF, 5)
    hand = HandFrying.peek(dim, pos)
    checks["by_hand"] = bool(hand and hand.frying.byHand)
    checks["saved"] = bool(data["panFrying"] and data["panFrying"].get("byHand"))
    checks["tray_shift_refused"] = not manager.action(playerId, list(pos), _click("inventory", 10, click="QUICK_MOVE")) and _inPan(dim, pos) == (BEEF, 5)
    checks["library_cannot_take"] = not manager.action(playerId, list(pos), _click("station", 0, group="pan"))
    tossed = bool(manager.action(playerId, list(pos), _custom("toss", {"strength": 0.8}))) and bool(hand and hand.tosses == 1)
    manager.action(playerId, list(pos), _custom("toss", {"strength": 0.8}))
    checks["tossed_once"] = tossed and hand.tosses == 1
    before = _count(playerId, BEEF)
    manager.action(playerId, list(pos), _custom("take"))
    checks["taken"] = _inPan(dim, pos) is None and _count(playerId, BEEF) == before + 5 and not hand.frying.byHand
    manager.action(playerId, list(pos), _click("inventory", max(0, _slotOf(playerId, BEEF))))
    manager.action(playerId, list(pos), _custom("place", {"one": False}))
    checks["placed_again"] = _inPan(dim, pos) == (BEEF, 5)
    saved = data["panFrying"]
    checks["save_shape"] = bool(saved) and sorted(saved) == ["batch", "byHand", "down", "up"]
    checks["closed"] = bool(manager.close(playerId, "self test"))
    data["cookingDict"] = None                      # 不然拆锅时牛肉会掉出来
    data["panFrying"] = None
    HandFrying.forget(dim, pos)
    blockInfo.SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    blockInfo.SetBlockNew((pos[0], pos[1] - 1, pos[2]), {"name": "minecraft:air"}, 0, dim)
    return {"case": "pan_station", "checks": checks, "ok": all(checks.values()), "duration_ms": int((time.time() - started) * 1000)}
