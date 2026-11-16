# -*- coding: utf-8 -*-
"""
手势识别（内核）：把界面送来的原始输入（按下、抬起、悬停、按键、滚轮、每帧的指针位置）交给格子类型的交互
（Common/Slots.Interaction），记着进行中的手势与界面要画的状态。拿放的规矩不在这里：每一种输入先交给那一格的交互，交互不接
（返回假）时交给标准交互（Common/Slots.standard()，库带的是 Std/Interactions.Standard：原版容器界面的全部手势，键鼠、手柄、
触屏，各步都是可以改写的方法）。

一次按下到松开（Press）有一个主人（交互）：之后每帧（holdTick）、指针移进别的格子（holdHover）、松开或被打断（holdRelease）
都交给它。标准交互的按住记在 Press 的 mode 上（拖动分配、渐进拿取、选数量……）；格子类型接管的按住（hold）是 "held"。
面板外的点击、拿在指针上的东西的 Q、手柄 Y 手上有东西时的丢出不属于哪一格，交给标准交互。
悬停时按的键盘键（引擎报的键码）交给悬停那一格的交互（key），滚轮先问悬停那一格的交互（wheel），手柄提示条的说明也问它
（helpers）；交互不接时照标准交互。

本模块只依赖镜像（Mirror）与规则，不依赖引擎；时间、指针位置都由调用方给出，便于离线测试。
按住的计时照原版：键鼠从按下前最近一次 tick 算起（原版按住事件的倒计时在按下那一帧就扣掉一整帧），
触屏长按从按下后第一次 tick 算起（原版在按下后的第一次刷新才记下起点）。
界面读本模块的状态来画：preview（拖动与按住时的预览，{容器格: 物品堆}）、selection、progress、slider、hovered、
bundleHover、bundleActive；另外把一次性的视觉效果放进 effects 由界面取走：("fly", 飞行列表，起止是容器格)、("details", 格)、
("detailsStack", 物品堆)、("hideDetails", None)、("lock", 提示文案键)、("sound", 音效名或 (音效名, 音量))。
"""
import math

from ..Common import Bundles, Items, Ops, Rules, Slots
from ..Common.Collections import CURSOR_REF
from . import Flights

PRIMARY = Rules.PRIMARY
SECONDARY = Rules.SECONDARY

MOUSE = Slots.MOUSE
TOUCH = Slots.TOUCH
GAMEPAD = Slots.GAMEPAD

TOUCH_LONG_PRESS_SECONDS = 0.525   # 触屏长按进入选数量：原版取玩家的控制设置（拆分物品触发时间），这是它的缺省值
TOUCH_SCROLL_PIXELS = 35.4         # 触屏按下之后手指动过这么多屏幕像素算拖动（滚动、分配），不算点按


def _distance(a, b):
    if a is None or b is None:
        return 0.0
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Press(object):
    """一次按下到松开的过程。owner 是它的主人（交互）；标准交互的按住记在 mode 等字段上，格子类型接管的记在 data 里。"""

    def __init__(self, ref, button, now, position, cursor, holdFrom=None, owner=None):
        self.ref = ref
        self.button = button
        self.start = now
        self.holdFrom = holdFrom      # 按住计时的起点（见模块说明）；触屏在按下后第一次 tick 时记
        self.position = position
        self.cursor = cursor          # 按下时手上的东西
        self.mode = "pending"         # 标准交互：pending / drag / progressive / scroll / slider / split / bundle；接管的是 held
        self.owner = owner            # 这次按住的主人（Common/Slots.Interaction）
        self.data = {}                # 接管的交互记在这次按住上的东西
        self.targets = [ref]
        self.progressStart = None
        self.amount = None
        self.sliderOrigin = None
        self.noSlider = False         # 触屏：这次长按不进入选数量
        self.keyboard = False         # 回车（或手柄确认键）按的：触屏下选数量随按住的时间涨；键鼠与手柄下见 onSlotDown
        self.sliderStart = None


