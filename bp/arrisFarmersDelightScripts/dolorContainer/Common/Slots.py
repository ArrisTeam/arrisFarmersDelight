# -*- coding: utf-8 -*-
"""
格子类型（docs/ARCHITECTURE.md 第 3.3 节）：一个集合里各格的规矩（收什么、每格上限、能不能拿走、停用）与手势（交互）。
两端共用：客户端预测与服务端执行跑同一份规矩。

SlotType 基类就是原版容器里的普通格子：收什么由 allow / deny / accept 定（收纳袋里一层层的东西也算），每格上限缺省是
物品的堆叠数（maxStack 可以压低），锁定的物品放不进，界面模型与容器实例另加的判断（底层状态的 accepts）也要过。
别的格子类型派生它、改写其中几个方法（标准库的只出、算出、只看、幽灵、来源、装备、可停用、虚拟见 Std/Slots）；
操作（Common/Rules）只问这些方法，不认识具体的类型。规矩的方法都收一个工作副本 ws（Rules.Workspace），它给出这一端的
物品规则（ws.rules）、结构、底层状态，以及界面数据（ws.data，按界面数据停用格子、显示内容的类型读它）。

Interaction 是格子类型的手势：手势识别（Client/Gestures）把一个输入先交给这一格的交互，交互接了（返回 True）就不再往下；
不接（返回假，基类什么都不接）时交给标准交互（standard()：库的缺省登记接上 Std/Interactions.Standard，原版容器界面的全部手势，
每一步都是可以改写的方法）。要在标准的基础上改几步，派生 Standard、改写那几个方法（不改的照原版）；要整个接管，派生
Interaction。交互经手势识别器 g 的公开方法做事（见 Client/Gestures"给格子类型的交互用的"一节），所以本模块不依赖客户端。
"""
from . import Bundles, Data, Items

# 输入方式（手势识别器的 device）
MOUSE = "mouse"
TOUCH = "touch"
GAMEPAD = "gamepad"


class Interaction(object):
    """
    格子类型的手势。各方法返回 True 表示接了这个手势（手势识别器不再照普通格子处理）。
    交互对象通常是几个界面共用的一份，要跨手势记的东西放在 g.memory(交互) 或按住对象的 data 里，不要记在自己身上。
    """

    def press(self, g, ref, button, now, position):
        """键鼠与手柄在 ref 上按下（button 为 Rules.PRIMARY / SECONDARY）。"""
        return False

    def touchPress(self, g, ref, now, position):
        """触屏在 ref 上按下。"""
        return False

    def quick(self, g, ref):
        """Shift 点击、手柄 Y（手柄手上有东西时那是丢出，不到这里）。"""
        return False

    def drop(self, g, ref, whole):
        """悬停时 Q（whole 为假）或 Ctrl+Q（手上空着时）。"""
        return False

    def hotbar(self, g, ref, index):
        """悬停时按快捷栏键位（index 为 0–8）。"""
        return False

    def holdTick(self, g, press, now, pointer):
        """接管的按住（g.hold 开始的）每帧调用。"""

    def holdRelease(self, g, press, ref, now):
        """接管的按住结束：松开（触屏的 ref 是松开处的格子），或被别的手势打断（ref 为 None）。"""

    def holdHover(self, g, press, ref, now):
        """接管的按住期间指针（手指）移进了另一格 ref（标准交互据此拖动分配）。"""

    def keysBlocked(self, g, press):
        """这次按住期间 Q、快捷栏键位不起作用（原版：渐进拿取时）。"""
        return False

    def moveSelected(self, g, selection, ref):
        """触屏：选中的是这一格（selection 是选中 {"ref", "amount"}，已经取消），点了别的格子 ref。"""
        return False

    def blank(self, g, name, button):
        """键鼠点在这个集合的格子区空白处（布局写了 $dc_scroll_blank）；不接时照面板空白处。"""
        return False

    def wheel(self, g, ref, up):
        """悬停在 ref 上滚轮（up 为真是向上）；不接时照标准交互（悬停收纳袋时在提示里选一项）。"""
        return False

    def key(self, g, ref, key, down):
        """
        悬停在 ref 上按了键盘的键（引擎报的键码，down 是按下 / 抬起）。原版已经有意义的键（Q、快捷栏键位、Shift）照常也走
        它们自己的手势；这里给模组自己的键（例如按 R 转一下）。
        """
        return False

    def helpers(self, g, ref):
        """
        悬停在 ref 上时手柄提示条四个键（x、a、y、b）的说明：语言文件的键的四元组；None 照标准交互（拿取、放置、快速转移……）。
        """
        return None


