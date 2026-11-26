# -*- coding: utf-8 -*-
"""McdkAdvTest - JE 的 21 条进度接成就系统（Compat/Advancements）的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。要带着成就系统（arrisAdvancements）的包跑，分两步（"拥有某物品"走真的背包事件，要等它到）：
    from arrisFarmersDelightScripts.Server.Debug import McdkAdvTest as T
    T.mcdk_test_adv_start()     # 接上没有、登记了几个节点；给第一个玩家逐条触发能用脚本触发的条件，真给几件物品
    # 等约 2 秒
    T.mcdk_test_adv_collect()   # 每条的 isDone / getProgress；收回给的物品；把这位玩家的 21 条进度 revoke 掉
触发的路：玩法模块报的事经 Server/Helpers/Deeds（和真的切菜、煎、放、摘同一个入口）；引擎事件直接调 AdvBridge 的处理函数
（放方块、吃、得到效果；真放、真吃要手动试）；烂番茄打中袭击者直接推进（真扔要手动试）；根节点和背包补扫调玩家进度装好时的那个回调；
"拥有某物品"真给物品（SpawnItemToPlayerInv），走 InventoryItemChangedServerEvent 的动态监听。
成就系统和 Compat 的模块都是运行时 ImportModule 取的（Server 不许静态导入 Compat）。revoke 之前的进度在结果的 before 里。
"""
import time

from ..Helpers import Deeds
from ..Helpers.Engine import compFactory, levelId, serverApi
from ...Shared.Data import Advancements as Data

API_MODULE = "dolorAdvancementsScripts.Api.Server"
BRIDGE_MODULE = "arrisFarmersDelightScripts.Compat.Advancements.AdvBridge"
TRIGGERS_MODULE = "arrisFarmersDelightScripts.Compat.Advancements.AdvTriggers"
GIVEN = ("arris:flint_knife", "arris:straw", "arris:ham", "arris:rich_soil", "arris:netherite_knife", "arris:cabbage_seeds",
         "arris:brown_mushroom_colony")
_state = {"player": None, "api": None, "before": {}, "steps": [], "started": 0.0}


def _ids():
    return [node["id"] for node in Data.NODES]


def _progress(api, playerId):
    return dict((nodeId, (api.isDone(playerId, nodeId), api.getProgress(playerId, nodeId))) for nodeId in _ids())


def _deeds(playerId):
    for deed, detail in ((Deeds.CUT_ON_BOARD, "arris:cabbage"), (Deeds.SKILLET_COOKED, "minecraft:beef"),
                         (Deeds.PLACED_BLOCK, "arris:skillet"), (Deeds.PLACED_BLOCK, "arris:rice_stage0"),
                         (Deeds.PLACED_BLOCK, "arris:brown_mushroom_colony"), (Deeds.HARVESTED, "arris:tomatoes_vine_stage3")):
        Deeds.done(playerId, deed, detail)
        _state["steps"].append(("deed", deed, detail))


def _engineEvents(bridge, triggers, playerId):
    for name in ("minecraft:campfire", "arris:cooking_pot", "arris:organic_compost_stage0", "arris:roast_chicken_block_stage0", "minecraft:wheat"):
        bridge.onBlockPlaced({"entityId": playerId, "fullName": name})
        _state["steps"].append(("placed", name))
    bridge.onEaten({"playerId": playerId, "itemDict": {"newItemName": "arris:cooked_rice", "count": 1}})
    bridge.onEffect({"entityId": playerId, "effectName": "arris:nourishment"})
    triggers.fire(bridge.api(), playerId, "hit", "minecraft:pillager")
    bridge.onPlayerReady({"playerId": playerId, "progress": {}})
    _state["steps"].extend([("eaten", "arris:cooked_rice"), ("effect", "arris:nourishment"), ("hit", "minecraft:pillager"), ("ready",)])


def mcdk_test_adv_start():
    """接上没有、登记了几个节点；逐条触发；约 2 秒后调 mcdk_test_adv_collect()。"""
    players = serverApi.GetPlayerList()
    if not players:
        return {"case": "advancements", "ok": False, "error": "no player"}
    api, bridge = serverApi.ImportModule(API_MODULE), serverApi.ImportModule(BRIDGE_MODULE)
    if api is None:
        return {"case": "advancements", "ok": False, "error": "没装成就系统（%s 导不进来）" % API_MODULE}
    playerId = players[0]
    registered = sorted(nodeId for nodeId in api.getAllNodeIds() if nodeId.startswith(Data.NAMESPACE))
    attached = bridge is not None and bridge.api() is api
    _state.update(player=playerId, api=api, before=_progress(api, playerId), steps=[], started=time.time())
    result = {"case": "advancements", "attached": attached, "registered": len(registered),
              "missing": sorted(set(_ids()) - set(registered)), "root": api.getNodeData(Data.NAMESPACE + "root")}
    if not attached:
        result["ok"] = False
        return result
    _deeds(playerId)
    _engineEvents(bridge, serverApi.ImportModule(TRIGGERS_MODULE), playerId)
    itemComp = compFactory.CreateItem(playerId)
    result["given"] = dict((name, itemComp.SpawnItemToPlayerInv({"itemName": name, "count": 1}, playerId)) for name in GIVEN)
    return result


def mcdk_test_adv_collect():
    """每条进度现在的 (isDone, getProgress)；收回给的物品；revoke 这位玩家的 21 条进度。"""
    api, playerId = _state["api"], _state["player"]
    if api is None or playerId is None:
        return {"case": "advancements", "ok": False, "error": "先调 mcdk_test_adv_start()"}
    after = _progress(api, playerId)
    command = compFactory.CreateCommand(levelId)
    cleared = dict((name, command.SetCommand("/clear @s %s 0 1" % name, playerId)) for name in GIVEN)
    revoked = dict((nodeId, api.revoke(playerId, nodeId)) for nodeId in _ids())
    expected = ("root", "craft_knife", "harvest_straw", "place_organic_compost", "get_rich_soil", "get_ham", "use_cutting_board",
                "obtain_netherite_knife", "get_fd_seed", "get_mushroom_colony", "plant_rice", "harvest_ropelogged_tomato",
                "hit_raider_with_rotten_tomato", "place_campfire", "use_skillet", "place_skillet", "place_cooking_pot",
                "eat_nourishing_food", "place_feast")
    notDone = [name for name in expected if not after[Data.NAMESPACE + name][0]]
    partial = dict((name, after[Data.NAMESPACE + name][1]) for name in ("plant_all_crops", "master_chef"))
    return {"case": "advancements", "ok": not notDone and partial == {"plant_all_crops": 3, "master_chef": 1},
            "notDone": notDone, "partial": partial, "after": after, "before": _state["before"], "steps": _state["steps"],
            "cleared": cleared, "revoked": revoked, "seconds": round(time.time() - _state["started"], 2)}
