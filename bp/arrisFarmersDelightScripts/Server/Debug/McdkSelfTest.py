# -*- coding: utf-8 -*-
"""McdkSelfTest - 游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；只有显式调用 mcdk_test_* 才会在世界里放方块。
用法（execute_code，服务端）：
    from arrisFarmersDelightScripts.Server.Debug import McdkSelfTest as T
    return T.mcdk_test_run()          # 同步用例的结果；同时启动需要等待的用例
    return T.mcdk_test_collect()      # 约 15 秒后再调：取异步用例的结果，并清理测试方块
测试区域在第一个玩家脚下往 +x / +z 偏 6 格的地方，会把那里的方块换成测试方块，结束时换回空气。
"""
import math
import time

from ..EventRegistry import handlerNames
from ..Helpers.Engine import compFactory, levelId, serverApi, GetBlockEntityData, GetBlockName, ItemPosType
from ..Helpers import BlockItems, PotContainer
from ..Helpers.Player import ResetPlayerUsedCD
from .. import CuttingBoard, Skillet
from ..BoneMeal import ApplyBoneMeal
from ...Api import LegacyModAttr

_async = {}
_placed = []


# ServerItemUseOnEvent 的处理函数按执行先后（ModServer.py 模块说明里的优先级表）；加了、删了处理函数要跟着改，
# tests/test_selftest_registry.py 对着源码里登记的函数名核对这张表有没有漏
ITEM_USE_ORDER = ["OnUseItemOnPlacedSkillet", "OnServerCuttingBoardItemUse", "OnUseItemOnHarvestable", "OnUseItemOnComposter",
                  "OnPlaceWildCrop", "OnUseSkilletItem",
                  "OnPlaceItemAsBlock", "OnPlaceRopeOnRope", "OnPlaceFullMat", "OnPlaceHalfMat", "OnServerItemUse", "OnStoveFire",
                  "OnServerStoveItemUse"]


def _player():
    players = serverApi.GetPlayerList()
    return players[0] if players else None


def _base(playerId):
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    return int(x) + 6, int(y), int(z) + 6, compFactory.CreateDimension(playerId).GetEntityDimensionId()


def _set(pos, name, dimensionId):
    compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": name}, 0, dimensionId)
    _placed.append((pos, dimensionId))


def _carry(playerId, name, count=1, aux=0):
    compFactory.CreateItem(playerId).SetEntityItem(ItemPosType.CARRIED, {"newItemName": name, "newAuxValue": aux, "count": count}, 0)


def _result(case, ok, started, **extra):
    data = {"case": case, "ok": bool(ok), "duration_ms": int((time.time() - started) * 1000)}
    data.update(extra)
    return data


def caseRegistryOrder():
    started = time.time()
    # 只看本包登记的（调试时临时挂的探针不算）；顺序就是 ModServer.py 模块说明里的优先级表
    names = [name for module, name in handlerNames("ServerItemUseOnEvent") if module.startswith(__name__.split(".")[0] + ".")]
    return _result("registry_order", names == ITEM_USE_ORDER, started, actual=names)


def caseLegacyModAttr():
    started = time.time()
    modAttr = compFactory.CreateModAttr("arris")
    ok = (modAttr.GetAttr("ArrisFarmersDelightInterface") is LegacyModAttr.ArrisFarmersDelightInterface
          and modAttr.GetAttr("ArrisFarmersDelightObtain") is LegacyModAttr.ArrisFarmersDelightObtain
          and modAttr.GetAttr("ArrisAddCookingPotRecipe") is LegacyModAttr.AddCookingPotRecipe)
    return _result("legacy_modattr", ok, started)


def caseBoneMeal(playerId, base):
    started = time.time()
    x, y, z, dim = base
    _set((x, y - 1, z), "minecraft:farmland", dim)
    _set((x, y, z), "arris:cabbages_stage0", dim)
    item = {"newItemName": "minecraft:bone_meal", "newAuxValue": 0, "count": 2}
    grew = ApplyBoneMeal(playerId, item, "arris:cabbages_stage0", (x, y, z), dim)
    after = GetBlockName((x, y, z), dim)
    # JE 的作物骨粉一次长 2~5 个年龄（CropBlock.getBonemealAgeIncrease = nextInt(2, 5)）
    ok = grew and after in ("arris:cabbages_stage2", "arris:cabbages_stage3", "arris:cabbages_stage4", "arris:cabbages_stage5")
    return _result("bone_meal", ok, started, block=after)


