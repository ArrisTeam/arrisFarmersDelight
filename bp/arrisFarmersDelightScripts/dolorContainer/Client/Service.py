# -*- coding: utf-8 -*-
"""
客户端服务：接服务端消息（open / ack / update / close），持有当前会话（镜像 + 手势），推界面、发请求。

同一时间最多一个会话。界面档（经典版 / 携带版）在开屏时定下；界面开着时切换了界面档就关掉重开。
几个模组各带一份本库时，界面登记键按使用方区分；推界面前经 Common.Shared 收起别的使用方开着的容器界面。
"""
import time

import mod.client.extraClientApi as clientApi

try:
    from mod.client.component import blockInfoCompClient, configCompClient
except ImportError:
    raise  # 组件模块按端提供，网易打包机审按"可能不存在"判，导入要包在 try 里；缺了照样抛

from ...QuModLibs.Client import AllowCall, Call, Listen, ListenForEvent
from .. import HOST
from ..Common import Collections, Data, Items, Modules, Schema, Shared
from ..Std.Client import Defaults  # noqa: F401  库自带的缺省实现（原版操作、配方的引擎查询……）随之登记
from . import Display, Emoticons, Gestures, Layouts, Paths, Widgets
from .Mirror import Mirror, MenuMissing
from .Remembered import Remembered

_levelId = clientApi.GetLevelId()
_factory = clientApi.GetEngineCompFactory()
_clientlevel = blockInfoCompClient.clientlevel
_OPTION_INPUT_MODE = clientApi.GetMinecraftEnum().OptionId.INPUT_MODE
Modules.addEngineImporter(clientApi.ImportModule)   # 可选件用到才载入（Common/Modules.py）：importlib 还没载入时经引擎导入
UI_NAMESPACE = "dolorContainer_" + HOST
_SCREEN_KEY = ("client", "screen")
_SCREEN_CLASS = __name__.rsplit(".", 1)[0] + ".Screen.ContainerScreen"

_basicInfo = {}
_hoverText = {}
_clientStates = {}   # 界面模型名 -> {客户端界面状态的名字: 值}：重开同一种界面时还在（只记在这次游戏里）
_EVENTS = object()   # 动态监听的名字空间：QuModLibs 按（名字空间，函数名）给监听起名、引擎按名字回调，不带名字空间时
                     # 同一个模组里同名的处理函数（库里的、使用方的）会串成一个
_CONFIG_NAME = "dolor_container_%s_client_state" % "".join(c if c.isalnum() else "_" for c in HOST)   # 本地配置名只能有字母数字下划线
_current = [None]
_buried = []   # 切换到别的布局时压在新屏幕下面的旧屏幕，从下往上（新屏幕上栈时整个藏起来；关界面时一起弹出）
_revealing = [None]   # 切回压在下面的屏幕时，等引擎弹完它上面的屏幕再显示的那一屏（_reveal）


def current():
    return _current[0]


def basicInfo(name, aux):
    key = (name, aux)
    info = _basicInfo.get(key)
    if info is None:
        info = _factory.CreateItem(_levelId).GetItemBasicInfo(name, aux) or {}
        _basicInfo[key] = info
    return info


def _maxDurability(name, aux):
    return basicInfo(name, aux).get("maxDurability", 0)


RULES = Items.ItemRules(lambda name, aux: basicInfo(name, aux).get("maxStackSize", 64), _maxDurability, basicInfo)


def _utf8(text):
    return text if isinstance(text, str) else text.encode("utf-8")


_texts = {}     # 语言文件的键 -> 字（每个会话开始时清空：中途换语言在下一个界面生效）
_names = {}     # 物品堆对象的 id -> (物品堆, 悬停名)（同一个物品堆对象反复画时不再问引擎）
_components = {}


def _component(kind):
    """这一端的引擎组件（按种类建一次，之后复用）。"""
    found = _components.get(kind)
    if found is None:
        found = _components[kind] = getattr(_factory, kind)(_levelId)
    return found


def text(key):
    """语言文件里 key 对应的中文（找不到时返回 key 本身）。按键记着。"""
    found = _texts.get(key)
    if found is None:
        found = _texts[key] = _utf8(_component("CreateGame").GetChinese(key))
    return found


