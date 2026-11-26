# -*- coding: utf-8 -*-
"""McdkPotSearchTest - 经典厨锅界面搜索的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code（is_client 为 true）/ 开发调试调用

不会自动运行，没有 RPC 端点。搜索只在看界面的那一端做（Shared/Rules/PotSearch：照 JEI 拆条件、逐件比，用这一端问到的显示名），
这里在客户端线程里按查询词各过滤一遍，回答：过滤出几道、前 12 道的行号 / 成品 / 标题（titleOf）/ 成品的显示名（ItemNames，问到了没有），
忘掉记着的之后第一次过滤（要问显示名、标签）和第二次（记着的）各几毫秒，番茄的显示名在这个线程里两个口（单机时两端的口都装在共用的
ItemNames 里）各给什么。查询词缺省是几条固定的：中文名（番茄）、中文模糊（牛炖：配得上牛肉炖）、标签（#common:tomato：探针包的番茄菜也在）、
模组（@fdprobe：只有装了探针包才有）、物品 ID（&arris:cook）、字母（tomato）。
先在客户端线程调这个，再在服务端线程调 Server/Debug/McdkPotSearchTest 的同名函数：单机时两端共用 Shared 的模块，显示名的缓存只有一份，
服务端线程先问会把它问到的名字记进去，藏住客户端的口答不答得出（2026-11-26 实机：GetItemBasicInfo 只在自己那一端的线程里答得出）。
    from arrisFarmersDelightScripts.Client.Debug import McdkPotSearchTest as T
    return T.mcdk_test_pot_search_probe()                 # 或者给一个查询词：T.mcdk_test_pot_search_probe(u"番茄")
"""
import time

from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Rules import CookingPotBook, ItemNames, PotSearch

QUERIES = (u"番茄", u"牛炖", u"#common:tomato", u"@fdprobe", u"&arris:cook", u"tomato")
PROBE_ITEM = ("arris:tomato", 0)
SHOWN = 12


def _ms(since):
    return round((time.time() - since) * 1000.0, 3)


def probe(query):
    """按 query 过滤一遍（先忘掉记着的）：几道、前几道是什么、两次各几毫秒。"""
    PotSearch.forget()
    started = time.time()
    rows = PotSearch.rows(query)
    first = _ms(started)
    started = time.time()
    PotSearch.rows(query)
    again = _ms(started)
    found = []
    for row in rows[:SHOWN]:
        recipe = CookingPotRecipeList[row]
        result = recipe["CookResult"]
        found.append({"row": row, "result": result[0], "title": repr(CookingPotBook.titleOf(recipe)),
                      "name": repr(ItemNames.nameOf(result[0], result[1]))})
    return {"query": query, "count": len(rows), "rows": found, "firstMs": first, "rememberedMs": again}


def portAnswers(name, aux=0):
    """装着的显示名口在这个线程里各自给什么（不经 ItemNames 的缓存）。"""
    answers = []
    for port in ItemNames.ports():
        try:
            answers.append(repr(port(name, aux))[:80])
        except Exception as error:  # noqa: BLE001 - 自检只报，不抛
            answers.append("raised %r" % (error,))
    return answers


def mcdk_test_pot_search_probe(query=None):
    """测试函数：在这个线程（客户端）里按查询词过滤；返回结构化结果。缺省的几条里"番茄"该过滤出几道（农夫乐事自带的番茄酱等）。"""
    queries = [query] if query is not None else list(QUERIES)
    probes = [probe(word) for word in queries]
    ok = query is not None or probes[0]["count"] > 0
    return {"case": "pot_search_probe", "thread": "client", "ok": ok, "fuzzy": PotSearch.FUZZY, "probes": probes,
            "ports": portAnswers(*PROBE_ITEM), "named": repr(ItemNames.nameOf(*PROBE_ITEM))}