def _shownItem(payloads, pos):
    """最后一次广播给这个方块的物品（客户端据此渲染）；没有广播过返回 False。"""
    found = [p for p in payloads if tuple(p["pos"]) == tuple(pos)]
    return found[-1]["items"].get("0") if found else False


def caseCuttingBoard(playerId, base):
    started = time.time()
    x, y, z, dim = base[0] + 2, base[1], base[2], base[3]
    _set((x, y - 1, z), "minecraft:stone", dim)
    _set((x, y, z), "arris:cutting_board", dim)
    args = {"blockName": "arris:cutting_board", "x": x, "y": y, "z": z, "dimensionId": dim, "playerId": playerId, "aux": 0}
    _carry(playerId, "arris:cabbage")
    ResetPlayerUsedCD(playerId)
    BlockItems.startRecording()
    CuttingBoard.OnServerCuttingBoardBlockUse(dict(args))
    data = GetBlockEntityData(dim, (x, y, z))
    shown = _shownItem(BlockItems.stopRecording(), (x, y, z))
    placed = bool(data and data["cuttingDict"] and shown and shown.get("newItemName") == "arris:cabbage")
    _carry(playerId, "arris:iron_knife")
    ResetPlayerUsedCD(playerId)
    BlockItems.startRecording()
    CuttingBoard.OnServerCuttingBoardBlockUse(dict(args))
    cut = bool(data and not data["cuttingDict"] and _shownItem(BlockItems.stopRecording(), (x, y, z)) == {})
    return _result("cutting_board", placed and cut, started, placed=placed, cut=cut)


def caseSkillet(playerId, base):
    started = time.time()
    x, y, z, dim = base[0] + 4, base[1], base[2], base[3]
    _set((x, y - 1, z), "minecraft:magma", dim)
    _set((x, y, z), "arris:skillet", dim)
    _carry(playerId, "minecraft:beef", 3)
    ResetPlayerUsedCD(playerId)
    BlockItems.startRecording()
    Skillet.OnServerSkilletBlockUse({"blockName": "arris:skillet", "x": x, "y": y, "z": z, "dimensionId": dim,
                                     "playerId": playerId, "aux": 0})
    shown = _shownItem(BlockItems.stopRecording(), (x, y, z))
    data = GetBlockEntityData(dim, (x, y, z))
    cooking = data["cookingDict"] if data else None
    ok = bool(cooking and cooking["count"] == 3 and shown and shown.get("count") == 3 and data["heatEnable"] is True)
    _async["skillet"] = {"pos": (x, y, z), "dim": dim, "started": started}
    return _result("skillet_start", ok, started, count=cooking and cooking["count"], shown=shown,
                   heat=data["heatEnable"] if data else None)


def _inventoryCount(playerId, itemName):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, False) or []
    return sum(item["count"] for item in items if item and item.get("newItemName") == itemName)


def _custom(name, data=None):
    return {"type": "custom", "name": name, "data": data or {}}


def caseCuttingBoardStation(playerId, base):
    """沉浸式交互前置在场时：开站 -> 把背包里的 3 块生牛肉整叠放上去（place，from 是背包格）-> 铁刀在背包里（选中的快捷栏格）切 1 刀 ->
    6 块碎牛肉进背包、板清空 -> 关站。直接驱动前置包服务端的 Manager（与客户端点击走同一条校验路径），前置没装则跳过。"""
    started = time.time()
    runtime = serverApi.ImportModule("arrisDiegesisScripts.Server.Runtime")
    manager = runtime.getManager() if runtime is not None else None
    if manager is None:
        return _result("cutting_board_station", True, started, skipped="diegesis not installed")
    fx, fy, fz = compFactory.CreatePos(playerId).GetFootPos()
    x, y, z, dim = int(math.floor(fx)) + 2, int(math.floor(fy)), int(math.floor(fz)), base[3]
    _set((x, y - 1, z), "minecraft:stone", dim)
    _set((x, y, z), "arris:cutting_board", dim)
    pos = [x, y, z]
    before = _inventoryCount(playerId, "arris:minced_beef")
    _carry(playerId, "minecraft:beef", 3)
    opened = manager.open(playerId, pos)
    placed = manager.action(playerId, pos, _custom("place", {"from": compFactory.CreateItem(playerId).GetSelectSlotId()}))
    data = GetBlockEntityData(dim, (x, y, z))
    onBoard = data["cuttingDict"]["count"] if data and data["cuttingDict"] else 0
    _carry(playerId, "arris:iron_knife")
    cut = manager.action(playerId, pos, _custom("chop", {"mark": 0, "at": 8.0}))
    gained = _inventoryCount(playerId, "arris:minced_beef") - before
    cleared = bool(data) and not data["cuttingDict"]
    closed = manager.close(playerId, "self test")
    ok = opened and placed and onBoard == 3 and cut and gained == 6 and cleared and closed
    return _result("cutting_board_station", ok, started, opened=opened, placed=placed, onBoard=onBoard, cut=cut,
                   gained=gained, cleared=cleared, closed=closed)


