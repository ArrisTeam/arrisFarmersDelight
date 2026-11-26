# -*- coding: utf-8 -*-
# runner: both
"""经典厨锅界面搜索的游戏内自检（Client/Debug/McdkPotSearchTest.py、Server/Debug/McdkPotSearchTest.py）离线跑得通：显示名用假的口，
缺省的几条查询词都过滤得出来（"番茄"至少一道），服务端那份过滤出来的每一行 pick 都收；每个口在这个线程里给什么也报得出（抛异常的照样报）。
不靠指针走一遍界面的那两个（客户端 mcdk_test_pot_screen_flow、服务端 mcdk_test_pot_screen_state）：拿不到界面（离线导入不了库的服务）时
返回说明、不抛；客户端那半在库的真镜像和真手势识别上走（会话、界面、文本框、食谱格是假的，只有自检读的那几样），打字走文本框的两下、
点格走按下 + 抬起（键鼠按下就选、触屏抬起才选），报出发的动作、换算出的行号、画成选中的格；服务端那半读会话里的 picked、配方和详情的成品。
格号换成行号、按行号画选中的格本身由 test_cooking_pot_menu.py 盯着，这里不重复。真正的数在游戏里跑（两个文件的说明：先客户端线程、后服务端线程）。"""
from __future__ import print_function

import time

import fdtest

ClientTest = fdtest.load("Client.Debug.McdkPotSearchTest")
ServerTest = fdtest.load("Server.Debug.McdkPotSearchTest")
Names = fdtest.load("Shared.Rules.ItemNames")
Search = fdtest.load("Shared.Rules.PotSearch")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
PotMenu = fdtest.load("Shared.Menus.CookingPot")
PotRecipes = fdtest.load("Shared.Menus.PotRecipes")
Mirror = fdtest.load("dolorContainer.Client.Mirror")
Gestures = fdtest.load("dolorContainer.Client.Gestures")
Collections = fdtest.load("dolorContainer.Common.Collections")
Items = fdtest.load("dolorContainer.Common.Items")
Libs = fdtest.load("dolorContainer.Common.Menus")
fdtest.load("dolorContainer.Std.Defaults")   # 库的缺省实现（标准交互、操作）随之登记，与游戏里一样

RULES = Items.ItemRules(lambda name, aux: 64)
RECIPES = PotMenu.RECIPES


def _named(name, aux):
    return u"番茄" if name == "arris:tomato" else None


def _wrongThread(name, aux):
    raise RuntimeError("wrong thread")


def _reset():
    Names.setPort(None)
    Names.forget()
    Search.forget()


def testBothSelfTestsRunOfflineAndReportWhatTheyFound():
    _reset()
    Names.setPort(_wrongThread)
    Names.setPort(_named)
    try:
        client = ClientTest.mcdk_test_pot_search_probe()
        assert client["ok"] and client["thread"] == "client" and client["fuzzy"] == Search.CJK, client
        assert [probe["query"] for probe in client["probes"]] == list(ClientTest.QUERIES) and client["probes"][0]["count"] > 0
        assert client["named"] == repr(u"番茄") and client["ports"][1] == repr(u"番茄") and client["ports"][0].startswith("raised")
        assert all(probe["firstMs"] >= 0 and probe["rememberedMs"] >= 0 for probe in client["probes"])
        server = ServerTest.mcdk_test_pot_search_probe()
        assert server["ok"] and server["thread"] == "server" and all(probe["allPickable"] for probe in server["probes"]), server
        assert ServerTest.QUERIES == ClientTest.QUERIES, "两端的查询词一样（各写一份）"
        stew = ClientTest.mcdk_test_pot_search_probe(u"牛炖")
        assert stew["ok"] and [probe["query"] for probe in stew["probes"]] == [u"牛炖"] and stew["probes"][0]["count"] >= 1, "牛肉炖"
        nothing = ServerTest.mcdk_test_pot_search_probe(u"绝对没有这道菜")
        assert nothing["ok"] and nothing["probes"][0]["count"] == 0
    finally:
        _reset()


# ---------------------------------------------------------------- 不靠指针走一遍界面：客户端


