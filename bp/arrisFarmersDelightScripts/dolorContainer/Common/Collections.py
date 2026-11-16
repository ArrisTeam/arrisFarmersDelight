# -*- coding: utf-8 -*-
"""
容器与格子集合（docs/ARCHITECTURE.md 第 3.4 节）。纯逻辑，两端共用。

- 容器：一份能放物品的格子。界面模型只声明它要哪些容器（种类与格数），由会话接上真的（Server/Containers）。
  种类是登记过的名字（ContainerKind）：玩家背包与手持物在这里（每个界面都有，见 Structure.player），玩家临时格、
  实例存储、只放算出格子的虚拟容器在标准库（Std/Containers），使用方可以登记自己的。
  存储与两端同步都按容器格 (容器, 下标) 进行；每个容器还声明同步方式（Common/Sync，缺省整份）。
- 集合：界面能绑定的一组格子，是某个容器上的一段，带格子类型（Common/Slots）。界面格子、请求、去向表都按格子 (集合名, 下标) 说话，
  与原版界面的 collection_name 一样；同一个容器格可以属于几个集合（快捷栏与合并背包），改动按容器格算，不会算重。
- 结构（Structure）：一个界面模型用到的全部容器、集合、去向表、算出格子的部件与面板，两端各建一份。
  可组合的一块（Common/Menus.Part）经 include 接进来，它的名字带上前缀。
- 面板（Panel）：一组集合与面板范围的界面数据的开关（子窗口、页签、锁住的行）。开关是界面模型里一个每位查看者状态或
  界面数据的名字（写成 (名字, 值) 时等于这个值才算开着）；面板关着时它的集合停用（不收不出，快速转移与双击收集也不碰），
  面板范围的界面数据不发，布局里标了这个面板的控件藏起来。
- 附加容器（Structure.attach）：格子放在别的容器实例里（相邻的箱子、存储网络、查看者自己的末影箱这类），由服务端按
  界面模型的 attachment 钩子接上，接没接上记在一个布尔的每位查看者状态（开关）里：断开时容器上的集合同样停用。
  要在断开时藏起布局里的控件，就把这些集合放进一个用同一个开关的面板。
- 内容来自界面数据的集合（格子类型的 itemsFrom：来源格、虚拟格、只看的预览）：落在不放东西的容器上，显示的东西是界面数据
  里的一份每格物品，两端的规则按它读（Rules.Workspace.get），普通操作不往里放、不从里拿。

玩家的四个集合照原版命名：hotbar_items（背包 0–8）、inventory_items（9–35）、
combined_hotbar_and_inventory_items（0–35，携带版用）、cursor_items（手持物）。
"""
import collections
import re

from . import Slots, Sync

PLAYER_SIZE = 36
HOTBAR_SIZE = 9
PLAYER_CONTAINER = "player"   # 玩家背包那个容器的名字（Structure.player）
HOTBAR = "hotbar_items"
INVENTORY = "inventory_items"
COMBINED = "combined_hotbar_and_inventory_items"
CURSOR_ITEMS = "cursor_items"
CURSOR_REF = (CURSOR_ITEMS, 0)
PLAYER_COLLECTIONS = (HOTBAR, INVENTORY, COMBINED, CURSOR_ITEMS)

PROFILE_CLASSIC = "classic"
PROFILE_POCKET = "pocket"
PROFILES = (PROFILE_CLASSIC, PROFILE_POCKET)