# 格子类型的 decorDepends：格子装饰依赖什么
DECOR_DATA = "data"       # 界面数据变了才重画（装饰只读界面数据）
DECOR_SLOTS = "slots"     # 显示的格子内容、界面数据、每位查看者的状态变了就重画
DECOR_CLIENT = "client"   # 再加上客户端界面状态（ws.client 读页签、搜索词这类）

STANDARD = Interaction()
_standard = [STANDARD]


def setStandard(interaction):
    """接上标准交互（库的缺省登记接 Std/Interactions.Standard；使用方可以换成自己派生的，影响所有界面）。"""
    _standard[0] = interaction


def standard():
    """标准交互：格子的交互不接的手势都交给它。"""
    return _standard[0]

SHORT_COUNT_FROM = 100   # 原版的数量字 100 起写成 99+；超堆叠的格子从这里起改写短写法


class Decoration(object):
    """
    一格这一次怎么画（客户端；格子类型的 decorate 给出）：placeholder 占位图标（贴图路径，空着时才有）；frames 是占位图标的
    帧：贴图是横排的方格帧时写 (帧数, 每帧边长（贴图像素）, 每秒几帧)，按时间轮流显示（照原版锻造台空格的底图），None 为整张图；
    bar 覆盖条 (样式, 0–1, (r, g, b))（样式 "fill" 从下往上、"line" 底边横条）；tint 底色 (r, g, b)；count 数量的写法
    （None 照常）；locked 锁住的样子；position 摆到哪 (x, y)（None 为格子区给的位置）；visible 显不显示（None 为不管）；
    cell 底格换成这张贴图（原版切石机选中的配方按钮；None 为不管：换过之后不会自己换回布局里的那张，换过的格子类型每次都写）；
    renderer 写给格子里自定义渲染器的属性包（布局在格子组件上写了 $dc_slot_renderer 才有那个渲染器；原版织布机的图案按钮上
    画的旗帜；None 为不管）；dim 为真时图标画暗（原版的禁用滤镜：原版交易界面做不成时的产物；None 为不管）；badge 右下角的
    小图标（贴图路径，原版创造栏组头的加号、减号；空串为不画，None 为不管）。
    """

    __slots__ = ("placeholder", "frames", "bar", "tint", "count", "locked", "position", "visible", "cell", "renderer",
                 "dim", "badge")

    def __init__(self):
        self.placeholder = None
        self.frames = None
        self.cell = None
        self.renderer = None
        self.bar = None
        self.tint = None
        self.count = None
        self.locked = False
        self.position = None
        self.visible = None
        self.dim = None
        self.badge = None

    def copy(self):
        """一份副本（格子类型可以给几格共用同一个装饰对象，改之前先复制）。"""
        out = Decoration()
        for name in Decoration.__slots__:
            setattr(out, name, getattr(self, name))
        return out