class _Session(object):
    """库的客户端会话（Client/Service.ClientSession）里自检用到的那几样：真的镜像和手势识别，发动作走镜像（可预测的当场改）。"""

    def __init__(self):
        self.mirror = Mirror.Mirror({"s": 3, "menu": PotMenu.MENU, "params": {}, "v": {"picked": -1}}, RULES)
        self.gestures = Gestures.Gestures(self.mirror, lambda request: None, lambda: Collections.PROFILE_CLASSIC, self.call)
        self.screen = None
        self.closed = False
        self.requests = []

    def call(self, name, args=(), done=None):
        request = self.mirror.call(name, args, time.time(), done)
        if request is not None:
            self.requests.append(request)
        return request is not None


class _Edit(object):
    """引擎的文本框控件：记下脚本写进去的字。"""

    def __init__(self):
        self.text = None

    def SetEditText(self, text):
        self.text = text


class _Lazy(object):
    """库的 Views.Lazy：用到时才取的控件。"""

    def __init__(self, control):
        self.control = control

    def get(self):
        return self.control


class _Box(object):
    """库的文本框（TextBox）收输入事件：记下事件，输入结束时提交（真的那个还边打边提交、清理字）。"""

    action, box = "search", "dc_text_1"

    def __init__(self, session):
        self.model, self.events = session, []
        self.edit = _Edit()
        self.control = _Lazy(self.edit)

    def onInput(self, event):
        self.events.append(event)
        if event["finished"]:
            self.model.call(self.action, [event["text"]])


class _Thing(object):
    def __init__(self, **values):
        self.__dict__.update(values)


class _Row(object):
    """一个行控件（库的 Placed）：显没显示。"""

    def __init__(self):
        self.visible = True

    def shown(self):
        return self.visible


class _Pane(object):
    """按行回收的食谱格（库的 ScrollGrid）里自检读的那几样：控件（上次设的底格）、第几个控件绑着哪一格、行控件显没显示。"""

    maxColumns = 4

    def __init__(self, cells):
        self.refs = [(RECIPES, cell) for cell in range(cells)]
        self.views = [_Thing(_cellImage=_Thing(_sprite=None)) for _ in self.refs]
        self.rowViews = [_Row() for _ in range(0, cells, self.maxColumns)]

    def refAt(self, index):
        return self.refs[index] if 0 <= index < len(self.refs) else None


class _Screen(object):
    """库的界面（Client/Screen.ContainerScreen）里自检用到的那几样：重画时照 decorate 给食谱格的控件设底格。"""

    ready = True

    def __init__(self, session, pane):
        self.session, self.effects, self.renders = session, 0, 0
        self.box = _Box(session)
        self.parts = _Thing(widgets=[_Thing(action="other"), self.box])
        self.panes = {ClientTest.GRID: pane}

    def applyEffects(self):
        self.effects += 1

    def render(self, force):
        self.renders += 1
        mirror, pane = self.session.mirror, self.panes[ClientTest.GRID]
        workspace, slot = self.session.gestures.workspace(), mirror.structure.get(RECIPES).slot
        for index, view in enumerate(pane.views):
            view._cellImage._sprite = slot.decorate(workspace, pane.refAt(index), None).cell


def _sentPairs(report):
    return [(sent["action"], sent["args"]) for sent in report["sent"]]


def testTheScreenSelfTestsExplainInsteadOfRaisingWhenThereIsNoScreen():
    flow = ClientTest.mcdk_test_pot_screen_flow(u"番茄", 0)
    assert flow["ok"] is False and flow["thread"] == "client" and "导入不了" in flow["why"], flow
    state = ServerTest.mcdk_test_pot_screen_state()
    assert state["ok"] is False and state["thread"] == "server" and "导入不了" in state["why"], state
    assert ClientTest.check(None)[0] is None and "没有开着" in ClientTest.check(None)[1]
    session = _Session()
    assert ClientTest.check(session) == (session, None)
    session.closed = True
    assert ClientTest.check(session)[0] is None
    other = _Thing(closed=False, mirror=_Thing(menu=_Thing(menuName="test:other")))
    assert ClientTest.check(other)[0] is None and "test:other" in ClientTest.check(other)[1]


