# -*- coding: utf-8 -*-
"""McdkPotSearchTest - 经典厨锅界面搜索的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。服务端不按搜索词判断任何事（选中的是配方在表里的行号：Shared/Menus/CookingPot 的 pick），这里看服务端这一侧：
同样的查询词在服务端线程里过滤出来的行（单机时两端共用 Shared 的模块、显示名的缓存只有一份，所以先在客户端线程调
Client/Debug/McdkPotSearchTest 的同名函数，这里看到的名字多半是客户端问到的）、这些行 pick 收不收（活的、形状对：CookingPotBook.recipeAt）、
服务端发给客户端的详情标题（titleOf：服务端线程问显示名，专用服务器上问到什么没核实）、番茄的显示名在服务端线程里两个口各给什么。
    from arrisFarmersDelightScripts.Server.Debug import McdkPotSearchTest as T
    return T.mcdk_test_pot_search_probe()                 # 或者给一个查询词：T.mcdk_test_pot_search_probe(u"番茄")
"""
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Rules import CookingPotBook, ItemNames, PotSearch

QUERIES = (u"番茄", u"牛炖", u"#common:tomato", u"@fdprobe", u"&arris:cook", u"tomato")   # 同客户端那份（两端互不导入，各写一份）
PROBE_ITEM = ("arris:tomato", 0)
SHOWN = 12


def portAnswers(name, aux=0):
    """装着的显示名口在这个线程里各自给什么（不经 ItemNames 的缓存）。"""
    answers = []
    for port in ItemNames.ports():
        try:
            answers.append(repr(port(name, aux))[:80])
        except Exception as error:  # noqa: BLE001 - 自检只报，不抛
            answers.append("raised %r" % (error,))
    return answers


def probe(query):
    """按 query 在这个线程里过滤：几道、每道 pick 收不收、服务端给的标题。"""
    rows = PotSearch.rows(query)
    found = []
    for row in rows[:SHOWN]:
        recipe = CookingPotRecipeList[row]
        found.append({"row": row, "result": recipe["CookResult"][0], "pickable": CookingPotBook.recipeAt(row) is recipe,
                      "title": repr(CookingPotBook.titleOf(recipe))})
    return {"query": query, "count": len(rows), "rows": found, "allPickable": all(entry["pickable"] for entry in found)}


def mcdk_test_pot_search_probe(query=None):
    """测试函数：在这个线程（服务端）里按查询词过滤；过滤出来的每一行 pick 都该收。返回结构化结果。"""
    queries = [query] if query is not None else list(QUERIES)
    probes = [probe(word) for word in queries]
    return {"case": "pot_search_probe", "thread": "server", "ok": all(entry["allPickable"] for entry in probes), "probes": probes,
            "ports": portAnswers(*PROBE_ITEM), "named": repr(ItemNames.nameOf(*PROBE_ITEM))}
