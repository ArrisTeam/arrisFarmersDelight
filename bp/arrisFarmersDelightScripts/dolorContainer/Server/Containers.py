# -*- coding: utf-8 -*-
"""
服务端的存储容器（docs/ARCHITECTURE.md 第 3.2 节）：会话按容器对象读写，不认识具体的种类。

界面模型声明的每个容器（Common/Collections.ContainerSpec，种类是登记过的名字）在会话里由按种类名登记的工厂
接上真的：factory(会话, 容器说明) -> Container。玩家背包、手持物与附加容器在这里（每个界面都可能有，关界面退回、
崩溃后找回、跨实例推送都靠它们）；玩家临时格、实例存储、只放算出格子的虚拟容器在标准库（Std/Server/Containers.py）；
使用方可以登记自己的。

容器读写的东西若是容器实例里的一份存储（几位查看者共用），backing() 给出 (实例, 存储容器名)：会话提交后把改动推给
看着那份存储的所有会话（看这个实例的，以及把它作为附加容器接上的），各自换成自己的容器名。

提交一次操作时，会话把工作副本的改动按容器分开，按 order 从小到大写：写入可能失败的（引擎的背包）排在前面，
一个写不进去就把前面写过的撤回，整条操作不生效。本模块不依赖引擎，离线可测。
"""
from ..Common import Items
from ..Common.Collections import ATTACHED_KIND, CURSOR_KIND, PLAYER_KIND, PLAYER_SIZE

_factories = {}
ticking = [None]   # 服务端每刻检查时是第几刻（检查之外为 None）：同一刻里几个容器共用从引擎读到的东西（EngineSlots）


def register(kind, factory):
    """登记容器种类 kind（Collections.registerKind 登记过的名字）在服务端的工厂：factory(会话, 容器说明) -> Container。"""
    _factories[kind] = factory


def create(session, spec):
    factory = _factories.get(spec.kind)
    if factory is None:
        raise ValueError("no server container for kind %r (import the module that registers it first)" % (spec.kind,))
    return factory(session, spec)


def same(a, b):
    """两堆东西一样（种类与数量）；都是空格也算一样。"""
    if Items.isEmpty(a) or Items.isEmpty(b):
        return Items.isEmpty(a) and Items.isEmpty(b)
    return Items.sameKind(a, b) and Items.count(a) == Items.count(b)