def uiProfilePocket():
    return _component("CreatePlayerView").GetUIProfile() == 1


def stackSplittingTrigger():
    """
    触屏长按多久进入选数量（秒）：原版取玩家控制设置里的"拆分物品触发时间"（毫秒，缺省 525，0 到 3000），
    这里照样每次开屏读一次，读不到时用缺省值。
    """
    try:
        value = float(configCompClient.setting.get_option("ctrl_stacksplittingtriggertime"))
    except Exception:  # noqa: BLE001
        return Gestures.TOUCH_LONG_PRESS_SECONDS
    return value / 1000.0 if 0.0 <= value <= 3000.0 else Gestures.TOUCH_LONG_PRESS_SECONDS


def detectDevice():
    mode = _component("CreatePlayerView").GetToggleOption(_OPTION_INPUT_MODE)
    if mode == 1 or clientApi.IsTouchWithMouse():
        return Gestures.TOUCH
    if mode == 2:
        return Gestures.GAMEPAD
    return Gestures.MOUSE


class ClientSession(object):

    def __init__(self, message):
        _texts.clear()   # 语言可能换过：字从这个会话起重新问引擎
        self._showTags = None
        self.mirror = Mirror(message, RULES)
        layoutName = self.mirror.menu.layout
        self.layout = Layouts.get(layoutName)
        # 物品显示与手势识别的类可以按布局换（Layouts.registerDisplay / registerGestures）
        displayClass = Layouts.displayClass(layoutName) or Display.Context
        self.display = displayClass(RULES, lambda name, aux: basicInfo(name, aux).get("id_aux"))
        self.sessionId = message["s"]
        self.typeId = message.get("type")
        self.title = Data.renderTitle(message.get("title"), text)   # 容器类型的 titleFor 给的，按语言拼
        self.inventoryTitle = text("chestScreen.header.player")
        self.texts = {"title": self.title, "inventoryTitle": self.inventoryTitle}   # 布局里写文字的控件按名字取
        self.pocket = uiProfilePocket()
        self.screen = None
        self.closed = False
        self._switching = False
        gesturesClass = Layouts.gesturesClass(layoutName) or Gestures.Gestures
        self.gestures = gesturesClass(self.mirror, self._sendAct, self._profile, self.call)
        self.gestures.longPress = stackSplittingTrigger()
        self.gestures.device = detectDevice()
        menu = self.mirror.menu
        fresh = menu.menuName not in _clientStates
        self._clientState = _clientStates.setdefault(menu.menuName, {})
        if fresh:
            _remembered.restore(menu, self._clientState)   # 这次游戏里第一次开这种界面：读回记在配置里的
        for name in menu.freshClientState:
            self._clientState.pop(name, None)   # 每次打开都从空值开始的那几项
        self.mirror.clientState = self._clientState   # 规则（格子装饰、提示）经 ws.client 读
        self._editing = {}   # 界面上正在改、还没定下来的值：名字 -> 值（setEditing）
        self.refusedWords = 0   # 文本框的字含敏感词的次数（布局里的敏感词提示按它闪，见 noteRefusedWords）
        self._displayed = {}    # 格子 -> ((显示内容的版本, 预览), 显示的东西)：控件每帧读格子时不重算（见 displayed）

    # ---------------------------------------------------------------- 给界面用

    def now(self):
        return time.time()

    def dataValue(self, name, now):
        """界面数据现在的值（算上还没应答的可预测动作，见 Mirror.dataValue）。"""
        return self.mirror.dataValue(name, now)

    def viewerValue(self, name):
        """这位查看者的状态现在的值（算上还没应答的可预测动作，见 Mirror.viewerValue）。"""
        return self.mirror.viewerValue(name)

    def value(self, name, now):
        """
        按名字取界面数据、每位查看者的状态或客户端界面状态现在的值（依次找，编译时已核对名字只是其中一种）；都不是时为 None。
        界面上正在改的值（setEditing）优先。
        """
        if name in self._editing:
            return self._editing[name]
        menu = self.mirror.menu
        if name in menu.data:
            return self.dataValue(name, now)
        if name in menu.viewerState:
            return self.viewerValue(name)
        if name in menu.clientState:
            return self.clientValue(name)
        return None

    def clientValue(self, name):
        """客户端界面状态现在的值（界面模型 clientState 里声明的名字；没改过时是字段的空值）。"""
        field = self.mirror.menu.clientState[name]
        return self._clientState.get(name, field.empty)

    def setClientValue(self, name, value):
        """
        改客户端界面状态：值按字段类型检查（字段的 decode 不收时抛 TypeError / ValueError），同一种界面重开时还在。
        返回变没变。
        """
        field = self.mirror.menu.clientState[name]
        value = field.decode(value)
        if self._clientState.get(name, field.empty) == value:
            return False
        self._clientState[name] = value
        self.mirror.clientRevision += 1
        return True

    def setEditing(self, name, value):
        """
        界面上正在改、还没定下来的值（拖着的滑块，发了动作还在等应答的滑块与下拉）：读值（value）时它优先，别的控件里按名字
        写的字跟着变。改完了（应答都回来了）调 clearEditing，回到界面数据或状态的值。
        """
        self._editing[name] = value

    def clearEditing(self, name):
        self._editing.pop(name, None)

    def noteRefusedWords(self):
        """文本框的字含敏感词（引擎换掉了、服务端拒了）：布局里的敏感词提示（Std/Components 的 words_hint）闪一下。"""
        self.refusedWords += 1

    def pushScreen(self, namespace, key, params=None):
        """
        在容器界面上推一个使用方写的纯客户端界面（使用方自己用 RegisterUI 登记）：容器的会话不关，那个界面关掉（弹出）后
        回到容器界面；容器关闭时连同盖在它上面的界面一起弹掉。参数里另有 dolorSession，是这个会话（读值、发动作）。
        容器界面不在最上面时不推，返回 False。在交互按钮的回调里调（键鼠与手柄按下时）先记下，这一下抬起时再推
        （按下就推的话抬起会落到新界面上，见界面的 deferPush），返回 True。
        """
        if self.closed or self.screen is None or clientApi.GetTopUINode() is not self.screen:
            return False
        args = dict(params or {})
        args["dolorSession"] = self
        if self.screen.deferPush(namespace, key, args):
            return True
        return clientApi.PushScreen(namespace, key, args) is not None

    def showDetails(self, text):
        """
        在屏幕底部的物品详情处显示一段字（照触屏按下格子时的物品详情：2 秒内淡出，位置听界面扩展的 detailsOffset）：控件在
        触屏点按时弹说明、动作做完弹结果这类。字可以多行、可以用 § 颜色。界面没开着、会话关了时什么都不做。
        """
        screen = self.screen
        if not self.closed and screen is not None:
            screen.showDetails(_utf8(text))

    def displayed(self, ref):
        """
        格子 ref（(集合名, 格号)）现在显示的东西：算上还没应答的预测与手势的预览，算出的格子当场算（显示内容没变时用上次的）。
        """
        gestures = self.gestures
        key = (self.mirror.revision, id(gestures.preview))
        cached = self._displayed.get(ref)
        if cached is not None and cached[0] == key:
            return cached[1]
        stack = gestures.displayed(ref)
        self._displayed[ref] = (key, stack)
        return stack

    # ---------------------------------------------------------------- 给控件用的（写自定义控件见 Client/Widgets 的说明）

    @property
    def menu(self):
        """这个会话的界面模型（客户端那一份）。"""
        return self.mirror.menu

    @property
    def structure(self):
        """界面模型的结构（Common/Collections.Structure：structure.get(集合名) 给出集合，collection.cid 是它落在的容器）。"""
        return self.mirror.structure

    @property
    def rules(self):
        """这一端的物品规则（Common/Items.ItemRules：堆叠数、耐久、引擎信息）。"""
        return self.mirror.rules

    def do(self, op):
        """发一个格子操作（预测、发请求、物品飞行与锁定提示照手势识别的做法）；做成了返回 True。"""
        return self.gestures.do(op)

    def device(self):
        """现在的输入方式（Common/Slots 的 MOUSE / TOUCH / GAMEPAD）。"""
        return self.gestures.device

    def hovered(self):
        """悬停的格子（键鼠的指针、手柄的焦点所在的格；没有为 None）。"""
        return self.gestures.hovered

    def memory(self, owner):
        """owner（控件、交互）跨手势记的东西：字典（与格子交互的 g.memory 同一份）。"""
        return self.gestures.memory(owner)

    def size(self, name):
        """集合 name 现在显示几格（有格数的是格数；不设上限的按预测之后的末尾格；算出的集合按部件给的显示几格）。"""
        return self.mirror.size(name)

    def contents(self, cid):
        """容器 cid 现在显示的格子（算上还没应答的预测）：{下标: 物品堆}（只有非空的；不要改它）。"""
        return self.mirror.contents(cid)

    def predictedSlots(self, cid):
        """容器 cid 里预测改了、还没应答的格子：{下标: 物品堆或 None}。"""
        return self.mirror.predictedSlots(cid)

    def syncOf(self, cid):
        """容器 cid 的同步方式（客户端那一半，同步方式自己的东西，例如列表增量的修订号）。"""
        return self.mirror.syncOf(cid)

    def pointer(self):
        """指针（鼠标、手柄的虚拟光标）这一帧的界面坐标；触屏没有指针，与取不到时一样为 None。"""
        gestures = self.gestures
        return None if gestures.device == Gestures.TOUCH else gestures.pointer

    def heldRef(self):
        """
        手上那一格（线上写法的格子引用）：触屏选中了一格时是那一格（触屏没有光标，东西留在选中的格里；选了几个不算），
        否则是光标。看手上拿着什么的动作（拿着桶点仪表）把它当参数。
        """
        selection = self.gestures.selection
        ref = selection["ref"] if selection and self.gestures.device == Gestures.TOUCH else Collections.CURSOR_REF
        return Schema.wireRef(ref, self.mirror.structure)

    def revision(self):
        """
        显示内容、界面数据、客户端界面状态的修订号：(内容, 界面数据, 客户端界面状态)，哪样变了哪个加一（预测与应答都算内容）。
        控件按它判断这一帧要不要重算。
        """
        return self.mirror.revision, self.mirror.dataRevision, self.mirror.clientRevision

    def uiScale(self):
        """
        整屏按比例缩放的布局（$dc_fit）现在缩到了设计大小的几倍（框的实际高 / 设计高）；不缩放的布局、界面还没建好时为 1。
        自己另调字号的控件拿它乘上自己的倍数（变了时界面调控件的 onScale）。
        """
        screen = self.screen
        return getattr(screen, "uiScale", 1.0) if screen is not None else 1.0

    def panelOpen(self, name, now):
        """面板现在开着没有（见 Mirror.panelOpen）：界面按它显隐布局里标了这个面板的控件。"""
        return self.mirror.panelOpen(name, now)

    def call(self, name, args=(), done=None):
        """
        发动作（Common/Actions）：args 是线上写法的参数；done(成没成, 返回值) 在应答到了时调用（没成时第二个参数是错误码）。
        动作不是这个界面模型的、参数不对时不发（记一行日志），返回 False。
        """
        if self.closed:
            return False
        request = self.mirror.call(name, args, time.time(), done)
        if request is None:
            log("action %r %r is not an action of menu %r or its arguments are wrong"
                % (name, list(args), self.mirror.menu.menuName))
            return False
        Call("dolorContainerCall", request)
        return True

    def maxDurabilityOf(self, name, aux):
        return _maxDurability(name, aux)

    def idAuxOf(self, stack):
        """物品飞行渲染器要的物品编号（与图标控件属性包里的 #item_id_aux 同一种写法：附魔的再加 1 << 15）。"""
        if Items.isEmpty(stack):
            return None
        idAux = self.display.idAuxOf(stack["newItemName"], stack.get("newAuxValue", 0))
        if idAux is None:
            return None
        return int(idAux) | (1 << 15 if Display.iconArgs(stack)[2] else 0)

    def playSound(self, name, volume=1.0):
        """
        在本地玩家的位置放一次原版音效（原版容器界面的收纳袋音效就是在玩家身上放的，不跟着实体走）。volume 是音量
        （原版锻造台的声音是铁砧的声音放 0.25）。
        """
        playerId = clientApi.GetLocalPlayerId()
        position = _factory.CreatePos(playerId).GetPos()
        if position is not None:
            _factory.CreateCustomAudio(_levelId).PlayCustomMusic(name, tuple(position), float(volume), 1.0, False, None)

    def text(self, key):
        return text(key)

    def itemName(self, stack):
        """物品的悬停名（引擎给的，带稀有度颜色）。同一个物品堆对象记着。"""
        found = _names.get(id(stack))
        if found is not None and found[0] is stack:
            return found[1]
        name = _utf8(_component("CreateItem").GetItemHoverName(stack["newItemName"], stack.get("newAuxValue", 0),
                                                                stack.get("userData")))
        if len(_names) > 256:
            _names.clear()
        _names[id(stack)] = (stack, name)
        return name

    def plainItemName(self, stack):
        """
        物品的名字，照原版界面里写物品名的标签（携带版熔炉产物格下面的那行）：自定的名字或物品本身的名字，不带引擎给悬停名
        加的稀有度颜色（开头的颜色码与结尾的 §r）。
        """
        return Display.plainName(self.itemName(stack))

    def showTags(self):
        """showtags 游戏规则：原版只在它开着时画物品的锁图标与锁定底格。每个脚本刻向引擎读一次（tick）。"""
        if self._showTags is None:
            self._showTags = bool(_clientlevel.get_game_rule("showtags"))
        return self._showTags

    def tick(self):
        """每个脚本刻（界面调）：会变、但不用每帧都向引擎读的状态下次用到时重读。"""
        self._showTags = None

    def hoverText(self, stack, showCategory=False):
        """
        物品的悬停文本，照原版容器界面：不带类别（原版只在配方书与创造栏的搜索页带：showCategory 为真时带，界面模型与部件的
        hoverCategory），:名字: 换成表情字形（脚本拿到的文本没经过这一步，见 Emoticons）。
        """
        if Items.isEmpty(stack):
            return ""
        key = (Items.identityKey(stack), bool(showCategory), Display.hoverTextVersion())
        cached = _hoverText.get(key)
        if cached is None:
            cached = Emoticons.emoticonify(_utf8(_factory.CreateItem(_levelId).GetItemFormattedHoverText(
                stack["newItemName"], stack.get("newAuxValue", 0), bool(showCategory), stack.get("userData"))))
            cached = _utf8(Display.applyHoverText(stack, cached))   # 模组加的悬停文本钩子（Display.addHoverText）
            if len(_hoverText) > 512:
                _hoverText.clear()
            _hoverText[key] = cached
        return cached

    def detectDevice(self):
        return detectDevice()

    def checkProfileChanged(self):
        """界面开着时切换了界面档：关掉重开成另一套布局。"""
        if uiProfilePocket() == self.pocket:
            return False
        self.pocket = not self.pocket
        self.reportProfile()
        self.gestures.reset()
        self._switching = True
        try:
            self._pop()
            self.screen = None
            if not _push(self):
                self.requestClose()
        finally:
            self._switching = False
        return True

    def log(self, message):
        log(message)

    # ---------------------------------------------------------------- 与服务端

    def _profile(self):
        return Collections.PROFILE_POCKET if self.pocket else Collections.PROFILE_CLASSIC

    def _sendAct(self, request):
        Call("dolorContainerAct", request)

    def reportProfile(self):
        """告诉服务端这个会话的界面档（开屏、切换界面档之后；服务端的规则与钩子读 session.profile）。"""
        Call("dolorContainerProfile", {"s": self.sessionId, "p": self._profile()})

    def ensure(self, name, start, end):
        """界面要显示集合 name 的 [start, end)：容器的同步方式还要向服务端拉的话发一次拉取（req）。"""
        mirror = self.mirror
        collection = mirror.structure.get(name)
        if collection is None:
            return
        cid, offset = collection.cid, collection.offset
        query = mirror.wants(cid, offset + start, offset + end, time.time())
        if query is not None:
            Call("dolorContainerReq", {"s": self.sessionId, "c": mirror.structure.containerId(cid), "q": query})

    def onAck(self, message):
        self.mirror.onAck(message, time.time())

    def onUpdate(self, message):
        self.mirror.onUpdate(message, time.time())

    def remember(self):
        """
        会话结束：界面上的控件先把要记的写进客户端界面状态（滚动位置这类，见 Widget.remember），再把要记在配置里的写回去
        （没变不写）。
        """
        if self.screen is not None:
            self.screen.rememberState()
        _remembered.save(self.mirror.menu, self._clientState)

    def requestClose(self):
        if self.closed:
            return
        self.closed = True
        self.remember()
        self.gestures.reset()
        Call("dolorContainerClose", {"s": self.sessionId})
        self._pop()

    def onServerClose(self):
        self.closed = True
        self.remember()
        self.gestures.reset()
        self._pop()

    def retire(self):
        """服务端把这个会话换成了另一个（切换、重开）：不再处理它，也不通知服务端关闭。界面由新会话接手或换掉。"""
        self.closed = True
        self.remember()
        self.gestures.reset()

    def screenDef(self):
        """这个会话用的屏幕定义（按开屏时的界面档）。"""
        return self.layout["screens"]["pocket" if self.pocket else "classic"]["screen"]

    def onScreenGone(self, screen):
        if screen is not self.screen:
            return
        self.screen = None
        if self._switching:
            return
        if not self.closed:
            self.closed = True
            self.remember()
            Call("dolorContainerClose", {"s": self.sessionId})
        if _current[0] is self:
            _current[0] = None
            Shared.unclaim(_SCREEN_KEY, HOST)

    def _pop(self):
        screen = self.screen
        if screen is None:
            return
        if clientApi.GetTopUINode() is screen:
            _popWithBuried()
            return
        above = _screensAbove(screen)
        if above:
            # 推上去的纯客户端界面还盖着：连同它们一起弹掉
            _popWithBuried(above)