MAX_NAME = 64
MAX_COLLECTIONS = 256           # 一个界面模型最多几个集合、几个容器（线上用编号代替名字）
MAX_FIXED_SIZE = 1024           # 有格数的容器最多几格（放真东西的整份同步）
MAX_VIRTUAL_SIZE = 1 << 16      # 不放东西的容器（只放算出的格子，内容不同步）最多几格：原版创造栏的目录近两千格
NO_COLLECTIONS = frozenset()
_TRUTHY = object()
_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class ContainerKind(object):
    """
    容器的种类（docs/ARCHITECTURE.md 第 3.2 节）：名字与两端都要知道的几条性质。服务端怎么接上真的存储，由按同一个
    名字登记的工厂决定（Server/Containers.register）。
    unbounded：可以不设上限；stored：内容跟容器实例存（所有查看者同一份）；holdsItems：放真东西（为假时只放算出的格子）。
    """

    def __init__(self, name, unbounded=False, stored=False, holdsItems=True):
        self.name = name
        self.unbounded = unbounded
        self.stored = stored
        self.holdsItems = holdsItems


_kinds = {}


def registerKind(kind):
    """登记容器种类（两端都要执行到），返回它的名字。重新载入时同名的新种类替换旧的。"""
    _kinds[kind.name] = kind
    return kind.name


def kindOf(name):
    return _kinds.get(name)


PLAYER_KIND = registerKind(ContainerKind("player"))   # 玩家背包 36 格（引擎）
CURSOR_KIND = registerKind(ContainerKind("cursor"))   # 手持物 1 格（属于会话）
ATTACHED_KIND = registerKind(ContainerKind("attached", unbounded=True))   # 附加容器：格子在别的实例里（Structure.attach）


class ContainerSpec(object):
    """
    界面模型声明的一个容器：名字、种类（登记过的名字）、格数（None 表示不设上限，要种类与同步方式都允许）、
    同步方式（Common/Sync 登记过的名字）。
    """

    __slots__ = ("cid", "kind", "size", "sync")

    def __init__(self, cid, kind, size, sync=Sync.FULL):
        info = _kinds.get(kind)
        if info is None:
            raise ValueError("unknown container kind: %r" % (kind,))
        strategy = Sync.get(sync)
        if strategy is None:
            raise ValueError("unknown sync strategy: %r" % (sync,))
        if size is None and not (info.unbounded and strategy.unbounded):
            raise ValueError("container %s cannot be unbounded (kind %s, sync %s)" % (cid, kind, sync))
        limit = MAX_FIXED_SIZE if info.holdsItems else MAX_VIRTUAL_SIZE
        if size is not None and (not isinstance(size, int) or not 0 < size <= limit):
            raise ValueError("bad container size for %s: %r" % (cid, size))
        self.cid = cid
        self.kind = kind
        self.size = size
        self.sync = sync

    @property
    def info(self):
        return _kinds[self.kind]

    def __repr__(self):
        return "ContainerSpec(%s, %s)" % (self.cid, self.kind)


class Collection(object):
    """
    集合：名字、落在哪个容器、从哪一格起、几格、格子类型（slot，Common/Slots.SlotType）。格数为 None 时随容器
    （不设上限的容器），显示几格由格数策略 sizer（Common/Sizers）按最后一个非空格算。
    """

    __slots__ = ("name", "container", "offset", "size", "slot", "sizer", "cid")

    def __init__(self, name, container, offset, size, slot, sizer):
        self.name = name
        self.container = container
        self.cid = container.cid
        self.offset = offset
        self.size = size
        self.slot = slot
        self.sizer = sizer

    def __repr__(self):
        return "Collection(%s)" % self.name


def _validName(name):
    return isinstance(name, str) and 0 < len(name) <= MAX_NAME and all(c.isalnum() or c in "_/." for c in name)


class Panel(object):
    """
    面板：名字、集合、面板范围的界面数据、开关。switch 是界面模型里一个每位查看者状态或界面数据的名字；
    value 不给时开关的值为真就开着，给了时等于它才开着（页签：几个面板用同一个开关、各认一个值）。
    """

    def __init__(self, name, collections, data, switch, value=_TRUTHY):
        self.name = name
        self.collections = tuple(collections)
        self.data = tuple(data)
        self.switch = switch
        self.value = value

    def opens(self, value):
        """开关现在的值是 value 时，面板开着没有。"""
        return bool(value) if self.value is _TRUTHY else value == self.value


