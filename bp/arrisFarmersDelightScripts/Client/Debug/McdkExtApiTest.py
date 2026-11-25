# -*- coding: utf-8 -*-
"""McdkExtApiTest - 新联动接口的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

服务端那一半（登记、删除、同步）和调用的先后见 Server/Debug/McdkExtApiTest.py。这里看客户端：ready 播了没有、客户端的能力名、
表同步过来的自检配方查不查得到、在客户端配不配得上（站点、书、经典界面的客户端预测读的就是这一份）、标签的口准备好没有、探针包的番茄认不认。
单机时两端在同一个进程里、共用一份表，这里只能看出客户端的接口通不通；表同步真的过了线，要第二个客户端（联机）才看得出来。
    from arrisFarmersDelightScripts.Client.Debug import McdkExtApiTest as T
    return T.mcdk_test_ext_api_client()
"""
from ...Api.ExtensionApi import Ready
from ...Api.ExtensionApi.Facade import getExtensionApi
from ...Shared.Rules import ItemTags

RECIPE_ID = "fdselftest:cooking/tag_mash"      # 和服务端那一半同一个
PROBE_TOMATO = "fdprobe:tomato"


def _match(ext, *names):
    found = ext.recipes.matchCooking(list(names))
    return found["id"] if found else None


def mcdk_test_ext_api_client():
    """测试函数：客户端的门面、自检配方查得到 / 配得上没有、探针包的番茄。"""
    ext = getExtensionApi("client")
    return {"case": "ext_api_client", "ready": Ready.status("client"), "capabilities": sorted(ext.capabilities),
            "view": ext.recipes.getRecipeById(RECIPE_ID), "fd_tomato": _match(ext, "arris:tomato", "minecraft:dirt"),
            "probe_tomato": _match(ext, PROBE_TOMATO, "minecraft:dirt"), "tags_ready": ItemTags.ready(),
            "probe_tomato_is_tomato": ItemTags.has(PROBE_TOMATO, "common:tomato"),
            "register_refused": ext.recipes.removeRecipe(RECIPE_ID)}