def settleBuried():
    """
    切换推入的屏幕上了栈：把压在它下面的旧屏幕整个藏起来（连同背景）。压在下面的屏幕平时不画，
    只在弹出它上面的屏幕的过程中会画，藏起来就不会露出来。
    """
    for screen in _buried:
        screen.hide(Paths.SCREEN)


def _buriedScreen(screenDef):
    """压在下面的屏幕里定义是 screenDef 的那一个（同一个定义在界面栈上只能有一个）。"""
    for screen in _buried:
        if getattr(screen, "screen_name", None) == screenDef:
            return screen
    return None


def _screensAbove(screen):
    """界面栈里盖在 screen 上面的界面有几个（screen 不在栈里时为 0）。"""
    manager = _uiManager()
    stack = list(getattr(manager, "_ui_screen_stack", None) or ()) if manager is not None else []
    return len(stack) - 1 - stack.index(screen) if screen in stack else 0


def _popWithBuried(above=0):
    """弹出最上面的界面，连同切换时压在它下面的旧屏幕（_buried）一起；above 是盖在容器界面上面、要一起弹掉的界面数。"""
    count = 1 + above + len(_buried)
    del _buried[:]
    _revealing[0] = None
    manager = _uiManager()
    if count > 1 and manager is not None:
        manager.pop_screen(count)
    else:
        clientApi.PopScreen()


