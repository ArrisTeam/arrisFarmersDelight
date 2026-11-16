# -*- coding: utf-8 -*-
"""
容器界面（ScreenNode）：按布局的绑定表（Client/Layouts.py）建控件（Client/Widgets.py，按控件名找控件类），把输入交给
手势识别，按镜像与手势状态画格子、手持物、提示。

界面是布局：库的界面底座（手持物、提示、选数量条、收纳袋提示、物品飞行渲染器、输入映射）加上布局的内容；
控件、写文字的控件与具名控件的路径都在绑定表里。显示格子的控件（Widgets.SlotArea）是格子区：悬停、焦点、格子上的按钮
经它们换成格子引用；别的控件在打开、每帧、关闭时被调用，控件下面映射到 #dc.widget 的按钮（按下与抬起）交给它所在的
控件；控件里照原版"交互"时机报的按钮（Widget.presses）、文本框（Widget.textBoxes）与滑块（Widget.sliders）按名字接上，
同样交给控件；控件按名字的绑定与原版下拉（Widget.bind）每个引擎屏幕登记一次（_Binder）。
布局特有的行为（例如面板随格数长高、滚动条侧栏）由按布局名登记的界面扩展做（Layouts.ScreenExtension），
这里只在打开、每帧、关闭时调用它。

输入从三条路来：格子与面板的按钮映射（ViewBinder，见 Paths.BUTTONS）、按键事件、轮询（输入方式、指针位置）。
跟画面同步的事放在每个渲染帧做（GameRenderTickEvent）：手势计时（渐进拿取、长按、选数量跟手）、悬停移出、
界面扩展的每帧更新、格子区同步（滚动视图的行回收）、控件的每帧更新、重画；界面的 Update 只有每秒 30 次，
放在那里做会一顿一顿的。
输入事件处理完当场重画，格子在按下的这一帧就变（与原版一致）。重画前检查显示内容有没有变，变了才动；
每个格子控件自己再挡掉没变的引擎调用。

格子区的滚动全交给引擎的滚动视图（原版容器的滚动面板）：滚轮、拖动滚动条、触屏拖动与惯性、手柄焦点滚进视口都与原版一致。
悬停记的是格子控件（格子区与控件序号），不是格子：控件被回收换了内容时（按行回收的格子区），悬停的格子跟着变。

界面定义开了 cache_screen（与原版容器界面一样）：引擎关掉界面后留着控件树，下次推入同一定义时复用，Python 这边的
视图对象（_Parts）也跟着复用，重开时只改有变化的地方。根控件属性包里的记号说明这棵树配的是哪一套视图对象。
"""
import collections
import time

import mod.client.extraClientApi as clientApi
from mod.client.ui import screenNode as _screenNode
from mod.client.ui.screenNode import ScreenNode

from ...QuModLibs.Client import ListenForEvent, UnListenForEvent
from .. import HOST
from ..Common import Bundles, Data, Items, Rules, Slots
from ..Common.Collections import CURSOR_REF
from . import Display, Gestures, Layouts, Nbt, Paths, Popups, Widgets
from .BundleViews import BundleTooltip
from .Views import CursorView, Lazy, Placed, ScreenHandle, UnknownState

# 网易打包机审的接口桩里没有 mod.client.ui.viewBinder，写成导入语句报 import-error：用公开接口取
ViewBinder = clientApi.GetViewBinderCls()

_ARROW_KEYS = (37, 38, 39, 40)
_TOUCH_HOVER_SECONDS = 6.0   # 触屏下按方向键后高亮保留多久（原版按整秒比较"超过 5 秒"，实际 6 秒才藏）
_FRAME_GAP = 0.1   # 渲染帧事件这么久没来时（界面刚建好、窗口最小化）脚本刻才补跑一次每帧的更新
_HOVER_RECHECK = 0.1   # 指针停着时隔多久再量一次悬停的格子（内容在停着的指针下挪开时，移出最多晚这么久）
_ICON = {False: 16.0, True: 24.0}   # 格子里图标的边长：经典版 16、携带版 24（照原版 container_item）
_MARKER = "#dc.views"        # 根控件属性包里的记号：这棵控件树配的是哪一套视图对象
_ENTER_PRESSED = 1           # 文本框文字事件里的字符结果：按了回车
_BUTTON_UP = 0               # 按名字登记按钮状态回调（add_button_handler）的最后一个参数：0 登记抬起
REVEAL_TIMEOUT = 0.5         # 压在下面的屏幕重新成为最上面的（revive）时最多等多久引擎弹完上面的屏幕
SCALE_FRAMES = 20            # 整屏按比例缩放：推入、屏幕尺寸变了之后量几帧缩放框（刚显示的控件给的是排版之前的尺寸）
_cache = {}                  # 屏幕定义名 -> _Parts
_serial = [0]


def _now():
    return time.time()




def _withStandIn(displayed, slotType, workspace):
    """格子显示什么：空着时换成格子类型替它显示的东西（standIn），有东西照常。"""
    def shown(ref):
        stack = displayed(ref)
        if Items.isEmpty(stack):
            standIn = slotType.standIn(workspace, ref)
            if standIn is not None:
                return standIn
        return stack
    return shown


def _fromRoot(path):
    """引擎在按钮事件里报的路径前面带着屏幕定义名（table_classic/variables_...）：取从屏幕根起的那一段。"""
    index = path.find(Paths.ROOT)
    return path[index:] if index >= 0 else path


class _TextRelay(object):
    """
    一个文本框的文字事件交给它所在的控件：引擎按屏幕与文本框的名字回调，参数里没有路径，所以每个文本框一个中转对象。
    改动回调收到全部事件（输入结束那一次也收到）；要提交的文本框另接输入结束回调（引擎在里面把含敏感词的字换成 ***），
    结束只认那一次。
    """

    def __init__(self, screen, widget, box, submit):
        self.screen, self.widget, self.box, self.submit = screen, widget, box, submit

    def changed(self, args):
        finished = bool(args.get("Finish"))
        if not (finished and self.submit):
            self.screen._onText(self, args, finished)

    def finished(self, args):
        self.screen._onText(self, args, True)


class _PressRelay(object):
    """
    一个按钮的"交互"事件（照原版：键鼠与手柄在按下时、触屏在抬起且没拖动时）交给它所在的控件：引擎的交互事件里没有
    按钮路径，所以每个按钮一个名字（按钮的 $pressed_button_name）、一个中转对象。同名另接抬起：引擎在同一个按钮事件里
    先报交互、再报按下或抬起，按下后指针移出按钮再松开，抬起也报给这个按钮。
    """

    submit = False

    def __init__(self, screen, widget, name):
        self.screen, self.widget, self.box = screen, widget, name

    def pressed(self, args):
        self.screen._onPressed(self)

    def released(self, args):
        self.screen._onReleased(self)


class _SliderRelay(object):
    """
    一个滑块的事件交给它所在的控件：引擎按屏幕与滑块的名字回调，参数是 (值, 是否结束, 集合下标)，没有路径，所以每个滑块
    一个中转对象。改动回调收到全部事件（结束的那一次也收到，只是报成没结束），结束回调只收结束；两个按登记的先后调用
    （先改动后结束），结束只认结束回调。
    """

    submit = False

    def __init__(self, screen, widget, name):
        self.screen, self.widget, self.box = screen, widget, name

    def changed(self, value, finished=False, index=0):
        self.screen._onSlider(self, value, False)

    def finished(self, value, finished=True, index=0):
        self.screen._onSlider(self, value, True)


class _Getter(object):
    """按名字的绑定（Widget.bind）：引擎每次更新这个绑定时调 get。取值出错时记一行日志、给缺省值（引擎里调的，不能抛出去）。"""

    def __init__(self, screen, func, default):
        self.screen, self.func, self.default = screen, func, default

    def get(self):
        try:
            return self.func()
        except Exception as error:  # noqa: BLE001
            self.screen._log("binding failed: %r" % (error,))
            return self.default


class _DropdownRelay(object):
    """原版下拉（Widget.bind 里的 binder.dropdown）：引擎问选中第几项（selected）、能不能用（enabled），报玩家选了第几项（picked）。"""

    def __init__(self, screen, selected, picked):
        self.screen, self._selected, self._picked = screen, selected, picked

    def selected(self):
        try:
            return int(self._selected())
        except Exception as error:  # noqa: BLE001  引擎更新控件时调的，不能抛出去
            self.screen._log("dropdown failed: %r" % (error,))
            return -1

    def picked(self, index):
        self.screen._onPicked(self._picked, index)

    def enabled(self):
        return True


