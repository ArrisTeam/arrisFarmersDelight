# -*- coding: utf-8 -*-
"""
界面模型（docs/ARCHITECTURE.md 第 2.4 节）：一种界面一个类，描述它用到的容器、集合、集合规则、去向表与算出格子的部件。

两端各建一份，规则代码完全相同：服务端那份由会话接上真实容器，客户端那份接镜像（JE 的界面类也是两端各一份）。
所以界面模型要写在两端都导入的模块里，按名字登记（register）；打开界面时线上只传名字与参数，客户端按同样的名字与参数
建同一个界面模型。参数只能是简单值（数字、字符串、布尔、None、由它们组成的列表与字典）。

    @Menus.register("mymod:table5")
    class Table5(Menus.Menu):
        layout = "mymod:table5"
        def define(self, s):
            grid = s.container("grid", 种类, 25)    # 容器种类是登记过的名字，常用的见 Std/Containers
            ...
            s.player()

只在服务端调用的钩子（accepts、onOpen、onClose、dataValues）与动作的处理写在同一个类里；它们要用的引擎接口在函数里导入，
客户端不会调用它们。动作（按钮、开关这类格子操作以外的请求）用 @Actions.action 声明，见 Common/Actions.py。
两端都调用的钩子 quickMove（Shift 点击的去处）与规则一样不碰引擎。东西被拿走、内容变了时做事写在格子类型上
（Common/Slots 的 onTake、onChanged）。

每位查看者的状态（选中项、页码、打开的面板）：viewerState = {名字: 字段类型}（Common/Data 的类型），每个会话各一份，
不存档；初值是各字段的空值，再按 viewerInitial 改；开屏时发给这位查看者，动作经 ctx.viewer 改（可预测的动作在客户端先改
view.viewer），只发给他自己。按查看者算的东西都读它：范围是 VIEWER 的界面数据（viewerValues）、算出的格子
（部件的 derive / match 收到它，见 Collections.Structure）。

客户端界面状态（页签、滚动、搜索词、折叠、子窗口位置）：clientState = {名字: 字段类型}，只在客户端，服务端不知道它。
初值是各字段的空值；客户端按界面模型的名字各记一份，重开同一种界面时还在（Client/Service 的 ClientSession.clientValue、
setClientValue）。控件与界面扩展读写它，例如搜索框把打的字写进去。savedClientState 列出的那几项另记在这台设备的客户端
配置里（Client/Remembered），下次进游戏还在；freshClientState 列出的那几项反过来，每次打开都从空值开始（原版携带版工作台
右边每次都开在合成页）。

面板（s.panel，见 Collections.Panel）：开关是 viewerState 或 data 里的一个名字（不能是面板范围的数据）；面板范围的数据
（scope 是 PANEL）要在且只在一个面板里。附加容器（s.attach）的开关是 viewerState 里一个布尔的名字，服务端在接上、断开时
改它（attachment 钩子决定接到哪）。界面模型建好时核对这些。

部件（Part）：可以组合进界面模型的一块（合成格、熔炉、多合一的页签、女仆的背包），s.include(部件, prefix) 接进来。
部件声明的 data、viewerState、clientState 与动作由界面模型合并，名字加上前缀；内核经界面模型的合并入口（allDataValues、
allViewerValues、allViewerInitial、advanceAll、nextEventAll、anyHoverCategory）把界面模型自己的钩子与各部件的一起调用，
界面模型改写自己的钩子时不用管部件。
"""
from . import Actions, Collections, Data, Schema

SERVER = "server"
CLIENT = "client"

_menus = {}
_built = {}


def register(name):
    """登记界面模型类（两端都要执行到）。重新载入时同名的新类替换旧的。"""
    def decorate(cls):
        if ":" not in name:
            raise ValueError("menu name needs a namespace: %r" % (name,))
        cls.menuName = name
        _menus[name] = cls
        for key in [key for key in _built if key[0] == name]:
            del _built[key]
        return cls
    return decorate


def get(name):
    return _menus.get(name)


def names():
    """登记过的界面模型名（布局编译工具按它找要生成布局的界面模型）。"""
    return sorted(_menus)