def log(message):
    print("[dolorContainer:%s] %s" % (HOST, message))


def _config():
    return _factory.CreateConfigClient(_levelId)


# 界面模型的 savedClientState：记在这台设备的全局配置里（各个存档共用），下次进游戏还在
_remembered = Remembered(lambda: _config().GetConfigData(_CONFIG_NAME, True),
                         lambda data: _config().SetConfigData(_CONFIG_NAME, data, True), log)


# ---------------------------------------------------------------- 界面登记与推屏


def _register(args=None):
    """登记全部布局的屏幕（布局表见 Client/Layouts.py）：界面类按布局换过的用换过的（Layouts.registerScreenClass）。"""
    for name in Layouts.names():
        screenClass = Layouts.screenClass(name) or _SCREEN_CLASS
        for key, screen in Layouts.screensOf(name):
            clientApi.RegisterUI(UI_NAMESPACE, key, screenClass, screen)


def _screenDefs():
    return set(screen for _, screen in Layouts.screens())


ListenForEvent("UiInitFinished", _EVENTS, _register)
Shared.forgetHost(HOST, "client")   # 重新载入时，上一次载入的登记已经失效


def _uiManager():
    """
    推界面（PushScreen）用的那个界面管理器。mod.client.ui.uiManager 是另一个模块对象，单例也是另一个，
    它的界面栈一直是空的：要用 PushScreen 自己导入的 client.ui.uiManager。按名字取（Common/Modules.importModule）：
    网易打包机审的接口桩里没有引擎的 client 包，写成导入语句报 import-error。
    """
    try:
        return Modules.importModule("client.ui.uiManager").instance()
    except Exception:  # noqa: BLE001
        return None


