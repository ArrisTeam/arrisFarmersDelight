# -*- coding: utf-8 -*-
"""
物品操作的工作副本与公共工具（docs/ARCHITECTURE.md 第 3.5 节）。纯逻辑，两端共用：服务端按操作改真实状态，客户端用它预测。

格子写成 (集合名, 下标)（见 Collections）；读写落到容器格 (容器, 下标)，同一个容器格属于几个集合时改动只算一次。
每个集合的规矩（收不收、每格上限、能不能拿走、停用）来自它的格子类型（Common/Slots），这里只在"能不能放、还能放几个、
能不能拿走"这几步问它，其余的拿放逻辑所有集合共用，不认识具体的格子类型。

每个操作作用在一个 Workspace 上：读穿到底层状态，写只进覆盖层，操作成功后由调用方一次提交 changes 与 drops，
格子写好之后再做 after 里的事（服务端：部件在格子之外的改动，例如铁砧扣经验；在写回存档之前做，改的实例状态随这次
一起存下；提交不成就不做）。
一个手势对应一个操作（例如拖动分配是一次分配，而不是逐格放置），所以服务端一次请求要么整体生效、要么整体不生效。
这里放操作作者要用的工具（搬运、交换、放下整堆、按快速转移的规矩填进集合、凭空放进集合）与关界面时的退回；
原版的各个操作（点击、快速转移、拖动分配、收纳袋、合成……）在标准库 Std/Operations.py，按名字登记（Common/Ops）。
"""
from . import Items
from .Collections import COMBINED, CURSOR_REF

PRIMARY = 0     # 左键、手柄 A：拿起整堆 / 放下整堆
SECONDARY = 1   # 右键、手柄 X：拿起一半 / 放下一个

EVEN = 0        # 拖动分配：平均分配（左键拖、触屏拖）
ONE = 1         # 拖动分配：每格一个（右键拖）


class RuleError(Exception):
    """参数本身不成立（不是"这次做不成"）：服务端据此拒绝请求。"""

    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


class SlotState(object):
    """
    Workspace 的底层状态：按容器格读。服务端接真实容器与背包，客户端接镜像，测试接内存表。
    structure 是界面模型的结构（Collections.Structure）；viewer 是在看、在操作的那一位的每位查看者状态
    （{名字: 值}，界面模型的 viewerState；没有查看者时为 None），按查看者算的格子读它。playerId 是在操作的那位玩家
    （客户端是本地玩家；离线测试可以为 None）；session 是服务端的会话（Server/Session 的公开部分：read、creative、
    giveExperience、instance、viewer、profile……；客户端预测与离线测试为 None）。
    """

    structure = None
    menu = None        # 界面模型（Common/Menus：Shift 点击问它的 quickMove）
    viewer = None
    creative = False   # 在操作的那一位是创造模式（装备格的绑定诅咒对他不起作用）
    playerId = None
    session = None

    def dataValue(self, name):
        """
        界面数据 name 现在的值，写法与客户端读到的一样（服务端把原始值按字段类型编码再解码；客户端算上可预测的动作）。
        规则按它停用格子、显示格子的内容；没有这个数据时为 None。
        """
        return None

    def clientValue(self, name):
        """客户端界面状态 name 现在的值（只在客户端有：格子装饰、提示按页签、搜索词画）；服务端与没有时为 None。"""
        return None

    def closedCollections(self):
        """面板关着的集合（停用：不收不出），这一次操作里不变。没有面板时为空。"""
        return frozenset()

    def lockedCells(self):
        """
        锁住的容器格（不收不出，效果与只读的格子一样；物品宿主所在的那一格，见 Server/Hosts.lockedSlot），
        这一次操作里不变。没有时为空。
        """
        return frozenset()

    def read(self, key):
        """容器格 (容器, 下标) 里的物品堆，空格为 None。"""
        raise NotImplementedError

    def highestUsed(self, cid):
        """不设上限的容器里最后一个非空格的下标，空容器为 -1。"""
        return -1

    def findKind(self, cid, stack):
        """
        容器 cid 里放着 stack 那种东西（不看数量）的下标，没有为 None。种类存储（一种东西只占一格，Std/ListSync）按它找格子；
        缺省逐格找（不设上限的容器找到末尾），两端的状态各按自己的索引找。
        """
        for index in range(self._extent(cid)):
            if Items.sameKind(self.read((cid, index)), stack):
                return index
        return None

    def freeIndex(self, cid):
        """容器 cid 里给新的一种东西用的下标：最前面的空格（没有空格时是末尾之后）。缺省逐格找。"""
        extent = self._extent(cid)
        for index in range(extent):
            if Items.isEmpty(self.read((cid, index))):
                return index
        return extent

    def _extent(self, cid):
        size = self.structure.containers[cid].size if self.structure is not None else None
        return size if size is not None else self.highestUsed(cid) + 1

    def accepts(self, ref, stack):
        """格子 ref 收不收这种东西：格子类型之外、只在服务端才有的判断（例如次元背包不收自己）。"""
        return True

    def canLeave(self, ref, stack):
        """stack 能否离开 ref（锁在格子里的物品不能动，手持物上的除外）。"""
        return Items.lockMode(stack) != Items.LOCK_IN_SLOT or ref == CURSOR_REF

    def canDrop(self, stack):
        """能否丢进世界（锁定的物品不能丢）。"""
        return Items.lockMode(stack) == Items.LOCK_NONE