def testTheFlowTypesAndClicksLikeTheScreenAndReportsWhatThisSideSent():
    _reset()
    session = _Session()
    idle = ClientTest.flow(session)
    assert idle["ok"] and idle["sent"] == [] and idle["waiting"] == [] and idle["typed"] is None and idle["clicked"] is None, idle
    assert idle["picked"] == {"shown": -1, "confirmed": -1} and idle["selected"] == [] and idle["rows"] == Search.rows(u"")
    assert idle["drawn"] is None and idle["window"] is None and idle["device"] == Gestures.MOUSE
    stew = Search.rows(u"牛炖")
    assert len(stew) == 1 and Recipes.CookingPotRecipeList[stew[0]]["Id"] == "farmersdelight:cooking/beef_stew"
    report = ClientTest.flow(session, u"牛炖", 0)
    assert report["ok"] and report["typed"] == {"query": u"牛炖", "via": "action"}, report
    assert report["clicked"] == {"cell": 0, "row": stew[0]} and _sentPairs(report) == [("search", [u"牛炖"]), ("pick", [stew[0]])]
    assert report["search"] == {"shown": u"牛炖", "confirmed": u""} and report["picked"] == {"shown": stew[0], "confirmed": -1}
    assert report["rows"] == stew and report["selected"] == [0] and report["consistent"] and report["waiting"] == ["search", "pick"]
    # 应答回来（服务端记下了搜索词和行号、发了详情的成品）：只读的那一下 confirmed 跟上，没有还在等的
    session.mirror.onAck({"id": session.requests[0]["id"], "ok": True, "v": {"search": u"牛炖"}})
    session.mirror.onAck({"id": session.requests[1]["id"], "ok": True, "v": {"picked": stew[0]},
                          "d": {"bookResult": {"newItemName": "arris:cookbeef_stew", "newAuxValue": 0, "count": 1}}})
    settled = ClientTest.flow(session)
    assert settled["ok"] and settled["sent"] == [] and settled["waiting"] == [] and settled["selected"] == [0], settled
    assert settled["picked"] == {"shown": stew[0], "confirmed": stew[0]} and settled["search"]["confirmed"] == u"牛炖"
    assert settled["bookResult"]["newItemName"] == "arris:cookbeef_stew"
    _reset()


def testOnTouchTheCellIsPickedWhenTheFingerLiftsAndAnEmptyCellSendsNothing():
    _reset()
    session = _Session()
    session.gestures.device = Gestures.TOUCH
    row = Search.rows(u"")[3]
    report = ClientTest.flow(session, None, 3)
    assert report["ok"] and report["device"] == Gestures.TOUCH and report["clicked"] == {"cell": 3, "row": row}, report
    assert _sentPairs(report) == [("pick", [row])] and report["selected"] == [3]
    # 搜到只剩一道、点第 5 格：没有这一格，什么都不发；选中的那一行被过滤掉了，哪格都不亮（选中留着）
    far = ClientTest.flow(session, u"牛炖", 5)
    assert not far["ok"] and far["clicked"] == {"cell": 5, "row": None} and "第 5 格" in far["why"], far
    assert _sentPairs(far) == [("search", [u"牛炖"])] and far["picked"]["shown"] == row and far["selected"] == []
    assert far["consistent"]
    _reset()


