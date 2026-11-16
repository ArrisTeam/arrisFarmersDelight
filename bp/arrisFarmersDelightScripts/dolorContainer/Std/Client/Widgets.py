# -*- coding: utf-8 -*-
"""
标准库的运行时控件（docs/ARCHITECTURE.md 第 3.10 节；接口见 Client/Widgets.py，布局里的写法见 Std/Components.py）：

- slots：每个格子控件固定对应一个格子，不滚动（单格、网格、经典版的主背包与快捷栏）；
- scroll_slots：引擎滚动视图里的固定格子，每格一个控件，列数按视口宽度算（携带版的背包区，36 格）；
- clip：绑定界面数据的裁剪贴图（熔炉的火焰与箭头）；
- text：按格式串写字（界面数据、每位查看者的状态、客户端界面状态）；
- text_box：文本框（输入结束时提交成动作，或每打一个字改客户端界面状态；搜索框也是它）；
- button、toggle、cycle_button、tab：按钮、开关、循环按钮、页签（按原版"交互"时机发动作或改客户端界面状态）；
- slider：滑块（松手时或拖动中节流发动作，或改客户端界面状态）；
- dropdown：原版下拉（开合与单选由引擎做，这里给出选项与选中的项，选了发动作或改客户端界面状态）；
- list：列表（滚动的按行回收，或分页），点一行选中，行里的按钮发动作；
- bar：条（连续的按比例裁，一格一格的每个图标显示空、半或满）；gauge：仪表（资源的填充与贴图、悬停文本、点了发动作）；
- doll：纸娃娃（按实体编号的实体、方块、骨骼模型；看着指针、自己转；引擎接口在 Std/Client/Dolls.py；装备穿在盔甲架上的预览
  交给原版的装备预览渲染器）；banner：旗帜（交给原版的旗帜图案渲染器）；
- item：物品图标（不是格子：图标、数量、耐久条，悬停写物品的悬停文本）；tooltip：提示区域（悬停时按格式串写悬停文本；
  按钮类控件的 $dc_tooltip 也是它的写法）；window：可拖动的子窗口（位置记在客户端界面状态里）；
- visible：按值显隐（布局里普通控件上的 $dc_visible）。
按行回收的格子区（scroll_grid）在 Std/Windowed/Client.py，与 scroll_slots 共用这里的 ScrollArea，与列表共用 RowWindow。

滚动本身（滚轮、拖动、滚动条、触屏惯性、手柄焦点滚进视口）全由引擎的滚动视图处理；这里每帧读滚动位置与视口尺寸，
按列数排格子、设内容高度。滚动视图的内容路径在键鼠与触屏两种样式下不同（按平台定，界面建好后不变），建界面时向滚动视图要。
每个格子区另有一个收纳袋张开的覆盖层（bundleOpen），与格子在同一个父控件里（滚动时一起被视口裁剪），
positionOf 给出某一格在那里的位置。

写自定义控件用得着的公开件：utf8、cutText、withoutName（文字与物品堆的小工具）；Label、Sprite（字、贴图没变时不调用引擎）；
TextPattern、FormattedLabel（格式串，与库的文字控件同一套）；Flip（几对控件按值切换）；Pending（发改一个值的动作，应答回来之前
显示成正在改的值）；holds（$dc_visible 写法的条件）；RowWindow、ScrollPort、ScrollArea（按行回收与滚动视图）；fluidBands、
equipmentBag。库的控件可派生、改写方法（见各控件的说明）：仪表与流体堆叠的 tipText、textureOf；物品图标的 stackOf、tipText、
countText、durability；列表的行部件（RowPart，registerRowPart 登记）；纸娃娃的种类（registerDollKind 登记）。
"""
import math

from ...Client import Display, Layout, Paths, Widgets
from ...Client.BundleViews import BundleOpen
from ...Client.Views import Fade, ItemView, Lazy, Placed
from ...Common import Data, Items
from ...Common.Slots import TOUCH
from .. import Banners, TextFormat
from ..Measures import (BLOCK_FIT, DOLL_STAGE, EYE_HEIGHT, FLUID_LAYERS, FLUID_MIN_BAND, GAUGE_FILL, GAUGE_INSET,
                        GAUGE_TIP_NAMES, PAGE_ARROWS, PAGE_FORMAT, PAGE_NAMES, PLAYER_PIXELS, STATE_TEXT_LIMIT,
                        dropdownLabel, dropdownOption, dropdownShown, dropdownText)
from . import Dolls

try:
    _TEXT = (str, unicode)  # noqa: F821
except NameError:
    _TEXT = (str,)


def utf8(text):
    """py2 下 unicode 编成 utf-8 的 str（引擎的文本接口只收 str）。"""
    return text if isinstance(text, str) else text.encode("utf-8")


def cutText(text, limit):
    """截到 limit 个字（按字数，不按字节）。"""
    chars = text.decode("utf-8") if isinstance(text, bytes) else text
    return utf8(chars[:limit])


def withoutName(stack):
    """去掉自定名字的副本（附加数据 display 里的 Name；display 空了整个拿掉）。没有自定名字时原样返回。"""
    if Items.customName(stack) is None:
        return stack
    user = dict(stack.get("userData") or {})
    display = dict(user.get("display") or {})
    display.pop("Name", None)
    display.pop("FilteredName", None)
    if display:
        user["display"] = display
    else:
        user.pop("display", None)
    return dict(stack, userData=user or None)


