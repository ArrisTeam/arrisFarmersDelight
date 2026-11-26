# -*- coding: utf-8 -*-
"""McdkPotSearchTest - 经典厨锅界面搜索的游戏内自检（客户端）：测试函数，仅供 MCDK-MCP 的 execute_code（is_client 为 true）/ 开发调试调用

不会自动运行，没有 RPC 端点。两样：
- mcdk_test_pot_search_probe(query=None)：搜索只在看界面的那一端做（Shared/Rules/PotSearch：照 JEI 拆条件、逐件比，用这一端问到的显示名），
  这里在客户端线程里按查询词各过滤一遍，回答：过滤出几道、前 12 道的行号 / 成品 / 标题（titleOf）/ 成品的显示名（ItemNames，问到了没有），
  忘掉记着的之后第一次过滤（要问显示名、标签）和第二次（记着的）各几毫秒，番茄的显示名在这个线程里两个口（单机时两端的口都装在共用的
  ItemNames 里）各给什么。查询词缺省是几条固定的：中文名（番茄）、中文模糊（牛炖：配得上牛肉炖）、标签（#common:tomato：探针包的番茄菜也在）、
  模组（@fdprobe：只有装了探针包才有）、物品 ID（&arris:cook）、字母（tomato）。
  先在客户端线程调它，再在服务端线程调 Server/Debug/McdkPotSearchTest 的同名函数：单机时两端共用 Shared 的模块，显示名的缓存只有一份，
  服务端线程先问会把它问到的名字记进去，藏住客户端的口答不答得出（2026-11-26 实机：GetItemBasicInfo 只在自己那一端的线程里答得出）。
- mcdk_test_pot_screen_flow(query=None, cell=None)：不靠指针把经典厨锅界面那条线走一遍（界面先用投递的右键打开：没装前置包、或者厨锅站点
  关着时右键开的是它）。query 不是 None：框里先写上这些字（真打字时框里本来就是，截图看得到搜了什么），再照引擎报给搜索框的两下
  （打字中、输入结束，Screen._onText）交给库的文本框 TextBox.onInput——它清理字（上限 32）、边打边提交 search 动作；界面还没建好、
  找不到框时直接发 search 动作（报告的 typed.via 写走了哪条）。
  cell 不是 None：照界面收到食谱格第 cell 格按钮的按下、抬起（Screen._slotEvent）交给手势识别 Gestures.onSlotDown / onSlotUp，按现在的
  输入方式走 PotRecipes.TapToPick（键鼠、手柄按下就选，触屏抬起才选：_select 把这一格换成本端过滤结果里的行号、发 pick）。
  每一下之后照界面处理完输入那样当场取走一次性效果、重画（applyEffects + render）。两个都不给只读现在的样子。
  报：输入方式 device；这次发出去、还没应答的动作和参数 sent（应答一到就不在里面了）、所有还没应答的 waiting；这一端的 search / picked
  （shown 算上还没应答的预测，confirmed 是服务端确认过的）；这一端过滤出的行号 rows；点的那格换算出的行号 clicked.row；按 decorate 画成
  选中的格 selected（consistent：正好是 picked 那一行所在的格，那一行被过滤掉时是空的）；食谱格的控件上现在画成选中的格 drawn 和控件绑着的格
  window（读库的内部字段 _cellImage._sprite，读不到是 None；格数、滚动窗口要到下一帧才同步，刚搜过时 window 可能还是旧的），drawnAgrees：
  绑着的格里画的和 decorate 算的一样；详情的成品和标题 bookResult / bookTitle（客户端收到的界面数据）。ok：点的那格有东西、发出了那一行的
  pick、这一端的 picked 跟上、画成选中的格都对得上，不对时 why 写第一处。界面没开、开着的不是厨锅界面时返回说明，不抛。
  先后：① 客户端线程 mcdk_test_pot_screen_flow(u"牛炖", 0)（搜、点）；② 等应答回来（一两刻），客户端线程再调一次不带参数的：confirmed 应当
  和 shown 一样、waiting 是空的、drawn 是画好之后的；③ 服务端线程 Server/Debug/McdkPotSearchTest.mcdk_test_pot_screen_state()：
  服务端会话里的 search / picked / pickedAt、按 picked 取到的配方、发出去的详情成品。
    from arrisFarmersDelightScripts.Client.Debug import McdkPotSearchTest as T
    return T.mcdk_test_pot_search_probe()                 # 或者给一个查询词：T.mcdk_test_pot_search_probe(u"番茄")
    return T.mcdk_test_pot_screen_flow(u"牛炖", 0)        # 搜"牛炖"、点第 0 格；T.mcdk_test_pot_screen_flow() 只读
"""
import time

