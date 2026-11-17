# -*- coding: utf-8 -*-
# runner: both
"""HoD 配置里的 recipe_book（Compat/Diegesis/BookSources）：关了，四个站点旁都不挂食谱书（HandsOnConfig.recipeBook()：RecipeBook 里关着就不开、书的节点收起）；
缺省照旧挂。四个站点的表现开站时都经同一个 attach 挂书，所以一处就管全。前置包太旧（视图没有 book 接口）时两种配置都什么也不做。"""
from __future__ import print_function

import io
import os

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import dgstation
import fdtest
import panclient as C
from optkit import Config

dgstation.install()
BookSources = C.load("Compat.Diegesis.BookSources")
Scenes = C.load("Compat.Diegesis.PanScenes")
PanView = C.load("Compat.Diegesis.PanView")
POS = C.POS
KINDS = ("pot", "board", "pan", "grill")
SOURCE_OF = {"pot": "PotSource", "board": "BoardSource", "pan": "PanSource", "grill": "GrillSource"}


class View(object):
    """前置包的视图：只记下挂上去的书和重算了几次。"""

    def __init__(self):
        self.hung, self.refreshed = [], 0

    def book(self, source):
        self.hung.append(source)

    def refreshBook(self):
        self.refreshed += 1


def testEveryStationHangsItsBookByDefault():
    for kind in KINDS:
        view = View()
        BookSources.attach(view, kind)
        BookSources.refresh(view)
        assert [source.__class__.__name__ for source in view.hung] == [SOURCE_OF[kind]] and view.refreshed == 1, kind


def testWithTheRecipeBookOffNoStationHangsABook():
    with Config(recipe_book=False):
        for kind in KINDS:
            view = View()
            BookSources.attach(view, kind)
            BookSources.refresh(view)
            assert view.hung == [] and view.refreshed == 0, kind
    view = View()
    BookSources.attach(view, "pan")
    assert len(view.hung) == 1, "with 块出来放回原样"


def testOtherSwitchesDoNotTouchTheBook():
    with Config(cooking_pot=False, skillet=False, stove=False, cutting_board=False, stirring_required=False, cooking_pot_time=5.0):
        view = View()
        BookSources.attach(view, "pot")
        assert len(view.hung) == 1, "站点关了的书这里不管：站点没登记，也就没有视图来挂"


def testAnOldKernelWithoutTheBookInterfaceIsLeftAlone():
    class Old(object):
        pass
    for flag in (True, False):
        with Config(recipe_book=flag):
            for kind in KINDS:
                BookSources.attach(Old(), kind)
                BookSources.refresh(Old())


def testTheRealPanViewHangsNoBookWhenTheOptionIsOff():
    for flag, hung in ((True, True), (False, False)):
        C.install().reset()
        C.world.blocks[POS] = ("arris:skillet", 0)
        Scenes._scenes.clear()
        Scenes.enable()
        behavior = PanView.register(C.makeApi())(C.FakeView(POS, 0, None))
        with Config(recipe_book=flag):
            behavior.onOpen()
            assert (behavior.view.booked is not None) is hung, flag


def testAllFourStationViewsHangTheirBookThroughTheOneFunction():
    # 开关只在 BookSources.attach 里查：每个站点的表现开站时都得经它挂书，别的写法会绕过开关
    folder = os.path.join(fdtest.BP, fdtest.SCRIPTS, "Compat", "Diegesis")
    for kind, view in (("pot", "PotView"), ("board", "BoardView"), ("pan", "PanView"), ("grill", "GrillView")):
        source = io.open(os.path.join(folder, view + ".py"), encoding="utf-8").read()
        assert 'BookSources.attach(self.view, "%s")' % kind in source, view
        assert ".book(" not in source and "BookPanel" not in source, view + "：别的路挂书会绕过 recipe_book"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