def _removeStale():
    """
    引擎自己关掉的界面（例如重新加载、换维度）不会走 Python 的关闭流程，节点还留在 Python 的界面栈里，
    同名的界面就再也推不上去：推之前把不是当前会话的同名节点移出栈。
    """
    manager = _uiManager()
    session = _current[0]
    if manager is None:
        return
    for fullname in _screenDefs():
        node = manager.get_screen(fullname)
        ours = node is not None and getattr(node, "dolorHost", None) == HOST
        if ours and (session is None or node is not session.screen) and node not in _buried:
            manager.remove_screen_from_stack(node)


def _replaceScreen(screen, session):
    """
    换成另一个屏幕定义（切换到别的布局）：用新布局不带进入动画的那份屏幕，没有进入动画、中间不空一帧，手持物一直画着
    （关界面时的关闭动画照常）。
    旧屏幕 screen 一律不先弹：推入的屏幕要等引擎把它建好（至少一帧）才上栈，先弹旧的，中间就空出来。所以旧屏幕压在
    新屏幕下面，新屏幕上栈时（它的 Create）再整个藏起来，关界面时一起弹出。新布局的那份已经压在下面（来回切换）时
    不再推（同一个定义在界面栈上只能有一个），把它显示出来、换上新会话，再弹掉它上面的。
    布局没有不带进入动画的那份（旧版编译工具编的）时返回 False，由调用方照常弹出再推入。
    """
    profile = "pocket" if session.pocket else "classic"
    quiet = session.layout["screens"][profile].get("quiet")
    manager = _uiManager()
    if manager is None or not quiet:
        return False
    target = _buriedScreen(quiet)
    if target is not None:
        _reveal(target, screen, session, manager)
        return True
    screen.cleanup()
    _buried.append(screen)
    _removeStale()
    key = Layouts.screenKey(session.mirror.menu.layout, profile + Layouts.QUIET)
    node = clientApi.PushScreen(UI_NAMESPACE, key, {"dolorContainer": True})
    if node is None:
        _register()
        node = clientApi.PushScreen(UI_NAMESPACE, key, {"dolorContainer": True})
    if node is None:
        # 推不上去：旧屏幕连同压着的都在栈上，弹掉它们；告诉服务端关掉
        log("cannot push the screen of layout %r" % (session.mirror.menu.layout,))
        count = len(_buried)
        del _buried[:]
        manager.pop_screen(count)
        session.requestClose()
    return True