class Workspace(object):

    def __init__(self, state, rules):
        self.state = state
        self.rules = rules
        self.structure = state.structure
        self.changes = {}   # 容器格 -> 物品堆
        self.drops = []
        self.after = []     # 格子写好之后、写回存档之前要做的事（无参函数，服务端按顺序调用）
        self._closed = None  # 面板关着的集合（用到时问一次底层状态）
        self._locked = None  # 锁住的容器格（同上）
        self._derived = {}   # 算出的集合名 -> (算的时候的每位查看者状态, {下标: 物品堆})：改了格子就忘掉

    # ---------------------------------------------------------------- 读写

    def key(self, ref):
        return self.structure.locate(ref)

    @property
    def viewer(self):
        """在操作的那一位的每位查看者状态（见 SlotState.viewer）。"""
        return self.state.viewer

    @property
    def menu(self):
        """界面模型（见 SlotState.menu；没有时为 None）。"""
        return self.state.menu

    @property
    def playerId(self):
        """在操作的那位玩家（见 SlotState.playerId）。"""
        return self.state.playerId

    @property
    def session(self):
        """服务端的会话（见 SlotState.session）：读格子、给经验、宿主的实例；客户端预测时为 None。"""
        return self.state.session

    @property
    def creative(self):
        """在操作的那一位是不是创造模式（见 SlotState.creative）。"""
        return self.state.creative

    def data(self, name):
        """界面数据 name 现在的值（见 SlotState.dataValue）。"""
        return self.state.dataValue(name)

    def client(self, name):
        """客户端界面状态 name 现在的值（见 SlotState.clientValue；服务端为 None，规则不能靠它定能不能放）。"""
        return self.state.clientValue(name)

    def get(self, ref):
        if ref[0] in self.structure.derivers:
            return self.derivedOf(ref[0]).get(ref[1])   # 算出的格子按工作副本当前的内容算
        shown = self.structure.dataBacked.get(ref[0])
        if shown is not None:
            return (self.state.dataValue(shown) or {}).get(ref[1])   # 内容来自界面数据的格子
        key = self.structure.locate(ref)
        if key is None:
            return None
        if key in self.changes:
            return self.changes[key]
        return self.state.read(key)

    def set(self, ref, stack):
        self.changes[self.structure.locate(ref)] = Items.normalize(stack)
        if self._derived:
            self._derived.clear()

    def derivedOf(self, name):
        """
        算出的集合 name 现在的全部格子 {下标: 物品堆}（部件的 derive，按工作副本当前的内容与每位查看者状态算）：一样的输入只算
        一次，改了格子、每位查看者状态变了就重算（一格一格地读时不再每格把整个集合算一遍）。
        """
        viewer = self.state.viewer
        cached = self._derived.get(name)
        if cached is not None and cached[0] == viewer:
            return cached[1]
        values = self.structure.derivers[name].derive(name, self.get, viewer) or {}
        self._derived[name] = (dict(viewer) if viewer is not None else None, values)
        return values

    def _read(self, key):
        return self.changes[key] if key in self.changes else self.state.read(key)

    def highestUsed(self, cid):
        """不设上限的容器里最后一个非空格（算上工作副本里的改动）。"""
        top = self.state.highestUsed(cid)
        for (container, index), stack in self.changes.items():
            if container == cid and stack is not None and index > top:
                top = index
        while top >= 0 and Items.isEmpty(self._read((cid, top))):
            top -= 1
        return top

    # ---------------------------------------------------------------- 格数与规矩

    def collection(self, ref):
        return self.structure.collections.get(ref[0])

    def size(self, name, extraTop=-1):
        """集合现在有几格：有格数的就是格数；不设上限的由格数策略按最后一个非空格算（extraTop 当作也放了东西）。"""
        collection = self.structure.collections.get(name)
        if collection is None:
            return 0
        if collection.size is not None:
            return collection.size
        top = max(self.highestUsed(collection.cid) - collection.offset, extraTop)
        return collection.sizer.visibleCount(top)

    def exists(self, ref):
        return 0 <= ref[1] < self.size(ref[0])

    def active(self, name):
        """集合 name 现在启用着：不在关着的面板里（停用的集合不收不出，快速转移与双击收集也不碰它）。"""
        closed = self._closed
        if closed is None:
            closed = self._closed = self.state.closedCollections()
        return name not in closed

    def locked(self, ref):
        """ref 是锁住的格子（不收不出，数字键换不走、丢不出）。"""
        cells = self._locked
        if cells is None:
            cells = self._locked = self.state.lockedCells()
        return bool(cells) and self.structure.locate(ref) in cells

    def canPlace(self, ref, stack, checkExists=True):
        """
        普通操作能不能往 ref 放 stack 这种东西（不看数量与空间）。checkExists 为假时不看 ref 现在显示没显示出来。
        内容来自界面数据的格子不放真东西，普通操作不往里放。
        """
        collection = self.collection(ref)
        if collection is None or (checkExists and not self.exists(ref)) or not self.active(ref[0]) \
                or self.locked(ref) or ref[0] in self.structure.dataBacked:
            return False
        return collection.slot.mayPlace(self, ref, stack)

    def canLeave(self, ref, stack):
        collection = self.collection(ref)
        if collection is None or not self.active(ref[0]) or self.locked(ref) \
                or ref[0] in self.structure.dataBacked or not collection.slot.mayTake(self, ref, stack):
            return False
        return self.state.canLeave(ref, stack)

    def placeable(self, ref):
        """ref 这一格现在显示着、启用着、没锁住（专门的操作往幽灵格、来源格写东西之前看它，不问格子类型收不收）。"""
        return self.exists(ref) and self.active(ref[0]) and not self.locked(ref)

    def limit(self, ref, stack):
        """ref 这一格最多放几个 stack 那种东西：由格子类型定（缺省是物品的堆叠数）。"""
        return self.collection(ref).slot.capacity(self, ref, stack)

    def room(self, ref, stack):
        """ref 里还能再放多少个 stack 那种东西（放不进去为 0）。"""
        if not self.canPlace(ref, stack):
            return 0
        return self.space(ref, stack)

    def space(self, ref, stack):
        """只看数量：ref 现在的内容旁边还容得下几个 stack 那种东西（不看这一格收不收）。"""
        target = self.get(ref)
        if Items.isEmpty(target):
            return self.limit(ref, stack)
        if not self.rules.canStack(target, stack):
            return 0
        return max(0, self.limit(ref, target) - Items.count(target))

    def fits(self, ref, stack):
        """整堆 stack 能不能原样放进 ref（交换时用：不看 ref 里现在有什么）。"""
        return self.canPlace(ref, stack) and Items.count(stack) <= self.limit(ref, stack)

    def same(self, a, b):
        """两个格子是不是同一个容器格（快捷栏第 2 格与合并背包第 2 格是同一格）。"""
        return self.key(a) == self.key(b)