class Container(object):
    """
    服务端一个容器在一次会话里的样子。几个类属性：
    synced：内容发给客户端（为假时客户端自己算，例如只放算出格子的容器）；
    held：内容属于这位查看者、由会话保管（玩家临时格）：改了就存进玩家数据，服务器在界面开着时崩溃，下次进游戏退回；
    returnsOnClose：关界面时把里面的东西退回背包；
    order：提交时写入的先后，写入可能失败的排在前面（0）；
    ticks：会话每刻调用它的 tick（有这种容器的会话才每刻检查，见 Session.tick）。
    """

    synced = True
    held = False
    returnsOnClose = False
    order = 1
    ticks = False

    def __init__(self, session, spec):
        self.session = session
        self.spec = spec

    def begin(self, everything=False):
        """一次请求（或关界面）开始：丢掉上一次读到的东西。everything 为真时这次会读遍全部格子，可以一次读完。"""

    def read(self, index):
        return None

    def items(self, start, end):
        """[start, end) 里的非空格：[(下标, 物品堆)]，按下标排。"""
        return []

    def highestUsed(self):
        """不设上限的容器里最后一个非空格的下标，空容器为 -1。"""
        return -1

    def findKind(self, stack):
        """放着 stack 那种东西（不看数量）的下标，没有为 None（种类存储按索引找；缺省逐格找）。"""
        for index, item in self.items(0, self._extent()):
            if Items.sameKind(item, stack):
                return index
        return None

    def freeIndex(self):
        """给新的一种东西用的下标：最前面的空格（没有空格时是末尾之后；缺省逐格找）。"""
        used = set(index for index, item in self.items(0, self._extent()) if not Items.isEmpty(item))
        index = 0
        while index in used:
            index += 1
        return index

    def _extent(self):
        return self.spec.size if self.spec.size is not None else self.highestUsed() + 1

    def accepts(self, stack):
        """格子类型之外，容器自己收不收这种东西（实例存储不收装着它自己的物品）。"""
        return True

    def write(self, changes):
        """
        写入 {下标: 物品堆}，只写真的变了的格子，返回 {下标: (原来的, 写入后的)}。
        写不进去时恢复原样并返回 None（会话随即撤回前面写过的容器，整条操作不生效）。
        """
        return {}

    def revert(self, written):
        """撤回 write 写过的（排在后面的容器写入失败时）。只有写入可能失败的容器（order 为 0）会被要求撤回。"""

    def told(self, values):
        """这些格子的内容已经发给客户端：{下标: 物品堆}（空格为 None）。"""

    def refresh(self):
        """别处改了这个容器：返回与客户端所知不同的格子 {下标: 物品堆}，并记作已发。"""
        return {}

    def heldStacks(self):
        """held 的容器：现在保管着的东西（按下标排）。"""
        return []

    def clear(self):
        """held 的容器：清空（东西已经丢出或退回）。"""

    def handOver(self):
        """held 的容器：切换会话时交出保管着的东西 {下标: 物品堆}，自己清空。"""
        return {}

    def takeOver(self, slots):
        """held 的容器：切换会话时接过上一个会话同一个容器交出的东西。"""

    def backing(self):
        """读写的是哪个实例里的哪份存储：(容器实例, 存储容器名)；不是实例里的存储（背包、临时格）时为 None。"""
        return None

    def tick(self):
        """ticks 为真的容器每刻调用：要推给客户端的格子 {下标: 物品堆}（空格为 None），没有时为 None。"""
        return None

    def release(self):
        """会话结束（关闭、切换走）：放开会话之外拿着的东西（附加容器接着的实例）。"""


class PlayerContainer(Container):
    """
    玩家背包 36 格（会话注入的 inventory：read()、readSlot(下标)、write({下标: 物品堆}) -> 实际写入的）。
    一次请求里用到哪一格才向引擎读哪一格，读过的记住（在容器里拿放这类操作根本不碰背包）；写入后核对，
    与预期不符就改回原样。另记着客户端知道的背包（推送别处的改动时比对）。
    """

    order = 0

    def __init__(self, session, spec):
        Container.__init__(self, session, spec)
        self.inventory = session.inventory
        self.known = [None] * PLAYER_SIZE
        self._slots = {}

    def begin(self, everything=False):
        self._slots = dict(enumerate(self.inventory.read())) if everything else {}

    def read(self, index):
        slots = self._slots
        if index not in slots:
            slots[index] = self.inventory.readSlot(index)
        return slots[index]

    def items(self, start, end):
        current = self.inventory.read()
        self._slots = dict(enumerate(current))
        return [(index, current[index]) for index in range(max(0, start), min(end, PLAYER_SIZE)) if current[index]]

    def write(self, changes):
        written = {}
        for index, stack in changes.items():
            old = self.read(index)
            if not same(stack, old):
                written[index] = (old, stack)
        if not written:
            return written
        wanted = dict((index, new) for index, (old, new) in written.items())
        actual = self.inventory.write(wanted)
        if any(not same(actual.get(index), stack) for index, stack in wanted.items()):
            self.revert(written)
            return None
        self._slots.update(wanted)
        return written

    def revert(self, written):
        self.inventory.write(dict((index, old) for index, (old, new) in written.items()))
        for index, (old, new) in written.items():
            self._slots[index] = old

    def told(self, values):
        for index, stack in values.items():
            self.known[index] = stack

    def refresh(self):
        current = self.inventory.read()
        changes = dict((index, current[index]) for index in range(PLAYER_SIZE) if not same(current[index], self.known[index]))
        self.known = list(current)
        return changes