class FixedSlots(Widgets.SlotArea):
    """
    绑定：first、count、columns，pitch（相邻两格的间距，没有时是格子的边长；格子居中在间距里），dim（图标画暗的绑定名：
    单格是一个名字，网格是每格一个的列表）。第 k 个控件对应集合的第 first + k 格；控件按列数从左上排起（位置已写在界面 JSON
    里）。有 dim 时向引擎登记它们，按格子装饰画暗（格子控件的 dimmed）。有 flow（rows 或 columns，另有 rows 与 center）时按集合实际的格数重排（见
    Std/Components 的网格）：多出来的控件藏起来、不算在格子区里，显示的那几格按保持的行数或列数从左上排，center 时居中。
    """

    def __init__(self, screen, path, spec):
        Widgets.SlotArea.__init__(self, screen, path, spec)
        self.refs = [(self.collection, spec["first"] + index) for index in range(spec["count"])]
        self._refSet = set(self.refs)
        self.pitch = spec.get("pitch", self.slot)
        self.inset = (self.pitch - self.slot) / 2.0
        self.flow = spec.get("flow")
        self.shown = None   # 重排的网格显示着几格（还没同步过为 None）
        columns = self.columns
        for index in range(len(self.refs)):
            row, column = divmod(index, columns)
            self.views.append(self.viewClass(screen, "%s/s%d" % (path, index), self._at(column, row)))
        self.bundleOpen = BundleOpen(screen, path + Paths.BUNDLE_OPEN)

    def _at(self, column, row, dx=0.0, dy=0.0):
        return (dx + column * self.pitch + self.inset, dy + row * self.pitch + self.inset)

    def sync(self, count, limit=None):
        if self.flow is None:
            return False
        shown = max(0, min(len(self.views), count - self.spec["first"]))
        if shown == self.shown:
            return False
        self.shown = shown
        layoutRows = self.spec["rows"]
        if self.flow == "rows":
            rows, columns = layoutRows, max(1, -(-shown // layoutRows))
        else:
            columns = self.columns
            rows = max(1, -(-shown // columns))
        dx = dy = 0.0
        if self.spec.get("center"):
            dx = (self.columns - min(columns, self.columns)) * self.pitch / 2.0
            dy = (layoutRows - min(rows, layoutRows)) * self.pitch / 2.0
        for index, view in enumerate(self.views):
            if index < shown:
                row, column = divmod(index, columns)
                view.place(*self._at(column, row, dx, dy))
            view.setVisible(index < shown)
        Widgets.forgetDrawn(self.views)
        self.revision += 1
        return True

    def _count(self):
        return len(self.refs) if self.shown is None else self.shown

    def bind(self, binder):
        dim = self.spec.get("dim")
        if dim:
            # 单格是一个名字，网格每格一个（编译按布局生成）：引擎按名字来要这一格画不画暗
            for name, view in zip(dim if isinstance(dim, list) else [dim], self.views):
                binder.boolean(name, lambda view=view: view.dimmed)

    def positionOf(self, ref):
        return self.views[self.refs.index(ref)].position() if self.covers(ref) else None

    def covers(self, ref):
        return ref in self._refSet and self.refs.index(ref) < self._count()

    def indexIn(self, ref):
        return self.refs.index(ref)

    def indexOf(self, path):
        index = Widgets.indexAfter(path, self.path + "/s")
        return index if index is not None and index < self._count() else None

    def refAt(self, index):
        return self.refs[index] if 0 <= index < self._count() else None

    def render(self, displayed, selection, context, showLocks, releaseBar):
        refs = {}
        shown = self._count()
        for view, ref in zip(self.views[:shown], self.refs[:shown]):
            Widgets.redrawSlot(view, ref, displayed(ref), Widgets.selectionFor(selection, ref), context, showLocks,
                               releaseBar)
            refs[ref] = view
        return refs


WINDOW_MARGIN = 2    # 行回收时可见行上下各多留的行数（按行回收的格子区与列表共用）


class RowWindow(object):
    """
    行控件的环形回收。rows[k] 是第 k 个行控件现在显示的内容行（没在用时为 None）。
    窗口取视口顶边所在行往上 WINDOW_MARGIN 行起、共 len(rows) 行（不超出内容），只给离开窗口的行控件换新行。
    """

    def __init__(self, poolRows, slot, margin=WINDOW_MARGIN):
        self.rows = [None] * poolRows
        self.slot = slot
        self.margin = margin

    def window(self, top, total):
        """视口顶边在内容的 top 处、内容共 total 行时，窗口覆盖的内容行 [first, last)。"""
        size = len(self.rows)
        first = max(0, int(top // self.slot) - self.margin)
        last = min(total, first + size)
        return max(0, last - size), last

    def reset(self):
        """列数变了：每一行显示的格子都变了，全部重新分配。"""
        self.rows = [None] * len(self.rows)

    def place(self, top, total, startRow):
        """
        按窗口重新分配全部行控件，第 0 个行控件显示 startRow（打开后滚回记着的位置时：缺省焦点在第 0 个行控件上，让它留在
        视口里，引擎不为了露出焦点再滚一次）。
        """
        first, last = self.window(top, total)
        rows = list(range(first, last))
        if startRow in rows:
            index = rows.index(startRow)
            rows = rows[index:] + rows[:index]
        self.rows = rows + [None] * (len(self.rows) - len(rows))

    def assign(self, top, total):
        """按新的窗口重新分配，返回有变化的 [(行控件, 新内容行或 None)]；没离开窗口的行控件不动。"""
        first, last = self.window(top, total)
        wanted = set(range(first, last))
        free = []
        for index, row in enumerate(self.rows):
            if row is not None and row in wanted:
                wanted.discard(row)
            else:
                free.append(index)
        changes = []
        for row in sorted(wanted):
            index = free.pop(0)
            self.rows[index] = row
            changes.append((index, row))
        for index in free:
            if self.rows[index] is not None:
                self.rows[index] = None
                changes.append((index, None))
        return changes

    def rowOf(self, contentRow):
        """显示内容第 contentRow 行的行控件；不在窗口里时为 None。"""
        try:
            return self.rows.index(contentRow)
        except ValueError:
            return None


class ScrollPort(object):
    """
    引擎的滚动视图（原版滚动面板）：内容路径、视口、内容高度、滚动位置，格子区（ScrollArea）与列表共用。内容路径在键鼠与
    触屏两种样式下不同（按平台定，界面建好后不变），建界面时向滚动视图要。
    """

    def __init__(self, screen, path):
        self.screen = screen
        control = screen.GetBaseUIControl(path)
        self.scrollView = control.asScrollView() if control is not None else None
        content = self.scrollView.GetScrollViewContentPath() if self.scrollView is not None else ""
        self.contentPath = content or None
        self.touchBar = bool(content) and "/scroll_touch/" in content   # 触屏样式：滚动条盖在内容上，不占宽度
        self.content = Placed(screen, content) if content else None
        self.viewport = screen.GetBaseUIControl(content.rsplit("/", 1)[0]) if content else None
        # 滚动条连同轨道（与视口并排，内容 -> 视口 -> 视口与背景 -> 滚动视图里的那一层）
        self.bar = Lazy(screen, content.rsplit("/", 3)[0] + "/bar_and_track") if content else None
        self.contentHeight = None

    def valid(self):
        return self.scrollView is not None and self.viewport is not None and self.content is not None

    def setContentHeight(self, height, refresh=True):
        """
        设内容高度（没变时不调用引擎）。refresh 为真时让引擎刷新界面：滚动条滑块的长短才会跟着变（内容不超出视口、
        没有滚动条时不用）。
        """
        if height != self.contentHeight:
            self.contentHeight = height
            self.content.setHeight(height)
            if refresh:
                self.screen.UpdateScreen(False)

    def barShown(self):
        """引擎此刻有没有显示滚动条。引擎按上一次排版时内容与视口的尺寸决定显隐，比尺寸的变化晚一帧。"""
        bar = self.bar.get() if self.bar is not None else None
        return bar is not None and bool(bar.GetVisible())

    def readTop(self):
        top = self.scrollView.GetScrollViewPos()
        return float(top) if top is not None else 0.0

    def resetScroll(self):
        """回到顶上。"""
        if self.valid():
            self.scrollView.SetScrollViewPos(0)


SCROLL_RESTORE_FRAMES = 10   # 打开后滚回记着的位置：引擎没收下（内容的排版还没跟上）时接着设，最多这么多帧


class ScrollMemory(object):
    """
    滚动位置记在客户端界面状态里（组件的 $dc_scroll，绑定的 scroll）：会话写回客户端界面状态之前（控件的 remember）与界面
    关闭时（close）记下，开的时候滚回去——内容高度设好之后（restore，每帧调，只在还没滚回去时做事）设一次，引擎没收下时
    下一帧再设，最多 SCROLL_RESTORE_FRAMES 帧（内容变短了滚不到的就停在能滚到的地方）。step 是行高：滚回的位置对齐到整行
    （按行回收的控件把第 0 个行控件摆到最上面那一行，缺省焦点在它上面时整个露出来）。只在开、关界面时各多做一次，滚动中
    不写。没写 $dc_scroll 的什么都不做。
    """

    def __init__(self, port, name, step=None):
        self.port, self.name, self.step = port, name, step
        self.pending = None
        self.tries = 0

    def open(self, model):
        wanted = model.clientValue(self.name) if self.name else 0
        if wanted and wanted > 0 and self.step:
            wanted = int(round(float(wanted) / self.step)) * self.step
        self.pending = int(wanted) if wanted and wanted > 0 else None
        self.tries = 0

    def restore(self):
        """还没滚回去时设一次滚动位置；返回这一帧是不是刚滚回去（之后不再设）。"""
        if self.pending is None or not self.port.valid():
            return False
        self.tries += 1
        self.port.scrollView.SetScrollViewPos(self.pending)
        if abs(self.port.readTop() - self.pending) < 1.0 or self.tries >= SCROLL_RESTORE_FRAMES:
            self.pending = None
            return True
        return False

    def remember(self, model):
        """记下滚到哪（还没滚回记着的位置时不记，免得把没滚回去的位置当成玩家滚到的）。"""
        if self.name and model is not None and self.pending is None and self.port.valid():
            model.setClientValue(self.name, int(round(self.port.readTop())))

    def close(self, model):
        self.remember(model)
        self.pending = None


class ScrollArea(Widgets.SlotArea):
    """
    引擎滚动视图里的格子区：视口尺寸、列数、内容高度、滚动位置。columns 是最多几列；fixedColumns 为真时列数固定为它、
    网格靠左，不按视口宽度算；align 为 left 时按宽度算列数、网格靠左（缺省居中）。界面打开时滚回顶上；绑定有 scroll 时
    关的时候记下滚动位置、开的时候滚回去（ScrollMemory）。
    """

    def __init__(self, screen, path, spec):
        Widgets.SlotArea.__init__(self, screen, path, spec)
        self.maxColumns = spec["columns"]
        self.columns = None
        self.fixedColumns = bool(spec.get("fixedColumns"))
        self.alignLeft = spec.get("align") == "left"
        port = self.port = ScrollPort(screen, path)
        content = port.contentPath or ""
        self.scrollView, self.contentPath, self.touchBar = port.scrollView, port.contentPath, port.touchBar
        self.content, self.viewport = port.content, port.viewport
        self.left = 0.0
        self.height = 0.0
        self.count = 0
        self.top = 0.0
        self.bundleOpen = BundleOpen(screen, content + Paths.BUNDLE_OPEN) if content else None
        self.memory = ScrollMemory(port, spec.get("scroll"), self.slot)

    def open(self, model):
        Widgets.SlotArea.open(self, model)
        self.resetScroll()
        self.memory.open(model)

    def remember(self):
        self.memory.remember(self.model)

    def close(self):
        self.memory.close(self.model)

    def valid(self):
        return self.port.valid()

    def _measure(self):
        """读视口尺寸：宽度定列数与左边距（列数固定的不看宽度），高度记下（判断哪些行要画）；返回列数或左边距有没有变。"""
        width, self.height = self.viewport.GetSize()
        if self.fixedColumns:
            columns, left = self.maxColumns, 0.0
        else:
            columns = Layout.gridColumns(width, self.slot, self.maxColumns)
            left = 0.0 if self.alignLeft else Layout.gridLeft(width, columns, self.slot)
        if (columns, left) == (self.columns, self.left):
            return False
        self.columns, self.left = columns, left
        return True

    def _setContentRows(self, rows, limit=None):
        """
        内容高度跟着行数变，limit 是上限（超出的行照样画，由视口裁剪）。改了高度要让引擎刷新界面，滚动条滑块的长短才会
        跟着变；有上限时内容不超出视口、没有滚动条，不用刷新。
        """
        height = rows * self.slot
        if limit is not None and height > limit:
            height = limit
        self.port.setContentHeight(height, limit is None)

    def barShown(self):
        """引擎此刻有没有显示滚动条（见 ScrollPort.barShown）。"""
        return self.port.barShown()

    def readTop(self):
        return self.port.readTop()

    def resetScroll(self):
        """回到顶上（打开界面时）。"""
        if self.valid():
            self.port.resetScroll()
            self.top = 0.0


class ScrollSlots(ScrollArea):
    """
    绑定：first、count、columns（最多几列）。每格一个控件（数量固定），列数随视口宽度。集合现在显示的格数少于控件数时
    （算出的集合按部件的 shown：切石机的配方）多出来的控件藏起来，内容高度按显示的格数算。
    """

    def __init__(self, screen, path, spec):
        ScrollArea.__init__(self, screen, path, spec)
        self.first = spec["first"]
        self.refs = [(self.collection, self.first + index) for index in range(spec["count"])]
        self._refSet = set(self.refs)
        self.count = len(self.refs)
        self.shown = None   # 显示着几个控件（还没同步过为 None）
        prefix = self.contentPath or ""
        self.views = [self.viewClass(screen, "%s/s%d" % (prefix, index), (0, 0)) for index in range(len(self.refs))]

    def positionOf(self, ref):
        return self.views[self.refs.index(ref)].position() if ref in self._refSet else None

    def covers(self, ref):
        return ref in self._refSet

    def indexIn(self, ref):
        return self.refs.index(ref)

    def sync(self, count, limit=None):
        if not self.valid():
            return False
        shown = max(0, min(len(self.refs), count - self.first))
        changed = self._measure()
        if changed:
            for index, view in enumerate(self.views):
                row, column = divmod(index, self.columns)
                view.place(self.left + column * self.slot, row * self.slot)
        if changed or shown != self.shown:
            if shown != self.shown:
                for index, view in enumerate(self.views):
                    view.setVisible(index < shown)
                self.shown = shown
            Widgets.forgetDrawn(self.views)
            self._setContentRows(Layout.contentRows(shown, self.columns))
            self.revision += 1
            changed = True
        self.memory.restore()
        self.top = self.readTop()
        return changed

    def indexOf(self, path):
        if not self.contentPath:
            return None
        index = Widgets.indexAfter(path, self.contentPath + "/s")
        return index if index is not None and index < len(self.views) else None

    def refAt(self, index):
        return self.refs[index] if 0 <= index < len(self.refs) else None

    def render(self, displayed, selection, context, showLocks, releaseBar):
        refs = {}
        for view, ref in zip(self.views, self.refs):
            Widgets.redrawSlot(view, ref, displayed(ref), Widgets.selectionFor(selection, ref), context, showLocks,
                               releaseBar)
            refs[ref] = view
        return refs


def _image(control):
    return control.asImage()


class Clip(Widgets.Widget):
    """
    绑定界面数据的裁剪贴图（布局里图片控件上的 $dc_data）。绑定：data 是数据名，steps 是取整的格数，round 为 ceil 时往上取整，
    frames 与 frameLength 是逐帧循环的帧表（见 Std/Components 的 clip）。
    数据是 0–1 的进度，按 steps 格往下取整（原版按像素取整；steps 为 0 时不取整），裁掉其余的部分；
    裁剪方向由布局里图片的 clip_direction 定。每帧按会话里数据现在的值裁，值没变时不调用引擎。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.control = Lazy(screen, path, _image)
        self.dataName = spec["data"]
        self.steps = spec.get("steps", 0)
        self.ceil = spec.get("round") == "ceil"
        self.frames = spec.get("frames")
        self.frameLength = spec.get("frameLength", 1)
        self._ratio = None   # 裁剪比例 JSON 里可能写了任何值：第一次总要设

    def frame(self, now):
        if self.model is not None:
            self.show(self.model.dataValue(self.dataName, now))

    def show(self, value):
        value = value or 0.0
        if self.frames:
            if value <= 0:
                value = 0.0
            else:
                value = self.frames[int(value // self.frameLength) % len(self.frames)] / float(self.steps)
        value = max(0.0, min(1.0, value))
        if self.steps:
            rounder = math.ceil if self.ceil else math.floor
            value = rounder(value * self.steps + (-1e-6 if self.ceil else 1e-6)) / float(self.steps)
        ratio = 1.0 - value
        if ratio == self._ratio:
            return
        control = self.control.get()
        if control is not None:
            control.SetSpriteClipRatio(ratio)
            self._ratio = ratio


def _label(control):
    return control.asLabel()


def _editBox(control):
    return control.asTextEditBox()


class Label(object):
    """
    一个写字的文字控件：show 的字与上一次的一样时不调用引擎。tip 为真时写的是原版悬停文本（common.hover_text 的属性包里的
    #hover_text；可以多行、可以用 § 颜色，空着时引擎不画）。写自定义控件时用。
    """

    def __init__(self, screen, path, tip=False):
        self.control = Lazy(screen, path, None if tip else _label)
        self.tip = tip
        self.text = None   # 控件上现在的字（JSON 里写的可能是别的：第一次总要设）

    def show(self, text):
        if text == self.text:
            return
        control = self.control.get()
        if control is not None:
            if self.tip:
                control.SetPropertyBag({"#hover_text": text})
            else:
                control.SetText(text)
            self.text = text


class Sprite(object):
    """一张换贴图的图片控件：show 的贴图与上一次的一样时不调用引擎。写自定义控件时用。"""

    def __init__(self, screen, path):
        self.control = Lazy(screen, path, _image)
        self.texture = None

    def show(self, texture):
        if texture == self.texture:
            return
        image = self.control.get()
        if image is not None:
            image.SetSprite(texture)
            self.texture = texture


class TextPattern(object):
    """
    格式串（Std/TextFormat：{名字}、{名字:格式}）：pattern 是格式串或语言文件的键，names 是它用到的名字（编译时取好，见
    Std/Components.formatNames）。open 时查语言文件、拆好；render 按值现在的样子写成字（算上还没应答的预测）。写自定义控件时
    与 Label 一起用（FormattedLabel 就是这两样）。
    """

    def __init__(self, pattern, names):
        self.pattern = pattern
        self.names = list(names or ())
        self.pieces = []

    def open(self, model):
        # 带花括号的是格式串本身，不是语言文件的键：不经语言文件查（引擎查的时候把 % 当转义吃掉，{x:.0%} 会变成 {x:.0}）
        pattern = self.pattern if not self.pattern or "{" in self.pattern else utf8(model.text(self.pattern))
        try:
            self.pieces = TextFormat.parse(utf8(pattern)) if pattern else []
        except TextFormat.FormatError:
            self.pieces = [(self.pattern, None, "")]   # 语言文件里的那一条写错了：照原样显示

    def render(self, model, now, extra=None):
        """extra 是格式串里另有的名字的值（列表的一行：value、index、number），优先于界面模型的名字。"""
        values = dict((name, extra[name] if extra is not None and name in extra else model.value(name, now))
                      for name in self.names)
        return TextFormat.render(self.pieces, values, utf8, model.plainItemName, model.text)


class FormattedLabel(TextPattern):
    """
    按格式串写字的文字控件（文字控件上的 $dc_format、按钮上的 $dc_label）：TextPattern 写进 Label，每帧按值现在的样子写，
    字没变时不调用引擎。tip 为真时写的是原版悬停文本（字里的 % 经 Display.hoverLiteral 照原样显示）。
    """

    def __init__(self, screen, path, pattern, names, tip=False):
        TextPattern.__init__(self, pattern, names)
        self.label = Label(screen, path, tip)
        self._values = None   # 上一次写字时用到的值（与这一帧的一样就不拼字）
        self._extra = None    # 上一次交来的这一行的值（列表按行重用同一个字典）
        self._extraOnly = False   # 用到的名字全在那一行的值里

    def open(self, model):
        TextPattern.open(self, model)
        self._values, self._extra = None, None

    def frame(self, model, now, extra=None):
        if extra is not None and extra is self._extra and self._extraOnly and self.label.text is not None:
            return   # 只用这一行的值，这一行没变
        values = tuple(extra[name] if extra is not None and name in extra else model.value(name, now)
                       for name in self.names)
        self._extra = extra
        self._extraOnly = extra is not None and all(name in extra for name in self.names)
        if values == self._values and self.label.text is not None:
            return   # 用到的值都没变：字也不变（不用格式串的字打开后只写一次）
        self._values = values
        text = TextFormat.render(self.pieces, dict(zip(self.names, values)), utf8, model.plainItemName, model.text)
        self.label.show(Display.hoverLiteral(text) if self.label.tip else text)


class Text(Widgets.Widget):
    """文字控件上的 $dc_format（Std/Components 的 text）。绑定：format（格式串，或语言文件的键）、names（用到的名字）。"""

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.text = FormattedLabel(screen, path, spec["format"], spec.get("names"))

    def open(self, model):
        Widgets.Widget.open(self, model)
        self.text.open(model)

    def frame(self, now):
        if self.model is not None:
            self.text.frame(self.model, now)


class TextBox(Widgets.Widget):
    """
    文本框（Std/Components 的 text_box、search_box）。绑定：box（JSON 里的 text_box_name）；action 与 args（提交的动作，
    字是它的最后一个参数）与 value（平时显示的值），或 state（只改客户端界面状态）；limit（最多几个字，没写时取动作参数的
    上限，只改客户端界面状态的取 STATE_TEXT_LIMIT）；live（每改一个字就提交）；enabled（[绑定名, 名字] 或 [绑定名, 名字, 值]：
    成立时能用；原版文本框按这个全局绑定设能不能用，控件按名字登记取值，变了时当场设一次）；item（改名的框：一件物品的名字）。
    - 打进来的字按动作参数的规则清理（Schema.Text.clean：去掉不允许的字、截到上限）：提交、写进客户端界面状态的都是清理过的；
      框里的字等输入结束才改回清理过的（打字时改，系统输入那一侧对不上）。要打字时就挡掉，在布局里写原版文本框的字类型
      （$text_edit_box_text_type：NumberChars 只收数字），字数上限由引擎在打字时挡；
    - 提交：输入结束或按回车时（live 的每改一个字），字与上一次提交的不同才发动作（live 的输入结束那一次照发）；应答回来之前
      框里留着打的字，被拒时回到 value 的值；
    - 敏感词（照网易版原版铁砧、制图台）：输入结束时引擎换掉了敏感词（结束时的字与打的不一样），或提交的那一次（live 的是输入
      结束那一次）被服务端按敏感词拒了：框里回到这次打字之前的字（改名的框回到物品自定的名字；写了 fallback 的回到这几格里
      第一个有东西的那一格里物品自定的名字；没有就是空的）并提交它，布局里的敏感词提示（Std/Components 的 words_hint）闪一下；
    - 只改客户端界面状态的：每打一个字就改；
    - 平时（没在打字、没在等应答）框里显示 value 现在的值或客户端界面状态，变了跟着改；没有 value 的提交框打开时是空的；
    - 改名的框（照原版铁砧）：框里平时显示 item（物品）的名字（自定的名字或物品本身的名字），物品换了就回到新物品的名字；
      动作的最后两个参数是字与"字与物品的名字一样"（一样就是没改：服务端不知道物品在玩家的语言里叫什么）；
    - placeholder（[绑定名, 集合名, 格号]）：框里没有字时的提示是那一格现在显示的东西的名字（不算自定的名字），原版文本框
      按这个全局绑定取，控件按名字登记取值；
    - multiline（多行的框）：回车换行，不提交（输入结束时照常提交）。
    """

    textFromEnd = 1   # 提交的动作参数里字是倒数第几个（改名的框是倒数第二个；子类可以在字后面再带参数）

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.box = spec["box"]
        self.action = spec.get("action")
        self.args = list(spec.get("args") or ())
        self.valueName = spec.get("value")
        self.state = spec.get("state")
        self.limit = spec.get("limit")
        self.live = bool(spec.get("live"))
        self.enabled = spec.get("enabled")
        self.itemName = spec.get("item")
        self.placeholder = spec.get("placeholder")
        self.fallback = spec.get("fallback")   # 按敏感词回退时取名字的几格（[[集合名, 格号], ...]）
        self.multiline = bool(spec.get("multiline"))
        self._hint = (None, "")   # 提示字：按哪个物品堆对象算的、算出的字
        self.control = Lazy(screen, path, _editBox)
        self.clear = Placed(screen, path + Paths.TEXT_CLEAR_PATH) if spec.get("clear") else None   # 原版的清空按钮
        self.field = None        # 提交的动作的文字参数（Schema.Text）
        self.maxLength = STATE_TEXT_LIMIT
        self._shown = None       # 框里现在的字（控件写的或玩家打的）
        self._editing = False    # 玩家打了字、还没结束输入：这时不按值改框里的字
        self._waiting = 0        # 提交了还没应答的次数：这时也不改
        self._submitted = None   # 上一次提交的字（改名的框：字与是否一样）
        self._usable = None      # 现在能不能用（引擎上设的）
        self._item = _ANY        # 改名的框：框里的名字是按哪件物品给的
        self._typed = None       # 打字时最后的字（输入结束时与它比，看引擎换没换敏感词）；结束过、回退过时是标记
        self._kept = ""          # 这次输入结束时定下的字
        self._before = ""        # 这次打字之前框里的字（按敏感词回退时回到它；改名的框回到物品自定的名字）

    def textBoxes(self):
        return ((self.box, self.action is not None),)

    def open(self, model):
        Widgets.Widget.open(self, model)
        self.field = None
        if self.action is not None:
            action = model.menu.actions.get(self.action)
            position = -2 if self.itemName is not None else -self.textFromEnd
            self.field = action.fields[position] if action is not None and len(action.fields) >= -position else None
        self.maxLength = self.limit if self.limit is not None else \
            (self.field.limit if self.field is not None else STATE_TEXT_LIMIT)
        control = self.control.get()
        if control is not None:
            control.SetEditTextMaxLength(self.maxLength)
        self._shown = None
        self._editing = False
        self._waiting = 0
        self._submitted = None
        self._usable = None
        self._item = _ANY
        self._typed = None
        self._before = ""
        now = model.now()
        self._applyUsable(now)
        wanted = self._wanted(now)
        self._show("" if wanted is None else wanted)

    def _nameOf(self, stack):
        return self.model.plainItemName(stack) if not Items.isEmpty(stack) else ""

    def _hintNow(self):
        """提示字：placeholder 那一格现在显示的东西的名字（去掉自定的名字），空着为空串。按物品堆对象缓存。"""
        if self.model is None:
            return ""
        stack = self.model.displayed(tuple(self.placeholder[1:]))
        if stack is not self._hint[0]:
            text = self.model.plainItemName(withoutName(stack)) if not Items.isEmpty(stack) else ""
            self._hint = (stack, text)
        return self._hint[1]

    def _wanted(self, now):
        """平时框里该显示的字；没有绑值的提交框为 None（框里的字不动）。改名的框只在物品换了时给（新物品的名字）。"""
        if self.state is not None:
            return self.model.clientValue(self.state)
        if self.itemName is not None:
            stack = self.model.value(self.itemName, now)
            if self._item is not _ANY and stack == self._item:
                return None
            self._item = stack
            self._submitted = None
            self._typed = None
            return self._nameOf(stack)
        if self.valueName is None:
            return None
        value = self.model.value(self.valueName, now)
        if value is None:
            return ""
        return utf8(value) if isinstance(value, _TEXT) else str(value)

    def bind(self, binder):
        if self.enabled is not None:
            binder.boolean(self.enabled[0], lambda: self._usableNow(self.model.now()) if self.model is not None else True)
        if self.placeholder is not None:
            binder.string(self.placeholder[0], self._hintNow)
        if self.clear is not None:
            binder.boolean(Paths.TEXT_CLEAR_VISIBLE, lambda: bool(self._shown))

    def _usableNow(self, now):
        return holds(self.model.value(self.enabled[1], now), self.enabled[2:])

    def _applyUsable(self, now):
        """enabled 写了时：值变了当场设一次能不能用（引擎下次更新绑定时也按登记的取值设）。"""
        if self.enabled is None:
            return
        usable = self._usableNow(now)
        if usable != self._usable:
            control = self.control.get()
            if control is not None:
                control.SetTouchEnable(usable)
                self._usable = usable

    def frame(self, now):
        if self.model is None:
            return
        self._applyUsable(now)
        if self.clear is not None:
            # 照原版只在框里有字时显示（原版按全局绑定设显隐：控件按名字登记取值；引擎不是每帧来要，所以当场设）
            self.clear.setVisible(bool(self._shown))
        if self._editing or self._waiting:
            return
        wanted = self._wanted(now)
        if wanted is not None and wanted != self._shown:
            self._typed = None   # 框里的字照值换了：下一次输入结束是新的一次，不当成同一次重报
            self._show(wanted)

    def _show(self, text):
        if text == self._shown:
            return
        control = self.control.get()
        if control is not None:
            control.SetEditText(text)
            self._shown = text

    def _clean(self, text):
        if self.field is not None:
            return self.field.clean(text)
        return cutText(text, self.maxLength)

    def onInput(self, event):
        if event.get("kind") == "clear" and self.model is not None:
            self.clearText()
            return
        if event.get("kind") != "text" or self.model is None:
            return
        raw = event["text"]
        text = self._clean(raw)
        finished = bool(event.get("finished"))
        if not finished and not self._editing:
            self._before = self._shown or ""
        self._editing = not finished
        self._shown = raw
        if finished:
            # 清理掉了字：输入结束（框已经不在打字状态）才改回框里。打字时改，系统输入那一侧记着的字与框里的对不上，
            # 后面打的字就进不来
            self._show(text)
        if self.state is not None:
            self.model.setClientValue(self.state, text)
            return
        if not finished:
            self._typed = text
        elif self._typed is _REFUSED or self._typed is _FINISHED:
            self._show(self._kept)   # 同一次输入结束报了不止一次：框里留着这次定下的字
            return
        elif self._typed is not None and text != self._typed:
            self._typed = _REFUSED
            self._refused()   # 引擎在输入结束时换掉了敏感词
            return
        else:
            self._typed = _FINISHED
            self._kept = text
        if finished or (event.get("enter") and not self.multiline) or self.live:
            self._submit(text, finished)

    def clearText(self):
        """
        框里原版的清空按钮（$text_clear_button_enabled）：清掉框里的字，当作这次输入以空字结束（只改客户端界面状态的框改成空，
        提交的框提交空字；原版创造栏的搜索框点 × 回到全部）。照原版，键鼠与手柄点了之后选中文本框接着打字（触屏只在正在打字
        时）：重新选中也让系统输入那一侧的字跟着清掉（打字途中只改框里的字，后面打的字接不上）；按钮事件结束时引擎清掉选中，
        所以用界面的延后选中。
        """
        editing = self._editing
        self._editing = False
        self._typed = _FINISHED
        self._kept = ""
        self._show("")
        if editing or self.model.device() != TOUCH:
            self.screen.SetSelectControl(self.path, True)
        if self.state is not None:
            self.model.setClientValue(self.state, "")
            return
        self._submit("", True)

    def _submit(self, text, final=False):
        """
        提交框里的字（与上一次提交的一样就不发）。边打边提交的框输入结束时那一次照发；看敏感词的是边打边提交的框输入结束时
        那一次与别的框的每一次：按它的应答看是不是因为敏感词被拒，这一端就查出不合格式（敏感词）时照原版回退。
        """
        args = self._argsFor(text)
        final = final or not self.live
        if args == self._submitted and not (final and self.live):
            return
        self._submitted = args
        if self.call(self.action, self.args + args, self._answeredFinal if final else self._answered):
            self._waiting += 1
        elif final:
            self._typed = _REFUSED
            self._refused()

    def _argsFor(self, text):
        """提交的动作参数里跟在 $dc_args 后面的那几个：字（改名的框再带"字与物品的名字一样"）。"""
        args = [text]
        if self.itemName is not None:
            args.append(text == self._nameOf(None if self._item is _ANY else self._item))
        return args

    def _refused(self):
        """
        框里有敏感词（照网易版原版铁砧、制图台）：回到这次打字之前的字（改名的框回到物品自定的名字，没有就是空的）并提交它，
        敏感词提示闪一下。
        """
        if self.itemName is not None:
            text = self._customName(None if self._item is _ANY else self._item)
        elif self.fallback is not None:
            stacks = [self.model.displayed(tuple(slot)) for slot in self.fallback]
            text = self._customName(next((stack for stack in stacks if not Items.isEmpty(stack)), None))
        else:
            text = self._before
        self._kept = text
        self._show(text)
        self.model.noteRefusedWords()
        self._submit(text)

    def _customName(self, stack):
        """物品自定的名字（照动作参数清理过）；没有为空串。"""
        name = Items.customName(stack)
        return self._clean(utf8(name)) if name is not None else ""

    def _answered(self, ok, result):
        self._waiting = max(0, self._waiting - 1)
        if not ok:
            self._submitted = None   # 被拒：下次同样的字还能再提交

    def _answeredFinal(self, ok, result):
        """看敏感词的那一次提交的应答：服务端按敏感词拒了时照原版回退（又在打字了就不管）。"""
        self._answered(ok, result)
        if not ok and result == "words" and not self._editing and self._typed is not _REFUSED:
            self._typed = _REFUSED
            self._refused()


class Flip(object):
    """几对叠在一起的控件（on、off）：按值切换显示哪一个（JSON 里 off 显示、on 藏着），值没变时不调用引擎。"""

    def __init__(self, screen, pairs):
        self.pairs = [(Placed(screen, on, False), Placed(screen, off, True)) for on, off in pairs]

    def show(self, on):
        for onControl, offControl in self.pairs:
            onControl.setVisible(on)
            offControl.setVisible(not on)


_STATES = ("/default", "/hover", "/pressed")   # 原版按钮的三个状态控件（库组件文件里 toggle、tab 模板的写法）


class Pressable(Widgets.Widget):
    """
    按钮类控件的共同部分（Std/Components 的 button、toggle、cycle_button、tab）。绑定：label 与 names（上面的字，格式串），
    action 与 args（按下发的动作），sound 与 soundVolume（发动作时放的音效与音量），value（显示哪个值），press（按钮名）。按原版"交互"时机按下：
    写了动作的发动作（可预测的动作客户端当场变），没写的改客户端界面状态（local）。每帧写字、按值换样子（show）。
    """

    LABELS = ("/label",)
    TIP = "/hover/tip/text"   # 悬停态里的原版悬停文本

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.labels = [FormattedLabel(screen, path + suffix, spec.get("label") or "", spec.get("names"))
                       for suffix in self.LABELS]
        if "tooltip" in spec:
            self.labels.append(FormattedLabel(screen, path + self.TIP, spec["tooltip"], spec["tooltipNames"], tip=True))
        self.action = spec.get("action")
        self.args = list(spec.get("args") or ())
        self.valueName = spec.get("value")

    def presses(self):
        return (self.spec["press"],) if "press" in self.spec else ()

    def open(self, model):
        Widgets.Widget.open(self, model)
        for label in self.labels:
            label.open(model)

    def frame(self, now):
        if self.model is None:
            return
        for label in self.labels:
            label.frame(self.model, now)
        self.show(now)

    def show(self, now):
        """按值换样子（开关勾没勾、页签选没选）。"""

    def value(self, now):
        return self.model.value(self.valueName, now)

    def onInput(self, event):
        if self.model is None:
            return
        if "push" in self.spec:
            # 推界面的按钮映射到按路径分发的按钮：抬起时推（这时容器界面还在最上面，这一下的抬起不会落到新界面上）
            if event.get("kind") == "button" and not event.get("down"):
                self.model.pushScreen(*self.spec["push"])
            return
        if event.get("kind") != "press":
            return
        if self.action is not None:
            if self.call(self.action, self.args) and self.spec.get("sound"):
                self.model.playSound(self.spec["sound"], self.spec.get("soundVolume", 1.0))
        else:
            self.local(self.model.now())

    def local(self, now):
        """没写动作时按下：改客户端界面状态。"""


class Button(Pressable):
    """按钮：按下发动作，或者把客户端界面状态 state 改成 set，或者推纯客户端界面 push（[命名空间, 名字]），或者关掉界面（close）。"""

    def local(self, now):
        if self.spec.get("close"):
            self.model.requestClose()
        else:
            self.model.setClientValue(self.spec["state"], self.spec["set"])


class TextButton(Button):
    """浅色文字按钮（Std/Components 的 text_button）：字写在四个状态各自的标签上，悬停文本在按钮的悬停态里。"""

    LABELS = ("/button/default/content/label", "/button/hover/content/label", "/button/pressed/content/label",
              "/locked/content/label")
    TIP = "/button/hover/tip/text"


class Toggle(Pressable):
    """开关（勾选框）：value 为真时勾上；没写动作时按下把客户端界面状态 value 取反。"""

    def __init__(self, screen, path, spec):
        Pressable.__init__(self, screen, path, spec)
        self.flip = Flip(screen, [(path + state + "/on", path + state + "/off") for state in _STATES])

    def show(self, now):
        self.flip.show(bool(self.value(now)))

    def local(self, now):
        self.model.setClientValue(self.valueName, not self.value(now))


class Cycle(Pressable):
    """
    循环按钮：没写动作时按下把客户端界面状态 value（枚举）换成下一个取值（最后一个之后回到第一个）。绑定里的 labels
    （{取值: {label, names}}）是按取值写的字：取值变了时上面的字换成那一条（没写到的取值用 label）。
    """

    def __init__(self, screen, path, spec):
        Pressable.__init__(self, screen, path, spec)
        self.valueLabels = spec.get("labels") or {}
        self._labelled = _NOTHING   # 上面的字现在按哪个取值写

    def open(self, model):
        Pressable.open(self, model)
        self._labelled = _NOTHING

    def frame(self, now):
        if self.model is not None and self.valueLabels:
            value = self.value(now)
            if value != self._labelled:
                entry = self.valueLabels.get(value) or {"label": self.spec.get("label") or "",
                                                        "names": self.spec.get("names")}
                for label in self.labels[:len(self.LABELS)]:
                    label.pattern, label.names = entry["label"], list(entry.get("names") or ())
                    label.open(self.model)
                self._labelled = value
        Pressable.frame(self, now)

    def local(self, now):
        values = self.model.menu.clientState[self.valueName].values
        current = self.value(now)
        index = values.index(current) if current in values else -1
        self.model.setClientValue(self.valueName, values[(index + 1) % len(values)])


class Tab(Pressable):
    """页签：value 等于 tab 时是选中的样子（底图与字色都换）；没写动作时按下把客户端界面状态 value 改成 tab。"""

    LABELS = ("/label_on", "/label_off")

    def __init__(self, screen, path, spec):
        Pressable.__init__(self, screen, path, spec)
        self.tab = spec["tab"]
        pairs = [(path + state + "/on", path + state + "/off") for state in _STATES]
        self.flip = Flip(screen, pairs + [(path + "/label_on", path + "/label_off")])

    def show(self, now):
        self.flip.show(self.value(now) == self.tab)

    def local(self, now):
        self.model.setClientValue(self.valueName, self.tab)


LIVE_INTERVAL = 0.1   # 拖动中也发动作的滑块最多隔多久发一次（秒）
SLIDER_RETRY = 0.25   # 引擎没收下写给滑块的值时（控件没有尺寸），隔多久再写（秒）


def _slider(control):
    return control.asSlider()


class Slider(Widgets.Widget):
    """
    滑块（Std/Components 的 slider）。绑定：slider（JSON 里的 slider_name）、value、min、max、step；action 与 args（值是动作的
    最后一个参数）与 live，或者没有动作（改客户端界面状态）。
    引擎的分格滑块按格报格序号（0 起）：拖动中报"没结束"，松手、点轨道、手柄选中后左右键的每一步报"结束"。玩家正在动它时
    引擎不收脚本写的值，所以没在动、没在等应答时才按值现在的样子摆滑块（值没变时不调用引擎）。
    - 发动作的：动着的值记成会话里正在改的值（按名字写的字跟着变）；一下动完了，值与这一下开始时的不同才发，live 的拖动中
      也发，每 LIVE_INTERVAL 秒最多一次；应答都回来了才去掉正在改的值（被拒时回到原来的值）；
    - 改客户端界面状态的：每变一格就改。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.slider = spec["slider"]
        self.low, self.step = spec["min"], spec.get("step", 1)
        self.steps = (spec["max"] - self.low) // self.step + 1
        self.valueName = spec["value"]
        self.action = spec.get("action")
        self.args = list(spec.get("args") or ())
        self.live = bool(spec.get("live"))
        self.control = Lazy(screen, path, _slider)
        self._reset()

    def _reset(self):
        self._index = None      # 滑块上现在摆的格
        self._moving = False    # 玩家正在动（这一下还没完）
        self._waiting = 0       # 发了还没应答的次数
        self._sent = None       # 这一下开始时的值，之后是这一下最后发出的值
        self._unsent = None     # live：拖动中还没发出去的值
        self._lastSend = None
        self._retryAt = 0.0     # 引擎没收下写的值时，到这个时间再写

    def sliders(self):
        return (self.slider,)

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._reset()

    def _indexOf(self, value):
        try:
            index = int(round((float(value) - self.low) / self.step))
        except (TypeError, ValueError):
            index = 0
        return max(0, min(self.steps - 1, index))

    def frame(self, now):
        if self.model is None:
            return
        if self._unsent is not None and now - self._lastSend >= LIVE_INTERVAL:
            self._send(self._unsent, now)
        if self._moving or self._waiting:
            return
        index = self._indexOf(self.model.value(self.valueName, now))
        if index != self._index and now >= self._retryAt:
            control = self.control.get()
            if control is not None:
                control.SetSliderValue(index)
                # 引擎在控件没有尺寸时（还没排版、藏着）不收分格滑块的值：读回来对不上就过一会儿再写
                if int(round(control.GetSliderValue())) == index:
                    self._index = index
                else:
                    self._retryAt = now + SLIDER_RETRY

    def onInput(self, event):
        if event.get("kind") != "slider" or self.model is None:
            return
        try:
            index = max(0, min(self.steps - 1, int(round(event["value"]))))
        except (TypeError, ValueError):
            return
        now = self.model.now()
        value = self.low + index * self.step
        finished = bool(event.get("finished"))
        if not self._moving:
            self._sent = self.model.value(self.valueName, now)   # 这一下开始时的值
        self._index = index
        self._moving = not finished
        if self.action is None:
            self.model.setClientValue(self.valueName, value)
            return
        self.model.setEditing(self.valueName, value)
        if finished:
            self._send(value, now)
        elif self.live:
            if self._lastSend is None or now - self._lastSend >= LIVE_INTERVAL:
                self._send(value, now)
            else:
                self._unsent = value
        self._settle()

    def _send(self, value, now):
        self._unsent = None
        if value == self._sent:
            return
        self._sent = value
        self._lastSend = now
        if self.call(self.action, self.args + [value], self._answered):
            self._waiting += 1

    def _answered(self, ok, result):
        self._waiting = max(0, self._waiting - 1)
        self._settle()

    def _settle(self):
        """不在动、没在等应答：去掉正在改的值，回到界面数据或状态的值（被拒时就是原来的值）。"""
        if not self._moving and not self._waiting and self._unsent is None and self.model is not None:
            self.model.clearEditing(self.valueName)


class Pending(object):
    """
    发改一个值的动作（下拉、列表的选中）：发之前把要改成的值记成会话里正在改的值（读值的地方都先看到它），应答都回来了
    才去掉，回到界面数据或状态的值（被拒时就是原来的值）。
    """

    def __init__(self, widget, name):
        self.widget, self.name = widget, name
        self.waiting = 0

    def reset(self):
        self.waiting = 0

    def send(self, action, args, value):
        model = self.widget.model
        model.setEditing(self.name, value)
        if self.widget.call(action, list(args) + [value], self._answered):
            self.waiting += 1
        elif not self.waiting:
            model.clearEditing(self.name)

    def _answered(self, ok, result):
        self.waiting = max(0, self.waiting - 1)
        if not self.waiting and self.widget.model is not None:
            self.widget.model.clearEditing(self.name)


class Dropdown(Widgets.Widget):
    """
    原版下拉（Std/Components 的 dropdown）。绑定：drop（下拉名，单选项与绑定的名字由它派生）、value；options（静态表
    [[值, 字], ...]）或 source 与 max（选项来自列表，最多 max 项）；placeholder；action 与 args，或者没有动作（改客户端界面状态）。
    开合、单选、点到别处收起都由引擎做（bind 里登记原版下拉）；这里给出选中第几项、开关上的字，选项来自列表时还给出每一项
    的字与显隐。玩家选了一项：发动作的把选的值记成会话里正在改的值再发出去，应答都回来了才去掉（被拒时回到原来的值）；
    没写动作的改客户端界面状态。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.drop = spec["drop"]
        self.valueName = spec["value"]
        self.static = [tuple(entry) for entry in spec["options"]] if spec.get("options") else None
        self.source = spec.get("source")
        self.max = spec.get("max", 0)
        self.placeholder = spec.get("placeholder") or ""
        self.action = spec.get("action")
        self.args = list(spec.get("args") or ())
        self.pending = Pending(self, self.valueName)
        self._options = None   # 选项来自列表时：(列表的值, 选项表)，值没换就不重建（引擎每一项的字与显隐都来问）

    def open(self, model):
        Widgets.Widget.open(self, model)
        self.pending.reset()
        self._options = None

    def bind(self, binder):
        count = len(self.static) if self.static is not None else self.max
        binder.dropdown(self.drop, [dropdownOption(self.drop, index) for index in range(count)], self.selected,
                        self.picked)
        binder.string(dropdownLabel(self.drop), self.label)
        if self.static is None:
            for index in range(count):
                binder.string(dropdownText(self.drop, index), lambda index=index: self.optionText(index))
                binder.boolean(dropdownShown(self.drop, index), lambda index=index: self.optionShown(index))

    def options(self):
        """现在的选项：[(值, 字)]；字为 None 的（选项来自列表）就写值本身。"""
        if self.static is not None:
            return self.static
        values = self.model.value(self.source, self.model.now())
        memo = self._options
        if memo is not None and memo[0] is values:
            return memo[1]
        options = [(value, None) for value in list(values or ())[:self.max]]
        self._options = (values, options)
        return options

    def _text(self, value, label):
        """选项的字：语言文件的键查成文字（不是键时原样）。"""
        text = label if label is not None else (value if isinstance(value, _TEXT) else str(value))
        return utf8(self.model.text(utf8(text)))

    def selected(self):
        """引擎问：选中的是第几项（值不在选项里为 -1）。"""
        if self.model is None:
            return -1
        current = self.model.value(self.valueName, self.model.now())
        for index, (value, _) in enumerate(self.options()):
            if value == current:
                return index
        return -1

    def label(self):
        """开关上的字：选中那一项的字；值不在选项里时是 placeholder。"""
        if self.model is None:
            return ""
        index = self.selected()
        if index < 0:
            return self._text(self.placeholder, None) if self.placeholder else ""
        return self._text(*self.options()[index])

    def optionText(self, index):
        options = self.options() if self.model is not None else ()
        return self._text(*options[index]) if index < len(options) else ""

    def optionShown(self, index):
        return self.model is not None and index < len(self.options())

    def picked(self, index):
        """玩家选了第 index 项（引擎已经收起列表）。"""
        if self.model is None:
            return
        options = self.options()
        if not 0 <= index < len(options):
            return
        value = options[index][0]
        if self.action is None:
            self.model.setClientValue(self.valueName, value)
            return
        if value != self.model.value(self.valueName, self.model.now()):
            self.pending.send(self.action, self.args, value)


_NOTHING = object()
PAGER_BUTTONS = ("prev", "next")   # 分页的列表底下两个翻页按钮（库组件文件里的 list_pager）


class RowPart(object):
    """
    行部件：列表的一行里由控件按这一行画的部分（行里控件上的 $dc_visible、物品图标这类）。列表给每个行控件建一个：
    path 是它在这个行控件里的完整路径，spec 是编译时组件的 rowPart 给的说明（part 是登记的名字）。open(model) 是界面打开，
    frame(model, now, extra) 每帧给显示着的行调（extra 是这一行的 value、index、number），close() 是界面关闭。
    模组写自己的：组件写 rowPart（见 Std/Components 的 ItemIcon），运行时按名字 registerRowPart。
    """

    def __init__(self, screen, path, spec):
        self.screen, self.path, self.spec = screen, path, spec

    def open(self, model):
        pass

    def frame(self, model, now, extra):
        pass

    def close(self):
        pass

    def onScale(self, scale):
        """整屏按比例缩放的布局缩放的比例变了（见 Client/Widgets 的 Widget.onScale）。"""


_rowParts = {}


def registerRowPart(name, partClass):
    """登记行部件（同名的新登记替换旧的）。返回它，可以当类装饰器的内层用。"""
    _rowParts[name] = partClass
    return partClass


class RowVisible(RowPart):
    """行里控件上的 $dc_visible：when 是条件（名字可以是 value、index、number：这一行的），shown 是 JSON 里写定的显隐。"""

    def __init__(self, screen, path, spec):
        RowPart.__init__(self, screen, path, spec)
        self.control = Placed(screen, path, spec.get("shown", True))
        self.name, self.rest = spec["when"][0], tuple(spec["when"][1:])

    def frame(self, model, now, extra):
        value = extra[self.name] if self.name in extra else model.value(self.name, now)
        self.control.setVisible(holds(value, self.rest))


class List(Widgets.Widget):
    """
    列表（Std/Components 的 list）。绑定：items（静态表）或 source（列表的名字）；value（选中的值）与 key（value / index：
    一行按它的值还是序号认）；action 与 args（点一行发的动作）；rowHeight；rows（每个行控件的按钮名 press、行里按钮的
    buttons）；texts（行里按格式串写的文字：path、format、names）、buttons（行里的按钮：path、action、args、label、names）、
    parts（行部件：part、path 与部件自己的说明）；shown（JSON 里一开始显示的行控件数）；分页的另有 pageSize、page（页码的
    客户端界面状态，可以没有）、prev、next、pageFormat 与 pageNames（页码的格式串）、arrows（翻页按钮上的字）。
    - 滚动的：引擎滚动视图里按行回收（RowWindow，同按行回收的格子区）：内容高度按行数设，每帧按滚动位置给离开窗口的行控件
      换行；没显示过的行控件等滚近了再显示（打开时视口下面的不显示：引擎挑默认焦点只在看得见的控件里挑）；
    - 分页的：行控件就是一页，按页码显示那一页的行、没有的藏起来，底下写"n / m"；上一页、下一页两个按钮与滚轮翻页；
    - 每帧给显示着的行按这一行写字（字没变时不调用引擎）、画行部件，选中的行盖一层选中的样子；
    - 点一行：写了动作的发动作（参数再加上这一行；有 value 的把它记成正在改的值，应答回来之前就显示成选中），没写的把
      客户端界面状态 value 改成这一行；行里的按钮发它的动作（参数再加上这一行）。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.static = list(spec["items"]) if spec.get("items") else None
        self.source = spec.get("source")
        self.valueName = spec.get("value")
        self.byIndex = spec.get("key") == "index"
        self.action = spec.get("action")
        self.args = list(spec.get("args") or ())
        self.rowHeight = spec["rowHeight"]
        self.pageSize = spec.get("pageSize")
        self.pageName = spec.get("page")
        self.buttons = spec.get("buttons") or []
        rows = spec["rows"]
        self.shown = spec.get("shown", len(rows))
        if self.pageSize:
            self.port, prefix = None, path + "/rows"
            self.pageLabel = Label(screen, path + "/pager/page")
            self.pageText = TextPattern(spec.get("pageFormat") or PAGE_FORMAT, spec.get("pageNames") or PAGE_NAMES)
            self.arrows = [FormattedLabel(screen, path + "/pager/%s/label" % name, text, ())
                           for name, text in zip(PAGER_BUTTONS, spec.get("arrows") or PAGE_ARROWS)]
        else:
            self.port = ScrollPort(screen, path)
            prefix, self.pageLabel, self.pageText, self.arrows = self.port.contentPath or "", None, None, []
        self.control = Lazy(screen, path)
        self.window = RowWindow(len(rows), self.rowHeight)
        self.rowViews = [Placed(screen, "%s/r%d" % (prefix, index), visible=index < self.shown,
                                position=(0, index * self.rowHeight)) for index in range(len(rows))]
        self.selectedViews = [Placed(screen, "%s/r%d/selected" % (prefix, index), False) for index in range(len(rows))]
        self.labels = []   # 每个行控件里按这一行写的字：行里的文字与按钮上的字
        self.parts = []    # 每个行控件里的行部件
        partSpecs = spec.get("parts") or ()
        self._unknownParts = sorted(set(part["part"] for part in partSpecs if part["part"] not in _rowParts))
        for index in range(len(rows)):
            content = "%s/r%d/content" % (prefix, index)
            labels = [FormattedLabel(screen, content + text["path"], text["format"], text["names"])
                      for text in spec.get("texts") or ()]
            labels += [FormattedLabel(screen, content + button["path"] + "/label", button["label"], button["names"])
                       for button in self.buttons]
            self.labels.append(labels)
            self.parts.append([_rowParts.get(part["part"], RowPart)(screen, content + part["path"], part)
                               for part in partSpecs])
        self._targets = {}   # 按钮名 -> (行控件, 行里第几个按钮；整行为 None)
        for index, row in enumerate(rows):
            self._targets[row["press"]] = (index, None)
            for number, press in enumerate(row["buttons"]):
                self._targets[press] = (index, number)
        self.pageButtons = dict((spec[key], step) for key, step in (("prev", -1), ("next", 1)) if key in spec)
        self.pending = Pending(self, self.valueName) if self.valueName else None
        self.memory = ScrollMemory(self.port, spec.get("scroll"), self.rowHeight) if self.port is not None else None
        self._page = 0        # 页码不记在客户端界面状态里时记在这里（重开从第一页起）
        self._items = []
        self._source, self._sourceItems = None, []   # 上一次取到的值与它的一份列表（值没换就不再复制）
        self._extras = [None] * len(rows)   # 每个行控件上一帧的 (行号, 这一行的值, extra)：没变时交同一个 extra
        self._pageOnly = self.pageText is not None and all(name in PAGE_NAMES for name in self.pageText.names)
        self._pageShown = None   # 页码只用页码与页数时：上一次写的 (页码, 页数)

    def presses(self):
        return tuple(self._targets) + tuple(self.pageButtons)

    def onScale(self, scale):
        for parts in self.parts:
            for part in parts:
                part.onScale(scale)

    def open(self, model):
        Widgets.Widget.open(self, model)
        for label in [label for labels in self.labels for label in labels] + self.arrows:
            label.open(model)
        for arrow in self.arrows:
            arrow.frame(model, model.now())
        if self.pageText is not None:
            self.pageText.open(model)
        for parts in self.parts:
            for part in parts:
                part.open(model)
        for name in self._unknownParts:
            model.log("row part %r of a list is not registered" % (name,))
        self._page = 0
        self._extras = [None] * len(self.rowViews)
        self._pageShown = None
        if self.pending is not None:
            self.pending.reset()
        if self.port is not None:
            self.port.resetScroll()
            self.memory.open(model)

    def items(self, now):
        if self.static is not None:
            return self.static
        values = self.model.value(self.source, now)
        if values is not self._source:
            self._source, self._sourceItems = values, list(values) if values else []   # 值换了才复制一份
        return self._sourceItems

    def keyOf(self, row, items):
        """第 row 行当作"这一行"发出去、与选中的值比的那个值：它的值或序号。"""
        return row if self.byIndex else items[row]

    def page(self):
        return self.model.clientValue(self.pageName) if self.pageName is not None else self._page

    def pages(self, count):
        return max(1, -(-count // self.pageSize))

    def setPage(self, page, count):
        page = max(0, min(self.pages(count) - 1, page))
        if self.pageName is not None:
            self.model.setClientValue(self.pageName, page)
        else:
            self._page = page

    def frame(self, now):
        if self.model is None:
            return
        items = self._items = self.items(now)
        if self.pageSize:
            self._placePage(len(items), now)
        elif not self._scroll(len(items)):
            return
        current = self.model.value(self.valueName, now) if self.valueName else _NOTHING
        extras = self._extras
        for index, row in enumerate(self.window.rows):
            if row is None or not self.rowViews[index].shown():
                continue
            value, known = items[row], extras[index]
            if known is not None and known[0] == row and known[1] is value:
                extra = known[2]   # 这个行控件显示的还是同一行、同一个值
            else:
                extra = {"value": value, "index": row, "number": row + 1}
                extras[index] = (row, value, extra)
            for label in self.labels[index]:
                label.frame(self.model, now, extra)
            for part in self.parts[index]:
                part.frame(self.model, now, extra)
            self.selectedViews[index].setVisible(current is not _NOTHING and self.keyOf(row, items) == current)

    def _scroll(self, count):
        """滚动的：内容高度、按滚动位置给离开窗口的行控件换行、显隐；滚动视图还没建好时返回 False。"""
        port = self.port
        if not port.valid():
            return False
        port.setContentHeight(count * self.rowHeight)
        restored = self.memory.restore()
        top, height = port.readTop(), port.viewport.GetSize()[1]
        if restored:
            self.window.place(top, count, int(top // self.rowHeight))
        self.window.assign(top, count)
        first = int(top // self.rowHeight) - WINDOW_MARGIN
        last = int(math.ceil((top + height) / float(self.rowHeight) - 1e-6)) + WINDOW_MARGIN
        for placed, row in zip(self.rowViews, self.window.rows):
            if row is not None:
                placed.place(0, row * self.rowHeight)
            placed.setVisible(row is not None and (placed.shown() or first <= row < last))
        return True

    def _placePage(self, count, now):
        """分页的：显示这一页的行，没有的藏起来；页码超出时按最后一页显示；底下按页码的格式串写（缺省"n / m"）。"""
        pages = self.pages(count)
        page = max(0, min(pages - 1, self.page()))
        start = page * self.pageSize
        for index, placed in enumerate(self.rowViews):
            row = start + index
            self.window.rows[index] = row if row < count else None
            placed.setVisible(row < count)
        if self._pageOnly and self._pageShown == (page, pages):
            return
        self._pageShown = (page, pages)
        self.pageLabel.show(self.pageText.render(self.model, now, {"page": page + 1, "pages": pages}))

    def onInput(self, event):
        if event.get("kind") != "press" or self.model is None:
            return
        name = event.get("name")
        if name in self.pageButtons:
            self.setPage(self.page() + self.pageButtons[name], len(self._items))
            return
        target = self._targets.get(name)
        row = self.window.rows[target[0]] if target is not None else None
        if row is None or row >= len(self._items):
            return
        key, number = self.keyOf(row, self._items), target[1]
        if number is not None:
            button = self.buttons[number]
            self.call(button["action"], list(button.get("args") or ()) + [key])
        elif self.action is not None:
            if self.pending is None:
                self.call(self.action, self.args + [key])
            elif key != self.model.value(self.valueName, self.model.now()):
                self.pending.send(self.action, self.args, key)
        elif self.valueName is not None:
            self.model.setClientValue(self.valueName, key)

    def remember(self):
        if self.memory is not None:
            self.memory.remember(self.model)

    def onWheel(self, up, pointer):
        """分页的列表：指针在列表上时滚轮翻页（滚动的列表由引擎的滚动视图滚）。"""
        if not self.pageSize or pointer is None or self.model is None:
            return False
        control = self.control.get()
        if control is None:
            return False
        (left, top), (width, height) = control.GetGlobalPosition(), control.GetSize()
        if not (left <= pointer[0] < left + width and top <= pointer[1] < top + height):
            return False
        self.setPage(self.page() + (-1 if up else 1), len(self._items))
        return True

    def close(self):
        """界面关闭、控件树留给下次复用时：滚回顶上，行控件摆回 JSON 初始的样子（第 k 个在第 k 行，只有开头几个显示）。"""
        for parts in self.parts:
            for part in parts:
                part.close()
        if self.port is None or not self.port.valid():
            return
        self.memory.close(self.model)
        self.port.resetScroll()
        self.window.reset()
        for index, placed in enumerate(self.rowViews):
            placed.place(0, index * self.rowHeight)
            placed.setVisible(index < self.shown)


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class Bar(Widgets.Widget):
    """
    条（Std/Components 的 bar）。绑定：value、max 或 maxName；连续的有 steps（裁剪取整的格数，0 为不取整）；一格一格的有
    count（图标数）、half（有没有半格的图）。每帧按值现在的样子画（没变时不调用引擎）：连续的裁 fill，一格一格的每个图标
    显示空、半或满。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.valueName = spec["value"]
        self.maxName = spec.get("maxName")
        self.limit = spec.get("max", 1)
        self.count = spec.get("count")
        if self.count:
            self.half = bool(spec.get("half"))
            self.icons = [(Placed(screen, "%s/i%d/half" % (path, index), False) if self.half else None,
                           Placed(screen, "%s/i%d/full" % (path, index), False)) for index in range(self.count)]
        else:
            self.fill = Clip(screen, path + "/fill", {"data": self.valueName, "steps": spec.get("steps", 0)})

    def fraction(self, now):
        limit = _number(self.model.value(self.maxName, now)) if self.maxName else float(self.limit)
        return 0.0 if limit <= 0 else max(0.0, min(1.0, _number(self.model.value(self.valueName, now)) / limit))

    def frame(self, now):
        if self.model is None:
            return
        fraction = self.fraction(now)
        if not self.count:
            self.fill.show(fraction)
            return
        units = fraction * self.count   # 满了几个图标（带小数）
        for index, (half, full) in enumerate(self.icons):
            filled = units - index
            full.setVisible(filled >= 1.0 - 1e-6)
            if half is not None:
                half.setVisible(0.5 - 1e-6 <= filled < 1.0 - 1e-6)


POINTER_RECHECK = 0.1   # 指针停着时隔多久再量一次控件的位置（控件在停着的指针下挪动时，最多晚这么久跟上）


class _Resources(Widgets.Widget):
    """
    仪表与流体堆叠共同的部分：贴图（textureOf）、名字的字（labelOf）、悬停文本的格式串（绑定里的 tip 这几项，见组件的
    TIPS）。悬停文本只在显示的东西变了时重算；格式串用到界面模型的名字时它们的值也算在里面，liveTip 为真时每帧算。
    """

    TIPS = ()
    liveTip = False   # 派生的控件改写了悬停文本、要每帧算时写 True

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.valueName = spec["value"]
        self.textures = dict(spec.get("textures") or {})
        self.labels = dict(spec.get("labels") or {})
        self.unit = spec.get("unit") or ""
        self.action = spec.get("action")
        self.args = list(spec.get("args") or ())
        self.inset = spec.get("inset", GAUGE_INSET)
        self.patterns = dict((field, TextPattern(spec[field], spec.get(field + "Names")))
                             for field in self.TIPS if spec.get(field))
        # 格式串用到的界面模型的名字（GAUGE_TIP_NAMES 之外的）：它们的值变了悬停文本也重算
        self._modelNames = tuple(sorted(set(name for field in self.TIPS for name in spec.get(field + "Names") or ()
                                            if name not in GAUGE_TIP_NAMES)))
        self.tip = Label(screen, path + "/button/hover/highlight/hover_text", tip=True)
        self._labels = {}       # 资源名 -> 字（打开时查好语言文件）
        self._tipKey = _NOTHING   # 上一次算悬停文本时显示的东西

    def presses(self):
        return (self.spec["press"],) if "press" in self.spec else ()

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._labels = dict((name, utf8(model.text(utf8(label)))) for name, label in self.labels.items())
        for pattern in self.patterns.values():
            pattern.open(model)
        self._tipKey = _NOTHING

    def textureOf(self, name):
        """资源名 name 的填充贴图：$dc_textures 里找，"*" 给没写的名字，再没有就是纯色的白底。"""
        return self.textures.get(name) or self.textures.get("*") or GAUGE_FILL

    def labelOf(self, name):
        """资源名 name 在悬停文本里的字：$dc_labels 里的（查过语言文件），没写就是资源名。"""
        return self._labels.get(name, utf8(name))

    def unitText(self):
        """数量后面的单位（前面带一个空格；没写单位时为空）。"""
        return " " + utf8(self.unit) if self.unit else ""

    def tipValues(self, resource):
        """格式串里多出来的名字（GAUGE_TIP_NAMES）的值。"""
        return {"name": self.labelOf(resource.name) if resource.name else "", "amount": resource.amount,
                "capacity": resource.capacity, "unit": utf8(self.unit), "fraction": resource.fraction}

    def render(self, field, resource, now):
        return self.patterns[field].render(self.model, now, self.tipValues(resource))

    def showTip(self, key, now, *args):
        """
        显示的东西（key，连同格式串用到的界面模型的值）变了、或要每帧算时，按 tipText(*args, now) 写悬停文本（字里的 %
        照原样显示，见 Display.hoverLiteral；字没变时不调用引擎）。
        """
        if self._modelNames:
            key = (key, tuple(self.model.value(name, now) for name in self._modelNames))
        if key != self._tipKey or self.liveTip:
            self._tipKey = key
            self.tip.show(Display.hoverLiteral(self.tipText(*(args + (now,)))))


class Gauge(_Resources):
    """
    仪表（Std/Components 的 gauge）。绑定：value（资源的名字）、textures（{资源名: 贴图}，"*" 给没写的名字）、labels（{资源名: 字}）、
    unit，tip 与 tipNames（另写的悬停文本），inset；写了动作的有 action、args、press。每帧按资源现在的样子画：填充换成资源名
    对应的贴图（textureOf）、按比例裁，悬停文本写 tipText（没变时不调用引擎）。点了发动作，参数是 args 再加手上那一格
    （会话的 heldRef：光标，触屏时是选中的格）。
    """

    TIPS = ("tip",)

    def __init__(self, screen, path, spec):
        _Resources.__init__(self, screen, path, spec)
        self.fill = Sprite(screen, path + "/fill")
        self.clip = Clip(screen, path + "/fill", {"data": self.valueName})

    def tipText(self, resource, now):
        """悬停文本：没有资源时为空（引擎不画）；写了 $dc_tip 的按它写，不然"名字\\n数量 / 容量 单位"。"""
        name = getattr(resource, "name", "") or ""
        if not name:
            return ""
        if "tip" in self.patterns:
            return self.render("tip", resource, now)
        return "%s\n%s%s" % (self.labelOf(name), format(resource, ""), self.unitText())

    def frame(self, now):
        if self.model is None:
            return
        resource = self.model.value(self.valueName, now)
        self.fill.show(self.textureOf(getattr(resource, "name", "") or ""))
        self.clip.show(getattr(resource, "fraction", 0.0))
        self.showTip(resource, now, resource)

    def onInput(self, event):
        if event.get("kind") == "press" and self.model is not None and self.action is not None:
            self.call(self.action, self.args + [self.model.heldRef()])


def fluidBands(fractions, height, minimum=FLUID_MIN_BAND):
    """
    流体堆叠里每种流体画多高（界面像素，整数）：fractions 是每种占储罐的比例（从下往上），height 是里面的高。每种按比例
    往上取整、至少 minimum（少的也看得见、点得到；种数多到放不下时按种数均分）；加起来放不下时从最高的那段一像素一像素地减
    （一样高时先减下面的），储罐没满时顶上至少留 minimum 的空（一眼看得出没满）。比例为 0 的是 0。
    """
    heights = [0] * len(fractions)
    present = [index for index, fraction in enumerate(fractions) if fraction > 0]
    height = int(height)
    if not present or height <= 0:
        return heights
    minimum = min(minimum, height // len(present))
    for index in present:
        heights[index] = max(minimum, int(math.ceil(fractions[index] * height - 1e-9)))
    full = sum(fractions[index] for index in present) >= 1.0 - 1e-9
    room = max(minimum * len(present), height if full else height - minimum)
    excess = sum(heights) - room
    while excess > 0:
        index = max(present, key=lambda k: (heights[k], -k))
        heights[index] -= 1
        excess -= 1
    return heights


class FluidStack(_Resources):
    """
    流体堆叠（Std/Components 的 fluid_stack）。绑定同仪表：value（资源列表的名字）、textures、labels、unit，tip、tipLine、
    tipTotal（另写的悬停文本），inset；写了动作的有 action、args、press。每帧按列表现在的样子分段（fluidBands，最多
    FLUID_LAYERS 种）：第 k 段把第 k 层的面板往上挪到下面那些段的总高、填充裁成这一段的高、换成这种流体的贴图（textureOf）；
    悬停文本按指针在哪一段写（tipText，见组件的说明），悬停的高亮同样挪到那一段、裁成那一段的高（不在段上时裁光）；没变时
    不调用引擎。点了按指针在哪一段发动作（触屏用抬起的那一点），参数是 args 再加段的序号；没点在流体上时不发。
    """

    TIPS = ("tip", "tipLine", "tipTotal")

    def __init__(self, screen, path, spec):
        _Resources.__init__(self, screen, path, spec)
        self.control = Lazy(screen, path)
        self.slides = [Lazy(screen, "%s/layer%d" % (path, index)) for index in range(FLUID_LAYERS)]
        self.fills = [Lazy(screen, "%s/layer%d/fill" % (path, index), _image) for index in range(FLUID_LAYERS)]
        self.bandSlide = Lazy(screen, path + "/button/hover/band")
        self.bandFill = Lazy(screen, path + "/button/hover/band/fill", _image)
        self._height = 0     # 里面的高（界面像素）：布局好了才取得到
        self._bands = []     # 这一帧每段的 (起点, 高)，从下往上
        self._shown = [(None, 0, 1.0)] * FLUID_LAYERS   # 每层现在的贴图、起点与裁剪比例（组件文件里初始裁光、没挪）
        self._band = (0, 1.0)   # 悬停高亮现在的起点与裁剪比例
        self._drawn = None      # 上一次分段时的 (值, 高)
        self._fluids = []
        self._hover = (None, None, None)   # 上一次量悬停时的 (指针, 段的序号, 时间)

    def open(self, model):
        _Resources.open(self, model)
        self._drawn, self._hover = None, (None, None, None)

    def onScale(self, scale):
        """比例变了：重新量里面的高、重新分段；用 SetPosition 摆过的层与高亮按新的内缩重新摆。"""
        self._height = 0
        self._drawn, self._hover = None, (None, None, None)
        self._shown = [(texture, None, ratio) for texture, _, ratio in self._shown]
        self._band = (None, self._band[1])

    def frame(self, now):
        if self.model is None:
            return
        value = self.model.value(self.valueName, now)
        height = self._innerHeight()
        if self._drawn is None or self._drawn[0] is not value or self._drawn[1] != height:
            self._drawn = (value, height)   # 值换了（或刚量到高）才重新分段
            fluids = self._fluids = list(value or ())
            drawn = fluids[:FLUID_LAYERS]
            bands, start = [], 0
            for size in fluidBands([fluid.fraction for fluid in drawn], height):
                bands.append((start, size))
                start += size
            self._bands = bands
            self._hover = (None, None, None)
            for index in range(FLUID_LAYERS):
                start, size = bands[index] if index < len(bands) else (0, 0)
                name = drawn[index].name if size else ""
                self._showLayer(index, self.textureOf(name), start, size, height)
        fluids, bands = self._fluids, self._bands
        pointer, hover = self.model.pointer(), self._hover
        if hover[2] is None or pointer != hover[0] or now - hover[2] >= POINTER_RECHECK:
            self._hover = hover = (pointer, self._bandAt(pointer), now)   # 指针动了（或停了一阵）才重量在哪一段
        hovered = hover[1]
        self._showBand(bands[hovered] if hovered is not None else None, height)
        self.showTip((self._drawn, hovered), now, fluids, hovered)

    def _innerHeight(self):
        if self._height <= 0:
            slide = self.slides[0].get()
            if slide is not None:
                self._height = int(slide.GetSize()[1])
        return self._height

    def _showLayer(self, index, texture, start, size, height):
        fill, slide = self.fills[index].get(), self.slides[index].get()
        if fill is None or slide is None:
            return
        shownTexture, shownStart, shownRatio = self._shown[index]
        ratio = 1.0 - float(size) / height if size > 0 else 1.0
        if size > 0 and texture != shownTexture:
            fill.SetSprite(texture)
            shownTexture = texture
        if size > 0 and start != shownStart:
            inset = self.inset * self.screen.scale   # 里面的高是量的界面像素，内缩写的是设计像素
            slide.SetPosition((float(inset), float(inset - start)))
            shownStart = start
        if ratio != shownRatio:
            fill.SetSpriteClipRatio(ratio)
            shownRatio = ratio
        self._shown[index] = (shownTexture, shownStart, shownRatio)

    def _showBand(self, band, height):
        """悬停的高亮：挪到那一段、裁成那一段的高；band 为 None 时裁光。"""
        slide, fill = self.bandSlide.get(), self.bandFill.get()
        if slide is None or fill is None:
            return
        start, ratio = self._band
        if band is not None and band[0] != start:
            inset = self.inset * self.screen.scale
            slide.SetPosition((float(inset), float(inset - band[0])))
            start = band[0]
        wanted = 1.0 - float(band[1]) / height if band is not None else 1.0
        if wanted != ratio:
            fill.SetSpriteClipRatio(wanted)
            ratio = wanted
        self._band = (start, ratio)

    def _bandAt(self, pointer):
        """指针（界面坐标）在哪一段上：段的序号，不在任何一段上、没有指针时为 None。"""
        if pointer is None or not self._bands:
            return None
        control = self.control.get()
        if control is None:
            return None
        (left, top), (width, _) = control.GetGlobalPosition(), control.GetSize()
        if not left <= pointer[0] < left + width:
            return None
        rise = top + self.inset * self.screen.scale + self._height - pointer[1]   # 指针在里面的底边之上多高
        for index, (start, size) in enumerate(self._bands):
            if start <= rise < start + size:
                return index
        return None

    def tipText(self, fluids, hovered, now):
        """
        悬停文本：指针在第 hovered 段上时写那一种（$dc_tip，缺省"名字\\n数量 单位"）；不在任何一段上时一行一种列出全部（上面的
        在前，$dc_tip_line，缺省"名字 数量 单位"），最后一行总量（$dc_tip_total，缺省"总量 / 容量 单位"）；空的储罐为空。
        """
        if hovered is not None:
            fluid = fluids[hovered]
            if "tip" in self.patterns:
                return self.render("tip", fluid, now)
            return "%s\n%s%s" % (self.labelOf(fluid.name), format(fluid, "amount"), self.unitText())
        if not fluids:
            return ""
        if "tipLine" in self.patterns:
            lines = [self.render("tipLine", fluid, now) for fluid in reversed(fluids)]
        else:
            lines = ["%s %s%s" % (self.labelOf(fluid.name), format(fluid, "amount"), self.unitText())
                     for fluid in reversed(fluids)]
        total = sum(fluid.amount for fluid in fluids)
        total = round(total, 6) if isinstance(total, float) else total
        capacity = max(fluid.capacity for fluid in fluids)
        if "tipTotal" in self.patterns:
            lines.append(self.render("tipTotal", Data.ResourceValue("", total, capacity), now))
        else:
            lines.append("%s / %s%s" % (total, capacity, self.unitText()))
        return "\n".join(lines)

    def onInput(self, event):
        if event.get("kind") != "press" or self.model is None or self.action is None:
            return
        index = self._bandAt(self.model.pointer() or self.screen.pointer(None))   # 触屏没有指针：取抬起的那一点
        if index is not None:
            self.call(self.action, self.args + [index])


WINDOW_RECHECK = 1.0   # 子窗口没拖动时多久检查一次在不在屏幕里（屏幕大小会变）


class Window(Widgets.Widget):
    """
    可拖动的子窗口（Std/Components 的 window）。绑定：position（客户端界面状态里记位置的名字）。打开时把窗口摆到记着的位置，
    没记过时摆在布局算出的位置，都用脚本摆（引擎的拖动之后直接挪它相对父控件的位置，不再由布局摆）；每帧读位置：拖出屏幕的
    拉回来（这时引擎不管范围），变了记进客户端界面状态（[x, y]，相对父控件的左上角）。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.control = Lazy(screen, path)
        self.root = Lazy(screen, Paths.ROOT)
        self._placed = False
        self._saved = None
        self._seen = None      # 上一帧读到的位置
        self._checked = 0.0    # 上一次检查拖没拖出屏幕的时间

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._placed = False
        self._saved = None
        self._seen = None

    def frame(self, now):
        control = self.control.get()
        if self.model is None or control is None:
            return
        name = self.spec["position"]
        scale = self.screen.scale   # 记的位置是设计像素（整屏按比例缩放的布局里乘上比例才是界面像素）
        if not self._placed:
            saved = self.model.clientValue(name)
            if len(saved or ()) == 2:
                position = (saved[0] * scale, saved[1] * scale)
            else:
                position = tuple(control.GetPosition())
            control.SetPosition((float(position[0]), float(position[1])))
            self._placed, self._saved = True, list(saved or ())
        x, y = control.GetPosition()
        if (x, y) == self._seen and now - self._checked < WINDOW_RECHECK:
            return   # 没拖动：不量位置（屏幕大小变了时每秒检查一次）
        self._checked = now
        inside = self._inside(control, x, y)
        if inside != (x, y):
            control.SetPosition(inside)
            x, y = inside
        self._seen = (x, y)
        position = [int(round(x / scale)), int(round(y / scale))]
        if position != self._saved:
            self._saved = position
            self.model.setClientValue(name, position)

    def onScale(self, scale):
        """比例变了：按记着的位置（设计像素）重新摆。"""
        self._placed = False

    def _inside(self, control, x, y):
        """窗口相对父控件的位置 (x, y) 拉进屏幕里（屏幕根的范围）。"""
        root = self.root.get()
        if root is None:
            return x, y
        (gx, gy), (width, height) = control.GetGlobalPosition(), control.GetSize()
        (rx, ry), (rw, rh) = root.GetGlobalPosition(), root.GetSize()
        nx = min(max(gx, rx), rx + max(rw - width, 0))
        ny = min(max(gy, ry), ry + max(rh - height, 0))
        return x + nx - gx, y + ny - gy


class Banner(Widgets.Widget):
    """
    旗帜（Std/Components 的 banner）。绑定：value（物品的名字）或 slot（[集合名, 格号]）。每帧把物品现在的样子写进原版旗帜图案
    渲染器的属性包（Std/Banners.rendererBag），没变时不调用引擎。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.renderer = Lazy(screen, path + "/r")
        self._slot = tuple(spec["slot"]) if spec.get("slot") is not None else None
        self._bag = None   # 引擎里的属性包（JSON 初始是空的，第一帧总写一次）
        self._stack = _NOTHING   # 写着的属性包是按哪个物品堆对象算的

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._bag, self._stack = None, _NOTHING

    def close(self):
        self._bag, self._stack = None, _NOTHING

    def frame(self, now):
        model = self.model
        if model is None:
            return
        stack = model.displayed(self._slot) if self._slot is not None else model.value(self.spec["value"], now)
        if stack is self._stack:
            return   # 同一个物品堆对象：属性包不变
        bag = Banners.rendererBag(stack)
        if bag != self._bag:
            control = self.renderer.get()
            if control is None:
                return
            control.SetPropertyBag(bag)
            self._bag = bag
        self._stack = stack


class Tooltip(Widgets.Widget):
    """提示区域（Std/Components 的 tooltip）。绑定：tooltip（格式串或语言文件的键）、tooltipNames。每帧按值写悬停文本。"""

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.text = FormattedLabel(screen, path + "/hover/tip/text", spec["tooltip"], spec["tooltipNames"], tip=True)

    def open(self, model):
        Widgets.Widget.open(self, model)
        self.text.open(model)

    def frame(self, now):
        if self.model is not None:
            self.text.frame(self.model, now)


class ItemIcon(Widgets.Widget):
    """
    物品图标（Std/Components 的 item_<界面档>）。绑定：value（物品的名字）或 item（写死的 [物品名, 附加值, 数量]），tip（为 False
    时不写悬停文本），disabled（[绑定名, 名字] 或 [绑定名, 名字, 值]：向引擎按绑定名登记要不要画暗）。每帧按物品现在的样子画
    （show：照格子画图标、数量、耐久条、收纳袋容量条，悬停文本照原版格子），物品没变时不调用引擎。
    可改写：stackOf（画哪个物品）、tipText（悬停文本）、countText / durability / storage / iconExtras（数量的字、耐久条、
    收纳袋容量条、图标的附加项；缺省照会话的物品显示 model.display，即布局登记的物品显示类）。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.view = ItemView(screen, path + "/item/item_renderer", path + "/item/stack_count_label",
                             path + "/durability_bar", path + "/storage_bar", rendererVisible=True)
        self.tip = Label(screen, path + "/tip/hover/tip/text", tip=True) if spec.get("tip", True) else None
        item = spec.get("item")
        self.static = Items.normalize({"newItemName": item[0], "newAuxValue": item[1], "count": item[2]}) if item else None
        self._stack = _NOTHING

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._stack = _NOTHING

    def onScale(self, scale):
        self.view.scaleFont(scale)

    def bind(self, binder):
        dim = self.spec.get("disabled")
        if dim:
            binder.boolean(dim[0], self.dimmed)

    def dimmed(self):
        model, dim = self.model, self.spec["disabled"]
        if model is None:
            return False
        return holds(model.value(dim[1], model.now()), dim[2:])

    def stackOf(self, now):
        """画哪个物品：写死的，或 value 现在的值。"""
        return self.static if self.static is not None else self.model.value(self.spec["value"], now)

    def frame(self, now):
        if self.model is not None:
            self.show(self.stackOf(now))

    def show(self, stack):
        """画物品堆 stack（与上一次的是同一个对象时不动）。"""
        if stack is self._stack:
            return
        self._stack = stack
        self.view.showItem(stack, self, False)
        if self.tip is not None:
            self.tip.show(self.tipText(stack))

    def tipText(self, stack):
        """悬停文本（照原版格子：物品的悬停文本；空着为空串，引擎不画）。"""
        return self.model.hoverText(stack)

    def countText(self, stack):
        return self.model.display.countText(stack)

    def durability(self, stack):
        return self.model.display.durability(stack)

    def storage(self, stack):
        return self.model.display.storage(stack)

    def iconExtras(self, stack):
        return self.model.display.iconExtras(stack)


class RowItem(RowPart):
    """
    列表的一行里的物品图标（Std/Components 的 item_<界面档> 写在行里）：spec 同物品图标；value 写 value 时画这一行的值。
    画法照 iconClass（物品图标的类），stackOf 可改写。
    """

    iconClass = ItemIcon

    def __init__(self, screen, path, spec):
        RowPart.__init__(self, screen, path, spec)
        self.icon = self.iconClass(screen, path, spec)

    def open(self, model):
        self.icon.open(model)

    def stackOf(self, model, now, extra):
        if self.icon.static is not None:
            return self.icon.static
        name = self.spec["value"]
        return extra[name] if name == "value" else model.value(name, now)

    def frame(self, model, now, extra):
        self.icon.show(self.stackOf(model, now, extra))

    def close(self):
        self.icon.close()

    def onScale(self, scale):
        self.icon.onScale(scale)


DOLL_RETRY = 1.0      # 实体不在这台客户端上时隔多久再看（秒）；画着的实体也按这个间隔看还在不在
DOLL_CHECK = 0.5      # 骨骼模型交给纸娃娃之后最多看多久（秒）：每帧看建出来没有（引擎画过才有），到时还没有就是没登记
DOLL_SPIN = 30.0      # 方块自己转的速度（度每秒，与引擎让实体、骨骼模型自己转的一样）
DOLL_FIT = 0.8        # 实体缺省按碰撞箱放满控件的多少
DOLL_TURN = 1.4       # 实体转身后看着比碰撞箱宽（身长比宽长）：横向按碰撞箱宽的这么多倍放
DOLL_FOOT = 0.08      # 实体（玩家除外）的脚离控件底边多少（控件高的比例）：实体绕脚倾斜，前倾时身子前端往下伸
HEAD_HEIGHT = 0.85    # 实体看着指针时从碰撞箱高度的多少处（头）看出去；玩家从眼睛
LOOK_DIVIDER = 40.0   # 看着指针照原版人物渲染器：偏移除以 40 取反正切，转头乘 40、转身与低头乘 20（度）


def _paperDoll(control):
    return Dolls.PaperDoll(control.asNeteasePaperDoll())


_NO_COLOR = -1   # 属性包里"没有自定义颜色"（0xFFFFFFFF 按有符号 32 位写）


def _userText(user, key):
    value = user.get(key) if isinstance(user, dict) else None
    if isinstance(value, dict) and "__value__" in value:
        value = value["__value__"]
    return utf8(value) if isinstance(value, _TEXT) else ""


def equipmentBag(stack, idAux):
    """
    原版装备预览渲染器的属性包（照原版界面按格子绑的四项）：物品编号（附魔的带光效位，空着为 0）、自定义颜色（附加数据里有
    customColor 时照它、不透明，没有为 0xFFFFFFFF）、盔甲纹饰的图案与材料（附加数据里的 Trim，没有为空串）。
    """
    user = stack.get("userData") if not Items.isEmpty(stack) else None
    trim = user.get("Trim") if isinstance(user, dict) else None
    color = user.get("customColor") if isinstance(user, dict) else None
    if isinstance(color, dict):
        color = color.get("__value__")
    return {"#item_id_aux": int(idAux or 0),
            "#item_custom_color": Display.int32(color | 0xFF000000) if isinstance(color, int) else _NO_COLOR,
            "#armor_trim_pattern": _userText(trim, "Pattern"), "#armor_trim_material": _userText(trim, "Material")}


def _look(dx, dy):
    """看着指针的转头、转身、低头（度）：dx、dy 是看的那一点减去指针（界面单位）。"""
    turn = math.atan(dx / LOOK_DIVIDER)
    return turn * 40.0, turn * 20.0, -math.atan(dy / LOOK_DIVIDER) * 20.0


class PaperDoll(Widgets.Widget):
    """
    网易纸娃娃上画的东西（Std/Components 的 doll 的 entity、block、model；看界面的玩家全由原版人物渲染器做，没有控件）。
    绑定：kind、rotate、yaw、pitch、size，scale（可无）与各种类自己的。交给纸娃娃（showing）与按朝向转（turn）由各种类的
    子类写；这里每帧算朝向：看着指针照原版人物渲染器的写法（触屏没有指针时正对着看的人），自己转的（spins 为真的种类）
    每帧转一点；朝向没变时不调用引擎。
    """

    spins = False   # 自己转（$dc_rotate spin）由控件每帧转（方块要绕自己的竖轴转；实体、骨骼模型由引擎转）

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.width, self.height = spec["size"]
        self.root = Lazy(screen, path)
        self.stage = Placed(screen, path + "/stage")
        self.doll = Lazy(screen, path + "/stage/r", _paperDoll)
        self._reset()

    def _reset(self):
        self._shown = None    # 交给纸娃娃的东西（各种类自己记）
        # 看的那一点（相对控件左上角），空元组是还没定。不用 None 当「没有」：网易打包机审（py2 的 pylint 1.9.5）按这里
        # 的 None 推断，下面判过有没有、取 [0] 也报 E1136（unsubscriptable-object），整包被拦
        self._look = ()
        self._angles = None
        self._start = 0.0
        self._pointer = None  # 上一次按指针算朝向时的 (指针, 看的那一点, 朝向, 时间)

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._reset()

    def close(self):
        self._reset()

    def frame(self, now):
        if self.model is None:
            return
        doll = self.doll.get()
        if doll is None or not self.showing(doll, now):
            return
        angles = self.anglesAt(now)
        if angles != self._angles:
            self._angles = angles
            self.turn(doll, angles)

    def showing(self, doll, now):
        """交给纸娃娃（没交过、要画的东西变了时）；返回现在画着东西没有。"""
        return False

    def turn(self, doll, angles):
        """按 (转头, 转身, 低头, 自己转) 的度数转纸娃娃上的东西（底下的朝向 yaw、pitch 加在上面）。"""

    def anglesAt(self, now):
        """(转头, 转身, 低头, 自己转) 的度数（保留一位小数，没变时不调用引擎）。"""
        head = body = pitch = spin = 0.0
        rotate = self.spec["rotate"]
        if rotate == "pointer":
            pointer = self.model.pointer()
            memo = self._pointer
            if memo is not None and memo[0] == pointer and memo[1] == self._look and now - memo[3] < POINTER_RECHECK:
                return memo[2]   # 指针没动：朝向不变（不量控件的位置）
            root = self.root.get()
            if pointer is not None and root is not None and self._look:
                x, y = root.GetGlobalPosition()
                scale = self.screen.scale   # 看的那一点按设计像素算，指针与控件的位置是界面像素
                head, body, pitch = _look((x - pointer[0]) / scale + self._look[0],
                                          (y - pointer[1]) / scale + self._look[1])
            angles = tuple(round(value, 1) for value in (head, body, pitch, spin))
            self._pointer = (pointer, self._look, angles, now)
            return angles
        elif rotate == "spin" and self.spins:
            spin = (now - self._start) * DOLL_SPIN % 360.0
        return tuple(round(value, 1) for value in (head, body, pitch, spin))


class EntityDoll(PaperDoll):
    """
    实体（绑定的 value 是实体编号的名字）：实体缺省按碰撞箱放满八成（横向留出转身的余地），脚站在控件底边（玩家的原点在
    眼睛，往上挪眼睛的高度；别的实体绕脚倾斜，脚离底边留一点）。实体编号变了重新交，实体不在这台客户端上时隔一秒再看，
    画着的实体离开过（走远、卸载）也重新交。
    """

    def _reset(self):
        PaperDoll._reset(self)
        self._tried = None    # 上一次试着交的实体编号
        self._wait = 0.0      # 下一次看的时间

    def showing(self, doll, now):
        target = utf8(self.model.value(self.spec["value"], now) or "")
        if target != self._shown:
            if target != self._tried or now >= self._wait:
                self._tried, self._wait = target, now + DOLL_RETRY
                if self._showEntity(doll, target):
                    self._shown = target
        elif target and now >= self._wait:
            self._wait = now + DOLL_RETRY
            if Dolls.entitySize(target) is None:
                self._shown = None
        return bool(target) and self._shown == target

    def _showEntity(self, doll, target):
        size = Dolls.entitySize(target) if target else None
        if size is None:
            doll.blank()
            return not target
        width, height = size
        pixels = self.spec.get("scale") or min(self.height * DOLL_FIT / height,
                                               self.width * DOLL_FIT / (max(width, 0.1) * DOLL_TURN))
        player = Dolls.isPlayer(target)
        origin = self.height - (EYE_HEIGHT * pixels if player else self.height * DOLL_FOOT)
        self.stage.place(self.width / 2.0, origin)
        self._look = (self.width / 2.0, origin if player else self.height - height * HEAD_HEIGHT * pixels)
        self._angles = None
        return doll.entity(target, pixels / DOLL_STAGE)

    def turn(self, doll, angles):
        head, body, pitch, spin = angles
        yaw, view = self.spec["yaw"], self.spec["pitch"]
        doll.turnEntity(yaw + body, yaw + head, pitch, view + pitch)


class BlockDoll(PaperDoll):
    """方块（绑定的 block、aux）：合成一格的模型（合成不了就不画，记一行日志），在控件正中按等轴的一格放下，可以自己转。"""

    spins = True

    def showing(self, doll, now):
        if self._shown is None:
            self._shown, self._start = self._showBlock(doll), now
        return self._shown is True

    def _showBlock(self, doll):
        spec = self.spec
        self._angles = None
        geometry = Dolls.blockGeometry(spec["block"], spec["aux"])
        if geometry is None:
            doll.blank()
            self.model.log("block %r of a doll cannot be made into a model" % (spec["block"],))
            return False
        self._look = (self.width / 2.0, self.height / 2.0)
        pixels = spec.get("scale") or min(self.width / BLOCK_FIT[0], self.height / BLOCK_FIT[1])
        return doll.block(geometry, pixels / Dolls.BLOCK_PIXELS)

    def turn(self, doll, angles):
        head, body, pitch, spin = angles
        doll.turnBlock(self.spec["yaw"] + head + spin, self.spec["pitch"] + pitch)


class ModelDoll(PaperDoll):
    """
    骨骼模型（绑定的 model、animation）：缺省按控件的高取原版物品栏的比例；交给纸娃娃之后看建出来没有（引擎画过才有），
    到时还没有就不画（没登记，记一行日志）。
    """

    def _reset(self):
        PaperDoll._reset(self)
        self._verify = None   # 看建出来没有的时间

    def showing(self, doll, now):
        if self._shown is None:
            self._shown, self._start = self._showModel(doll), now
        if self._verify is not None:
            if not doll.modelMissing():
                self._verify = None
            elif now >= self._verify:
                self._verify = None
                doll.blank()
                self._shown = False
                self.model.log("skeleton model %r of a doll is not registered" % (self.spec["model"],))
        return self._shown is True

    def _showModel(self, doll):
        spec = self.spec
        self._angles = None
        pixels = spec.get("scale") or self.height * PLAYER_PIXELS
        self._look = (self.width / 2.0, self.height / 2.0)
        self._verify = self.model.now() + DOLL_CHECK
        return doll.model(spec["model"], spec["animation"], pixels / DOLL_STAGE)

    def turn(self, doll, angles):
        head, body, pitch, spin = angles
        doll.turnModel(self.spec["yaw"] + head, self.spec["pitch"] + pitch)


class RendererDoll(Widgets.Widget):
    """原版渲染器画的纸娃娃（装备预览、马类的实体预览）：每帧按 bag(now) 写渲染器的属性包，没变时不调用引擎。"""

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.renderer = Lazy(screen, path + "/r")
        self._bag = None   # 引擎里的属性包（JSON 初始没有，第一帧总写一次）
        self._memo = None  # 各种类记的上一次 bag 的 (输入, 属性包)：输入没变时交回同一个属性包

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._bag = self._memo = None

    def close(self):
        self._bag = self._memo = None

    def frame(self, now):
        if self.model is None:
            return
        bag = self.bag(now)
        if bag is not self._bag and bag != self._bag:
            control = self.renderer.get()
            if control is not None:
                control.SetPropertyBag(bag)
                self._bag = bag

    def bag(self, now):
        return {}


class EquipmentDoll(RendererDoll):
    """装备预览（绑定的 value 或 slot）：物品现在的样子写进原版装备预览渲染器的属性包（equipmentBag），朝向写在 JSON 里。"""

    def bag(self, now):
        model, slot = self.model, self.spec.get("slot")
        stack = model.displayed(tuple(slot)) if slot is not None else model.value(self.spec["value"], now)
        memo = self._memo
        if memo is not None and memo[0] is stack:
            return memo[1]   # 同一个物品堆对象：不再拼
        bag = equipmentBag(stack, model.idAuxOf(stack))
        self._memo = (stack, bag)
        return bag


class MountDoll(RendererDoll):
    """马类的实体预览（绑定的 value）：实体编号写进原版渲染器的属性包（#entity_id）。"""

    def bag(self, now):
        target = self.model.value(self.spec["value"], now)
        memo = self._memo
        if memo is not None and memo[0] == target:
            return memo[1]
        bag = {"#entity_id": utf8(target or "")}
        self._memo = (target, bag)
        return bag


DOLL_KINDS = {"entity": EntityDoll, "block": BlockDoll, "model": ModelDoll, "equipment": EquipmentDoll,
              "mount": MountDoll}   # 纸娃娃的种类（绑定的 kind）-> 控件类


def registerDollKind(kind, widgetClass):
    """登记纸娃娃的一种（组件 Std/Components 的 Doll 派生时加的种类，绑定的 kind 是它）。返回控件类。"""
    DOLL_KINDS[kind] = widgetClass
    return widgetClass


def Doll(screen, path, spec):
    """纸娃娃（Std/Components 的 doll，控件名 doll）：按绑定的 kind 在 DOLL_KINDS 里找控件类建。"""
    widgetClass = DOLL_KINDS.get(spec["kind"])
    if widgetClass is None:
        raise KeyError("doll kind %r is not registered" % (spec["kind"],))
    return widgetClass(screen, path, spec)


def holds(value, rest):
    """
    条件（$dc_visible 的写法，名字后面的部分）对现在的值 value 成立没有：[] 是值为真，[值] 是等于它，["!=", 值] 是不等于它。
    """
    if not rest:
        return bool(value)
    if len(rest) == 2:
        return value != rest[1]
    return value == rest[0]


_ANY = object()
_REFUSED = object()   # 文本框：这次输入结束时已经按敏感词回退过
_FINISHED = object()  # 文本框：这次输入已经结束、提交过


class Visible(Widgets.Widget):
    """
    普通控件上的 $dc_visible（Std/Components 的 visible）。绑定：value（名字）、equals（等于它才显示）或 differs（不等于它才
    显示；两样都没有时值为真才显示）、shown（JSON 里写定的初始显隐，没有时不知道）。每帧按值现在的样子显隐，没变时不调用引擎。
    """

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.control = Placed(screen, path, spec.get("shown"))
        self.valueName = spec["value"]
        if "differs" in spec:
            self.rest = ("!=", spec["differs"])
        else:
            self.rest = (spec["equals"],) if "equals" in spec else ()

    def frame(self, now):
        if self.model is None:
            return
        self.control.setVisible(holds(self.model.value(self.valueName, now), self.rest))


UI_TEMPLATES = ("words_alpha",)   # 运行时按名字挂的模板（敏感词提示的淡出动画；见 Client/Paths.py 的 UI_TEMPLATES）


class WordsHint(Widgets.Widget):
    """
    敏感词提示（Std/Components 的 words_hint）：会话记下的敏感词次数（文本框的字含敏感词时加一，见
    ClientSession.noteRefusedWords）变了就显示，背景与字从头播淡出（照网易版原版铁砧，1.5 秒）。模板里的子路径与淡出动画名
    是类属性（tools/gen_ui.py 的 words_hint 模板与 animations）。
    """

    ANIMATION = "words_alpha"
    PARTS = ("/hint_background", "/hint_label")

    def __init__(self, screen, path, spec):
        Widgets.Widget.__init__(self, screen, path, spec)
        self.panel = Placed(screen, path, False)
        self.fades = [Fade(Lazy(screen, path + part), self.ANIMATION) for part in self.PARTS]
        self._seen = 0

    def open(self, model):
        Widgets.Widget.open(self, model)
        self._seen = model.refusedWords

    def frame(self, now):
        if self.model is None or self.model.refusedWords == self._seen:
            return
        self._seen = self.model.refusedWords
        self.panel.setVisible(True)
        for fade in self.fades:
            fade.restart()

    def close(self):
        self.panel.setVisible(False)


class Bag(Widgets.Widget):
    """
    普通控件上的 $dc_bag（Std/Components 的 bag）。绑定：values（[[绑定名, 名字], ...]）。向引擎按绑定名登记取值：名字现在的值
    是不是真（引擎更新控件时来要，改写到属性包里那个属性上）。
    """

    def bind(self, binder):
        for name, value in self.spec["values"]:
            binder.boolean(name, lambda value=value: self.truth(value))

    def truth(self, name):
        model = self.model
        return bool(model.value(name, model.now())) if model is not None else False


Widgets.register("slots", FixedSlots)
Widgets.register("scroll_slots", ScrollSlots)
Widgets.register("clip", Clip)
Widgets.register("text", Text)
Widgets.register("text_box", TextBox)
Widgets.register("button", Button)
Widgets.register("text_button", TextButton)
Widgets.register("toggle", Toggle)
Widgets.register("cycle_button", Cycle)
Widgets.register("tab", Tab)
Widgets.register("visible", Visible)
Widgets.register("words_hint", WordsHint)
Widgets.register("bag", Bag)
Widgets.register("slider", Slider)
Widgets.register("dropdown", Dropdown)
Widgets.register("list", List)
Widgets.register("bar", Bar)
Widgets.register("gauge", Gauge)
Widgets.register("fluid_stack", FluidStack)
Widgets.register("doll", Doll)
Widgets.register("banner", Banner)
Widgets.register("item", ItemIcon)
Widgets.register("tooltip", Tooltip)
Widgets.register("window", Window)
registerRowPart("visible", RowVisible)
registerRowPart("item", RowItem)