class Structure(object):
    """
    一个界面模型用到的容器、集合（带格子类型）、去向表与算出格子的部件。两端各建一份（界面模型的 define 填它），建好后不再改。

    去向表：quick = {界面档: {来源集合: ((目标集合, 放进去了就停), ...)}}；gather = {界面档: {点中的集合: (集合, ...)}}。
    面板：panels = {名字: Panel}，panelData = {面板范围的数据名: 面板名}。附加容器：attachments = {容器名: 开关}。
    部件：derivers = {算出的集合名: 部件}，部件有 derive(集合名, 读格子, 查看者) -> {下标: 物品堆}、match(读格子, 查看者) /
    consume（见 Std/Operations.craft）；查看者是在看的那一位的每位查看者状态（{名字: 值}，没有时为 None），
    按查看者算的格子（每位玩家各自的产物）读它。部件可以另给 shown(集合名, 读格子, 查看者) -> 现在显示几格（不超过集合的
    格数；切石机的配方随原料变），界面按它显示，不给时显示全部。
    side 是这一份在哪一端（"server" / "client"），itemRules 是这一端的物品规则（Items.ItemRules）；部件按需要用它们
    （例如向这一端的引擎查配方）。
    """

    def __init__(self, side=None, itemRules=None):
        self.side = side
        self.itemRules = itemRules
        self.containers = collections.OrderedDict()
        self.collections = collections.OrderedDict()
        self.quick = {}
        self.gather = {}
        self.derivers = {}
        self.dataBacked = {}   # 内容来自界面数据的集合名 -> 界面数据名（格子类型的 itemsFrom，建好时填）
        self.panels = collections.OrderedDict()
        self.panelData = {}
        self.attachments = collections.OrderedDict()   # 附加容器名 -> 开关（布尔的每位查看者状态）
        self.parts = []     # 接进来的部件（Menus.Part），按接进来的先后
        self._byContainer = {}
        self._containerIds = []
        self._collectionIds = []
        self._finished = False

    # ---------------------------------------------------------------- 声明

    def container(self, cid, kind, size=None, sync=Sync.FULL):
        self._open()
        if not _validName(cid) or cid in self.containers:
            raise ValueError("bad or duplicate container name: %r" % (cid,))
        spec = ContainerSpec(cid, kind, size, sync)
        self.containers[cid] = spec
        return spec

    def attach(self, cid, size=None, sync=Sync.FULL, switch=None):
        """
        声明附加容器 cid：格子放在别的容器实例的存储容器里（同样的格数），服务端打开时按界面模型的
        attachment(名字, 实例, 玩家) 接上。switch 是界面模型里一个布尔的每位查看者状态：接上时服务端把它设为真，
        接不上或附加的宿主失效时设为假，这时容器上的集合停用。返回容器说明（集合照常声明在它上面）。
        """
        if not isinstance(switch, str) or not switch:
            raise ValueError("attached container %s needs a switch (a Bool viewer state name)" % (cid,))
        spec = self.container(cid, ATTACHED_KIND, size, sync)
        self.attachments[cid] = switch
        return spec

    def collection(self, name, container, offset=0, size=None, slot=None, sizer=None):
        """
        在容器 container（名字或 ContainerSpec）的 [offset, offset + size) 上声明集合 name，格子类型 slot（缺省普通格子）。
        size 可以是 0：按这一次的参数没有格子的集合（没带箱子的马的箱子格），布局照有格子时写，界面上一格都不显示。
        """
        self._open()
        spec = self.containers[container] if not isinstance(container, ContainerSpec) else container
        if not _validName(name) or name in self.collections:
            raise ValueError("bad or duplicate collection name: %r" % (name,))
        if size is None and spec.size is not None:
            size = spec.size - offset
        if size is not None and (offset < 0 or size < 0 or (spec.size is not None and offset + size > spec.size)):
            raise ValueError("collection %s does not fit in container %s" % (name, spec.cid))
        if size is None and sizer is None:
            raise ValueError("collection %s on an unbounded container needs a sizer" % name)
        result = Collection(name, spec, offset, size, slot or Slots.DEFAULT_SLOT, sizer)
        self.collections[name] = result
        return result

    def player(self, slot=None, cursorSlot=None):
        """
        玩家背包与手持物，以及照原版命名的四个集合。slot 是背包三个集合（快捷栏、主背包、合并背包）的格子类型，cursorSlot 是
        手持物的，缺省都是 Slots.PLAYER_SLOT（什么都收）。
        """
        slot = slot or Slots.PLAYER_SLOT
        player = self.container(PLAYER_CONTAINER, PLAYER_KIND, PLAYER_SIZE)
        cursor = self.container("cursor", CURSOR_KIND, 1)
        self.collection(HOTBAR, player, 0, HOTBAR_SIZE, slot)
        self.collection(INVENTORY, player, HOTBAR_SIZE, PLAYER_SIZE - HOTBAR_SIZE, slot)
        self.collection(COMBINED, player, 0, PLAYER_SIZE, slot)
        self.collection(CURSOR_ITEMS, cursor, 0, 1, cursorSlot or Slots.PLAYER_SLOT)
        return self

    def routes(self, quick=None, gather=None):
        """去向表（覆盖同一来源的旧条目）。"""
        self._open()
        for table, rows in ((self.quick, quick), (self.gather, gather)):
            for profile, entries in (rows or {}).items():
                table.setdefault(profile, {}).update(entries)
        return self

    def derive(self, name, part):
        """集合 name 的内容由部件 part 算出（它的格子类型要是算出的，computed 为真）。"""
        self._open()
        self.derivers[name] = part
        return self

    def include(self, part, prefix=None):
        """
        接进一个部件（Common/Menus.Part）：它的名字都加上前缀 prefix（"craft" -> craft.crafting_input；为 None 时不加，
        名字照部件写的）。一个部件对象只能接一次。返回部件。
        """
        self._open()
        if getattr(part, "included", False):
            raise ValueError("this part object is already included somewhere")
        if prefix is not None and not _PREFIX.match(prefix):
            raise ValueError("bad part prefix: %r" % (prefix,))
        part.prefix = prefix
        part.included = True
        part.define(self)
        self.parts.append(part)
        return part

    def panel(self, name, collections=(), data=(), switch=None):
        """
        声明面板 name：集合 collections、面板范围的界面数据 data 跟着开关 switch（每位查看者状态或界面数据的名字，
        或 (名字, 值)）开关。一个集合、一个数据只能在一个面板里。
        """
        self._open()
        if not _validName(name) or name in self.panels:
            raise ValueError("bad or duplicate panel name: %r" % (name,))
        value = _TRUTHY
        if isinstance(switch, (tuple, list)) and len(switch) == 2:
            switch, value = switch
        if not isinstance(switch, str) or not switch:
            raise ValueError("panel %s needs a switch (a viewer state or data name, or (name, value))" % name)
        result = Panel(name, collections, data, switch, value)
        for other in self.panels.values():
            shared = set(other.collections) & set(result.collections) or set(other.data) & set(result.data)
            if shared:
                raise ValueError("%r is in both panel %s and panel %s" % (sorted(shared)[0], other.name, name))
        self.panels[name] = result
        for dataName in result.data:
            self.panelData[dataName] = name
        return result

    def closedCollections(self, opens, viewer=None):
        """
        停用的集合：面板关着的（opens(面板) -> 开着没有），加上断开了的附加容器上的（viewer 是这位查看者的状态，
        附加容器的开关为假就是断开了）。没有面板也没有附加容器时为空。
        """
        if not self.panels and not self.attachments:
            return NO_COLLECTIONS
        closed = set(name for panel in self.panels.values() if not opens(panel) for name in panel.collections)
        for cid, switch in self.attachments.items():
            if not (viewer or {}).get(switch):
                closed.update(collection.name for collection in self._byContainer.get(cid, ()))
        return frozenset(closed)

    def finish(self):
        """检查并定下编号（线上用编号代替名字）。"""
        if self._finished:
            return self
        if len(self.collections) > MAX_COLLECTIONS or len(self.containers) > MAX_COLLECTIONS:
            raise ValueError("a menu may declare at most %d collections and %d containers (got %d and %d)"
                             % (MAX_COLLECTIONS, MAX_COLLECTIONS, len(self.collections), len(self.containers)))
        for profile, rows in list(self.quick.items()) + list(self.gather.items()):
            if profile not in PROFILES:
                raise ValueError("unknown profile in routes: %r" % (profile,))
            for source, targets in rows.items():
                names = [source] + [t[0] if isinstance(t, (tuple, list)) else t for t in targets]
                for name in names:
                    if name not in self.collections:
                        raise ValueError("unknown collection in routes: %r" % (name,))
        for panel in self.panels.values():
            for name in panel.collections:
                if name not in self.collections:
                    raise ValueError("panel %s: unknown collection %r" % (panel.name, name))
        for name, collection in self.collections.items():
            derived = name in self.derivers
            if derived != bool(collection.slot.computed):
                raise ValueError("collection %s: a computed slot type and a deriving part go together" % name)
            if derived and collection.container.info.holdsItems:
                raise ValueError("computed collection %s must live on a container that holds no items" % name)
            shown = collection.slot.itemsFrom
            if shown is not None:
                if derived or collection.container.info.holdsItems or collection.size is None:
                    raise ValueError("collection %s shows data %r: it must have a size and live on a container that "
                                     "holds no items, and it cannot be computed" % (name, shown))
                self.dataBacked[name] = shown
        for name, collection in self.collections.items():
            self._byContainer.setdefault(collection.cid, []).append(collection)
        self._containerIds = list(self.containers)
        self._collectionIds = list(self.collections)
        self._finished = True
        return self

    def _open(self):
        if self._finished:
            raise ValueError("structure is finished")

    # ---------------------------------------------------------------- 查询

    def get(self, name):
        return self.collections.get(name)

    def locate(self, ref):
        """格子 (集合, 下标) 落在哪个容器格 (容器, 下标)；集合不存在为 None（不查下标范围）。"""
        collection = self.collections.get(ref[0])
        if collection is None:
            return None
        return (collection.cid, collection.offset + ref[1])

    def refsAt(self, key):
        """容器格 key 属于哪些格子：[(集合, 下标), ...]。"""
        cid, index = key
        out = []
        for collection in self._byContainer.get(cid, ()):
            local = index - collection.offset
            if local >= 0 and (collection.size is None or local < collection.size):
                out.append((collection.name, local))
        return out

    def derived(self, ref, reader, viewer=None):
        """算出的格子 ref 现在显示什么（不是算出的集合返回 None）；viewer 是在看的那一位的每位查看者状态。"""
        part = self.derivers.get(ref[0])
        if part is None:
            return None
        return part.derive(ref[0], reader, viewer).get(ref[1])

    def quickTargets(self, name, profile):
        return [(target, bool(stop)) for target, stop in self.quick.get(profile, {}).get(name, ())]

    def gatherOrder(self, name, profile):
        return list(self.gather.get(profile, {}).get(name, ()))

    # ---------------------------------------------------------------- 线上编号

    def collectionId(self, name):
        return self._collectionIds.index(name)

    def collectionName(self, cid):
        return self._collectionIds[cid] if 0 <= cid < len(self._collectionIds) else None

    def containerId(self, cid):
        return self._containerIds.index(cid)

    def containerName(self, number):
        return self._containerIds[number] if 0 <= number < len(self._containerIds) else None