class _Binder(object):
    """
    控件向这一屏的引擎登记按名字的绑定与原版下拉（Widget.bind）。引擎按对象与方法名回调，每项一个中转对象（引擎拿着它们）。
    原版下拉由引擎的下拉控制做开合与单选：它把下拉开关的状态绑在 "#下拉名" 上、单选项的状态绑在各自的名字上，选了一项时
    报给 picked 并收起，点到别处收起；开关上的字由控件按名字另外绑定，引擎自带的那一份字不用（valueLabelDict 留空）。
    """

    def __init__(self, screen):
        self.screen = screen
        self.relays = []

    def string(self, name, func):
        relay = _Getter(self.screen, func, "")
        self.relays.append(relay)
        _screenNode.gui.bind_string_handler(self.screen.screen_name, name, relay, relay.get)

    def boolean(self, name, func):
        relay = _Getter(self.screen, func, False)
        self.relays.append(relay)
        _screenNode.gui.bind_bool_handler(self.screen.screen_name, name, relay, relay.get)

    def dropdown(self, name, options, selected, picked):
        relay = _DropdownRelay(self.screen, selected, picked)
        self.relays.append(relay)
        _screenNode.gui.add_dropdown_changed_handler(self.screen.screen_name, {
            "dropdownName": name, "dropdownShowLabel": "#%s_engine_label" % name, "enabledBindingName": "",
            "nameValueDict": dict((option, index) for index, option in enumerate(options)),
            "valueLabelDict": dict((index, "") for index in range(len(options))),
            "getValueFuncName": "selected", "setValueFuncName": "picked", "isEnableFuncName": "enabled"}, relay)


def _widget(screen, spec):
    """按绑定表里的一项建控件（布局用到的控件类没有登记时，客户端服务不会推这个界面）。"""
    widgetClass = Widgets.get(spec["widget"])
    if widgetClass is None:
        raise KeyError("widget %r is not registered" % (spec["widget"],))
    return widgetClass(screen, Paths.ROOT + spec["path"], spec)


class _LayoutScale(object):
    """
    整屏按比例缩放的布局（$dc_fit，绑定表的 scale）：缩放框的实际高与设计高之比。JSON UI 的百分比尺寸不管字号，比例变了
    给布局里的标签设字号（原有的倍数乘上比例）；标签跟着引擎缓存的控件树留着设过的字号，记下设的是哪个比例。
    """

    def __init__(self, screen, spec):
        self.design = float(spec["design"][1])
        self.box = Lazy(screen, Paths.ROOT + spec["box"])
        self.labels = [(Lazy(screen, Paths.ROOT + path), float(factor)) for path, factor in spec["labels"]]
        self.applied = None

    def measure(self):
        """现在的比例；框还没排版（高为 0）时为 None。"""
        control = self.box.get()
        size = control.GetSize() if control is not None else None
        if not size or size[1] <= 0:
            return None
        return round(min(size[1] / self.design, 1.0), 4)

    def apply(self, scale):
        """按比例给标签设字号；比例没变时什么都不做。返回设了没有。"""
        if scale == self.applied:
            return False
        for label, factor in self.labels:
            control = label.get()
            if control is not None:
                control.asLabel().SetTextFontSize(factor * scale)
        self.applied = scale
        return True


class _Parts(object):
    """
    一套界面的全部视图对象：控件（其中显示格子的是格子区）、手持物、弹出部件、收纳袋提示，以及布局的界面扩展。
    它们记着控件树现在的样子，界面关掉后跟着引擎缓存的树留下来，下次推入同一定义时整套复用。
    """

    def __init__(self, node, pocket, layout, extensionClass):
        _serial[0] += 1
        self.token = "%x:%d" % (id(self), _serial[0])
        self.handle = screen = ScreenHandle(node)
        if layout.get("scale"):
            # 整屏按比例缩放的布局：缩放框与侧栏都在布局的内容里，内容里经 Placed 摆的按设计像素写
            screen.scaledPrefix = Paths.ROOT + layout["scale"]["box"].rsplit("/", 1)[0] + "/"
        self.pocket = pocket
        self.layout = layout
        self.cursorView = CursorView(screen)
        self.popups = Popups.Popups(screen)
        self.bundleTooltip = BundleTooltip(screen, Paths.BUNDLE_CURSOR_TOOLTIP, pocket)
        self.bundleTouch = BundleTooltip(screen, Paths.BUNDLE_TOUCH_TOOLTIP, pocket, touch=True)
        self.widgets = [_widget(screen, spec) for spec in layout["widgets"]]
        # 布局里标了面板的控件（$dc_panel）：面板名 -> 控件，按面板开关显隐
        self.panels = dict((name, [Placed(screen, Paths.ROOT + path) for path in paths])
                           for name, paths in (layout.get("panels") or {}).items())
        # 每帧要更新的控件（改写了 frame 的）与它所在的面板（面板关着时不更新，开了接着画）
        self.framed = [(widget, _panelOf(widget.path, layout.get("panels") or {})) for widget in self.widgets
                       if _overridden(widget, "frame", Widgets.Widget)]
        # 整屏按比例缩放的布局（没有时为 None）与比例变了要告诉的控件（改写了 onScale 的）
        self.scale = _LayoutScale(screen, layout["scale"]) if layout.get("scale") else None
        self.scaled = [widget for widget in self.widgets if _overridden(widget, "onScale", Widgets.Widget)]
        self.panes = collections.OrderedDict((widget.name, widget) for widget in self.widgets
                                             if isinstance(widget, Widgets.SlotArea))
        self.texts = {}
        self.flying = node.GetBaseUIControl(Paths.FLYING)
        self.hiddenPath = None   # 换成别的屏幕定义时藏起过的控件（hide），下次推入时显示回来
        self.gateClosed = False  # 藏起过退出过渡的门（closeGate），下次推入时打开
        self.tipView = None      # 写着悬停文本的格子控件：字写在控件上，跟着缓存的控件树留到下次推入
        self.extension = (extensionClass or Layouts.ScreenExtension)(self)

    def path(self, name):
        """布局里 $dc_name 标的控件的完整路径。"""
        return Paths.ROOT + self.layout["names"][name]

    def setText(self, path, text):
        text = text if isinstance(text, str) else text.encode("utf-8")
        if self.texts.get(path) != text:
            control = self.handle.GetBaseUIControl(path)
            if control is not None:
                control.asLabel().SetText(text)
                self.texts[path] = text

    def remember(self):
        """会话写回客户端界面状态之前：控件把要记的写进去（见 Widget.remember）。"""
        for widget in self.widgets:
            widget.remember()

    def close(self):
        """界面关闭：控件把会影响下次推入的部分（默认焦点）摆回 JSON 初始的样子。"""
        for widget in self.widgets:
            widget.close()


def _overridden(obj, name, base):
    """obj 的类改写了 base 的方法 name（py2 的未绑定方法要取出函数再比）。"""
    mine, original = getattr(type(obj), name), getattr(base, name)
    return getattr(mine, "__func__", mine) is not getattr(original, "__func__", original)


def _panelOf(path, panels):
    """控件 path 在哪个面板里（布局的 panels：面板名 -> 标了面板的控件的路径），不在面板里为 None。"""
    for name, paths in panels.items():
        for panel in paths:
            full = Paths.ROOT + panel
            if path == full or path.startswith(full + "/"):
                return name
    return None


def _selectionKey(selection):
    """触屏选中在重画键里的样子（选中的格与选好的数量；选中是就地改数量的字典，所以不按对象比）。"""
    return (selection.get("ref"), selection.get("amount")) if selection else None


def _bundleKey(active):
    """触屏展开着的收纳袋在重画键里的样子（格、选中的网格格、提示收起了没有）。"""
    return (active.get("ref"), active.get("cell"), active.get("minimized")) if active else None


def _partsFor(node, pocket, layout, extensionClass, quiet=False):
    """
    这次推入的界面配哪一套视图对象：控件树带着缓存里那一套的记号就复用；没有记号是新建的树，照 JSON 初始值新建；
    有记号却对不上（引擎留着树、这边的缓存没了）就按状态未知新建，第一次设置都下发给引擎。
    不带进入动画的孪生屏幕（quiet）是另一个屏幕定义、另一棵控件树，视图对象也另缓存一套。
    """
    key = layout["quiet"] if quiet else layout["screen"]
    root = node.GetBaseUIControl(Paths.ROOT)
    marker = (root.GetPropertyBag() or {}).get(_MARKER) if root is not None else None
    parts = _cache.get(key)
    if parts is not None and marker is not None and marker == parts.token:
        parts.handle.node = node
        return parts
    if marker is None:
        parts = _Parts(node, pocket, layout, extensionClass)
    else:
        with UnknownState():
            parts = _Parts(node, pocket, layout, extensionClass)
        for path in (Paths.SCREEN, Paths.ROOT, Paths.GATE):   # 缓存里那一套藏起过哪里（hide、closeGate）已经不知道：都显示回来
            control = node.GetBaseUIControl(path)
            if control is not None:
                control.SetVisible(True)
    if root is not None:
        root.SetPropertyBag({_MARKER: parts.token})
    _cache[key] = parts
    return parts