def create(name, params, side, itemRules):
    """
    按名字与参数建界面模型（同一组名字、参数、端只建一次：结构建好后不再改，几个会话共用）。
    名字没登记过时返回 None。
    """
    cls = _menus.get(name)
    if cls is None:
        return None
    key = (name, _freeze(params), side)
    menu = _built.get(key)
    if menu is None:
        menu = cls(side, itemRules, **dict(params or {}))
        _built[key] = menu
    return menu


def _freeze(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _kind(module, kind):
    """类型名（module 里的，例如 Data 的 "Int"）或类 -> 类。"""
    return kind if isinstance(kind, type) else getattr(module, kind)


def _kindName(kind):
    return kind.__name__ if isinstance(kind, type) else kind


def _overridden(obj, name, base):
    """obj 的类改写了 base 的方法 name（py2 的未绑定方法要取出函数再比）。"""
    mine, original = getattr(type(obj), name), getattr(base, name)
    return getattr(mine, "__func__", mine) is not getattr(original, "__func__", original)


class Menu(object):
    """
    界面模型的基类。子类写 define(结构)；layout 是布局名（布局源文件里的 $dc_layout，编译后在绑定表里，见 Client/Layouts.py），
    title 是缺省标题（语言文件的键或文字，打开时可以另给）。

    服务端钩子：
    - accepts(格子, 物品堆)：集合规则之外、只在服务端的放入判断（客户端按集合规则预测，以服务端为准）；
    - onOpen(会话) / onClose(会话, 原因)：一位玩家打开了、他的会话结束了；
    - onTaken(会话, 格子, 物品堆)：东西从只出的格子（Std/Slots.Output）被拿走（熔炉据此给经验；别的格子写在格子类型的
      onTake / onChanged 上）；
    - dataValues(实例)：界面数据（见 data）现在的原始值 {名字: 值}。
    两端的钩子：quickMove(工作副本, 格子, 界面档, 数量)：Shift 点击这一格的去处（缺省照去向表）。
    部件有同名的钩子（Part），界面模型与部件里改写了的都调用；没人改写时内核什么都不调。

    界面数据：data = {名字: 字段类型}（Common/Data），布局里的数据小部件（$dc_data）按名字绑定。值由字段类型编码上线、
    客户端解码：会动的数（Data.Moving，熔炉的火焰与箭头）只在变化的那一刻推一次起点与速度，客户端自己往前算。
    服务端在打开、每次操作之后与机器推进之后算一遍，变了的推给所有看着的人。界面数据来自宿主在会话之外变的状态时（实体的
    血量、经验这类），写 dataEvery（正整数）：开着的界面每这么多刻再算一遍，变了的同样推过去。
    """

    menuName = None
    layout = None
    title = ""
    data = {}
    viewerState = {}  # 每位查看者的状态：{名字: 字段类型}
    clientState = {}  # 客户端界面状态：{名字: 字段类型}，只在客户端（见模块说明）
    savedClientState = ()   # 记在客户端配置里、下次进游戏还在的那几项客户端界面状态的名字
    freshClientState = ()   # 每次打开都从空值开始的那几项客户端界面状态的名字（不能也在 savedClientState 里）
    machine = False   # 机器（熔炉这类）：随时间变化，见 Server/Machines.py 与下面的 advance / nextEvent
    dataEvery = None  # 界面数据来自宿主在会话之外变的状态时：开着的界面每这么多刻再算一遍（见上面"界面数据"）

    def __init__(self, side, itemRules, **params):
        self.side = side
        self.params = params
        self.structure = Collections.Structure(side, itemRules)
        self.define(self.structure, **params)
        self.structure.finish()
        self.parts = list(self.structure.parts)
        self._actions = None
        self._hooks = {}   # 钩子名 -> 改写了它的（界面模型自己、部件），用到时算一次
        if self.parts:
            self._mergeParts()
        for name, field in list(self.data.items()) + list(self.viewerState.items()) + list(self.clientState.items()):
            if not isinstance(field, Data.Field):
                raise ValueError("menu %s: %r must be a Data field" % (self.menuName, name))
        for name in self.savedClientState:
            if name not in self.clientState:
                raise ValueError("menu %s: saved client state %r is not in clientState" % (self.menuName, name))
        for name in self.freshClientState:
            if name not in self.clientState or name in self.savedClientState:
                raise ValueError("menu %s: fresh client state %r must be in clientState and not saved"
                                 % (self.menuName, name))
        self._checkPanels()
        every = self.dataEvery
        if every is not None and (not isinstance(every, int) or isinstance(every, bool) or every < 1):
            raise ValueError("menu %s: dataEvery must be a positive int (ticks): %r" % (self.menuName, every))
        for name, field in self.data.items():
            if isinstance(field, Data.SlotValues) and self.structure.get(field.collection) is None:
                raise ValueError("menu %s: slot data %r is for collection %r, which the menu does not have"
                                 % (self.menuName, name, field.collection))
        for name, collection in self.structure.collections.items():
            collection.slot.check(self, name)

    def checkSlotData(self, collection, dataName, element):
        """
        格子类型核对它读的界面数据：dataName 要是集合 collection 的每格数据（Data.SlotValues），元素是 element 那种类型
        （Data 里的类型名 "Item"、"Bool"……或类本身；子类也算，Data.Long 算 "Int"），范围不是面板范围。不对时抛 ValueError。
        """
        field = self.data.get(dataName)
        if not isinstance(field, Data.SlotValues) or field.collection != collection \
                or not isinstance(field.value, _kind(Data, element)) or field.scope == Data.PANEL:
            raise ValueError("menu %s: collection %s reads data %r, which must be Data.SlotValues(Data.%s(), %r) "
                             "(shared or viewer scope)" % (self.menuName, collection, dataName, _kindName(element),
                                                           collection))

    def checkSlotAction(self, collection, actionName, kinds):
        """
        格子类型核对它发的动作：actionName 要是这个界面模型的动作，参数格式依次是 kinds 那些类型（Schema 里的类型名或类本身；
        子类也算，Schema.Amount 算 "Int"）。
        """
        action = self.actions.get(actionName)
        if action is None or len(action.fields) != len(kinds) or \
                not all(isinstance(field, _kind(Schema, kind)) for field, kind in zip(action.fields, kinds)):
            raise ValueError("menu %s: collection %s sends action %r, which must be an action of the menu taking (%s)"
                             % (self.menuName, collection, actionName, ", ".join(_kindName(kind) for kind in kinds)))

    def _mergeParts(self):
        """部件声明的界面数据、每位查看者状态与客户端界面状态并进来（名字加上前缀）；有部件是机器，界面模型就是机器。"""
        data, viewerState, clientState = dict(type(self).data), dict(type(self).viewerState), dict(type(self).clientState)
        for part in self.parts:
            for table, own in ((data, part.data), (viewerState, part.viewerState), (clientState, part.clientState)):
                for local, field in own.items():
                    name = part.name(local)
                    if name in table:
                        raise ValueError("menu %s: %r is declared twice (parts need different prefixes)"
                                         % (self.menuName, name))
                    table[name] = field.forPart(part.name)
        self.data, self.viewerState, self.clientState = data, viewerState, clientState
        self.savedClientState = tuple(type(self).savedClientState) + tuple(
            part.name(local) for part in self.parts for local in part.savedClientState)
        self.freshClientState = tuple(type(self).freshClientState) + tuple(
            part.name(local) for part in self.parts for local in part.freshClientState)
        self.machine = type(self).machine or any(part.machine for part in self.parts)

    def _checkPanels(self):
        """面板与附加容器的开关、面板范围的数据要对得上界面模型的声明。"""
        for cid, switch in self.structure.attachments.items():
            if not isinstance(self.viewerState.get(switch), Data.Bool):
                raise ValueError("menu %s: attached container %s switches on %r, which is not a Bool viewer state"
                                 % (self.menuName, cid, switch))
        panelData = self.structure.panelData
        for panel in self.structure.panels.values():
            field = self.data.get(panel.switch)
            if panel.switch not in self.viewerState and (field is None or field.scope == Data.PANEL):
                raise ValueError("menu %s: panel %s switches on %r, which is neither viewer state nor shared or viewer "
                                 "data" % (self.menuName, panel.name, panel.switch))
        for name, panelName in panelData.items():
            field = self.data.get(name)
            if field is None or field.scope != Data.PANEL:
                raise ValueError("menu %s: panel %s lists %r, which is not a PANEL data field"
                                 % (self.menuName, panelName, name))
        for name, field in self.data.items():
            if field.scope == Data.PANEL and name not in panelData:
                raise ValueError("menu %s: PANEL data field %r is in no panel" % (self.menuName, name))

    def define(self, structure, **params):
        raise NotImplementedError

    @property
    def actions(self):
        """动作表 {名字: 动作}：类里用 @Actions.action 声明的方法（连同基类的），加上各部件的（名字带前缀，绑到部件上）。"""
        table = self._actions
        if table is None:
            table = dict(Actions.table(type(self)))
            for part in self.parts:
                for local, action in Actions.table(type(part)).items():
                    name = part.name(local)
                    if name in table:
                        raise ValueError("menu %s: action %r is declared twice" % (self.menuName, name))
                    table[name] = action.bound(name, part)
            self._actions = table
        return table

    def accepts(self, ref, stack):
        return True

    def quickMove(self, ws, ref, profile, amount):
        """
        Shift 点击（快速转移）ref 这一格：返回做成了没有（真假）就照它，返回 None 照去向表（缺省）。两端都调用（客户端预测
        与服务端照同样的规矩），双击收集什么都没收到时的退路、种类存储的转出也经它。amount 为 None 时转整堆（超堆叠的格子
        一组），给出时只转这么多个。要照去向表转一部分时调 Std/Operations.routeQuickMove。
        """
        return None

    def onOpen(self, session):
        """服务端：一位玩家打开了（会话装上之后、开屏消息之前；切换、重开出来的新会话也算）。改的实例状态随之写回。"""

    def onClose(self, session, reason):
        """
        服务端：这位玩家的会话要结束了（在退回手持物与临时格之前）。reason 是 Common/Protocol 的 CLOSE_*；切换、重开到
        另一个会话时是 CLOSE_SWITCH。改的实例状态随之写回。
        """

    def onTaken(self, session, ref, stack):
        pass

    def dataValues(self, instance):
        return {}

    def viewerValues(self, instance, viewer):
        """范围是 VIEWER 的界面数据：按这位查看者（viewer 是他的状态 {名字: 值}）算 {名字: 值}。只在服务端调用。"""
        return {}

    def viewerInitial(self, instance, playerId):
        """每位查看者状态的初值（只写与空值不同的）{名字: 值}。只在服务端调用。"""
        return {}

    def hoverCategory(self, viewer):
        """
        界面里东西的悬停文本带不带它的分类（原版创造栏在搜索页时，界面里所有东西都带）。viewer 是在看的这一位的状态
        （{名字: 值}，没有时为 None）。只在客户端调用。
        """
        return False

    def attachment(self, name, instance, playerId):
        """
        附加容器 name（s.attach 声明的）对这位玩家接到哪：(容器类型, 实例键, 容器名)，接不上时 None。
        查看者自己的容器给他自己的玩家 ID 作实例键（按玩家存放的容器类型）。只在服务端、打开时调用一次。
        """
        return None

    def advance(self, instance, ticks):
        """机器：往前推 ticks 个游戏刻（改实例存储与 instance.state）。只在服务端调用。"""

    def nextEvent(self, instance):
        """机器：再过多少刻会有看着的人能看到的变化（格子，或界面数据的起点与速度），没有为 None。只在服务端调用。"""
        return None

    # ---------------------------------------------------------------- 内核调用的合并入口（不改写）

    def hooksFor(self, name):
        """改写了钩子 name（quickMove、onOpen、onClose）的：界面模型自己与各部件，按先后（第一次问时算好记下）。"""
        found = self._hooks.get(name)
        if found is None:
            found = self._hooks[name] = tuple(([self] if _overridden(self, name, Menu) else [])
                                              + [part for part in self.parts if _overridden(part, name, Part)])
        return found

    def quickMoveAll(self, ws, ref, profile, amount=None):
        """Shift 点击的去处：改写了 quickMove 的依次问，第一个给出结果的为准；都没给（或没人改写）时为 None。"""
        for owner in self.hooksFor("quickMove"):
            result = owner.quickMove(ws, ref, profile, amount)
            if result is not None:
                return result
        return None

    def allDataValues(self, instance):
        """界面模型与各部件的 dataValues 合在一起。"""
        values = dict(self.dataValues(instance) or {})
        for part in self.parts:
            values.update(part.dataValues(instance) or {})
        return values

    def allViewerValues(self, instance, viewer):
        values = dict(self.viewerValues(instance, viewer) or {})
        for part in self.parts:
            values.update(part.viewerValues(instance, viewer) or {})
        return values

    def anyHoverCategory(self, viewer):
        return self.hoverCategory(viewer) or any(part.hoverCategory(viewer) for part in self.parts)

    def allViewerInitial(self, instance, playerId):
        values = dict(self.viewerInitial(instance, playerId) or {})
        for part in self.parts:
            values.update(part.viewerInitial(instance, playerId) or {})
        return values

    def attachmentFor(self, name, instance, playerId):
        """附加容器 name 接到哪：界面模型自己的 attachment 先给，没给时问各部件（部件的附加容器名带着前缀）。"""
        target = self.attachment(name, instance, playerId)
        for part in self.parts:
            if target is not None:
                break
            target = part.attachment(name, instance, playerId)
        return target

    def advanceAll(self, instance, ticks):
        """机器推进：界面模型自己的 advance，再按先后推进是机器的部件。"""
        self.advance(instance, ticks)
        for part in self.parts:
            if part.machine:
                part.advance(instance, ticks)

    def nextEventAll(self, instance):
        """界面模型与是机器的部件里最早的下一个事件（都没有为 None）。"""
        delays = [self.nextEvent(instance)] + [part.nextEvent(instance) for part in self.parts if part.machine]
        delays = [delay for delay in delays if delay is not None]
        return min(delays) if delays else None


class Part(object):
    """
    可以组合进界面模型的一块（docs/ARCHITECTURE.md 第 3.6 节）：集合、去向、算出的格子、面板、动作、界面数据、
    每位查看者的状态、机器推进。界面模型的 define 里 s.include(部件, prefix=...) 接进来，接进来时调用 define(结构)。

    名字：部件里的集合、容器、面板、实例状态的键、界面数据、每位查看者状态与客户端界面状态的键，运行时一律经 self.name(名字)
    加上前缀（prefix 为 None 时不加）。类里声明的 data、viewerState、clientState 与 @Actions.action 动作写不带前缀的名字，
    由界面模型加上；
    钩子（dataValues、viewerValues、viewerInitial）返回的字典写带前缀的名字（self.name(...)）。部件的动作被调用时
    self 是部件，ctx 与界面模型的一样（ctx.viewer、ctx.state 是整份，用 self.name 取自己的）。

    一个部件对象只能接进一次；同一种部件接几块就建几个对象、给不同的前缀。
    """

    data = {}
    viewerState = {}
    clientState = {}
    savedClientState = ()
    freshClientState = ()
    machine = False
    prefix = None
    included = False

    def name(self, local):
        """部件里的名字加上前缀。"""
        return local if self.prefix is None else "%s.%s" % (self.prefix, local)

    def define(self, structure):
        raise NotImplementedError

    def dataValues(self, instance):
        return {}

    def viewerValues(self, instance, viewer):
        return {}

    def viewerInitial(self, instance, playerId):
        return {}

    def hoverCategory(self, viewer):
        """悬停文本带不带东西的分类，同 Menu.hoverCategory（任何一个部件要带就带）。"""
        return False

    def attachment(self, name, instance, playerId):
        """部件声明的附加容器（名字带前缀）接到哪，同 Menu.attachment。"""
        return None

    def advance(self, instance, ticks):
        """机器（machine 为真）：往前推 ticks 刻。"""

    def nextEvent(self, instance):
        return None

    def quickMove(self, ws, ref, profile, amount):
        """Shift 点击 ref 的去处，同 Menu.quickMove（界面模型先问，再按先后问部件）。"""
        return None

    def onOpen(self, session):
        """服务端：一位玩家打开了，同 Menu.onOpen。"""

    def onClose(self, session, reason):
        """服务端：这位玩家的会话要结束了，同 Menu.onClose。"""

    def onTaken(self, session, ref, stack):
        """东西从这个部件的只出格子（Std/Slots.Output，建它时给 owner=部件）被拿走。"""