from ...dolorContainer.Common.Rules import PRIMARY
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Menus import CookingPot as PotMenu
from ...Shared.Menus import PotRecipes
from ...Shared.Rules import CookingPotBook, ItemNames, PotSearch

QUERIES = (u"番茄", u"牛炖", u"#common:tomato", u"@fdprobe", u"&arris:cook", u"tomato")
PROBE_ITEM = ("arris:tomato", 0)
SHOWN = 12
SEARCH = "search"        # 搜索框提交的动作（Shared/Menus/CookingPot）
GRID = "recipe_grid"     # 食谱格那个格子区在布局里的名字（layouts/cooking_pot.json，编译在 dolorLayouts.py）


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


# ---------------------------------------------------------------- 不靠指针走一遍界面


def _plain(value):
    """报告里的值：utf-8 字节串解成 unicode（execute_code 的结果里好读），列表、字典逐项，别的原样。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, dict):
        return dict((_plain(key), _plain(item)) for key, item in value.items())
    return value


def check(session):
    """库的客户端会话能不能拿来走：(会话, None)；界面没开、开着的不是经典厨锅界面时是 (None, 为什么)。"""
    if session is None or session.closed:
        return None, "没有开着的 dolorContainer 界面（先用右键打开经典厨锅界面）"
    if session.mirror.menu.menuName != PotMenu.MENU:
        return None, "开着的界面是 %r，不是经典厨锅界面" % (session.mirror.menu.menuName,)
    return session, None


def _afterInput(session):
    """照界面处理完一个输入事件那样（Screen._afterInput）当场取走一次性效果（点中的音效）、重画；界面还没建好时留给下一帧。"""
    screen = session.screen
    if screen is not None and getattr(screen, "ready", False):
        screen.applyEffects()
        screen.render(False)


def _textBox(session):
    """界面上提交 search 动作、已经接上这个会话的文本框（库的 TextBox）；界面还没建好、找不到时是 None。"""
    parts = getattr(session.screen, "parts", None)
    for widget in getattr(parts, "widgets", None) or ():
        if getattr(widget, "action", None) == SEARCH and getattr(widget, "model", None) is session:
            return widget
    return None


def _type(session, text):
    """在搜索框里打 text，返回走的哪条路（text_box / action）。"""
    raw = text if isinstance(text, str) else text.encode("utf-8")   # 引擎报给文本框的字（Screen._onText 同样换成 utf-8）
    box = _textBox(session)
    if box is None:
        session.call(SEARCH, [raw])
        return "action"
    control = box.control.get() if getattr(box, "control", None) is not None else None
    if control is not None:
        control.SetEditText(raw)   # 真打字时框里本来就是这些字（TextBox 自己换框里的字也用它），截图看得到搜了什么
    for finished in (False, True):
        box.onInput({"kind": "text", "box": box.box, "text": raw, "finished": finished, "enter": False})
        _afterInput(session)
    return "text_box"


def _click(session, cell):
    """点食谱格第 cell 格：照界面收到这一格按钮的按下、抬起交给手势识别，每一下之后当场重画。"""
    ref, gestures = (PotMenu.RECIPES, cell), session.gestures
    gestures.onSlotDown(ref, PRIMARY, time.time(), None)
    _afterInput(session)
    gestures.onSlotUp(ref, PRIMARY, time.time(), None)
    _afterInput(session)


def _drawn(session):
    """食谱格的控件上现在画成选中的格、控件绑着（所在的行显示着）的格：读控件上次设的底格（库的内部字段）；读不到是 (None, None)。"""
    pane = (getattr(session.screen, "panes", None) or {}).get(GRID)
    views = getattr(pane, "views", None)
    if not views:
        return None, None
    rows, columns = getattr(pane, "rowViews", None), getattr(pane, "maxColumns", None) or 1
    chosen, bound = [], []
    for index, view in enumerate(views):
        ref = pane.refAt(index)
        if ref is None or (rows is not None and not rows[index // columns].shown()):
            continue   # 没分到格、所在的行藏着（藏着的行不重画，底格可能是旧的）
        bound.append(ref[1])
        if getattr(getattr(view, "_cellImage", None), "_sprite", None) == PotRecipes.CELLS[1]:
            chosen.append(ref[1])
    return sorted(chosen), sorted(bound)


def screenReport(session, before=(), typed=None, clicked=None):
    """会话现在的样子（见模块说明）；before 是走之前还没应答的请求编号（这之后新发的才算 sent）。"""
    mirror, gestures = session.mirror, session.gestures
    viewer, confirmed = mirror.viewer, mirror.confirmedViewer
    rows, picked = PotSearch.rows(PotRecipes.searchOf(viewer)), viewer.get("picked")
    workspace, slot = gestures.workspace(), mirror.structure.get(PotMenu.RECIPES).slot
    selected = [cell for cell in range(len(rows))
                if slot.decorate(workspace, (PotMenu.RECIPES, cell), None).cell == PotRecipes.CELLS[1]]
    drawn, bound = _drawn(session)
    now = time.time()
    return {"device": gestures.device, "typed": typed, "clicked": clicked,
            "sent": [{"id": entry[0], "action": entry[1].name, "args": _plain(list(entry[2]))}
                     for entry in mirror.calls if entry[0] not in before],
            "waiting": [entry[1].name for entry in mirror.calls],
            "search": {"shown": _plain(viewer.get("search")), "confirmed": _plain(confirmed.get("search"))},
            "picked": {"shown": picked, "confirmed": confirmed.get("picked")},
            "rows": rows, "count": len(rows), "selected": selected,
            "consistent": selected == ([rows.index(picked)] if picked in rows else []),
            "drawn": drawn, "window": [bound[0], bound[-1]] if bound else None,
            "drawnAgrees": None if drawn is None else drawn == [cell for cell in selected if cell in bound],
            "bookResult": _plain(mirror.dataValue("bookResult", now)), "bookTitle": _plain(mirror.dataValue("bookTitle", now))}


def _problem(report):
    """报告里第一处对不上的地方（都对得上是 None）。"""
    clicked = report["clicked"]
    if clicked is not None and clicked["row"] is None:
        return "第 %r 格没有东西（这一端过滤出 %d 道）" % (clicked["cell"], report["count"])
    if clicked is not None and not any(sent["action"] == "pick" and sent["args"] == [clicked["row"]] for sent in report["sent"]):
        return "点了第 %r 格（表里第 %r 行），没发出这一行的 pick" % (clicked["cell"], clicked["row"])
    if clicked is not None and report["picked"]["shown"] != clicked["row"]:
        return "发了 pick(%r)，这一端显示的 picked 是 %r" % (clicked["row"], report["picked"]["shown"])
    if not report["consistent"]:
        return "按 decorate 画成选中的格 %r 不是 picked（第 %r 行）所在的格" % (report["selected"], report["picked"]["shown"])
    if report["drawnAgrees"] is False:
        return "控件上画成选中的格 %r 和 decorate 算的 %r 对不上" % (report["drawn"], report["selected"])
    return None


def flow(session, query=None, cell=None):
    """在库的客户端会话 session 上先打 query、再点第 cell 格（见模块说明），返回报告。"""
    mirror = session.mirror
    before = frozenset(entry[0] for entry in mirror.calls)
    typed = clicked = None
    if query is not None:
        typed = {"query": _plain(query), "via": _type(session, query)}
    if cell is not None:
        clicked = {"cell": cell, "row": PotRecipes.rowOf(mirror.viewer, cell)}   # 点之前（打过字之后）这一格是哪一行
        _click(session, cell)
    report = screenReport(session, before, typed, clicked)
    why = _problem(report)
    report["ok"] = why is None
    if why is not None:
        report["why"] = why
    return report


def _current():
    """库的客户端服务现在的会话；不在游戏里（导入不了）时是 (None, 为什么)。"""
    try:
        from ...dolorContainer.Client import Service
    except Exception as error:  # noqa: BLE001 - 离线没有引擎：py3 是 ImportError，装了引擎桩的 py2 可能是别的
        return None, "导入不了库的客户端服务（不在游戏里？）：%r" % (error,)
    return check(Service.current())


def mcdk_test_pot_screen_flow(query=None, cell=None):
    """测试函数：经典厨锅界面开着时搜 query、点食谱格第 cell 格（都可以不给：只读）；返回结构化结果，拿不到界面时返回说明、不抛。"""
    session, why = _current()
    if session is None:
        return {"case": "pot_screen_flow", "thread": "client", "ok": False, "why": why}
    report = flow(session, query, cell)
    report.update({"case": "pot_screen_flow", "thread": "client"})
    return report
