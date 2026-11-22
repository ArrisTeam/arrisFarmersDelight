# -*- coding: utf-8 -*-
"""
按行回收的格子区（运行时控件 scroll_grid，docs/ARCHITECTURE.md 第 3.10 节；布局里的写法见 Std/Windowed/Common.py）。
配按窗口拉取的同步方式用：容器再大，控件数也不变。

引擎滚动视图里按行回收的格子：行控件比可见行多上下各两行，轮流显示内容的行，只有离开窗口的行控件换绑、挪位置
（RowWindow），所以手柄焦点所在的控件不会被换走，引擎把焦点滚进视口的行为与原版一致。
打开界面时视口下面多出来的那几行先藏着、不往里写物品（引擎把一整行控件显示出来要花半毫秒以上），
滚到离视口两行以内时再显示；显示过的不再藏，手柄焦点所在的行不会因为滚动被藏掉（焦点会跳走）。
经典版容器区固定 9 列：内容一超出视口，引擎当帧就显示滚动条、把视口挤窄，按宽度算列数会在那一帧排成 8 列再排回来
（看着是一闪），所以列数可以固定（fixedColumns），内容高度也由界面给上限（不滚动时不超出视口）。
"""
import math

from ...Client import Layout, Widgets
from ...Client.Views import Placed
from ..Client.Widgets import WINDOW_MARGIN, RowWindow, ScrollArea  # noqa: F401  按行回收（与列表共用）

PREFETCH = 256       # 窗口之外预先要的格数


class ScrollGrid(ScrollArea):
    """
    绑定：columns（最多几列）、poolRows（行控件数）、shownRows（JSON 里默认可见的行数）、fixedColumns。
    行控件 r0、r1……各带 columns 个格子控件 s0、s1……；refAt(k) 给出第 k 个格子控件显示的格子（集合的第几格）。
    格子在行里的位置写在 JSON 里不动，网格的左边距挪整行。
    """

    def __init__(self, screen, path, spec):
        ScrollArea.__init__(self, screen, path, spec)
        poolRows, slotSize, maxColumns = spec["poolRows"], self.slot, self.maxColumns
        self.shownRows = spec["shownRows"]
        self.window = RowWindow(poolRows, slotSize)
        prefix = self.contentPath or ""
        self.rowViews = [Placed(screen, "%s/r%d" % (prefix, row), visible=row < self.shownRows,
                                position=(0, row * slotSize))
                         for row in range(poolRows)]
        self.views = [self.viewClass(screen, "%s/r%d/s%d" % (prefix, row, column), (column * slotSize, 0))
                      for row in range(poolRows) for column in range(maxColumns)]

    def contentRows(self):
        return Layout.contentRows(self.count, self.columns or 1)

    def covers(self, ref):
        return ref is not None and ref[0] == self.collection

    def indexIn(self, ref):
        return ref[1]

    def positionOf(self, ref):
        """格子 ref 在滚动内容里的位置（它所在的行此刻没有行控件显示时为 None）。"""
        if ref[0] != self.collection or not self.columns:
            return None
        row, column = divmod(ref[1], self.columns)
        if row not in self.window.rows:
            return None
        return (self.left + column * self.slot, row * self.slot)

    def sync(self, count, limit=None):
        """每帧：列数、内容高度（limit 是上限）、滚动位置，给离开窗口的行控件分配新行。返回有没有要重画的变化。"""
        if not self.valid():
            return False
        changed = self._measure()
        if changed:
            self.window.reset()
        if count != self.count:
            self.count = count
            changed = True
        self._setContentRows(self.contentRows(), limit)
        if self.memory.restore():
            # 刚滚回记着的位置：第 0 个行控件（缺省焦点在它上面）摆到最上面那一行，引擎不为了露出焦点再滚
            self.top = self.readTop()
            self.window.place(self.top, self.contentRows(), int(self.top // self.slot))
            changed = True
        self.top = self.readTop()
        moves = self.window.assign(self.top, self.contentRows())
        first, last = self._shownRows()
        shown = False
        for placed, contentRow in zip(self.rowViews, self.window.rows):
            if contentRow is not None:
                placed.place(self.left, contentRow * self.slot)
            # 没分到行的藏起来（JSON 里开头几行默认可见）；还没显示过的等滚近了再显示，新显示出来的行要重画
            visible = contentRow is not None and (placed.shown() or first <= contentRow < last)
            shown = shown or (visible and not placed.shown())
            placed.setVisible(visible)
        if changed or moves or shown:
            self.revision += 1
            return True
        return False

    def _shownRows(self):
        """
        必须画出来的内容行 [first, last)：与视口相交的行，上下再各加 WINDOW_MARGIN 行（手柄焦点要能移进视口外的那一行，
        引擎才把它滚进来；滚得快时边上的行也已经画好）。
        """
        first = int(self.top // self.slot) - WINDOW_MARGIN
        last = int(math.ceil((self.top + self.height) / float(self.slot) - 1e-6)) + WINDOW_MARGIN
        return first, last

    def close(self):
        """
        界面关闭、控件树留给下次复用时：滚回顶上，行控件摆回 JSON 初始的样子（第 k 个行控件在第 k 行，只有开头几行显示）。
        下次推入时引擎挑默认焦点看到的与新建的树一样，不然焦点可能落在视口下面的行上，一打开就滚动。
        """
        if not self.valid():
            return
        self.memory.close(self.model)
        self.resetScroll()
        self.window.reset()
        for index, placed in enumerate(self.rowViews):
            placed.place(self.left, index * self.slot)
            placed.setVisible(index < self.shownRows)
        self.revision += 1

    def windowRange(self):
        """窗口覆盖的格子下标 [first, last)。"""
        if not self.columns:
            return (0, 0)
        first, last = self.window.window(self.top, self.contentRows())
        return (first * self.columns, last * self.columns)

    def wanted(self):
        """窗口覆盖的那一段，后面再多 PREFETCH 格（滚得快时下面的内容已经到了）。"""
        first, last = self.windowRange()
        return (self.collection, first, last + PREFETCH)

    def indexOf(self, path):
        if not self.contentPath:
            return None
        row = Widgets.indexAfter(path, self.contentPath + "/r")
        if row is None or row >= len(self.rowViews):
            return None
        column = Widgets.indexAfter(path, "%s/r%d/s" % (self.contentPath, row))
        return None if column is None or column >= self.maxColumns else row * self.maxColumns + column

    def refAt(self, index):
        row, column = divmod(index, self.maxColumns)
        if row >= len(self.window.rows) or self.columns is None or column >= self.columns:
            return None
        contentRow = self.window.rows[row]
        if contentRow is None:
            return None
        slot = contentRow * self.columns + column
        return (self.collection, slot) if slot < self.count else None

    def render(self, displayed, selection, context, showLocks, releaseBar):
        """selection：触屏选中 {"ref", "amount", ...} 或 None；releaseBar：选中框上显示选好的数量与否。返回 {格: 控件}。"""
        refs = {}
        for index, view in enumerate(self.views):
            ref = self.refAt(index)
            if ref is None:
                view.setVisible(False)
                view.drawn = None   # 再分到格子时重画（连同显示出来）
                continue
            if not self.rowViews[index // self.maxColumns].shown():
                continue   # 藏着的行不写（行显示出来时 sync 要求重画）
            if Widgets.redrawSlot(view, ref, displayed(ref), Widgets.selectionFor(selection, ref), context, showLocks,
                                  releaseBar):
                view.setVisible(True)   # 没重画的一直显示着（格子装饰另定了显隐的照装饰）
            refs[ref] = view
        return refs


Widgets.register("scroll_grid", ScrollGrid)