def _reveal(target, top, session, manager):
    """
    压在下面的 target 重新成为最上面的：target 换上新会话（还藏着），关上 top 退出过渡的门（不放关闭动画、当场弹出），
    弹掉它上面的全部。弹出做完之前 top 照常画着；做完时（_onPoppedTo）target 才显示出来，这时引擎已经把它跟随指针的
    手持物摆到了指针上，手持物不会在它被压下去时的位置闪一帧。
    """
    index = _buried.index(target)
    count = len(_buried) - index   # target 上面压着的，加上 top
    del _buried[index:]
    top.closeGate()   # 内部弹出：不放 top 的关闭动画（压着的几屏藏着，也不放）
    target.revive(session)
    _revealing[0] = target
    manager.pop_screen(count)


@Listen("PopScreenAfterClientEvent")
def _onPoppedTo(args):
    """引擎弹完了屏幕，最上面的成了切换回去的那一屏（_reveal）：这时显示它。"""
    screen = _revealing[0]
    if screen is not None and args.get("screenDef") == getattr(screen, "screen_name", None):
        _revealing[0] = None
        screen.show()


def _releaseScreen(key):
    """别的使用方的容器界面要推上来：收起这边的（它的服务端那边已经关掉了这边的会话）。"""
    session = _current[0]
    if session is not None:
        _current[0] = None
        if not session.closed:
            session.onServerClose()