class SlotType(object):
    """
    格子类型的基类：原版容器里的普通格子。allow：只收这些物品名（空表示不限）；deny：不收这些物品名（收纳袋里一层层的
    东西也算）；accept：收不收的谓词 accept(物品堆, 物品规则) -> 真假，可以读附加数据（例如电量）与物品的引擎信息
    （物品规则的 info），两端都跑，所以只能看物品本身；maxStack：每格最多几个（None 为物品的堆叠数）；multiplier：超堆叠，
    每格能放物品堆叠数的几倍（整数，或界面数据里一个 Data.Int 的名字：存储的升级这类；不能叠的东西照旧一格一个），数量 100 起
    写短写法（1.2k）；decor：格子装饰
    （标准库 Std/Decor.Decor：占位图标、覆盖条、底色、数量写法、锁住的格子、按数据的布局），它有 active / takeable
    （锁住、不在布局里的格子不收，锁住的拿不走）、hint、render、check 几个方法，本模块只调用它们。

    几个类属性：computed 为真时内容由部件算出（结构里要配 derive，只经合成操作拿走）；returnsOnClose 为真时，
    落在玩家临时格上的这种格子关界面时把里面的东西退回背包（只看、算出的格子不放真东西）；copies 为真时格子里放的是
    副本（幽灵格，经操作 ghost 设；快速转移进来时怎么放由 quickInto、copyInto 定）；itemsFrom 是界面数据里一个
    Data.SlotValues(Data.Item(), 集合) 的名字时，格子的内容就是它（不放真东西，要落在不放东西的容器上，普通操作不拿不放）；
    coalesce 为假时双击这一格不收集同类（键鼠、手柄的两下与触屏的双点都照两次普通的点算），照原版物品栏的盔甲格与副手格。
    """

    interaction = STANDARD
    computed = False
    returnsOnClose = True
    copies = False
    itemsFrom = None
    coalesce = True
    decorDepends = None   # 格子装饰依赖什么（客户端什么时候重画）：见 DECOR_*；None 为自动（改写了 decorate 的照 SLOTS，别的照 DATA）

    def __init__(self, allow=(), deny=(), maxStack=None, accept=None, decor=None, multiplier=None):
        if maxStack is not None and (not isinstance(maxStack, int) or maxStack < 1):
            raise ValueError("bad maxStack: %r" % (maxStack,))
        if multiplier is not None and not isinstance(multiplier, str) \
                and (not isinstance(multiplier, int) or isinstance(multiplier, bool) or multiplier < 1):
            raise ValueError("multiplier must be a positive int or a data name: %r" % (multiplier,))
        if accept is not None and not callable(accept):
            raise ValueError("accept must be callable: %r" % (accept,))
        self.allow = frozenset(allow)
        self.deny = frozenset(deny)
        self.maxStack = maxStack
        self.accept = accept
        self.decor = decor
        self.multiplier = multiplier

    def allows(self, stack, rules=None):
        """收不收这种东西（只看物品本身，不看格子里现在有什么）。rules 是这一端的物品规则，交给 accept。"""
        if self.allow and stack.get("newItemName") not in self.allow:
            return False
        if self.deny and any(item.get("newItemName") in self.deny for item in Bundles.walk(stack)):
            return False
        return self.accept is None or bool(self.accept(stack, rules))

    def mayPlace(self, ws, ref, stack):
        """普通操作能不能往 ref 放 stack 这种东西（不看数量与空间）。"""
        if Items.lockMode(stack) != Items.LOCK_NONE or not self.isActive(ws, ref) or not self.allows(stack, ws.rules):
            return False
        return ws.state.accepts(ref, stack)

    def capacity(self, ws, ref, stack):
        """ref 这一格最多放几个 stack 那种东西：物品的堆叠数（超堆叠的再乘倍数，不能叠的不乘），maxStack 给了时不超过它。"""
        largest = ws.rules.maxStack(stack)
        if self.multiplier is not None and largest > 1:
            factor = ws.data(self.multiplier) if isinstance(self.multiplier, str) else self.multiplier
            if isinstance(factor, int) and not isinstance(factor, bool) and factor > 1:
                largest *= factor
        return min(largest, self.maxStack) if self.maxStack is not None else largest

    def quickInto(self, ws, name, src, amount):
        """
        快速转移把 src 的 amount 个转进这种格子的集合 name：返回放不下的个数（返回 0 就不再往后面的去向试）；None 为照常
        （先补同种堆、再填空格）。改写它的：种类存储（Std/ListSync）并进同一种所在的那一格，没有就放进最前面的空格；幽灵格
        放一份副本、原格不动；能删东西的来源格（创造栏）把这些删掉。
        """
        return None

    def copyInto(self, ws, name, stack, amount):
        """
        来源格的快速转移（创造栏 Shift 点击）把凭空拿来的 amount 个 stack 放进这种格子的集合 name：返回放不下的个数；None 为
        照常（先补同种堆、再填空格）。改写它的：幽灵格不收（返回 amount）。
        """
        return None

    def mayTake(self, ws, ref, stack):
        """ref 里的东西能不能拿走（锁定在格子里的物品另由底层状态判断；装饰锁住的格子拿不走）。"""
        return self.decor is None or self.decor.takeable(ws, ref)

    def isActive(self, ws, ref):
        """ref 这一格启用着：停用的格子不收东西（装饰锁住的、不在布局里的也算停用）。"""
        return self.decor is None or self.decor.active(ws, ref)

    def hint(self, ws, ref):
        """ref 空着时悬停显示的提示（语言文件的键，例如合成器空格的"点击以禁用槽位"）；没有为 None。只在客户端调用。"""
        return self.decor.hint(ws, ref) if self.decor is not None else None

    def tip(self, ws, ref, stack, itemName):
        """
        ref（显示着 stack，不是空的）悬停时替物品的悬停文本写的字：可本地化的文字（Common/Data.Lang 的写法；itemName(物品堆)
        给出物品的名字，原版交易界面的材料格写"……不够"）；None 为照常写物品的悬停文本。只在客户端调用。
        """
        return None

    def hoverText(self, ws, ref, stack, text):
        """
        ref（显示着 stack）悬停时最终写的字：text 是照常写的（物品的悬停文本，或 tip 给的），返回要写的（缺省原样；追加一行写
        text + "\n" + 那一行）。只在客户端调用，改写了才调用。
        """
        return text

    def standIn(self, ws, ref):
        """
        ref 空着时替它显示的物品（不是真放在那里：照常画图标、悬停写它的悬停文本，点它照空格子处理；原版织布机的图案格空着时
        画选中的图案要的那种图案物品）；没有为 None。只在客户端调用。
        """
        return None

    def decorate(self, ws, ref, stack):
        """
        ref（现在显示 stack）这一次怎么画：装饰给出的 Decoration；超堆叠的格子数量 100 起写短写法（装饰没另给写法时）。
        都没有时为 None。只在客户端调用。
        """
        out = self.decor.render(ws, ref, stack) if self.decor is not None else None
        if self.multiplier is not None and Items.count(stack) >= SHORT_COUNT_FROM and (out is None or out.count is None):
            out = out if out is not None else Decoration()
            out.count = Items.shortCount(Items.count(stack))
        return out

    def check(self, menu, name):
        """界面模型建好时核对：这种格子用到的界面数据、动作在界面模型 menu 里（集合名 name）。不对时抛 ValueError。"""
        if self.itemsFrom is not None:
            menu.checkSlotData(name, self.itemsFrom, "Item")
        if self.decor is not None:
            self.decor.check(menu, name)
        if isinstance(self.multiplier, str) and not isinstance(menu.data.get(self.multiplier), Data.Int):
            raise ValueError("menu %s: collection %s multiplies by data %r, which must be a Data.Int"
                             % (menu.menuName, name, self.multiplier))

    def onTake(self, session, ref, stack):
        """服务端：一次操作提交后 ref 里少了 stack 这么多（拿到手上、转走、丢出、合成用掉都算；机器推进不算）。"""

    def onChanged(self, session, ref, old, new):
        """服务端：一次操作提交后 ref 的内容从 old 变成了 new（装备格据此作用到宿主；机器推进不算）。"""