def testTheFlowTypesThroughTheTextBoxAndReadsWhatTheGridControlsShow():
    _reset()
    session = _Session()
    soups = Search.rows(u"汤")
    assert len(soups) == 7
    screen = session.screen = _Screen(session, _Pane(len(soups)))
    report = ClientTest.flow(session, u"汤", 5)
    raw = u"汤" if isinstance(u"汤", str) else u"汤".encode("utf-8")   # 引擎报给文本框的字：py2 是 utf-8 字节串
    assert report["ok"] and report["typed"] == {"query": u"汤", "via": "text_box"}, report
    assert [(event["text"], event["finished"], event["box"]) for event in screen.box.events] == [(raw, False, "dc_text_1"),
                                                                                                (raw, True, "dc_text_1")]
    assert screen.box.edit.text == raw, "框里写上打的字（截图看得到搜了什么）"
    assert screen.renders == screen.effects == 4, "打字两下、按下抬起两下，每一下之后都当场重画"
    assert _sentPairs(report) == [("search", [u"汤"]), ("pick", [soups[5]])] and report["selected"] == [5]
    assert report["drawn"] == [5] and report["window"] == [0, 6] and report["drawnAgrees"]
    pane = screen.panes[ClientTest.GRID]
    pane.rowViews[1].visible = False      # 藏着的行不重画，底格可能是旧的：不算
    hidden = ClientTest.flow(session)
    assert hidden["ok"] and hidden["drawn"] == [] and hidden["window"] == [0, 3] and hidden["selected"] == [5], hidden
    assert hidden["drawnAgrees"], "只比绑着的格：选中的那格在藏着的行里"
    pane.views[2]._cellImage._sprite = PotRecipes.CELLS[1]       # 控件上画的和 decorate 算的不一样：报出来
    stale = ClientTest.flow(session)
    assert not stale["ok"] and stale["drawnAgrees"] is False and stale["drawn"] == [2] and "对不上" in stale["why"], stale
    _reset()


# ---------------------------------------------------------------- 不靠指针走一遍界面：服务端


class _ServerSession(object):
    """库的服务端会话（Server/Session）里自检读的那几样。"""

    def __init__(self, viewer, sent=None, menu=None):
        self.id = 9
        self.menu = menu or Libs.create(PotMenu.MENU, {}, Libs.SERVER, RULES)
        self.instance = _Thing(key=((10, 64, -3), 0))
        self.viewer = dict({"picked": -1, "search": "", "pickedAt": 0.0}, **viewer)
        self.dataSent = sent or {}


def testTheServerStateReadsThePickedRowItsRecipeAndTheDetails():
    _reset()
    stew = Search.rows(u"牛炖")[0]
    sent = {"bookResult": {"newItemName": "arris:cookbeef_stew", "newAuxValue": 0, "count": 1}}
    picked = _ServerSession({"picked": stew, "search": u"牛炖", "pickedAt": time.time() - 2.0}, sent)
    other = _ServerSession({}, menu=_Thing(menuName="test:other"))
    report = ServerTest.stateReport({"p2": _ServerSession({}), "p1": picked, "p3": other})
    assert report["ok"] and "why" not in report and [pot["player"] for pot in report["pots"]] == ["p1", "p2"], "别的界面不算，按玩家排"
    one, idle = report["pots"]
    assert one["picked"] == stew and one["search"] == u"牛炖" and 1.5 < one["sincePick"] < 60 and one["session"] == 9, one
    assert one["recipe"]["id"] == "farmersdelight:cooking/beef_stew" and one["recipe"]["result"] == ["arris:cookbeef_stew", 0]
    assert one["recipe"]["title"] == u"牛肉炖" and one["recipe"]["row"] == stew and one["pot"] == repr(((10, 64, -3), 0))
    assert one["bookResult"]["newItemName"] == one["bookResultNow"]["newItemName"] == "arris:cookbeef_stew" and one["consistent"]
    assert idle["recipe"] is None and idle["bookResultNow"] is None and idle["sincePick"] is None and idle["consistent"]
    alone = ServerTest.stateReport({"p1": picked}, "p1")
    assert alone["ok"] and len(alone["pots"]) == 1
    nobody = ServerTest.stateReport({"p1": picked, "p3": other}, "p2")
    assert not nobody["ok"] and nobody["sessions"] == 2 and "没有开着" in nobody["why"] and "p2" in nobody["why"], nobody
    assert ServerTest._consistent(stew, None, None) is False, "选中的那一行后来删掉了（墓碑）：对不上"
    tombstoned = _ServerSession({"picked": len(Recipes.CookingPotRecipeList) + 5})   # 表里没有的行：取不到配方
    wrong = ServerTest.stateReport({"p4": tombstoned})
    assert not wrong["ok"] and wrong["pots"][0]["recipe"] is None and "p4" in wrong["why"], wrong
    _reset()


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