def _push(session):
    _removeStale()
    key = Layouts.screenKey(session.mirror.menu.layout, "pocket" if session.pocket else "classic")
    node = clientApi.PushScreen(UI_NAMESPACE, key, {"dolorContainer": True})
    if node is None:
        _register()
        node = clientApi.PushScreen(UI_NAMESPACE, key, {"dolorContainer": True})
    return node is not None


@Listen("PopScreenEvent")
def _onPopScreen(args):
    """引擎关掉了我们的界面（没经过 Python）：把节点移出界面栈，并按正常关闭收尾。"""
    if args.get("screenDef") not in _screenDefs():
        return
    session = _current[0]
    screen = session.screen if session is not None else None
    manager = _uiManager()
    popped = manager.get_screen(args.get("screenDef")) if manager is not None else None
    if popped is not None and popped in _buried:
        # 引擎连压在下面的旧屏幕也弹了（例如一下清掉整个界面栈）
        _buried.remove(popped)
        manager.remove_screen_from_stack(popped)
        return
    if screen is None or manager is None or popped is not screen:
        return
    manager.remove_screen_from_stack(screen)
    screen.cleanup()
    _revealing[0] = None
    if _buried:
        # 压在下面的旧屏幕藏着、却会成为最上面的界面：跟着弹出
        count = len(_buried)
        del _buried[:]
        manager.pop_screen(count)