# ---------------------------------------------------------------- 搬运


def transfer(ws, src, dst, amount):
    """从 src 搬 amount 个到 dst（dst 为空或同种且放得下）。返回实际搬了几个。"""
    stack = ws.get(src)
    if Items.isEmpty(stack) or amount <= 0 or not ws.canLeave(src, stack):
        return 0
    moved = min(amount, Items.count(stack), ws.room(dst, stack))
    if moved <= 0:
        return 0
    target = ws.get(dst)
    base = Items.count(target) if not Items.isEmpty(target) else 0
    ws.set(dst, Items.withCount(stack if Items.isEmpty(target) else target, base + moved))
    ws.set(src, Items.withCount(stack, Items.count(stack) - moved))
    return moved


def swap(ws, a, b):
    """整堆交换。完全相同的两堆不换（返回 False）。"""
    sa, sb = ws.get(a), ws.get(b)
    if ws.rules.identical(sa, sb):
        return False
    if not Items.isEmpty(sa) and (not ws.canLeave(a, sa) or not ws.fits(b, sa)):
        return False
    if not Items.isEmpty(sb) and (not ws.canLeave(b, sb) or not ws.fits(a, sb)):
        return False
    ws.set(a, sb)
    ws.set(b, sa)
    return True


def placeAll(ws, src, dst):
    """放下整堆：dst 空就搬过去，同种有空间就合并（放不下的留在 src），满了或不同种就交换。"""
    stack, target = ws.get(src), ws.get(dst)
    if Items.isEmpty(stack):
        return False
    if Items.isEmpty(target):
        return transfer(ws, src, dst, Items.count(stack)) > 0
    if ws.rules.canStack(target, stack) and ws.room(dst, stack) > 0:
        return transfer(ws, src, dst, Items.count(stack)) > 0
    return swap(ws, src, dst)