class CursorContainer(Container):
    """手持物 1 格：会话的 cursor，改了就持久化（cursorStore），崩溃后下次进游戏退回背包。"""

    order = 3

    def read(self, index):
        return self.session.cursor

    def items(self, start, end):
        cursor = self.session.cursor
        return [(0, cursor)] if cursor and start <= 0 < end else []

    def write(self, changes):
        if 0 not in changes:
            return {}
        old = self.session.cursor
        self.session.setCursor(changes[0])
        return {0: (old, self.session.cursor)}   # 照旧：写过就算（应答里总带上手持物）


class AttachedContainer(Container):
    """
    附加容器（Collections.Structure.attach）：格子在别的容器实例的存储容器里。打开时按界面模型的 attachmentFor
    问一次接到哪（会话的登记表 resolve：类型登记过、不是机器、宿主让这位玩家打开、容器在那个界面模型里是同样格数的
    存储容器），之后每刻问那个宿主对这位玩家还有效没有（登记表 valid）：失效时断开——客户端那份清空、开关设为假
    （集合停用），有效了再接上、把内容发回去；会话不关。断开时读到的都是空格，写不进去（整条操作不生效）。
    查看者自己的容器（每人一份）就是按玩家存放的类型、实例键是这位查看者：各人接的是各自的实例，互相看不见。
    """

    ticks = True

    def __init__(self, session, spec):
        Container.__init__(self, session, spec)
        self.switch = session.structure.attachments[spec.cid]
        self.instance = None   # 接着的实例（断开时为 None）
        self.cid = None        # 它里面的存储容器名
        self.shown = set()     # 告诉过客户端的格子（断开时清空它们、接上时重发它们）
        registry = session.registry
        self.target = None if registry is None else registry.resolve(session.menu, spec, session.instance,
                                                                     session.playerId)
        self._attach()
        session.viewer[self.switch] = self.instance is not None

    def _attach(self):
        """接上 target（宿主有效、实例取得到时）。"""
        if self.target is None:
            return False
        registry = self.session.registry
        if not registry.valid(self.target, self.session.playerId):
            return False
        instance = registry.attachInstance(self.target)
        if instance is None:
            return False
        self.instance, self.cid = instance, self.target[2]
        instance.attachedViewers.add(self.session)
        return True

    def _detach(self):
        instance, self.instance, self.cid = self.instance, None, None
        if instance is not None:
            instance.attachedViewers.discard(self.session)
            self.session.registry.release(instance)

    @property
    def attached(self):
        return self.instance is not None

    def backing(self):
        return None if self.instance is None else (self.instance, self.cid)

    def read(self, index):
        return None if self.instance is None else self.instance.get(self.cid, index)

    def items(self, start, end):
        return [] if self.instance is None else self.instance.items(self.cid, start, end)

    def highestUsed(self):
        return -1 if self.instance is None else self.instance.highestUsed(self.cid)

    def accepts(self, stack):
        return self.instance is not None and self.instance.accepts(stack)

    def write(self, changes):
        written = {}
        for index, stack in changes.items():
            old = self.read(index)
            if not same(stack, old):
                written[index] = (old, stack)
        if written and self.instance is None:
            return None
        for index, (old, new) in written.items():
            self.instance.set(self.cid, index, new)
        return written

    def told(self, values):
        self.shown.update(values)

    def tick(self):
        """
        附加的宿主对这位玩家的有效性变了就接上或断开（接不上的下一刻再试），开关每刻按实际情况写一遍。
        接上或断开时返回告诉过客户端的格子现在的内容（接上时是实例里的，断开时都是空格），否则 None。
        """
        session = self.session
        before = self.attached
        if self.target is not None:
            wanted = session.registry.valid(self.target, session.playerId)
            if wanted and not before:
                self._attach()
            elif before and not wanted:
                self._detach()
        session.viewer[self.switch] = self.attached
        if self.attached == before:
            return None
        return dict((index, self.read(index)) for index in self.shown)

    def release(self):
        self._detach()


register(PLAYER_KIND, PlayerContainer)
register(CURSOR_KIND, CursorContainer)
register(ATTACHED_KIND, AttachedContainer)
