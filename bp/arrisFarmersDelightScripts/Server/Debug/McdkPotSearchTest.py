# -*- coding: utf-8 -*-
"""McdkPotSearchTest - 经典厨锅界面搜索的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。服务端不按搜索词判断任何事（选中的是配方在表里的行号：Shared/Menus/CookingPot 的 pick）。两样：
- mcdk_test_pot_search_probe(query=None)：同样的查询词在服务端线程里过滤出来的行（单机时两端共用 Shared 的模块、显示名的缓存只有一份，
  所以先在客户端线程调 Client/Debug/McdkPotSearchTest 的同名函数，这里看到的名字多半是客户端问到的）、这些行 pick 收不收（活的、形状对：
  CookingPotBook.recipeAt）、服务端发给客户端的详情标题（titleOf：服务端线程问显示名，专用服务器上问到什么没核实）、番茄的显示名在
  服务端线程里两个口各给什么。
- mcdk_test_pot_screen_state(playerId=None)：只读，看开着的经典厨锅界面在服务端的会话（库的 dolorContainer：Service.manager().sessions；
  playerId 不给时每位开着厨锅界面的玩家各一份）：这位查看者的 search / picked（表里的行号，-1 没选）/ pickedAt（选中的时刻）和离现在几秒、
  按 picked 取到的配方（Id、成品、服务端线程算的标题）、上次发给客户端的详情成品和标题 bookResult / bookTitle、现在算出来的成品
  bookResultNow（下一次界面数据刷新就发它）；consistent：没选时没有成品，选了时是那一行的成品（ok 是每一份都对得上，不对时 why 写是哪几位）。
  没有开着的厨锅界面时返回说明，不抛。
  在客户端线程调过 Client/Debug/McdkPotSearchTest.mcdk_test_pot_screen_flow(查询词, 格号)（不靠指针搜、点）、等应答回来之后调：
  picked 应当是客户端报的 clicked.row，search 是客户端打的字。
    from arrisFarmersDelightScripts.Server.Debug import McdkPotSearchTest as T
    return T.mcdk_test_pot_search_probe()                 # 或者给一个查询词：T.mcdk_test_pot_search_probe(u"番茄")
    return T.mcdk_test_pot_screen_state()                 # 或者只看一位玩家：T.mcdk_test_pot_screen_state(playerId)
"""
import time

from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Menus import CookingPot as PotMenu
from ...Shared.Rules import CookingPotBook, ItemNames, PotSearch
from ...Shared.Rules.TableWire import isInt

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


# ---------------------------------------------------------------- 开着的界面在服务端的会话


def _plain(value):
    """报告里的值：utf-8 字节串解成 unicode（execute_code 的结果里好读），列表、字典逐项，别的原样。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return dict((_plain(key), _plain(item)) for key, item in value.items())
    return value


def _consistent(picked, recipe, shown):
    """详情的成品对得上选中的行：没选时没有成品；选了时是那一行（还活着）的成品。"""
    if not isInt(picked) or picked < 0:
        return shown is None
    return recipe is not None and isinstance(shown, dict) and shown.get("newItemName") == recipe["CookResult"][0]


def sessionState(playerId, session):
    """一位玩家开着的厨锅界面在服务端的会话（库的 Server/Session）：见模块说明。"""
    viewer = session.viewer
    picked, pickedAt = viewer.get("picked"), viewer.get("pickedAt")
    recipe = CookingPotBook.recipeAt(picked) if isInt(picked) else None
    shown = (session.menu.allViewerValues(session.instance, viewer) or {}).get("bookResult")
    sent = session.dataSent
    return {"player": playerId, "session": session.id, "pot": repr(session.instance.key),
            "search": _plain(viewer.get("search")), "picked": picked, "pickedAt": pickedAt,
            "sincePick": round(time.time() - pickedAt, 3) if pickedAt else None,
            "recipe": None if recipe is None else {"row": picked, "id": _plain(recipe.get("Id")),
                                                   "result": _plain(recipe["CookResult"][:2]),
                                                   "title": _plain(CookingPotBook.titleOf(recipe))},
            "bookResult": _plain(sent.get("bookResult")), "bookTitle": _plain(sent.get("bookTitle")),
            "bookResultNow": _plain(shown), "consistent": _consistent(picked, recipe, shown)}


def stateReport(sessions, playerId=None):
    """sessions（{玩家 id: 会话}）里开着经典厨锅界面的那几位（playerId 给了只看他）各自的会话状态（pots，按玩家 id 排）和结论。"""
    pots = [sessionState(pid, sessions[pid]) for pid in sorted(sessions)
            if (playerId is None or pid == playerId) and getattr(sessions[pid].menu, "menuName", None) == PotMenu.MENU]
    if not pots:
        return {"ok": False, "sessions": len(sessions),
                "why": "没有开着的经典厨锅界面（库的服务端没有这样的会话%s）" % ("" if playerId is None else "，玩家 %r" % (playerId,))}
    wrong = [pot["player"] for pot in pots if not pot["consistent"]]
    report = {"ok": not wrong, "pots": pots}
    if wrong:
        report["why"] = "详情的成品和选中的行对不上：玩家 %r" % (wrong,)
    return report


def _sessions():
    """库的服务端现在开着的会话 {玩家 id: 会话}；不在游戏里（导入不了）时是 (None, 为什么)。"""
    try:
        from ...dolorContainer.Server import Service
    except Exception as error:  # noqa: BLE001 - 离线没有引擎：py3 是 ImportError，装了引擎桩的 py2 在 QuModLibs 建系统时抛 TypeError
        return None, "导入不了库的服务端服务（不在游戏里？）：%r" % (error,)
    return Service.manager().sessions, None


def mcdk_test_pot_screen_state(playerId=None):
    """测试函数：开着的经典厨锅界面在服务端的会话（只读）；返回结构化结果，没有开着的厨锅界面时返回说明、不抛。"""
    sessions, why = _sessions()
    report = {"ok": False, "why": why} if sessions is None else stateReport(sessions, playerId)
    report.update({"case": "pot_screen_state", "thread": "server"})
    return report