class PlayerSlot(SlotType):
    """玩家背包与手持物的格子：什么都收（锁定的物品也能在背包里挪），不问界面模型与容器实例。"""

    def mayPlace(self, ws, ref, stack):
        return True


DEFAULT_SLOT = SlotType()
PLAYER_SLOT = PlayerSlot()


def overrides(slotType, name):
    """slotType 的类改写了 SlotType 的方法 name（py2 的未绑定方法要取出函数再比）：例如改写了 isActive 的会停用格子。"""
    mine, original = getattr(type(slotType), name), getattr(SlotType, name)
    return getattr(mine, "__func__", mine) is not getattr(original, "__func__", original)


def decorated(slotType):
    """slotType 的格子要逐格画装饰（带装饰、超堆叠，或改写了 decorate）。"""
    return getattr(slotType, "decor", None) is not None or getattr(slotType, "multiplier", None) is not None \
        or overrides(slotType, "decorate")


def hinted(slotType):
    """slotType 的空格子可能有悬停提示（带装饰，或改写了 hint）。"""
    return getattr(slotType, "decor", None) is not None or overrides(slotType, "hint")


def tipped(slotType):
    """slotType 的格子悬停时可能另写字（改写了 tip）。"""
    return overrides(slotType, "tip")


def standsIn(slotType):
    """slotType 的空格子可能替它显示一样东西（改写了 standIn）。"""
    return overrides(slotType, "standIn")
