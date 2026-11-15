# -*- coding: utf-8 -*-
"""McdkSelfTest - 游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点；只有显式调用 mcdk_test_* 才会在世界里放方块。
用法（execute_code，服务端）：
    from arrisFarmersDelightScripts.Server.Debug import McdkSelfTest as T
    return T.mcdk_test_run()          # 同步用例的结果；同时启动需要等待的用例
    return T.mcdk_test_collect()      # 约 15 秒后再调：取异步用例的结果，并清理测试方块
测试区域在第一个玩家脚下往 +x / +z 偏 6 格的地方，会把那里的方块换成测试方块，结束时换回空气。
"""
import time

from ..EventRegistry import handlerNames
from ..Helpers.Engine import compFactory, levelId, serverApi, GetBlockEntityData, GetBlockName, ItemPosType
from ..Helpers.Player import ResetPlayerUsedCD
from .. import CookingPot, CuttingBoard, Skillet
from ..BoneMeal import ApplyBoneMeal
from ...Api import LegacyModAttr

_async = {}
_placed = []


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
    names = [name for _, name in handlerNames("ServerItemUseOnEvent")]
    expected = ["OnServerCuttingBoardItemUse", "OnUseItemOnHarvestable", "OnPlaceWildCrop", "OnPlaceItemAsBlock",
                "OnServerItemUse", "OnServerStoveItemUse"]
    return _result("registry_order", names == expected, started, actual=names)


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
    return _result("bone_meal", grew and after in ("arris:cabbages_stage2", "arris:cabbages_stage3"), started, block=after)


def caseCuttingBoard(playerId, base):
    started = time.time()
    x, y, z, dim = base[0] + 2, base[1], base[2], base[3]
    _set((x, y - 1, z), "minecraft:stone", dim)
    _set((x, y, z), "arris:cutting_board", dim)
    args = {"blockName": "arris:cutting_board", "x": x, "y": y, "z": z, "dimensionId": dim, "playerId": playerId, "aux": 0}
    _carry(playerId, "arris:cabbage")
    ResetPlayerUsedCD(playerId)
    CuttingBoard.OnServerCuttingBoardBlockUse(dict(args))
    data = GetBlockEntityData(dim, (x, y, z))
    placed = bool(data and data["cuttingDict"] and data["displayEntityId"])
    _carry(playerId, "arris:iron_knife")
    ResetPlayerUsedCD(playerId)
    CuttingBoard.OnServerCuttingBoardBlockUse(dict(args))
    cut = bool(data and not data["cuttingDict"] and not data["displayEntityId"])
    return _result("cutting_board", placed and cut, started, placed=placed, cut=cut)


def caseSkillet(playerId, base):
    started = time.time()
    x, y, z, dim = base[0] + 4, base[1], base[2], base[3]
    _set((x, y - 1, z), "minecraft:magma", dim)
    _set((x, y, z), "arris:skillet", dim)
    _carry(playerId, "minecraft:beef", 3)
    ResetPlayerUsedCD(playerId)
    Skillet.OnServerSkilletBlockUse({"blockName": "arris:skillet", "x": x, "y": y, "z": z, "dimensionId": dim,
                                     "playerId": playerId, "aux": 0})
    data = GetBlockEntityData(dim, (x, y, z))
    cooking = data["cookingDict"] if data else None
    displays = data["displayEntityList"] if data else None
    ok = bool(cooking and cooking["count"] == 3 and displays and len(displays) == 2 and data["heatEnable"] is True)
    _async["skillet"] = {"pos": (x, y, z), "dim": dim, "started": started}
    return _result("skillet_start", ok, started, count=cooking and cooking["count"], displays=len(displays or []),
                   heat=data["heatEnable"] if data else None)


def caseCookingPot(playerId, base):
    started = time.time()
    x, y, z, dim = base[0], base[1], base[2] + 3, base[3]
    _set((x, y - 1, z), "minecraft:magma", dim)
    _set((x, y, z), "arris:cooking_pot", dim)
    itemComp = compFactory.CreateItem(levelId)
    itemComp.SpawnItemToContainer({"newItemName": "minecraft:red_mushroom", "newAuxValue": 0, "count": 1}, 0, (x, y, z), dim)
    itemComp.SpawnItemToContainer({"newItemName": "minecraft:brown_mushroom", "newAuxValue": 0, "count": 1}, 1, (x, y, z), dim)
    itemComp.SpawnItemToContainer({"newItemName": "minecraft:bowl", "newAuxValue": 0, "count": 4}, CookingPot.VESSEL_SLOT, (x, y, z), dim)
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
    for case in (caseBoneMeal, caseCuttingBoard, caseSkillet, caseCookingPot):
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
        displays = data["displayEntityList"] if data else None
        # 每份 6 秒：还在煎时数量应已减少；3 份全煎完时数据与展示实体都应清空
        finished = data is not None and cooking is None and not displays
        ok = finished or bool(cooking and cooking["count"] < 3 and len(displays or []) <= 2)
        results.append({"case": "skillet_cooked", "ok": ok, "finished": finished, "count": cooking and cooking["count"],
                        "displays": len(displays or []), "seconds": int(time.time() - skillet["started"])})
    pot = _async.pop("cooking_pot", None)
    if pot:
        result = compFactory.CreateItem(levelId).GetContainerItem(pot["pos"], CookingPot.RESULT_SLOT, pot["dim"])
        vessel = compFactory.CreateItem(levelId).GetContainerItem(pot["pos"], CookingPot.VESSEL_SLOT, pot["dim"])
        ok = bool(result and result["newItemName"] == "minecraft:mushroom_stew" and vessel and vessel["count"] == 3)
        results.append({"case": "cooking_pot_served", "ok": ok, "result": result and (result["newItemName"], result["count"]),
                        "bowls_left": vessel and vessel["count"], "seconds": int(time.time() - pot["started"])})
    while _placed:
        pos, dim = _placed.pop()
        compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": "minecraft:air"}, 0, dim)
    return {"ok": bool(results) and all(r["ok"] for r in results), "results": results}