# ---------------------------------------------------------------- 服务端消息


def _sessionFor(message):
    """按开屏消息建客户端会话；界面模型、布局或控件缺了时记一行日志、告诉服务端关掉，返回 None。"""
    try:
        session = ClientSession(message)
    except MenuMissing as error:
        # 界面模型要在两端都登记：登记它的模块客户端没有导入时，这个界面打不开
        log("menu %r is not registered on the client" % (error.args[0],))
        Call("dolorContainerClose", {"s": message.get("s")})
        return None
    if session.layout is None:
        # 界面模型的布局没有编译进来（使用方的 dolor.json 没有列出它的布局源文件），
        # 或绑定表是旧版编译工具生成的
        log("layout %r of menu %r is not compiled in%s" % (session.mirror.menu.layout, message.get("menu"),
                                                         " (%s)" % Layouts.problem() if Layouts.problem() else ""))
        Call("dolorContainerClose", {"s": message.get("s")})
        return None
    missing = Widgets.missing(Layouts.widgetNames(session.layout))
    if missing:
        # 布局用到的控件类客户端没有登记（登记它们的模块客户端没有导入）
        log("widgets %r of layout %r are not registered on the client" % (missing, session.mirror.menu.layout))
        Call("dolorContainerClose", {"s": message.get("s")})
        return None
    return session


def _onOpen(current, message):
    """
    开屏。消息带 switch 时是服务端把开着的会话换成了这个（切换、重开）：用同一个屏幕定义就在原界面里换会话，
    不推不弹；不同时换成新布局不带进入动画的那份屏幕（_replaceScreen）。
    """
    switching = bool(message.get("switch")) and current is not None and not current.closed \
        and current.screen is not None
    if current is not None and not current.closed and not switching:
        current.onServerClose()
    session = _sessionFor(message)
    if session is None:
        if switching:
            current.onServerClose()
        return
    session.reportProfile()
    if switching:
        current.retire()
        screen = current.screen
        if session.pocket == current.pocket and session.screenDef() == current.screenDef():
            current.screen = None
            _current[0] = session
            screen.adopt(session)
            return
        _current[0] = session
        if _replaceScreen(screen, session):
            return
        screen.hide()
        current._pop()
    _current[0] = session
    Shared.claim(_SCREEN_KEY, HOST, _releaseScreen, log)
    if not _push(session):
        session.requestClose()
        if _current[0] is session:
            _current[0] = None
            Shared.unclaim(_SCREEN_KEY, HOST)


@AllowCall
def dolorContainerOnMessage(kind, message):
    session = _current[0]
    if kind == "open":
        _onOpen(session, message)
        return
    if session is None or not isinstance(message, dict) or message.get("s") != session.sessionId:
        return
    if kind == "ack":
        session.onAck(message)
    elif kind == "update":
        session.onUpdate(message)
    elif kind == "close":
        session.onServerClose()