class Gestures(object):
    """
    mirror：Mirror；send(request)：把请求发给服务端；profile()：当前界面档；call(动作名, 线上写法的参数) -> 发没发：
    发动作（格子类型的交互用，例如合成器式的停用格切换；不给时交互发不了动作）。
    """

    def __init__(self, mirror, send, profile, call=None):
        self.mirror = mirror
        self._send = send
        self._profile = profile
        self._call = call
        self.standard = Slots.standard()   # 标准交互：格子的交互不接的都交给它
        self.device = MOUSE
        self.press = None
        self.hovered = None
        self.selection = None          # 触屏选中：{"ref": 格, "amount": 数量或 None}
        self.lastPress = None          # 上一次按下：(格, 时间, 位置, 键)（双击收集）
        self.lastKeyboard = False      # 上一次按下是不是确认键按的（双击只认同一路：左键接回车不算）
        self.lastActionRef = None      # 上一个手势作用的格子（双击收集要求是同一格）
        self.preview = {}
        self._tooltipMemo = None       # tooltipRef 记着的：(悬停的格等, 手势预览, 镜像, 结果)
        self._layoutMemo = None        # 上一次排的收纳袋提示：(收纳袋的物品堆, 排布)
        self.progress = None           # (格, 数量, 总数)
        self.slider = None             # (格, 数量, 总数)
        self.outsidePress = None
        self.uiScale = 1.0             # 屏幕像素 / 界面单位（触屏的滚动阈值按屏幕像素算）
        self.decidingSince = None      # 触屏上一次按在有东西的格子上的时间
        self.longPress = TOUCH_LONG_PRESS_SECONDS   # 触屏长按多久进入选数量（客户端服务按玩家的设置改）
        self.bundleHover = None        # 键鼠与手柄悬停着的收纳袋：[格, 提示里选中的网格格或 None]
        self.bundleActive = None       # 触屏展开着的收纳袋：{"ref": 格, "cell": 选中的网格格或 None, "minimized": 提示收起了}
        self.effects = []              # 一次性的视觉效果，界面取走后清空
        self.pointer = None            # 这一帧的指针（tick 给的界面坐标）
        self.lastTick = None           # 上一次 tick 的时间（键鼠按住计时的起点）
        self._memory = {}              # 格子类型的交互跨手势记的东西：id(交互) -> 字典

    # ---------------------------------------------------------------- 状态

    def displayed(self, ref):
        return self.mirror.displayed(ref, self.preview)

    def tooltipRef(self):
        """
        该给悬停文本的格子，照原版：悬停的格子有东西（空着的格子要格子类型给了提示，见 hint），且没有按住（触屏下按住也给）。
        画不画出来由引擎按按钮的悬停态决定；触屏下高亮连同文本平时藏着，见界面的 _showHover。悬停的格子、按住、
        输入方式、显示内容、界面数据、客户端界面状态、手势预览都没变时记着上一次的（重画每帧都问它）。
        """
        if self.hovered is None or (self.press is not None and self.device != TOUCH):
            return None
        mirror = self.mirror
        stamp = (self.hovered, self.device, mirror.revision, mirror.dataRevision, mirror.clientRevision)
        memo = self._tooltipMemo
        if memo is not None and memo[0] == stamp and memo[1] is self.preview and memo[2] is mirror:
            return memo[3]
        if not Items.isEmpty(self.displayed(self.hovered)):
            found = self.hovered
        else:
            found = self.hovered if self.hint(self.hovered) or self.standIn(self.hovered) else None
        self._tooltipMemo = (stamp, self.preview, mirror, found)
        return found

    def hint(self, ref):
        """空着的格子 ref 悬停时的提示（格子类型的 hint：语言文件的键），没有为 None。"""
        slotType = self.slotType(ref)
        if slotType is None or not Slots.hinted(slotType):
            return None
        return slotType.hint(self.workspace(), ref)

    def standIn(self, ref):
        """空着的格子 ref 替它显示的物品（格子类型的 standIn，原版织布机的图案格），没有为 None。"""
        slotType = self.slotType(ref)
        if slotType is None or not Slots.standsIn(slotType):
            return None
        return slotType.standIn(self.workspace(), ref)

    def releaseBarVisible(self, now):
        """
        触屏选好数量后、选中框上显示数量的进度条，照原版：正在选数量时不显示；
        手指按在有东西的格子上之后的 0.525 秒内也不显示（不管松没松开）。
        """
        selection = self.selection
        if self.device != TOUCH or not selection or not selection["amount"] or self.slider is not None:
            return False
        return self.decidingSince is None or now - self.decidingSince > self.longPress

    def setDevice(self, device):
        if device != self.device:
            self.reset()
            self.bundleHover = None
            self.bundleActive = None
            self.device = device

    def reset(self):
        """输入方式切换、界面关闭：结束进行中的手势，清掉选中与预览（预测已发出的不受影响）。"""
        self.press = None
        self.preview = {}
        self.progress = None
        self.slider = None
        self.selection = None
        self.bundleActive = None
        self.outsidePress = None
        self.lastPress = None

    # ---------------------------------------------------------------- 发请求

    def do(self, op):
        """在镜像上预测一个操作并把请求发给服务端，带上物品飞行与锁定提示；做成了（改了东西）返回 True。"""
        kind = Ops.get(op[0])
        if kind is None:
            raise ValueError("operation %r is not registered (Ops.register)" % (op[0],))
        if kind.drops and not self.mirror.dropAllowed:
            return False   # 原版：不能丢东西时（访客、世界禁止丢弃）丢的手势什么都不做，也不提示
        cursorBefore = self.mirror.get(CURSOR_REF)
        request = self.mirror.predict(op, self._profile())
        if request is None:
            self._lockNotice(kind, op, cursorBefore)
            return False
        self._send(request)
        mirror = self.mirror
        flights = kind.flights(op, mirror.lastChanges, mirror.key, self.device)
        if flights is None and kind.flies(op, self.device, cursorBefore):
            cursor = mirror.key(CURSOR_REF)
            changes = dict((key, change) for key, change in mirror.lastChanges.items() if key != cursor)
            origin = kind.flyFrom(op)
            flights = Flights.transfers(changes, mirror.keyOrder, mirror.key(origin) if origin is not None else None)
        if flights:
            self.effects.append(("fly", flights))
        return True

    def _lockNotice(self, kind, op, cursorBefore):
        """
        原版：拿在指针上的东西做完操作后原样还在、而且是锁定的（操作因锁定没做成），上方提示一下（提示什么由操作定：
        丢弃时提示不能丢，其他提示不能移出）。触屏不走指针，不在这里提示。
        """
        if self.device == TOUCH or Items.isEmpty(cursorBefore) or Items.lockMode(cursorBefore) == Items.LOCK_NONE:
            return
        notice = kind.lockNotice(op)
        if notice:
            self.effects.append(("lock", notice))

    # ---------------------------------------------------------------- 给格子类型的交互用的

    def slotType(self, ref):
        """格子 ref 的格子类型（集合不存在为 None）。"""
        collection = self.mirror.structure.get(ref[0]) if ref is not None else None
        return collection.slot if collection is not None else None

    def interactionAt(self, ref):
        slotType = self.slotType(ref)
        return slotType.interaction if slotType is not None else Slots.STANDARD

    def profile(self):
        """当前界面档（预览操作时用）。"""
        return self._profile()

    def startPress(self, ref, button, now, position, owner, cursor=None, holdFrom=None):
        """开始一次以 owner（交互）为主人的按住（标准交互用它，mode 是 pending）；返回按住对象。"""
        self.press = press = Press(ref, button, now, position, cursor, holdFrom, owner)
        return press

    def hold(self, ref, button, now, position, owner):
        """
        开始一次由交互 owner 接管的按住：之后每帧调用 owner.holdTick，松开或被打断时调用 owner.holdRelease；
        这一下不进入拖动分配、渐进拿取与收集同类。返回按住对象（owner 可以往它的 data 里记东西）。
        """
        press = self.startPress(ref, button, now, position, owner)
        press.mode = "held"
        return press

    def finish(self, now):
        """结束键鼠与手柄进行中的按住（松开，或被别的手势打断）：交给它的主人（holdRelease，格子为 None）。"""
        press, self.press = self.press, None
        self.preview = {}
        self.progress = None
        if press is not None:
            (press.owner or self.standard).holdRelease(self, press, None, now)

    def forgetDoubleClick(self):
        """这一下之后的下一下不能接成双击。"""
        self.lastPress = None

    def beginSlider(self, press, origin, now):
        """触屏：把接管的按住转成选数量（交给标准交互），选中的就是按住的格子，之后照普通格子的选数量走。"""
        press.owner, press.mode = self.standard, "slider"
        press.sliderOrigin, press.sliderStart = origin, now
        self.selection = {"ref": press.ref, "amount": None, "origin": origin}
        self.effects.append(("hideDetails", None))   # 原版：进入选数量时撤掉物品详情

    def memory(self, owner):
        """交互 owner 跨手势记的东西（例如上一次松开的时间）。"""
        return self._memory.setdefault(id(owner), {})

    def call(self, name, args):
        """发动作（args 是线上写法的参数）：可预测的动作当场改显示的界面数据。发了返回 True。"""
        return bool(self._call is not None and self._call(name, args))

    def workspace(self):
        """在显示的状态上的一份工作副本（交互判断格子停没停用、收不收时用；不提交）。"""
        return Rules.Workspace(self.mirror.view, self.mirror.rules)

    def wire(self, ref):
        """格子的线上写法（发动作时当参数）。"""
        return Ops.wireRef(ref, self.mirror.structure)

    def oneStack(self, stack):
        """一次拿得动的一组（超堆叠的格子里渐进拿取、选数量、丢整堆都先截成原版的堆叠数）。"""
        return min(Items.count(stack), self.mirror.rules.maxStack(stack)) if not Items.isEmpty(stack) else 0

    def select(self, ref, amount=None):
        """触屏：选中 ref（amount 是选好的数量，None 为整堆）。"""
        self.selection = {"ref": ref, "amount": amount}

    def takeSelection(self):
        """触屏：取走选中的（{"ref", "amount"}，没有为 None）并取消选中。"""
        selection, self.selection = self.selection, None
        return selection

    def sound(self, name, volume=None):
        """在本地放一次音效（界面取走 effects 时放）。"""
        self.effects.append(("sound", name if volume is None else (name, volume)))

    def details(self, ref):
        """触屏：在底部显示 ref 里东西的完整悬停文本（原版的物品详情）。"""
        self.effects.append(("details", ref))

    def lockNotice(self, key):
        """上方显示锁定提示（文案键，原版的 notification.lock.*）。"""
        self.effects.append(("lock", key))

    def tapped(self, press, ref, now):
        """
        触屏：接管的按住松开时算不算一下点按（交互的 holdRelease 里用）：松开在按下的那一格、按住不到长按的时间、
        没有拖动过（交互在 holdTick 里记 press.data["moved"]）。
        """
        held = now - (press.holdFrom if press.holdFrom is not None else press.start)
        return ref == press.ref and held < self.longPress and not press.data.get("moved")

    def scrolled(self, press, pointer):
        """触屏：手指离按下的地方动过了滚动的距离（屏幕像素算）。"""
        return pointer is not None and _distance(pointer, press.position) * self.uiScale >= TOUCH_SCROLL_PIXELS

    def trackMove(self, press, pointer):
        """触屏：接管的按住期间手指动过了滚动的距离就记下（之后松开不算点按）。交互的 holdTick 里调用。"""
        if self.scrolled(press, pointer):
            press.data["moved"] = True

    # ---------------------------------------------------------------- 原始输入

    def onSlotDown(self, ref, button, now, position, keyboard=False):
        """
        keyboard：这一下是回车（或手柄确认键）按的。触屏下选数量随时间涨；键鼠与手柄下，左键与确认键同时按在同一格时
        照原版只算一下：一下还按着时，同一格、同一个键的另一路按下不算新的一下，两个抬起里先到的结束这一下。
        """
        interaction = self.interactionAt(ref)
        if self.device == TOUCH:
            # 上一下要是被滚动视图接走了，抬起不会报给格子：新的一下按下时丢掉它
            self.press = None
            if not interaction.touchPress(self, ref, now, position):
                self.standard.touchPress(self, ref, now, position)
            if self.press is not None:
                self.press.keyboard = keyboard
            return
        press = self.press
        if press is not None:
            if press.ref == ref and press.button == button and press.keyboard != keyboard:
                return
            self.finish(now)
        if keyboard != self.lastKeyboard:
            self.lastPress = None   # 原版的双击按同一个键判：左键点完接着按回车（或反过来）是两下普通的点按
        self.lastKeyboard = keyboard
        if not interaction.press(self, ref, button, now, position):
            self.standard.press(self, ref, button, now, position)
        if self.press is not None:
            self.press.keyboard = keyboard

    def onSlotUp(self, ref, button, now, position):
        if self.press is None:
            return
        if self.device == TOUCH:
            press, self.press = self.press, None
            self.preview = {}
            self.slider = None
            (press.owner or self.standard).holdRelease(self, press, ref, now)
            return
        self.finish(now)

    def onHover(self, ref, now, position):
        previous, self.hovered = self.hovered, ref
        self._hoverBundle(ref)
        press = self.press
        if press is None or ref == previous:
            return
        (press.owner or self.standard).holdHover(self, press, ref, now)

    def onHoverLost(self):
        """指针离开了所有格子（界面按指针位置判断后调用）。"""
        self.hovered = None
        self.bundleHover = None

    def rehover(self, ref):
        """滚动换掉了指针（或手柄焦点）下那个控件显示的格子：只更新悬停的格子，不当作指针移进了新格子。"""
        self.hovered = ref
        self._hoverBundle(ref)

    def _keysBlocked(self):
        press = self.press
        return press is not None and (press.owner or self.standard).keysBlocked(self, press)

    def onQuick(self, ref, now):
        """Shift 点击、手柄 Y（手柄手上有东西时是丢出整堆：原版这个键的意思，不问格子）。"""
        if self.press is not None:
            self.finish(now)
        if self.device == GAMEPAD and not Items.isEmpty(self.mirror.get(CURSOR_REF)):
            self.standard.dropHeld(self, True)
            return
        if self.device == TOUCH:
            return
        if not self.interactionAt(ref).quick(self, ref):
            self.standard.quick(self, ref)

    def onDrop(self, ref, whole):
        """悬停时 Q（whole 为假）或 Ctrl+Q（whole 为真）；手上有东西时 Q 丢手上的一个（不问格子）。"""
        if self.device != MOUSE or self._keysBlocked():
            return
        if not Items.isEmpty(self.mirror.get(CURSOR_REF)):
            if not whole:
                self.standard.dropHeld(self, False)
            return
        if not self.interactionAt(ref).drop(self, ref, whole):
            self.standard.drop(self, ref, whole)

    def onHotbarKey(self, index):
        """
        快捷栏键位（玩家键位设置里的快捷栏 1–9，index 为 0–8）：悬停时交给那一格的交互（缺省与快捷栏第 index 格互换）。
        照原版只在键鼠、不在渐进拿取时；网易版原版容器界面里这组键不起作用，这里保留。
        """
        if self.device != MOUSE or self.hovered is None or self._keysBlocked():
            return
        if not self.interactionAt(self.hovered).hotbar(self, self.hovered, index):
            self.standard.hotbar(self, self.hovered, index)

    def onKey(self, key, down):
        """悬停时按了键盘的键（引擎的键码，down 按下 / 抬起）：交给悬停那一格的交互（key）。接了返回 True。"""
        ref = self.hovered
        return ref is not None and bool(self.interactionAt(ref).key(self, ref, key, down))

    def onOutside(self, button, down, now):
        """在面板外按下 / 抬起：有按下中的手势时当作松开，不然交给标准交互（outside：丢出手上的、触屏选中的东西）。"""
        if self.press is not None and not down:
            self.onSlotUp(None, button, now, None)
            return
        self.standard.outside(self, button, down, now)

    def onBlank(self, name, button, down, now):
        """
        点在格子区 name 的空白处（布局写了 $dc_scroll_blank）：键鼠按下时交给这个集合的交互（Interaction.blank：原版创造栏
        左键删掉手上的，种类存储放进去）；触屏、交互不接的照面板空白处。
        """
        if down and name is not None and self.device != TOUCH and self.press is None \
                and self.interactionAt((name, 0)).blank(self, name, button):
            self.lastPress = None
            return
        self.onPanel(button, down, now)

    def onPanel(self, button, down, now):
        """点在面板空白处：不丢东西；有按下中的手势时当作松开。"""
        if not down and self.press is not None:
            self.onSlotUp(None, button, now, None)
        if self.device == TOUCH and down:
            self.outsidePress = None

    def onWheel(self, up):
        """滚轮：先问悬停那一格的交互（wheel），不接时照标准交互（键鼠悬停收纳袋时在提示里选一项）。"""
        ref = self.hovered
        if ref is not None and self.interactionAt(ref).wheel(self, ref, up):
            return
        self.standard.wheel(self, ref, up)

    def helpers(self):
        """手柄提示条四个键（x、a、y、b）的说明（语言文件的键）：先问悬停那一格的交互，没给时照标准交互。"""
        ref = self.hovered
        texts = self.interactionAt(ref).helpers(self, ref) if ref is not None else None
        return tuple(texts) if texts is not None else tuple(self.standard.helpers(self, ref))

    def tick(self, now, pointer):
        """每帧调用：收纳袋悬停状态、按住的计时与进行（交给按住的主人）。pointer 为界面坐标（手柄时可为 None）。"""
        self.pointer = pointer
        self._syncBundleHover()
        self._syncBundleActive()
        self.lastTick = now
        press = self.press
        if press is None:
            return
        if self.device == TOUCH and press.holdFrom is None:
            press.holdFrom = now        # 原版：按下后的第一次刷新记下长按的起点
        owner = press.owner or self.standard
        owner.holdTick(self, press, now, pointer)
        if self.press is press and press.owner is not None and press.owner is not owner:
            press.owner.holdTick(self, press, now, pointer)   # 交给了别的主人（转成选数量）：这一帧接着走

    # ---------------------------------------------------------------- 收纳袋的悬停状态

    def _hoverBundle(self, ref):
        """原版：键鼠与手柄移到一格上时，那一格是收纳袋就开始悬停它（提示里的选中清掉），不是就不悬停。"""
        if self.device == TOUCH:
            return
        self.bundleHover = [ref, None] if ref is not None and Bundles.isBundle(self.displayed(ref)) else None

    def _syncBundleHover(self):
        """悬停的格子变成收纳袋（比如刚放下一个）或不再是收纳袋时跟着变；选中的一项没了时清掉选中。"""
        if self.device == TOUCH:
            self.bundleHover = None
            return
        hovered = self.hovered
        bundle = self.displayed(hovered) if hovered is not None else None
        if not Bundles.isBundle(bundle):
            self.bundleHover = None
            return
        if self.bundleHover is None or self.bundleHover[0] != hovered:
            self.bundleHover = [hovered, None]
        elif self.bundleHover[1] is not None \
                and self._tooltipLayout(bundle).entryIndexAt(self.bundleHover[1]) is None:
            self.bundleHover[1] = None

    def bundleSelection(self):
        """悬停着的收纳袋与提示里选中的项：(格, 网格格, 内容的第几项)，没选中时后两项为 None；没悬停收纳袋时为 None。"""
        hover = self.bundleHover
        if hover is None:
            return None
        bundle = self.displayed(hover[0])
        if not Bundles.isBundle(bundle):
            return None   # 输入刚改了那一格、还没到下一帧同步悬停状态
        if hover[1] is None:
            return (hover[0], None, None)
        index = self._tooltipLayout(bundle).entryIndexAt(hover[1])
        return (hover[0], hover[1] if index is not None else None, index)

    def onBundleStick(self, direction):
        """
        原版：手柄悬停在装着东西的收纳袋上时，右摇杆在提示里移动选中（direction 为 "up" / "down" / "left" / "right"）：
        没选中时向右选第一格、其余方向选最后一格；左右在同一行里移动，上下隔一行，越界时不动。
        """
        hover = self.bundleHover
        if self.device != GAMEPAD or hover is None:
            return
        bundle = self.displayed(hover[0])
        if not Bundles.entries(bundle):
            return
        layout = self._tooltipLayout(bundle)
        first, last = layout.firstAndLast()
        cell = hover[1]
        if cell is None:
            hover[1] = first if direction == "right" else last
            return
        columns = layout.columns
        if direction in ("left", "right"):
            target = cell + (1 if direction == "right" else -1)
            if target // columns == cell // columns and first <= target <= last:
                hover[1] = target
        else:
            target = cell + (columns if direction == "down" else -columns)
            if first <= target <= last:
                hover[1] = target

    # ---------------------------------------------------------------- 收纳袋（触屏）的展开状态

    def closeBundle(self):
        """触屏：收起展开着的收纳袋，取消选中。"""
        self.bundleActive = None
        self.selection = None

    def activeBundleEntry(self):
        """触屏展开着的收纳袋在提示里选中的那一项是内容的第几项（没选中为 None）。"""
        active = self.bundleActive
        if active is None or active["cell"] is None or not Bundles.isBundle(self.mirror.get(active["ref"])):
            return None
        return self._tooltipLayout(self.mirror.get(active["ref"])).entryIndexAt(active["cell"])

    def _tooltipLayout(self, bundle):
        """收纳袋 bundle 的提示排布（Bundles.TooltipLayout）：同一个物品堆对象记着（悬停着收纳袋时每帧都问）。"""
        memo = self._layoutMemo
        if memo is not None and memo[0] is bundle:
            return memo[1]
        layout = Bundles.TooltipLayout(bundle)
        self._layoutMemo = (bundle, layout)
        return layout

    def onBundleCell(self, cell):
        """
        触屏点了提示里的一格（原版：再点同一格取消选中，否则选中它；提示收起；选中了就在底部显示它的完整悬停文本）。
        """
        active = self.bundleActive
        if active is None or self.device != TOUCH:
            return
        active["cell"] = None if active["cell"] == cell else cell
        active["minimized"] = True
        index = self.activeBundleEntry()
        if index is not None:
            self.effects.append(("detailsStack", Bundles.entryItem(Bundles.entries(self.mirror.get(active["ref"]))[index])))

    def onBundleHide(self):
        """触屏点了提示的关闭按钮：收起提示，收纳袋仍然选中。"""
        if self.bundleActive is not None and self.device == TOUCH:
            self.bundleActive["minimized"] = True

    def _syncBundleActive(self):
        """触屏展开着的收纳袋那一格不再是收纳袋（被别处拿走等）时收起。"""
        active = self.bundleActive
        if active is not None and (self.device != TOUCH or not Bundles.isBundle(self.mirror.get(active["ref"]))):
            self.bundleActive = None
            if self.selection is not None and self.selection["ref"] == active["ref"]:
                self.selection = None
