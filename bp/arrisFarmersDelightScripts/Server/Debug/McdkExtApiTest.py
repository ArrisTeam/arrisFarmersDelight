# -*- coding: utf-8 -*-
"""McdkExtApiTest - 新联动接口的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。按顺序调（客户端那一半在 Client/Debug/McdkExtApiTest.py）：
1. mcdk_test_ext_api_status()：门面在不在（ready 播了没有、主动导入拿到的是不是同一个）、两端的能力名、版本号、标签的口准备好没有、
   开服时读行为包 farmersdelight_recipes/ 的结果（ExtensionReady.scanReport：state 是 "unavailable" 说明 server_resource 这条路不通）。
   装了草稿目录里的探针包（fdprobe）时还看它的两条配方：ready 里用 Builder 登记的 fdprobe:cooking/builder_stew、
   它的 farmersdelight_recipes/ 里的 fdprobe:cooking/json_stew（读到了就说明跨包读文件是通的；2026-11-26 实机读到了，能力名 recipe_json_files 因此登记）。
2. mcdk_test_ext_api_register()：用 ext.recipes 登记一条带标签原料的厨锅配方（fdselftest:cooking/tag_mash：#common:tomato + 泥土 -> 绿宝石），
   拿农夫乐事的番茄、探针包的番茄（只靠它的 netease_tags 进 common:tomato）各配一次，再现在就同步给在线的玩家（syncToClients）。
3. 客户端：Client/Debug/McdkExtApiTest.mcdk_test_ext_api_client()（表同步过去之后客户端查到的、配出来的）。
4. mcdk_test_ext_api_remove()：删掉这条（墓碑），再配一次应当配不上，同步；之后客户端再调一次 3，应当查不到、配不上。
    from arrisFarmersDelightScripts.Server.Debug import McdkExtApiTest as T
    return T.mcdk_test_ext_api_status()
"""
from .. import ExtensionReady
from ..Helpers.Engine import serverApi
from ...Api.ExtensionApi import Ready
from ...Api.ExtensionApi.Facade import getExtensionApi
from ...Shared.Rules import ItemTags

RECIPE_ID = "fdselftest:cooking/tag_mash"
PROBE_IDS = ("fdprobe:cooking/builder_stew", "fdprobe:cooking/json_stew")
FD_TOMATO, PROBE_TOMATO = "arris:tomato", "fdprobe:tomato"


def _ext():
    return getExtensionApi("server")


def mcdk_test_ext_api_status():
    """测试函数：门面、能力名、版本、标签的口、开服读行为包配方 JSON 的结果、探针包的两条配方。"""
    ext = _ext()
    module = serverApi.ImportModule("arrisFarmersDelightScripts.Api.ExtensionApi.Facade")
    imported = module.getExtensionApi("server") if module else None
    probe = dict((recipeId, ext.recipes.getRecipeById(recipeId)) for recipeId in PROBE_IDS)
    return {"case": "ext_api_status", "ok": Ready.status("server") == Ready.SENT and imported is ext,
            "ready": Ready.status("server"), "imported_is_same": imported is ext, "api": ext.apiVersion, "host": ext.hostVersion,
            "capabilities": sorted(ext.capabilities), "tags_ready": ItemTags.ready(), "tags_generation": ItemTags.generation(),
            "scan": ExtensionReady.scanReport(), "probe": probe,
            "probe_tomato_is_tomato": ItemTags.has(PROBE_TOMATO, "common:tomato")}


def _match(*names):
    found = _ext().recipes.matchCooking(list(names))
    return found["id"] if found else None


def mcdk_test_ext_api_register():
    """测试函数：登记带标签原料的厨锅配方、两种番茄各配一次、现在就同步。"""
    recipes = _ext().recipes
    answer = recipes.createBuilder(RECIPE_ID, "cooking").ingredient("#common:tomato").ingredient("minecraft:dirt") \
        .output("minecraft:emerald").cookingTime(100).register()
    synced = recipes.syncToClients("cooking", RECIPE_ID)
    return {"case": "ext_api_register", "ok": bool(answer["ok"]) and _match(FD_TOMATO, "minecraft:dirt") == RECIPE_ID,
            "answer": answer, "view": recipes.getRecipeById(RECIPE_ID), "synced": synced,
            "fd_tomato": _match(FD_TOMATO, "minecraft:dirt"), "probe_tomato": _match(PROBE_TOMATO, "minecraft:dirt"),
            "probe_tomato_is_tomato": ItemTags.has(PROBE_TOMATO, "common:tomato")}


def mcdk_test_ext_api_remove():
    """测试函数：删掉自检的配方（墓碑），再配一次应当配不上，现在就同步。"""
    recipes = _ext().recipes
    answer = recipes.removeRecipe(RECIPE_ID)
    synced = recipes.syncToClients("cooking", RECIPE_ID)
    after = _match(FD_TOMATO, "minecraft:dirt")
    return {"case": "ext_api_remove", "ok": bool(answer["ok"]) and after is None and recipes.getRecipeById(RECIPE_ID) is None,
            "answer": answer, "match_after": after, "synced": synced}
