# -*- coding: utf-8 -*-
"""BookSources - 四个站点交给前置包的食谱书（客户端）

书页在 Shared/Rules/StationBooks.py；这里按站点同步来的数据回答前置包 Client/Book.py 的问话（接口见那里）。
锅、砧板摆盘的菜能从背包放料（书上再点一下选中的那道菜）：发 bookFill {"key", "sets"}，服务端 PotLogic 交给 BookFill.py、BoardLogic 交给 BoardAssemble.py；
切的、煎锅、炉灶的书只看（HoD 一样）。前置包太旧、视图没有 book 接口时什么都不做。
配置里关了食谱书（recipe_book，HandsOnConfig.recipeBook()：RecipeBook.opened / frame 里关着就不开、书的节点收起）：四个站点都经 attach 挂书，
这里一处不挂，站点旁就没有书；书是客户端的东西，服务端的放料动作（bookFill）照旧校验，不看这个开关。
"""
from ...Shared.Rules import BoardStation, GrillStation, PanStation, PotStation
from ...Shared.Rules import HandsOnOptions as Options
from ...Shared.Rules import StationBooks as Books
from ...Shared.Rules.HandsOn import PotBonus


class _Source(object):
    def __init__(self, view):
        self.view = view
        self._pages = None

    def pages(self):
        if self._pages is None:
            self._pages = self.build()
        return self._pages

    def build(self):
        return []

    def tabs(self):
        return []

    def inStation(self):
        return []

    def current(self):
        return None

    def canFill(self, key):
        return False

    def fill(self, key, sets):
        self.view.sendAction("bookFill", {"key": key, "sets": int(sets)})


class PotSource(_Source):
    def build(self):
        return Books.potPages()

    def inStation(self):
        return [item for item in self.view.state.getItems(PotStation.GROUP_INGREDIENTS) if item]

    def current(self):
        return Books.potCurrent(self.inStation(), self.view.data.get("meal"))

    def canFill(self, key):
        return Books.potRecipe(key) is not None

    def stars(self, key):
        """这道菜本人开了几颗星、离下一颗多远、搅满多送百分之几（HoD：盛出满 8 份开第 2 颗，满 32 份第 3 颗）。"""
        recipe = Books.potRecipe(key)
        result = recipe.get("CookResult") if recipe else None
        if not result:
            return None
        made = int((self.view.data.get("made_all") or {}).get(result[0]) or 0)
        opened = PotBonus.openStars(made)
        return {"open": opened, "next": PotBonus.nextStar(made), "bonus": PotBonus.bonusPercent(opened)}


class BoardSource(_Source):
    def build(self):
        return Books.boardPages()

    def tabs(self):
        return Books.BOARD_TABS

    def _layers(self):
        return [item for item in self.view.state.getItems(BoardStation.GROUP_LAYERS) if item]

    def inStation(self):
        board = self.view.state.getItem((BoardStation.GROUP_BOARD, 0))
        return self._layers() + ([board] if board else [])

    def current(self):
        return Books.boardCurrent(self._layers(), self.view.state.getItem((BoardStation.GROUP_BOARD, 0)))

    def canFill(self, key):
        return bool(Books.dishOf(key))


class PanSource(_Source):
    def build(self):
        return Books.panPages()

    def inStation(self):
        return [item for item in self.view.state.getItems(PanStation.GROUP_PAN) if item]

    def current(self):
        return Books.cookCurrent(self.inStation())


class GrillSource(_Source):
    def build(self):
        return Books.grillPages()

    def inStation(self):
        return [item for item in self.view.state.getItems(GrillStation.GROUP_GRILL) if item]

    def current(self):
        return Books.cookCurrent(self.inStation())


SOURCES = {"pot": PotSource, "board": BoardSource, "pan": PanSource, "grill": GrillSource}


def attach(view, kind):
    """开站时把这个站点的书交给前置包；配置里关了食谱书就不挂。"""
    book = getattr(view, "book", None)
    if book is not None and Options.recipeBook():
        book(SOURCES[kind](view))


def refresh(view):
    """站点里的东西变了：书马上重算一次（没挂书就没有可算的）。"""
    refreshBook = getattr(view, "refreshBook", None)
    if refreshBook is not None and Options.recipeBook():
        refreshBook()