def _decorDepends(slotType, mirror):
    """格子装饰依赖的东西现在的样子（变了就整片重画）：照格子类型的 decorDepends（None 为自动）。"""
    depends = getattr(slotType, "decorDepends", None)
    if depends is None:
        depends = Slots.DECOR_SLOTS if Slots.overrides(slotType, "decorate") else Slots.DECOR_DATA
    if depends == Slots.DECOR_DATA:
        return mirror.dataRevision
    if depends == Slots.DECOR_CLIENT:
        return (mirror.revision, mirror.clientRevision)
    return mirror.revision


class ContainerScreen(ScreenNode):

    dolorHost = HOST   # 哪个使用方的这份库推的界面（几个模组各带一份本库时，同一版本的几份共用界面定义）

    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.quiet = str(name).endswith(Layouts.QUIET)   # 不带进入动画的那份（切换到别的布局时推它）
        self.ready = False
        self.session = None
        self.panes = {}
        self.refViews = {}
        self.keyViews = {}           # 容器格 -> (显示它的格子控件, 格子边长)：物品飞行按容器格找起止
        self.extension = None
        self._renderKey = None
        self._walks = {}             # 格子区名 -> (输入, {格: 控件}, {容器格: (控件, 格子边长)}, [轮流显示帧的控件])
        self._decorInputs = {}       # 格子区名 -> 上一次画格子装饰时它依赖的修订号
        self._clientPanes = {}       # 格子区 -> 它的格子装饰依赖不依赖客户端界面状态
        self._actives = {}           # 格子区名 -> (修订号, {格: 启用着没有})：停用格的判断（修订号变了重新问）
        self._redrawAll = False      # 下一次重画每个格子区都重走、每格都重画
        self._animated = []          # 占位图标轮流显示着帧的格子控件（每帧推进）
        self._hoverSlot = None       # 指针或手柄焦点下的控件：(格子区名, 控件序号)
        self._hoverPointer = None    # 收到上一个悬停事件时指针的位置
        self._hoverChecked = None    # 上一次量悬停的格子还在指针下时的 (格子区名与控件序号, 指针, 时间)
        self._openPointer = None     # 推入时的指针位置（键鼠）：指针从那时起没动过、也没按过键时为它，否则为 None
        self._focusDropped = False   # 这次推入已经让引擎清过默认焦点
        self._dropFocus = False      # 下一帧让引擎清掉默认焦点
        self._tipKey = None         # 上一次写悬停文本时的 (控件, 格, 带不带分类, 数据修订号, 客户端修订号)
        self._tipStack = None        # 上一次写悬停文本时那一格显示的物品堆
        self._touchHoverUntil = None  # 触屏下按了方向键：高亮显示到这个时间
        self._revealBy = None        # 重新成为最上面的（revive）还没显示：最迟这个时间自己显示出来
        self._lastFrame = None       # 上一个渲染帧事件的时间（脚本刻据此判断要不要补跑每帧的更新）
        self._countsMemo = None      # 上一次算的各格子区格数：(镜像, 修订号, 数据修订号, 手势预览, 格数)
        self._openPanels = {}        # 这一帧各面板开着没有（_syncPanels 算，控件的每帧更新按它跳过关着的）
        self._relays = []            # 按名字接上了事件的文本框、按钮与滑块（_TextRelay、_PressRelay、_SliderRelay）
        self._pressing = None        # 交互按钮报了交互、还没抬起：它的名字
        self._pendingPush = None     # 按着交互按钮时要推的界面：(命名空间, 名字, 参数)，抬起时推
        self.uiScale = 1.0          # 整屏按比例缩放的布局缩到了几倍（不缩放的布局为 1）
        self._scaleFrames = 0        # 还要量几帧缩放框
        self._binder = None          # 控件按名字的绑定与原版下拉（_Binder，推入时登记）

    # ---------------------------------------------------------------- 生命周期

    def Create(self):
        from . import Service
        self.session = Service.current()
        if self.session is None or self.session.closed:
            clientApi.PopScreen()
            return
        session = self.session
        session.screen = self
        self.pocket = session.pocket
        layout = session.layout["screens"]["pocket" if self.pocket else "classic"]
        parts = self.parts = _partsFor(self, self.pocket, layout, Layouts.extensionClass(session.mirror.menu.layout),
                                       self.quiet)
        self.cursorView, self.popups, self.flying = parts.cursorView, parts.popups, parts.flying
        self.bundleTooltip, self.bundleTouch = parts.bundleTooltip, parts.bundleTouch
        self.panes = parts.panes
        self.extension = parts.extension
        self.uiScale = parts.scale.applied or 1.0 if parts.scale is not None else 1.0
        self.show()
        self._open(session)
        self._openPointer = self.pointer(Gestures.MOUSE) if session.gestures.device == Gestures.MOUSE else None
        self._focusDropped = self._dropFocus = False
        self._listenNamed()
        self._bindEngine()
        ListenForEvent("OnKeyPressInGame", self, self._onKey)
        ListenForEvent("GameRenderTickEvent", self, self._onFrame)
        self._listenScale(True)
        self.ready = True
        self.render(True)
        if self.quiet:
            # 切换过来的：引擎在这一屏上了栈的同时调 Create，压在下面的旧屏幕这时才藏起来，中间不空一帧
            Service.settleBuried()

    def _open(self, session):
        """
        按会话打开（推入时，或换会话时）：清掉上次留下的悬停文本，写文字、界面扩展与格子区开始、控件记下这次的会话、面板显隐。
        悬停文本写在格子控件上，跟着引擎缓存的控件树留到这次；那一格这次未必还有悬停文本（锁住的格子解锁了这类），不清掉的话
        指针移上去引擎照画上次的字。
        """
        tip = self.parts.tipView
        if tip is not None:
            tip.setTip("")
            self.parts.tipView = None
        layout = session.layout["screens"]["pocket" if self.pocket else "classic"]
        for name, paths in layout["texts"].items():
            for path in paths:
                self.parts.setText(Paths.ROOT + path, session.texts.get(name, ""))
        if self.parts.scale is not None:
            self._scaleFrames = SCALE_FRAMES   # 缓存的控件树留着上次的比例，屏幕尺寸可能变了：推入后量几帧
            self._checkScale()   # 缓存的树量得到上次排好的框：界面扩展与格子区摆之前先按它定比例
        counts = self._counts()
        self.extension.open(self, counts)
        self._syncPanes(counts)
        for widget in self.parts.widgets:
            widget.open(session)   # 滚动的格子区回到顶上，数据控件记下这次的会话
        self._syncPanels(_now())
        self._frameWidgets(_now())
        self._showHover(session.gestures.device != Gestures.TOUCH)

    def adopt(self, session):
        """
        换会话（切换到用同一个屏幕定义的界面、按新参数重开）：引擎的界面与控件照旧，不推不弹，所以没有关上再打开的动画，
        手持物一直画着；按新会话重新打开（格子区回到顶上，界面扩展重新开始），当场重画。
        """
        self.extension.close(self)
        self._switch(session)

    def revive(self, session):
        """
        压在下面的这一屏要重新成为最上面的（来回切换时切回它的布局）：接上事件（与 Create 一样），按新会话打开并重画，
        先不显示。上面的屏幕由客户端服务随后弹出，弹完时（引擎这时已经把跟随指针的手持物摆到指针上）它调 show；
        过了 REVEAL_TIMEOUT 还没等到就自己显示出来。
        """
        self._cleaned = False
        self._listenNamed()
        ListenForEvent("OnKeyPressInGame", self, self._onKey)
        ListenForEvent("GameRenderTickEvent", self, self._onFrame)
        self._listenScale(True)
        self.ready = True
        self._revealBy = _now() + REVEAL_TIMEOUT
        self._switch(session)

    def _switch(self, session):
        """换上会话 session：收起上一个会话留下的详情与悬停文本（_open 清），按新会话重新打开，当场重画。"""
        self.popups.hideDetails()
        self.session = session
        session.screen = self
        self.refViews, self.keyViews = {}, {}
        self._animated = []
        self._renderKey = None
        self._hoverSlot = self._hoverPointer = self._touchHoverUntil = self._openPointer = None
        self._tipKey = self._tipStack = None
        self._open(session)
        self.render(True)

    def hide(self, path=Paths.ROOT):
        """
        换成别的屏幕定义之前藏起控件 path（缺省是界面的内容，弹出时的退出动画就看不见；Paths.SCREEN 连背景一起，
        压在别的屏幕下面时用）。引擎留着的控件树下次推入（或重新成为最上面的）时再显示出来。
        """
        control = self.GetBaseUIControl(path)
        if control is not None:
            control.SetVisible(False)
            self.parts.hiddenPath = path

    def show(self):
        """显示回 hide 藏起的控件，打开 closeGate 关上的门。"""
        self._revealBy = None
        parts = self.parts
        if parts.hiddenPath is not None:
            control = self.GetBaseUIControl(parts.hiddenPath)
            if control is not None:
                control.SetVisible(True)
            parts.hiddenPath = None
        if parts.gateClosed:
            control = self.GetBaseUIControl(Paths.GATE)
            if control is not None:
                control.SetVisible(True)
            parts.gateClosed = False

    def closeGate(self):
        """
        藏起退出过渡的门：之后弹出这一屏时不放关闭动画、当场弹出（切换布局时内部弹出旧屏幕用；画面上什么都不变）。
        引擎留着的控件树下次推入时打开（show）。
        藏起控件之后，引擎要等这一屏下一次更新控件时才认为它不可见，而紧接着的弹出可能在那之前处理；SetVisible 自带的
        强制刷新对同一个屏幕定义的同一个控件只在第一次生效。所以这里当场刷新这一屏。
        """
        control = self.GetBaseUIControl(Paths.GATE)
        if control is not None:
            control.SetVisible(False, False)
            self.parts.gateClosed = True
            self.UpdateScreen(True)

    def Destroy(self):
        self.cleanup()

    def rememberState(self):
        """会话写回客户端界面状态之前（Client/Service 的 remember）：这套界面的控件把要记的写进去。"""
        parts = getattr(self, "parts", None)
        if parts is not None and self.ready:
            parts.remember()

    def showDetails(self, text):
        """在屏幕底部的物品详情处显示一段字（会话的 showDetails：控件弹说明、动作的结果）；位置听界面扩展的 detailsOffset。"""
        if self.ready:
            self.popups.showDetails(text, self.extension.detailsOffset(self))

    def cleanup(self):
        """界面关闭时的收尾（Python 关闭走 Destroy；引擎自己关掉时由客户端服务调用），可重复调用。"""
        if getattr(self, "_cleaned", False):
            return
        self._cleaned = True
        self.ready = False
        UnListenForEvent("OnKeyPressInGame", self, self._onKey)
        UnListenForEvent("GameRenderTickEvent", self, self._onFrame)
        self._listenScale(False)
        self._unlistenNamed()
        parts = getattr(self, "parts", None)
        if parts is not None and parts.handle.node is self:
            parts.extension.close(self)
            parts.close()
        if self.session is not None:
            self.session.onScreenGone(self)

    def Update(self):
        if not self.ready:
            return
        try:
            self._tick()
        except Exception as error:  # noqa: BLE001  界面每刻的更新不能抛出去（会连带跳过别的界面）
            self.session.log("update failed: %r" % (error,))

    def _onFrame(self, args=None):
        if not self.ready:
            return
        try:
            self._lastFrame = _now()
            self._frame()
        except Exception as error:  # noqa: BLE001  渲染帧事件里的异常同样不能抛出去
            self.session.log("frame failed: %r" % (error,))

    # ---------------------------------------------------------------- 给界面扩展用

    def now(self):
        return _now()

    def invalidate(self):
        """下一次重画不管显示内容有没有变都重画（布局变了）。"""
        self._renderKey = None
        self._redrawAll = True

    def pointer(self, device):
        """指针（手柄是虚拟光标）的界面坐标，取不到时为 None。"""
        if device == Gestures.GAMEPAD:
            return self.cursorView.position()
        try:
            return _screenNode.gui.get_mouse_position()
        except Exception:  # noqa: BLE001
            return None

    # ---------------------------------------------------------------- 每刻与每帧

    def _tick(self):
        """每个脚本刻（每秒 30 次）：界面档与输入方式、触屏高亮计时、拉取内容。"""
        session = self.session
        now = _now()
        session.tick()
        if session.checkProfileChanged():
            return
        device = session.detectDevice()
        if device != session.gestures.device:
            self._switchDevice(device)
        if self._touchHoverUntil is not None and now >= self._touchHoverUntil:
            self._endTouchHover()
        if self._revealBy is not None and now >= self._revealBy:
            self.show()
        if device == Gestures.TOUCH:
            session.gestures.uiScale = clientApi.GetGuiScale() or 1.0   # 窗口缩放会变，每刻取
        if self._lastFrame is None or now - self._lastFrame >= _FRAME_GAP:
            self._frame()   # 渲染帧事件好一阵没来（界面刚建好、窗口最小化）才在这里推进；平时渲染帧已经跑过
        self._ensureShown()

    def _frame(self):
        """
        每个渲染帧（原版容器界面的状态也是每帧更新）：手势计时、悬停移出、界面扩展（例如行数与面板高度的过渡）、
        格子区同步（滚动视图的行回收）、控件的每帧更新（数据控件）、重画（没变化时不动）。扩展要在格子区之前跟上格数，
        不然内容先变高、视口还没变，引擎会冒出一帧滚动条。
        """
        gestures = self.session.gestures
        now = _now()
        if self._dropFocus:
            self._dropFocus = False
            _screenNode.gui.handle_input_mode_change(self.screen_name)
        device = gestures.device
        # 触屏没按着时用不到指针（只有按住在拖、在滚时要）：不向引擎取
        pointer = self.pointer(device) if device != Gestures.TOUCH or gestures.press is not None else None
        gestures.tick(now, pointer)
        self._trackHover(device, pointer, now)
        if self._scaleFrames:
            self._checkScale()   # 在格子区与控件摆东西之前：这一帧按量到的比例摆
        counts = self._counts()
        self.extension.frame(self, now, counts)
        self._syncPanes(counts)
        self._followHover()
        self._syncPanels(now)
        self._frameWidgets(now)
        self._afterInput()
        for view in self._animated:   # 轮流显示的占位图标（格子装饰的帧）
            view.animate(now)

    # ---------------------------------------------------------------- 整屏按比例缩放

    def _listenScale(self, on):
        """整屏按比例缩放的布局开着时听屏幕尺寸变了（拉窗口、分屏这类，引擎在屏幕尺寸变了时报），变了再量缩放框。"""
        scale = getattr(self, "parts", None) and self.parts.scale
        if scale is None or on == getattr(self, "_scaleListened", False):
            return
        self._scaleListened = on
        (ListenForEvent if on else UnListenForEvent)("ScreenSizeChangedClientEvent", self, self._onScreenSize)

    def _onScreenSize(self, args=None):
        self._scaleFrames = SCALE_FRAMES

    def _checkScale(self):
        """
        量缩放框：比例变了给标签设字号，经 Placed 摆过的位置与尺寸按新的比例重新下发，手持物跟着缩，告诉改写了 onScale 的
        控件（格子区给数量字设字号）。量够几帧就停（推入、屏幕尺寸变了时重来）。
        """
        self._scaleFrames -= 1
        parts = self.parts
        scale = parts.scale.measure()
        if scale is None or not parts.scale.apply(scale):
            return
        self.uiScale = scale
        parts.handle.setScale(scale)
        self.cursorView.scale(scale)
        for widget in parts.scaled:
            widget.onScale(scale)

    def _syncPanels(self, now):
        """布局里标了面板的控件按面板开关显隐（没变时不调用引擎）；记下这一帧各面板开着没有。"""
        opened = self._openPanels = {}
        for name, views in self.parts.panels.items():
            shown = opened[name] = self.session.panelOpen(name, now)
            for view in views:
                view.setVisible(shown)

    def _frameWidgets(self, now):
        """
        控件的每帧更新（数据控件按界面数据现在的值画，值没变时不调用引擎）：只调改写了 frame 的，关着的面板里的不调
        （面板开了接着按现在的值画）。
        """
        opened = self._openPanels
        for widget, panel in self.parts.framed:
            if panel is None or opened.get(panel, True):
                widget.frame(now)

    def _afterInput(self):
        """取走一次性效果并当场重画：输入事件、渲染帧都走这里。"""
        self.applyEffects()
        self.render(False)

    def _switchDevice(self, device):
        """输入方式变了：结束进行中的手势；原版触屏下不显示格子的悬停高亮。"""
        self.session.gestures.setDevice(device)
        self._touchHoverUntil = None
        self._showHover(device != Gestures.TOUCH)

    def _showHover(self, visible):
        for pane in self.panes.values():
            pane.setHoverVisible(visible)

    def _beginTouchHover(self):
        """原版：触屏下按方向键（外接键盘）时显示格子的高亮与悬停文本，最后一次按键后一段时间或点了格子就藏起来。"""
        if self._touchHoverUntil is None:
            self._showHover(True)
        self._touchHoverUntil = _now() + _TOUCH_HOVER_SECONDS

    def _endTouchHover(self):
        self._touchHoverUntil = None
        if self.session.gestures.device == Gestures.TOUCH:
            self._showHover(False)

    def _trackHover(self, device, pointer, now):
        """
        鼠标移出了悬停的控件（引擎只把移入报给 Python，不报移出）：按指针位置判断。
        指针从收到悬停事件起没动过时不判断：那是方向键移动焦点（或内容在指针下滚动）带来的，原版此时悬停不变。
        指针从上一次量过起没动时隔 _HOVER_RECHECK 秒才再量（每次量要向引擎取控件的位置与尺寸）。
        """
        slot = self._hoverSlot
        if device != Gestures.MOUSE or slot is None or pointer is None:
            return
        anchor = self._hoverPointer
        if anchor is not None and abs(pointer[0] - anchor[0]) < 0.5 and abs(pointer[1] - anchor[1]) < 0.5:
            return
        checked = self._hoverChecked
        if checked is not None and checked[0] == slot and checked[1] == pointer and now - checked[2] < _HOVER_RECHECK:
            return
        control = self.panes[slot[0]].views[slot[1]].control
        if control is not None:
            x, y = control.GetGlobalPosition()
            width, height = control.GetSize()
            if x <= pointer[0] < x + width and y <= pointer[1] < y + height:
                self._hoverChecked = (slot, pointer, now)
                return
        self._hoverSlot = None
        self.session.gestures.onHoverLost()

    def _followHover(self):
        """回收换掉了指针（或手柄焦点）下那个控件显示的格子：悬停的格子跟着控件走。"""
        slot = self._hoverSlot
        if slot is None:
            return
        ref = self.panes[slot[0]].refAt(slot[1])
        if ref != self.session.gestures.hovered:
            self.session.gestures.rehover(ref)

    def _counts(self):
        """
        各个格子区显示几格：集合现在的格数，再算上手势预览（拖动分配、按下时的拿放）里放了东西的格子。
        格数随内容长的集合拖进末尾的空格时，后面的格子当场长出来，可以一路拖下去（规则也按拖过的格子都已放了东西来算）。
        预览只让格数变多：按下拿起最后一格的东西时不先缩回去。有格数的集合不受预览影响。
        """
        mirror, preview = self.session.mirror, self.session.gestures.preview
        memo = self._countsMemo
        if memo is not None and memo[0] is mirror and memo[1] == mirror.revision and memo[2] == mirror.dataRevision \
                and memo[3] is preview:
            return memo[4]   # 显示内容、界面数据、手势预览都没变：格数不变
        counts = {}
        for name, pane in self.panes.items():
            collection = mirror.structure.get(pane.collection)
            top = -1
            if collection is not None:
                for (cid, index), stack in preview.items():
                    if cid == collection.cid and index - collection.offset > top and not Items.isEmpty(stack):
                        top = index - collection.offset
            counts[name] = mirror.size(pane.collection, top)
        self._countsMemo = (mirror, mirror.revision, mirror.dataRevision, preview, counts)
        return counts

    def _syncPanes(self, counts):
        extension = self.extension
        for name, pane in self.panes.items():
            pane.sync(counts.get(name, 0), extension.contentLimit(name))

    def _ensureShown(self):
        """各格子区要显示的那一段（格子区自己报，例如按行回收的窗口再多一段）交给容器的同步方式：还没到客户端的就拉。"""
        session = self.session
        for pane in self.panes.values():
            wanted = pane.wanted()
            if wanted is not None:
                name, start, end = wanted
                session.ensure(name, start, min(session.mirror.size(name), end))

    # ---------------------------------------------------------------- 渲染

    def render(self, force):
        session = self.session
        gestures = session.gestures
        releaseBar = gestures.releaseBarVisible(_now())
        showTags = session.showTags()
        key = (session.mirror.revision, id(gestures.preview), _selectionKey(gestures.selection), gestures.progress,
               gestures.slider, gestures.device, gestures.tooltipRef(), gestures.hovered, releaseBar, showTags,
               tuple(gestures.bundleHover or ()), _bundleKey(gestures.bundleActive),
               tuple(pane.revision for pane in self.panes.values()), session.mirror.clientRevision)
        if not force and key == self._renderKey:
            return
        self._renderKey = key
        if force or self._redrawAll:
            self._forgetWalks()
        # 格子区画什么取决于：它自己的样子（滚动、格数），显示内容（镜像的修订号、手势预览），触屏选中与选好数量的条，
        # 标签；这些都没变的格子区沿用上一次的结果（滚动一个格子区时别的不重走）
        context = session.display
        inputs = (session.mirror.revision, id(gestures.preview), _selectionKey(gestures.selection), releaseBar,
                  showTags, id(context))
        refViews, keyViews, animated = {}, {}, []
        now = _now()
        clientInputs = (session.mirror.clientRevision,)
        for name, pane in self.panes.items():
            walk = self._walks.get(name)
            paneInputs = (pane.revision,) + inputs + (clientInputs if self._readsClient(pane) else ())
            if walk is None or walk[0] != paneInputs:
                walk = self._walks[name] = (paneInputs,) + self._walkPane(name, pane, showTags, releaseBar, now)
            refViews.update(walk[1])
            keyViews.update(walk[2])
            animated.extend(walk[3])
        self.refViews, self.keyViews = refViews, keyViews
        self._animated = animated
        touch = gestures.device == Gestures.TOUCH
        self.cursorView.show(None if touch else gestures.displayed(CURSOR_REF), context, showTags)
        self.cursorView.showProgress(None if touch else gestures.progress)
        self._renderTip(gestures, refViews)
        self._renderBundle(gestures, refViews)
        slider = gestures.slider
        self.popups.renderSplit(slider, refViews.get(slider[0]) if slider else None,
                                self._splitSide(slider[0]) if slider else None, self._origin())
        if gestures.device == Gestures.GAMEPAD:
            self.popups.renderHelpers(gestures, session)   # 手柄提示条只在用手柄时显示

    def _walkPane(self, name, pane, showTags, releaseBar, now):
        """
        重走格子区 pane：写格子（与上一次画的一样的格子不动，见 Widgets.redrawSlot）、停用底格，只给这次画了的格子算格子装饰。
        格子装饰依赖界面数据（改写了 decorate 的格子类型当作依赖显示的一切）：依赖的变了时整片重画。
        返回 ({格: 控件}, {容器格: (控件, 格子边长)}, [轮流显示占位图标的控件])。
        """
        session = self.session
        gestures, mirror = session.gestures, session.mirror
        collection = mirror.structure.get(pane.collection)
        slotType = collection.slot if collection is not None else None
        workspace = None
        shown = gestures.displayed
        if slotType is not None and Slots.standsIn(slotType):
            # 空着时替它显示一样东西的格子（织布机的图案格）：图标照那样东西画
            workspace = Rules.Workspace(mirror.view, mirror.rules)
            shown = _withStandIn(gestures.displayed, slotType, workspace)
        decorated = slotType is not None and Slots.decorated(slotType)
        if decorated:
            depends = _decorDepends(slotType, mirror)
            if self._decorInputs.get(name) != depends:
                self._decorInputs[name] = depends
                Widgets.forgetDrawn(pane.views)
        views = pane.render(shown, gestures.selection, session.display, showTags, releaseBar)
        if slotType is not None and Slots.overrides(slotType, "isActive"):
            # 会停用格子的格子类型（合成器式的停用格）：按显示的界面数据盖停用底格。判断按格记着，显示内容、界面数据、
            # 客户端界面状态都没变时不再问（触屏选中、拖动的预览、滚动换行也会重走格子区）
            stamp = (mirror.revision, mirror.dataRevision, mirror.clientRevision)
            known = self._actives.get(name)
            if known is None or known[0] != stamp:
                known = self._actives[name] = (stamp, {})
            actives = known[1]
            for ref, view in views.items():
                active = actives.get(ref)
                if active is None:
                    workspace = workspace or Rules.Workspace(mirror.view, mirror.rules)
                    active = actives[ref] = bool(slotType.isActive(workspace, ref))
                view.setDisabled(not active)
        animated = []
        if decorated:
            # 格子装饰（Std/Decor）：按显示的内容与界面数据画；占位图标的贴图布局可以按格子区另给
            workspace = workspace or Rules.Workspace(mirror.view, mirror.rules)
            for ref, view in views.items():
                if getattr(view, "fresh", True):
                    decoration = slotType.decorate(workspace, ref, gestures.displayed(ref))
                    if pane.placeholder and decoration is not None and decoration.placeholder is not None:
                        decoration = decoration.copy()   # 格子类型可以几格共用一个装饰对象：改之前先复制
                        decoration.placeholder, decoration.frames = pane.placeholder, None
                    view.decorate(decoration, now)
                if view.animated():
                    animated.append(view)
        locate = mirror.key
        keys = dict((locate(ref), (view, pane.slot)) for ref, view in views.items())
        return views, keys, animated

    def _readsClient(self, pane):
        """格子区的格子装饰依赖客户端界面状态（格子类型的 decorDepends 是 DECOR_CLIENT）：按格子区记一次。"""
        found = self._clientPanes.get(pane)
        if found is None:
            collection = self.session.mirror.structure.get(pane.collection)
            found = self._clientPanes[pane] = collection is not None and \
                getattr(collection.slot, "decorDepends", None) == Slots.DECOR_CLIENT
        return found

    def _forgetWalks(self):
        """下一次重画每个格子区都重走、每格都重画（强制重画、布局变了、换了会话）。"""
        self._redrawAll = False
        self._walks, self._decorInputs, self._clientPanes, self._actives = {}, {}, {}, {}
        self._tipKey = None
        for pane in self.panes.values():
            Widgets.forgetDrawn(pane.views)

    def _renderTip(self, gestures, refViews):
        """悬停文本写在悬停的那个格子控件上（引擎只画处于悬停态的按钮里的那份），换了格子时清掉上一个。"""
        tip = gestures.tooltipRef()
        view = refViews.get(tip) if tip is not None else None
        parts = self.parts
        if parts.tipView is not None and parts.tipView is not view:
            parts.tipView.setTip("")
            self._tipKey = None
        parts.tipView = view
        if view is not None:
            stack = gestures.displayed(tip)
            mirror = self.session.mirror
            key = (view, tip, self._category(), mirror.dataRevision, mirror.clientRevision)
            if key == self._tipKey and stack is self._tipStack:
                return   # 同一格、同一件东西，界面数据与客户端界面状态也没变：悬停文本不变
            self._tipKey, self._tipStack = key, stack
            if Items.isEmpty(stack):
                standIn = gestures.standIn(tip)   # 空着的格子：替它显示的东西的悬停文本，或格子类型给的提示
                hint = gestures.hint(tip) if standIn is None else None
                view.setTip(self.session.hoverText(standIn) if standIn is not None
                            else self.session.text(hint) if hint else "")
            else:
                slotType = gestures.slotType(tip)
                custom = slotType.tip(gestures.workspace(), tip, stack, self.session.plainItemName) \
                    if slotType is not None and Slots.tipped(slotType) else None
                if custom is not None:
                    text = Data.renderLang(custom, self.session.text)   # 格子类型另写的字（原版交易界面的材料格写"……不够"）
                else:
                    # 原版：收纳袋不给悬停文本，换成收纳袋提示
                    text = "" if Bundles.isBundle(stack) else self.session.hoverText(stack, self._category())
                if slotType is not None and Slots.overrides(slotType, "hoverText"):
                    text = slotType.hoverText(gestures.workspace(), tip, stack, text)   # 格子类型改写的（追加一行这类）
                view.setTip(text)

    def _category(self):
        """悬停文本带不带东西的分类（界面模型与部件的 hoverCategory：原版创造栏在搜索页时界面里所有东西都带）。"""
        mirror = self.session.mirror
        return bool(mirror.menu.anyHoverCategory(mirror.viewer))

    def _renderBundle(self, gestures, refViews):
        """
        收纳袋，照原版：键鼠与手柄悬停收纳袋时显示跟着指针的提示，提示里选中了一项时那一格上画张开的样子，
        选中的物品从袋口露出来；触屏展开收纳袋时底部显示提示（点了里面的一项或关闭按钮后收起），
        那一格一直画张开的样子。
        """
        session = self.session
        touch = gestures.device == Gestures.TOUCH
        openRef = selected = None
        selection = gestures.bundleSelection() if not touch else None
        if selection is None:
            self.bundleTooltip.hide()
        else:
            ref, cell, index = selection
            bundle = gestures.displayed(ref)
            if index is not None:
                openRef, selected = ref, Bundles.entryItem(Bundles.entries(bundle)[index])
            self.bundleTooltip.show(bundle, session.itemName(bundle), cell,
                                    session.itemName(selected) if selected else "", session.display, False)
        active = gestures.bundleActive if touch else None
        if active is not None and not Bundles.isBundle(gestures.displayed(active["ref"])):
            active = None   # 输入刚改了那一格、还没到下一帧同步展开状态
        if active is None:
            self.bundleTouch.hide()
        else:
            bundle = gestures.displayed(active["ref"])
            index = gestures.activeBundleEntry()
            openRef = active["ref"]
            selected = Bundles.entryItem(Bundles.entries(bundle)[index]) if index is not None else None
            if active["minimized"]:
                self.bundleTouch.hide()
            else:
                # 原版：触屏的标题后面补两个空格，给关闭按钮留位置
                self.bundleTouch.show(bundle, session.itemName(bundle) + "  ", active["cell"] if index is not None else None,
                                      session.itemName(selected) if selected else "", session.display, True)
        openPane = self._paneOf(openRef) if openRef is not None else None
        for name, pane in self.panes.items():
            overlay = pane.bundleOpen
            if overlay is None:
                continue
            position = pane.positionOf(openRef) if name == openPane else None
            view = refViews.get(openRef)
            if position is None or view is None:
                overlay.hide()
                continue
            bundle = gestures.displayed(openRef)
            overlay.show(position, session.idAuxOf(bundle), selected, session.display.storage(bundle), touch,
                         session.display)

    def _paneOf(self, ref):
        """格子在哪个格子区（没有显示它的格子区时为 None）。"""
        for name, pane in self.panes.items():
            if pane.covers(ref):
                return name
        return None

    def _origin(self):
        root = self.GetBaseUIControl(Paths.ROOT)
        return root.GetGlobalPosition() if root is not None else (0.0, 0.0)

    def _splitSide(self, ref):
        """
        原版选数量条的方向：格子区可以指定（经典版快捷栏朝上）；其余按格子在格子区网格里的位置，
        第一列朝右、最后一列朝左、第一行朝下、其余朝上。
        """
        name = self._paneOf(ref)
        pane = self.panes[name] if name is not None else None
        if pane is None:
            return "above"
        if pane.split:
            return pane.split
        columns, index = pane.columns or 1, pane.indexIn(ref)
        column, row = index % columns, index // columns
        if column == 0:
            return "right"
        if column == columns - 1:
            return "left"
        return "below" if row == 0 else "above"

    # ---------------------------------------------------------------- 一次性效果

    def applyEffects(self):
        """取走手势识别留下的一次性效果：物品飞行、物品详情（显示或撤掉）、锁定提示。"""
        gestures = self.session.gestures
        if not gestures.effects:
            return
        effects, gestures.effects = gestures.effects, []
        for kind, value in effects:
            if kind == "fly":
                self._fly(value)
            elif kind == "details":
                stack = gestures.displayed(value)
                if not Items.isEmpty(stack):
                    self.popups.showDetails(self.session.hoverText(stack, self._category()),
                                            self.extension.detailsOffset(self))
            elif kind == "detailsStack":
                self.popups.showDetails(self.session.hoverText(value), self.extension.detailsOffset(self))
            elif kind == "hideDetails":
                self.popups.hideDetails()
            elif kind == "lock":
                self.popups.showLock(self.session.text(value))
            elif kind == "sound":
                if isinstance(value, tuple):
                    self.session.playSound(value[0], value[1])
                else:
                    self.session.playSound(value)
            elif not self.extension.effect(self, kind, value):
                # 自定义的种类（格子的交互放进 g.effects 的）：界面扩展不接时问控件（Widget.onEffect），都不接的丢掉
                any(widget.onEffect(kind, value) for widget in self.parts.widgets)

    def _fly(self, flights):
        """
        原版物品飞行渲染器：每次飞行把物品编号、起止位置（图标左上角）与缩放（图标宽 / 16）写进它的属性包，
        由引擎画飞行过程。起止格子有一个不在屏幕上就不飞（与原版一样）。
        图标位置按格子算（图标居中在格子里）：空格的图标控件是隐藏的，引擎给不出它的尺寸。
        """
        if self.flying is None:
            return
        count = int((self.flying.GetPropertyBag() or {}).get("flying_item_count", 0) or 0)
        scale = self.uiScale   # 整屏按比例缩放的布局：格子与图标都缩了
        icon = _ICON[self.pocket] * scale
        updates = {}
        for stack, source, target, _ in flights:
            origin, destination = self.keyViews.get(source), self.keyViews.get(target)
            if origin is None or destination is None or origin[0].control is None or destination[0].control is None:
                continue
            idAux = self.session.idAuxOf(stack)   # 飞的是这堆东西（从收纳袋取出时起点那一格画的是收纳袋）
            if idAux is None:
                continue
            index = str(count)
            for prefix, (view, slot) in (("origin", origin), ("destination", destination)):
                inset = (slot * scale - icon) / 2.0
                x, y = view.control.GetGlobalPosition()
                updates["flying_item_%s_position_x%s" % (prefix, index)] = float(x) + inset
                updates["flying_item_%s_position_y%s" % (prefix, index)] = float(y) + inset
                updates["flying_item_%s_scale%s" % (prefix, index)] = icon / 16.0
            updates["flying_item_id_aux" + index] = int(idAux)
            # 原版带上物品的附加数据（网络格式 NBT 的 base64），飞着的旗帜、盾牌、装好的弩才画得对
            updates["flying_item_user_data" + index] = Nbt.networkBase64(stack.get("userData"))
            modValue, modExtend = Display.flyingModValues(stack)
            updates["flying_item_mod_value" + index] = modValue
            updates["flying_item_mod_extend_value" + index] = modExtend
            count += 1
        if updates:
            updates["flying_item_count"] = count
            self.flying.SetPropertyBag(updates)

    # ---------------------------------------------------------------- 事件

    def _onKey(self, args):
        """方向键：触屏下（外接键盘）显示格子的高亮与悬停文本，见 _beginTouchHover。"""
        try:
            key, down = int(args.get("key")), str(args.get("isDown")) == "1"
        except (TypeError, ValueError):
            return
        if down:
            self._openPointer = None   # 按过键（方向键挪焦点）之后，焦点带来的悬停照常
        if self.onKey(key, down):
            self._afterInput()   # 派生的界面类接了这个键
        elif down and key in _ARROW_KEYS and self.session.gestures.device == Gestures.TOUCH:
            self._beginTouchHover()
            self._afterInput()
        elif self.session.gestures.onKey(key, down):
            self._afterInput()   # 悬停那一格的交互接了这个键（Interaction.key）

    def onKey(self, key, down):
        """
        键盘按键（界面开着时引擎报的，key 是键码，down 按下为真）：派生的界面类（Layouts.registerScreenClass）加自己的按键，
        接了返回 True（不再交给方向键与悬停那一格的交互），之后当场重画。界面类还可以照常用 ViewBinder.binding 绑自己布局里
        的按钮名。经 self.session 用会话的公开接口（与控件的 model 同一个）。
        """
        return False

    def _hotbarKey(self, index):
        self.session.gestures.onHotbarKey(index)
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot1")
    def _onSlot1(self, args):
        """快捷栏键位：按玩家的键位设置（缺省数字键 1–9），按原版"交互"时机（键盘在按下时）。"""
        self._hotbarKey(0)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot2")
    def _onSlot2(self, args):
        self._hotbarKey(1)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot3")
    def _onSlot3(self, args):
        self._hotbarKey(2)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot4")
    def _onSlot4(self, args):
        self._hotbarKey(3)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot5")
    def _onSlot5(self, args):
        self._hotbarKey(4)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot6")
    def _onSlot6(self, args):
        self._hotbarKey(5)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot7")
    def _onSlot7(self, args):
        self._hotbarKey(6)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot8")
    def _onSlot8(self, args):
        self._hotbarKey(7)

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.slot9")
    def _onSlot9(self, args):
        self._hotbarKey(8)

    def _widgetsAt(self, path):
        """
        按钮路径在哪些控件下面：路径最长的那一层上的控件（同一个控件上可以挂几个，例如按钮与按值显隐）；不在任何控件下面
        时为空。path 从屏幕根算起（引擎报的按钮路径前面还带着屏幕定义名，先用 _fromRoot 去掉）。
        """
        found = []
        for widget in self.parts.widgets:
            if path == widget.path or path.startswith(widget.path + "/"):
                if not found or len(widget.path) > len(found[0].path):
                    found = [widget]
                elif len(widget.path) == len(found[0].path):
                    found.append(widget)
        return found

    def _dispatch(self, path, event):
        """把按钮事件交给按钮所在的控件（event 补上按钮相对控件的路径），处理完当场重画。"""
        widgets = self._widgetsAt(path)
        if not widgets:
            return
        for widget in widgets:
            widget.onInput(dict(event, path=path[len(widget.path):]))
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, Paths.TEXT_CLEAR_BUTTON)
    def _onTextClear(self, args):
        """原版文本框里的清空按钮（$text_clear_button_enabled）：按下时交给按钮所在的控件（文本框清掉框里的字）。"""
        if args.get("ButtonState") == 1:
            self._dispatch(_fromRoot(args.get("ButtonPath") or ""), {"kind": "clear"})

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.widget")   # Paths.WIDGET_BUTTON
    def _onWidget(self, args):
        """控件里的按钮（映射到 #dc.widget）：按下与抬起各一次。"""
        self._dispatch(_fromRoot(args.get("ButtonPath") or ""),
                       {"kind": "button", "down": args.get("ButtonState") == 1, "position": self._position(args)})

    def _listenNamed(self):
        """
        按名字接上控件里的按钮（交互事件与抬起）、文本框（文字事件）与滑块（滑块事件）（推入与重新成为最上面的时候）。引擎按
        屏幕名与名字登记，同名再登记一次会叠加，所以先撤再登；中转对象记在界面上。
        """
        gui = _screenNode.gui
        name = self.screen_name
        self._unlistenNamed()
        for widget in self.parts.widgets:
            for press in widget.presses():
                relay = _PressRelay(self, widget, press)
                gui.unregister_interact_button_handler(name, press)
                gui.register_interact_button_handler(name, press, relay, relay.pressed)
                gui.remove_button_state_handler(name, press, _BUTTON_UP)
                gui.add_button_handler(name, press, relay, relay.released, _BUTTON_UP)
                self._relays.append(relay)
            for box, submit in widget.textBoxes():
                relay = _TextRelay(self, widget, box, bool(submit))
                gui.unregister_text_edit_changed_handler(name, box)
                gui.register_text_edit_changed_handler(name, box, relay, relay.changed, False, False)
                if relay.submit:
                    gui.unregister_text_edit_finished_handler(name, box)
                    gui.register_text_edit_finished_handler(name, box, relay, relay.finished)
                self._relays.append(relay)
            for slider in widget.sliders():
                relay = _SliderRelay(self, widget, slider)
                gui.unregister_slider_changed_handler(name, slider)
                gui.unregister_slider_finished_handler(name, slider)
                gui.register_slider_changed_handler(name, slider, relay, relay.changed)   # 先改动后结束（见 _SliderRelay）
                gui.register_slider_finished_handler(name, slider, relay, relay.finished)
                self._relays.append(relay)

    def _unlistenNamed(self):
        gui = _screenNode.gui
        for relay in self._relays:
            if isinstance(relay, _PressRelay):
                gui.unregister_interact_button_handler(self.screen_name, relay.box)
                gui.remove_button_state_handler(self.screen_name, relay.box, _BUTTON_UP)
            elif isinstance(relay, _SliderRelay):
                gui.unregister_slider_changed_handler(self.screen_name, relay.box)
                gui.unregister_slider_finished_handler(self.screen_name, relay.box)
            else:
                gui.unregister_text_edit_changed_handler(self.screen_name, relay.box)
                if relay.submit:
                    gui.unregister_text_edit_finished_handler(self.screen_name, relay.box)
        self._relays = []
        self._pressing = self._pendingPush = None

    def _bindEngine(self):
        """
        控件向这一屏的引擎登记按名字的绑定与原版下拉（Widget.bind）：每个引擎屏幕一次（推入时）。登记跟着引擎的屏幕走，
        弹出时失效；压在下面再重新成为最上面的还是同一个引擎屏幕，不再登记。
        """
        self._binder = _Binder(self)
        for widget in self.parts.widgets:
            widget.bind(self._binder)

    def _log(self, message):
        if self.session is not None:
            self.session.log(message)

    def _onPressed(self, relay):
        """
        按钮照原版"交互"时机被按下：交给它所在的控件，处理完当场重画。到这个按钮抬起之前推的界面先记下（deferPush）；
        上一下没等到抬起时记下的不推了。
        """
        if not self.ready:
            return
        self._pressing, self._pendingPush = relay.box, None
        relay.widget.onInput({"kind": "press", "name": relay.box})
        self._afterInput()

    def _onReleased(self, relay):
        """交互按钮抬起（触屏的交互在抬起时报，紧接着就是这里）：推按着时记下的界面。"""
        if self._pressing != relay.box:
            return
        pending, self._pressing, self._pendingPush = self._pendingPush, None, None
        if pending is not None and self.ready and self.session is not None:
            self.session.pushScreen(*pending)

    def deferPush(self, namespace, key, params):
        """
        会话的 pushScreen 问：交互按钮报了交互、还没抬起时，要推的界面先记下，抬起时再推，返回 True；没按着时返回 False
        （当场推）。键鼠与手柄的交互在按下时报，这时就推的话这一下的抬起落到新界面上：引擎把刚推入的界面里的焦点控件当成
        悬停，抬起按到它（常见的是新界面自己的"返回"，新界面一出来就弹掉）。
        """
        if self._pressing is None:
            return False
        self._pendingPush = (namespace, key, params)
        return True

    def _onText(self, relay, args, finished):
        """文本框改了文字或输入结束：交给它所在的控件，处理完当场重画。"""
        if not self.ready:
            return
        text = args.get("Text") or ""
        relay.widget.onInput({"kind": "text", "box": relay.box, "text": text if isinstance(text, str) else
                              text.encode("utf-8"), "finished": finished,
                              "enter": args.get("TextCharEventResult") == _ENTER_PRESSED})
        self._afterInput()

    def _onSlider(self, relay, value, finished):
        """滑块动了：交给它所在的控件，处理完当场重画。"""
        if not self.ready:
            return
        relay.widget.onInput({"kind": "slider", "name": relay.box, "value": float(value), "finished": finished})
        self._afterInput()

    def _onPicked(self, picked, index):
        """原版下拉里选了第 index 项（引擎已经收起列表）：交给控件，处理完当场重画。"""
        if not self.ready:
            return
        picked(int(index))
        self._afterInput()

    def _slotOf(self, args):
        """按钮事件来自哪个格子控件：(格子区名, 控件序号)，按事件里的按钮路径找。"""
        path = args.get("ButtonPath") or ""
        for name, pane in self.panes.items():
            index = pane.indexOf(path)
            if index is not None:
                return (name, index)
        return None

    def _refOf(self, args):
        slot = self._slotOf(args)
        return self.panes[slot[0]].refAt(slot[1]) if slot is not None else None

    @staticmethod
    def _position(args):
        if "TouchPosX" in args:
            return (args.get("TouchPosX"), args.get("TouchPosY"))
        return None

    def _slotEvent(self, args, button, keyboard=False):
        ref = self._refOf(args)
        gestures = self.session.gestures
        down = args.get("ButtonState") == 1
        if down and ref is None:
            return
        if down and self._touchHoverUntil is not None:
            self._endTouchHover()
        if down:
            gestures.onSlotDown(ref, button, _now(), self._position(args), keyboard)
        else:
            gestures.onSlotUp(ref, button, _now(), self._position(args))
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.primary")
    def _onPrimary(self, args):
        self._slotEvent(args, Gestures.PRIMARY)

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.ok")
    def _onOk(self, args):
        """回车（与手柄的确认键）：当作左键 / A；触屏下按住回车选数量时数量随按住的时间涨（原版）。"""
        self._slotEvent(args, Gestures.PRIMARY, keyboard=True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.secondary")
    def _onSecondary(self, args):
        self._slotEvent(args, Gestures.SECONDARY)

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.quick")
    def _onQuick(self, args):
        ref = self._refOf(args)
        if ref is not None and args.get("ButtonState") == 1:
            self.session.gestures.onQuick(ref, _now())
            self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.drop")
    def _onDrop(self, args):
        ref = self._refOf(args)
        if ref is not None and args.get("ButtonState") == 1:
            self.session.gestures.onDrop(ref, False)
            self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.dropall")
    def _onDropAll(self, args):
        ref = self._refOf(args)
        if ref is not None and args.get("ButtonState") == 1:
            self.session.gestures.onDrop(ref, True)
            self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.hover")
    def _onHover(self, args):
        if args.get("ButtonState") != 1:
            return
        slot = self._slotOf(args)
        ref = self.panes[slot[0]].refAt(slot[1]) if slot is not None else None
        if ref is None or self._focusHover(slot):
            return
        self._hoverSlot = slot
        self._hoverPointer = self.pointer(Gestures.MOUSE)
        self.session.gestures.onHover(ref, _now(), self._position(args))
        self._afterInput()

    def _focusHover(self, slot):
        """
        刚推入、指针还没动过时引擎报来的悬停（键鼠）：引擎把界面建好时挑的焦点格当成悬停（原版打开时按指针所在的格子算）。
        这一格不在指针下面时不当悬停，下一帧让引擎清掉焦点（悬停高亮与悬停文本没了，按下也不再落到它上面；脚本没法让引擎
        按指针现在的位置重算悬停，所以指针动之前没有悬停的格子），每次推入清一次。指针动过、按过键之后照常。返回是不是这种悬停。
        """
        anchor = self._openPointer
        if anchor is None or self.session.gestures.device != Gestures.MOUSE:
            return False
        pointer = self.pointer(Gestures.MOUSE)
        if pointer is None or abs(pointer[0] - anchor[0]) >= 0.5 or abs(pointer[1] - anchor[1]) >= 0.5:
            self._openPointer = None
            return False
        control = self.panes[slot[0]].views[slot[1]].control
        if control is None:
            return False
        (x, y), (width, height) = control.GetGlobalPosition(), control.GetSize()
        if x <= pointer[0] < x + width and y <= pointer[1] < y + height:
            return False
        if not self._focusDropped:
            self._focusDropped = self._dropFocus = True
        return True

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.panel")
    def _onPanel(self, args):
        self.session.gestures.onPanel(Gestures.PRIMARY, args.get("ButtonState") == 1, _now())
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.panel2")
    def _onPanel2(self, args):
        self.session.gestures.onPanel(Gestures.SECONDARY, args.get("ButtonState") == 1, _now())
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.blank")
    def _onBlank(self, args):
        """点在空白处交给集合的格子区（$dc_scroll_blank）：左键、确认键（原版创造栏删掉手上的，种类存储放进去）。"""
        self.session.gestures.onBlank(self._blankCollection(args), Gestures.PRIMARY, args.get("ButtonState") == 1,
                                      _now())
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.blank2")
    def _onBlank2(self, args):
        """同上，右键。"""
        self.session.gestures.onBlank(self._blankCollection(args), Gestures.SECONDARY, args.get("ButtonState") == 1,
                                      _now())
        self._afterInput()

    def _blankCollection(self, args):
        """点的是哪个空白处交给集合的格子区（按按钮路径；找不到时是第一个）的集合。"""
        path = _fromRoot(args.get("ButtonPath") or "")
        found = [pane for pane in self.panes.values() if pane.spec.get("blank")]
        for pane in found:
            if pane.path and path.startswith(pane.path):
                return pane.collection
        return found[0].collection if found else None

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.outside")
    def _onOutside(self, args):
        self.session.gestures.onOutside(Gestures.PRIMARY, args.get("ButtonState") == 1, _now())
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.outside2")
    def _onOutside2(self, args):
        self.session.gestures.onOutside(Gestures.SECONDARY, args.get("ButtonState") == 1, _now())
        self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.wheelup")
    def _onWheelUp(self, args):
        """原版界面里滚轮向上也是一个按键：悬停收纳袋时在提示里选上一项（指针在分页的列表上时翻页）。"""
        if args.get("ButtonState") == 1:
            self._wheel(True)

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.wheeldown")
    def _onWheelDown(self, args):
        if args.get("ButtonState") == 1:
            self._wheel(False)

    def _wheel(self, up):
        """滚轮：先问控件（Widget.onWheel：指针在分页的列表上时翻页），控件都不要时交给手势；处理完当场重画。"""
        pointer = self.pointer(self.session.gestures.device)
        if not any(widget.onWheel(up, pointer) for widget in self.parts.widgets):
            self.session.gestures.onWheel(up)
        self._afterInput()

    def _stick(self, args, direction):
        if args.get("ButtonState") == 1:
            self.session.gestures.onBundleStick(direction)
            self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.stickup")
    def _onStickUp(self, args):
        """原版：手柄右摇杆在悬停的收纳袋提示里移动选中。"""
        self._stick(args, "up")

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.stickdown")
    def _onStickDown(self, args):
        self._stick(args, "down")

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.stickleft")
    def _onStickLeft(self, args):
        self._stick(args, "left")

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.stickright")
    def _onStickRight(self, args):
        self._stick(args, "right")

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.bcell")
    def _onBundleCell(self, args):
        """触屏点了收纳袋提示里的一格（格子按钮在 .../item_grid/c<格>/slot/button）。"""
        if args.get("ButtonState") != 1:
            return
        path = args.get("ButtonPath") or ""
        marker = path.find("/item_grid/c")
        digits = ""
        for char in path[marker + len("/item_grid/c"):] if marker >= 0 else "":
            if not char.isdigit():
                break
            digits += char
        if digits:
            self.session.gestures.onBundleCell(int(digits))
            self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.bhide")
    def _onBundleHide(self, args):
        if args.get("ButtonState") == 1:
            self.session.gestures.onBundleHide()
            self._afterInput()

    @ViewBinder.binding(ViewBinder.BF_ButtonClick, "#dc.btip")
    def _onBundleTip(self, args):
        """触屏点在收纳袋提示的空白处：原版只是吃掉这一下（不算点在面板外）。"""
        return

    @ViewBinder.binding(ViewBinder.BF_InteractButtonClick, "#dc.close")
    def _onClose(self, args):
        """与原版退出一样按"交互"触发：键鼠与手柄在按下时、触屏在抬起时。"""
        self.session.requestClose()

    # ---------------------------------------------------------------- 工具

    def stackAt(self, ref):
        return self.session.gestures.displayed(ref) if ref is not None else None

    def isEmptyAt(self, ref):
        return Items.isEmpty(self.stackAt(ref))