def fill(ws, name, src, remaining, exclude=None):
    """
    把 src 里的 remaining 个按快速转移的规矩放进集合 name：先按格序补满已有的同种堆，再按格序填空格。
    返回放不下的个数。
    """
    remaining = topUp(ws, name, src, remaining, exclude)
    return fillEmpty(ws, name, src, remaining, exclude)


def topUp(ws, name, src, remaining, exclude=None):
    """按格序补满集合 name 里已有的同种堆，返回放不下的个数。exclude 是不算在内的那一格（按容器格比）。"""
    stack = ws.get(src)
    skip = ws.key(exclude) if exclude is not None else None
    for index in range(ws.size(name)):
        if remaining <= 0:
            return 0
        ref = (name, index)
        if skip is not None and ws.key(ref) == skip:
            continue
        target = ws.get(ref)
        if not Items.isEmpty(target) and ws.rules.canStack(target, stack):
            remaining -= transfer(ws, src, ref, remaining)
    return remaining


def fillEmpty(ws, name, src, remaining, exclude=None):
    """
    按格序把剩下的放进集合 name 的空格，返回放不下的个数。格数随内容增长的集合（例如"已用 + 1"）
    每放进一格都重新算格数，所以能一路往后放。
    """
    skip = ws.key(exclude) if exclude is not None else None
    index = 0
    while remaining > 0 and index < ws.size(name):
        ref = (name, index)
        if (skip is None or ws.key(ref) != skip) and Items.isEmpty(ws.get(ref)):
            remaining -= transfer(ws, src, ref, remaining)
        index += 1
    return remaining


def addTo(ws, ref, stack, amount):
    """往 ref（空格或同种）里凭空加最多 amount 个 stack 那种东西，返回加了几个（以这一格的空间为限）。"""
    put = min(ws.space(ref, stack), amount)
    if put <= 0:
        return 0
    target = ws.get(ref)
    base = 0 if Items.isEmpty(target) else Items.count(target)
    ws.set(ref, Items.withCount(stack if Items.isEmpty(target) else target, base + put))
    return put


def insertInto(ws, name, stack, amount=None):
    """
    把 amount 个（None 为整堆）stack 那种东西凭空放进集合 name：先按格序补同种堆、再按格序填空格。
    返回放不下的个数（由调用方决定放到别处还是丢出）。合成的产物、附带产物用它放进背包。
    """
    left = Items.count(stack) if amount is None else amount
    for wantEmpty in (False, True):
        for index in range(ws.size(name)):
            if left <= 0:
                break
            ref = (name, index)
            target = ws.get(ref)
            if Items.isEmpty(target) != wantEmpty or not ws.canPlace(ref, stack):
                continue
            if not wantEmpty and not ws.rules.canStack(target, stack):
                continue
            left -= addTo(ws, ref, stack, left)
    return left


def fitsIn(ws, name, stack):
    """整份 stack 能不能放进集合 name（补同种、填空格）。"""
    amount = Items.count(stack)
    for index in range(ws.size(name)):
        ref = (name, index)
        if ws.canPlace(ref, stack):
            amount -= ws.space(ref, stack)
            if amount <= 0:
                return True
    return False


# ---------------------------------------------------------------- 关闭界面


def returnCursor(ws):
    """关闭界面时手持物退回背包：先补已有的同种堆、再填空格，都从快捷栏 0 号起；放不下的丢在脚下。"""
    stack = ws.get(CURSOR_REF)
    if Items.isEmpty(stack):
        return False
    remaining = fill(ws, COMBINED, CURSOR_REF, Items.count(stack))
    if remaining > 0:
        ws.drops.append(Items.withCount(stack, remaining))
        ws.set(CURSOR_REF, None)
    return True


def returnItems(ws, containers):
    """
    关闭界面时把容器 containers（容器名的列表，例如玩家临时格：工作台的合成格、铁砧的输入）里的东西退回背包：
    只退放真东西的格子（格子类型的 returnsOnClose），按集合的声明顺序、集合内按格序，同一段容器格只退一次；
    每一格先补已有的同种堆、再填空格，都从快捷栏 0 号起；放不下的丢在脚下。返回退回了没有。
    """
    returned = False
    for collection in _returning(ws.structure, containers):
        for index in range(collection.size):
            ref = (collection.name, index)
            stack = ws.get(ref)
            if Items.isEmpty(stack):
                continue
            returned = True
            remaining = fill(ws, COMBINED, ref, Items.count(stack))
            if remaining > 0:
                ws.drops.append(Items.withCount(stack, remaining))
                ws.set(ref, None)
    return returned


def _returning(structure, containers):
    seen, out = set(), []
    for collection in structure.collections.values():
        if collection.cid in containers and collection.slot.returnsOnClose:
            key = (collection.cid, collection.offset, collection.size)
            if key not in seen:
                seen.add(key)
                out.append(collection)
    return out