def caseCookingPot(playerId, base):
    started = time.time()
    x, y, z, dim = base[0], base[1], base[2] + 3, base[3]
    _set((x, y - 1, z), "minecraft:magma", dim)
    _set((x, y, z), "arris:cooking_pot", dim)
    itemComp = compFactory.CreateItem(levelId)
    itemComp.SpawnItemToContainer({"newItemName": "minecraft:red_mushroom", "newAuxValue": 0, "count": 1}, 0, (x, y, z), dim)
    itemComp.SpawnItemToContainer({"newItemName": "minecraft:brown_mushroom", "newAuxValue": 0, "count": 1}, 1, (x, y, z), dim)
    itemComp.SpawnItemToContainer({"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 4}, PotContainer.VESSEL_SLOT, (x, y, z), dim)
    data = GetBlockEntityData(dim, (x, y, z))
    _async["cooking_pot"] = {"pos": (x, y, z), "dim": dim, "started": started}
    return _result("cooking_pot_start", bool(data and data["heatEnable"] is True), started,
                   heat=data["heatEnable"] if data else None)


def mcdk_test_run():
    """测试函数：跑同步用例并启动异步用例，返回结构化结果。"""
    playerId = _player()
    if playerId is None:
        return {"ok": False, "error": "no player"}
    base = _base(playerId)
    results = [caseRegistryOrder(), caseLegacyModAttr()]
    for case in (caseBoneMeal, caseCuttingBoard, caseCuttingBoardStation, caseSkillet, caseCookingPot):
        try:
            results.append(case(playerId, base))
        except Exception as e:  # noqa: BLE001 - 测试边界：把异常作为失败结果返回
            results.append({"case": case.__name__, "ok": False, "error": repr(e)})
    compFactory.CreateItem(playerId).SetEntityItem(ItemPosType.CARRIED, None, 0)
    return {"ok": all(r.get("ok") for r in results), "results": results, "collect_after_seconds": 15}


def mcdk_test_collect():
    """测试函数：取异步用例的结果（煎锅煎出 1 份、厨锅煮好并装碗），然后清理测试方块。"""
    results = []
    skillet = _async.pop("skillet", None)
    if skillet:
        data = GetBlockEntityData(skillet["dim"], skillet["pos"])
        cooking = data["cookingDict"] if data else None
        # 每份 6 秒：还在煎时数量应已减少；3 份全煎完时数据应清空
        finished = data is not None and cooking is None
        ok = finished or bool(cooking and cooking["count"] < 3)
        results.append({"case": "skillet_cooked", "ok": ok, "finished": finished, "count": cooking and cooking["count"],
                        "seconds": int(time.time() - skillet["started"])})
    pot = _async.pop("cooking_pot", None)
    if pot:
        result = compFactory.CreateItem(levelId).GetContainerItem(pot["pos"], PotContainer.RESULT_SLOT, pot["dim"])
        vessel = compFactory.CreateItem(levelId).GetContainerItem(pot["pos"], PotContainer.VESSEL_SLOT, pot["dim"])
        ok = bool(result and result["newItemName"] == "minecraft:mushroom_stew" and vessel and vessel["count"] == 3)
        results.append({"case": "cooking_pot_served", "ok": ok, "result": result and (result["newItemName"], result["count"]),
                        "bowls_left": vessel and vessel["count"], "seconds": int(time.time() - pot["started"])})
    while _placed:
        pos, dim = _placed.pop()
        compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    return {"ok": bool(results) and all(r["ok"] for r in results), "results": results}
