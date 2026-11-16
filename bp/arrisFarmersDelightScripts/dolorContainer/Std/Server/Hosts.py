# -*- coding: utf-8 -*-
"""
标准库：常用的宿主与机器的时钟（docs/ARCHITECTURE.md 第 3.1、3.13 节；接口见 Server/Hosts.py）。只在服务端用。

- Player：按玩家存放。实例键是玩家 ID，数据存在玩家实体上、跟着玩家存档；机器在那位玩家在线时走。
- World：按世界存放。实例键由打开方给出（方块坐标、编号这类），数据存在世界上；给了 clock=ALWAYS 时能放机器，一直走。
- Item：按物品存放。实例键是物品上记的编号（第一次打开时写上，记在附加数据的哪一项可以指定），数据存在世界上；
  手持绑定的物品使用时打开；物品不能放进它自己里面；机器在那件物品带在某位在线玩家身上时走。界面开着时那件物品所在的格子锁住，
  那件物品离开那一格（被命令清掉、被别的模组拿走）时界面关上。物品在哪里找（places）：缺省是主手与背包 36 格，加上
  身上穿戴的（WORN：盔甲 4 格与副手）就也找盔甲位、副手（穿在胸甲位的背包）；模组自己的饰品栏改写 stacksAt / readAt / writeAt
  并在改了时调 CARRIED.changed。位置一律写成 (容器种类, 格)，锁的就是那一格。
- InItem：物品内存放（潜影盒式）。与 Item 一样绑物品名、手持使用时打开、锁住那一格，但内容写在那件物品的附加数据里，
  跟着物品走（丢出再捡起、交给别人、带去别的存档都还在），每次操作写回那件物品；不能放机器。
- Transient：不存。实例键是玩家 ID，界面模型不能有实例存储（便携工作台这类，格子都在玩家临时格上）。
每种都收 access（谁能打开的规矩，见 Std/Server/Access.py）与 visitors（为真时不查游戏的规矩，见 Server/Hosts.Host），
例如 Hosts.World(access=Access.Policy())、Hosts.Transient(visitors=True)。

存储键与以前的存放范围完全一样（按玩家、不存：存储键本身；按世界、按物品：存储键@实例键；物品内存放：存储键本身，
在那件物品的附加数据里），已有存档照常读。
引擎在用到时才导入（离线测试不碰引擎）。
"""
import ast
import uuid
import zlib

from ... import HOST
from ...Common import Items
from ...Common.Collections import PLAYER_KIND, PLAYER_SIZE
from ...Server import Storage
from ...Server.Hosts import Clock, Host
from ..Containers import WORN, WORN_OFFHAND, WORN_SIZE
from . import Containers as WornSlots

_EVENTS = object()   # 动态监听的名字空间：QuModLibs 按（名字空间，函数名）给监听起名、引擎按名字回调，不带名字空间时
                     # 同一个模组里同名的处理函数（库里的、使用方的）会串成一个
ITEM_ID_KEY = "dc_uid"    # 按物品存放时物品附加数据里记编号的键（NBT 字符串），物品宿主没指定别的键时用它
NBT_STRING = 8            # 附加数据里字符串的 NBT 类型

try:
    _TEXT = (str, unicode)  # noqa: F821
except NameError:
    _TEXT = (str,)


def _engine():
    from ...Server import Engine
    return Engine


def itemUid(stack, key=ITEM_ID_KEY):
    """物品上记的实例编号（附加数据里 key 那一项，按物品存放的容器），没有时为 None。"""
    return userText(stack, key) or None


def userText(stack, key):
    """物品附加数据里 key 那一项的字符串（引擎读出的带类型的写法与直接的值都认），没有、不是字符串时为 None。"""
    user = stack.get("userData") if stack else None
    value = user.get(key) if isinstance(user, dict) else None
    if isinstance(value, dict):
        value = value.get("__value__")
    if not isinstance(value, _TEXT):
        return None
    return value if isinstance(value, str) else value.encode("utf-8")


# ---------------------------------------------------------------- 时钟


class Online(Clock):
    """玩家在线时走（按玩家存放的机器）。"""

    def __init__(self):
        self.types = []

    def attach(self, manager, containerType):
        self.types.append(containerType.typeId)
        for playerId in manager.players():
            manager.machines.resume((containerType.typeId, playerId))

    def playerJoined(self, manager, playerId):
        for typeId in self.types:
            manager.machines.resume((typeId, playerId))

    def playerLeft(self, manager, playerId):
        for typeId in self.types:
            manager.machines.pause((typeId, playerId))


class CarriedTracker(object):
    """
    哪些按物品存放的机器现在带在玩家身上。身上格子的变化接进来：slotChanged（一格变了，格是 (容器种类, 格) 或别的能做键的
    东西，给变化后的物品，要带附加数据）、playerJoined（进游戏时身上的格子：{格: 物品堆}，或背包 36 格的列表）、playerLeft。
    同一件（同一个编号）在几格里、几位玩家身上时，只要还在一格里时钟就走。
    handleOf(物品堆) -> (类型, 实例键) 或 None：这一堆是不是要跟踪的机器。
    """

    def __init__(self, machines, handleOf):
        self.machines = machines
        self.handleOf = handleOf
        self._slots = {}    # 玩家 -> {格: (类型, 实例键)}
        self._counts = {}   # (类型, 实例键) -> 在几格里

    def slotChanged(self, playerId, slot, stack):
        handle = self.handleOf(stack)
        slots = self._slots.setdefault(playerId, {})
        old = slots.get(slot)
        if old == handle:
            return
        if handle is None:
            slots.pop(slot, None)
        else:
            slots[slot] = handle
            self._add(handle)
        if old is not None:
            self._remove(old)

    def playerJoined(self, playerId, inventory):
        entries = inventory.items() if isinstance(inventory, dict) else enumerate(inventory)
        for slot, stack in entries:
            self.slotChanged(playerId, slot, stack)

    def playerLeft(self, playerId):
        for handle in list((self._slots.pop(playerId, None) or {}).values()):
            self._remove(handle)

    def carriedBy(self, playerId):
        return set((self._slots.get(playerId) or {}).values())

    def holds(self, playerId, slot):
        """这一格现在有要跟踪的机器没有。"""
        return slot in (self._slots.get(playerId) or ())

    def _add(self, handle):
        self._counts[handle] = self._counts.get(handle, 0) + 1
        if self._counts[handle] == 1:
            self.machines.resume(handle)

    def _remove(self, handle):
        count = self._counts.get(handle, 0) - 1
        if count > 0:
            self._counts[handle] = count
            return
        self._counts.pop(handle, None)
        self.machines.pause(handle)


class Carried(Clock):
    """
    那件物品带在某位在线玩家身上时走（按物品存放的机器）：背包 36 格，宿主的 places 有身上穿戴的（WORN）时还有盔甲位与副手。
    第一次接上机器时开始跟踪这些格子的变化（变化事件带上附加数据，只看绑定的物品名），在线玩家身上先对一遍。模组自己的
    饰品栏改了时调 changed(玩家, (容器种类, 格), 物品堆)。
    """

    def __init__(self):
        self.types = {}      # 物品名 -> (容器类型编号, 物品附加数据里记编号的那一项)
        self.tracker = None
        self.worn = False    # 也跟踪盔甲位与副手（有宿主的 places 带 WORN）
        self._wornListened = False

    def bind(self, containerType):
        """记下这种机器绑定的物品与记编号的那一项、要不要跟踪身上穿戴的（不碰引擎）。"""
        host = containerType.host
        for name in host.items:
            self.types[name] = (containerType.typeId, host.idKey)
        if WORN in getattr(host, "places", ()):
            self.worn = True

    def changed(self, playerId, place, stack):
        """
        玩家身上一格变了（place 是 (容器种类, 格)，stack 是变化后的、带附加数据）：时钟跟着那件物品在不在身上走。不是绑定的
        物品、那一格原来也没有要跟踪的时什么都不做（背包一变就报，先看物品名再规整）。
        """
        tracker = self.tracker
        if tracker is None:
            return
        if (not stack or stack.get("newItemName") not in self.types) and not tracker.holds(playerId, place):
            return
        tracker.slotChanged(playerId, place, Items.normalize(stack))

    def carriedStacks(self, playerId):
        """这位玩家身上要对一遍的格子：{(容器种类, 格): 物品堆}（背包 36 格，跟踪身上穿戴的时加上盔甲位与副手）。"""
        stacks = dict(((PLAYER_KIND, index), stack)
                      for index, stack in enumerate(_engine().PlayerInventory(playerId).read()))
        if self.worn:
            stacks.update(((WORN, index), WornSlots.ENGINE.worn(playerId, index)) for index in range(WORN_SIZE))
        return stacks

    def handleOf(self, stack):
        bound = self.types.get(stack.get("newItemName")) if stack else None
        uid = itemUid(stack, bound[1]) if bound is not None else None
        return (bound[0], uid) if uid else None

    def attach(self, manager, containerType):
        self.bind(containerType)
        if self.tracker is None:
            self.tracker = CarriedTracker(manager.machines, self.handleOf)
            _listenInventory()
        if self.worn and not self._wornListened:
            self._wornListened = True
            _listenWorn()
        for playerId in manager.players():
            self.tracker.playerJoined(playerId, self.carriedStacks(playerId))

    def playerJoined(self, manager, playerId):
        if self.tracker is not None:
            self.tracker.playerJoined(playerId, self.carriedStacks(playerId))

    def playerLeft(self, manager, playerId):
        if self.tracker is not None:
            self.tracker.playerLeft(playerId)


SAVE_SECONDS = 10.0   # 在场的机器每这么久（现实时间）推进一次并存档：服务器关掉、崩溃时最多少算这一段
ADVANCE_STEPS = 10    # 定期推进分成这么多批，每 SAVE_SECONDS / ADVANCE_STEPS 推一批（不一下子推全部）


class TrackedClock(Clock):
    """
    记着机器实例的时钟（方块的区块加载、实体存活、一直）的基类：机器实例打开过就记下（按容器类型存在世界上，跨存档），
    present(handle) 为真（在场）时走。离场时（区块要卸载、实体要离开）读不了实例，不推进，只记下走过还没推进的刻数，
    回到场上时一并算上（这些刻数也存在世界上：离场期间服务器关了，下次回到场上照样补上）。在场的每 SAVE_SECONDS 推进一次
    并存档（分成 ADVANCE_STEPS 批轮流推，每台各在自己那一批），最后一位玩家离开时（单人游戏关存档）也推进一次；服务器崩溃
    最多少算一段。宿主没了（Service.discard）时忘掉。
    子类给出 present，并在在场与离场时调用 arrive / leave；start 在第一次接上机器时调用（开始监听事件）；group 给出按什么
    分组（方块按区块），事件里用 handlesIn 找一组。一个事件里有许多台一起到场、离场时，在 hold() 与 flush() 之间做：记下的
    刻数最后一起存一次。
    """

    def __init__(self):
        self.manager = None
        self.types = []
        self.known = {}       # (类型, 实例键) -> 离场时走过还没推进的刻数（在场时为 0）
        self.running = set()
        self.groups = {}      # 分组 -> 这一组的 (类型, 实例键)
        self._timer = None
        self._holding = 0     # hold 的层数：大于 0 时存档先记着（_unsaved），flush 时一起写
        self._unsaved = set()
        self._turn = 0        # 分批推进轮到第几批

    def present(self, handle):
        """机器实例现在在场没有（区块加载着、实体在世界里）。"""
        return True

    def group(self, handle):
        """按什么分组（方块按所在的区块）；不分组时为 None。"""
        return None

    def handlesIn(self, group):
        return list(self.groups.get(group, ()))

    def _remember(self, handle, elapsed):
        self.known[handle] = elapsed
        group = self.group(handle)
        if group is not None:
            self.groups.setdefault(group, set()).add(handle)

    def _forget(self, handle):
        del self.known[handle]
        group = self.group(handle)
        members = self.groups.get(group)
        if members is not None:
            members.discard(handle)
            if not members:
                del self.groups[group]

    def start(self):
        """第一次接上机器：开始监听在场与离场的事件。"""

    def attach(self, manager, containerType):
        self.manager = manager
        typeId = containerType.typeId
        if typeId in self.types:
            return
        self.types.append(typeId)
        if len(self.types) == 1:
            self.start()
            self._timer = _engine().addRepeatedTimer(SAVE_SECONDS / ADVANCE_STEPS, self.advanceSome)
        handles = []
        for key, elapsed in sorted(literal(_engine().levelBackend().get(self._storageKey(typeId)), {}).items()):
            handles.append((typeId, key))
            self._remember(handles[-1], max(0, int(elapsed)))
        self.hold()
        try:
            for handle in handles:   # 都记下了再接着走（接着走时把这一种存一遍：一起存一次）
                if self.present(handle):
                    self.arrive(handle)
        finally:
            self.flush()

    def track(self, manager, handle):
        if handle[0] not in self.types:
            return
        if handle not in self.known:
            self._remember(handle, 0)
            self._save(handle[0])
        if handle not in self.running and self.present(handle):
            self.arrive(handle)

    def untrack(self, manager, handle):
        if handle not in self.known:
            return
        self._forget(handle)
        self.running.discard(handle)
        manager.machines.suspend(handle)
        self._save(handle[0])

    def arrive(self, handle):
        """机器实例回到场上：接着走，离场时记下的刻数一并算上。"""
        if handle not in self.known or handle in self.running:
            return
        self.running.add(handle)
        elapsed = self.known[handle]
        if elapsed:
            self.known[handle] = 0
            self._save(handle[0])
        self.manager.machines.resume(handle, elapsed)

    def leave(self, handle):
        """机器实例离场（区块要卸载、实体要离开，这时读不了它）：停下，记下走过还没推进的刻数。"""
        if handle not in self.running:
            return
        self.running.discard(handle)
        elapsed = self.manager.machines.suspend(handle) or 0
        self.known[handle] = self.known.get(handle, 0) + elapsed
        if elapsed:
            self._save(handle[0])

    def advanceAll(self):
        """在场的都推进到现在、存下来。"""
        if self.manager is not None:
            for handle in sorted(self.running):
                self.manager.machines.advance(handle)

    def advanceSome(self):
        """定期推进的一批（每 SAVE_SECONDS / ADVANCE_STEPS 一次）：在场的里轮到这一批的推进到现在、存下来。"""
        turn, self._turn = self._turn % ADVANCE_STEPS, self._turn + 1
        if self.manager is not None:
            for handle in sorted(self.running):
                if batchOf(handle) == turn:
                    self.manager.machines.advance(handle)

    def hold(self):
        """开始一批：之后的存档先记着，flush 时一起写（可以套着调）。"""
        self._holding += 1

    def flush(self):
        """结束一批（最外面一层）：记着要存的种类一起写。"""
        self._holding = max(0, self._holding - 1)
        if self._holding or not self._unsaved:
            return
        unsaved, self._unsaved = sorted(self._unsaved), set()
        self._write(unsaved)

    def playerLeft(self, manager, playerId):
        if manager.players() == [playerId]:
            self.advanceAll()   # 最后一位玩家要走（单人游戏关存档）

    def _storageKey(self, typeId):
        return "dolor_container:%s:clock@%s" % (HOST, typeId)

    def _save(self, typeId):
        if self._holding:
            self._unsaved.add(typeId)
        else:
            self._write([typeId])

    def _write(self, typeIds):
        backend = _engine().levelBackend()
        for typeId in typeIds:
            mine = dict((key, elapsed) for (kind, key), elapsed in self.known.items() if kind == typeId)
            if mine:
                backend.set(self._storageKey(typeId), repr(mine))
            else:
                backend.delete(self._storageKey(typeId))
        backend.save()


def batchOf(handle):
    """机器实例分在定期推进的哪一批（0 到 ADVANCE_STEPS - 1；每次运行都一样）。"""
    return (zlib.crc32(repr(tuple(handle)).encode("utf-8")) & 0xffffffff) % ADVANCE_STEPS


class Always(TrackedClock):
    """一直走（按世界存放的机器：Hosts.World(clock=ALWAYS)）：服务器开着就走，关掉期间不算。"""


OPEN = "open"     # 方块、实体宿主的 use 的结果：打开容器
BLOCK = "block"   # 拦下：不打开，手里的东西也不用出去
PASS = "pass"     # 放过：不打开，照常（原版方块自己的交互、手里的东西照常用出去）


def verdict(answer):
    """宿主的 use 的返回值规整成 OPEN / BLOCK / PASS：真为打开，假与 None 为拦下。"""
    if answer in (OPEN, BLOCK, PASS):
        return answer
    return OPEN if answer is True else BLOCK


class Watchers(object):
    """
    宿主的失效事件要通知的函数（Host.watch 记下的）：实例键 -> 函数。一个宿主服务几个容器类型时同一个键可以有几个实例
    有人看着，各记各的，失效时都调用。
    """

    def __init__(self):
        self._byKey = {}

    def add(self, key, onInvalid):
        """记下 onInvalid；返回不再盯着时调用的函数（Host.watch 的返回值）。"""
        self._byKey.setdefault(key, []).append(onInvalid)
        return lambda: self._remove(key, onInvalid)

    def _remove(self, key, onInvalid):
        functions = self._byKey.get(key)
        if functions is not None and onInvalid in functions:
            functions.remove(onInvalid)
            if not functions:
                del self._byKey[key]

    def fire(self, key):
        """实例键 key 失效了：调用记着的函数（调用时可能撤掉自己）。"""
        functions = self._byKey.get(key)
        if functions:
            for onInvalid in list(functions):
                onInvalid()

    def __contains__(self, key):
        return key in self._byKey

    def __len__(self):
        return len(self._byKey)


def literal(text, empty):
    """存的文字（repr 写的）读回成 empty 那种类型（字典、列表）；没有、读不了、类型不对时是 empty。"""
    if not text:
        return empty
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return empty
    return value if isinstance(value, type(empty)) else empty


ONLINE = Online()
CARRIED = Carried()
ALWAYS = Always()


def _listenInventory():
    import mod.server.extraServerApi as serverApi
    from ....QuModLibs.Server import ListenForEvent
    serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId()).GetUserDataInEvent(
        "InventoryItemChangedServerEvent")
    ListenForEvent("InventoryItemChangedServerEvent", _EVENTS, _onCarriedChanged)


def _listenWorn():
    """盔甲位与副手的变化事件（带上附加数据）：有物品宿主的 places 带身上穿戴的才听。"""
    import mod.server.extraServerApi as serverApi
    from ....QuModLibs.Server import ListenForEvent
    item = serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId())
    for name, handler in (("OnNewArmorExchangeServerEvent", _onArmorChanged),
                          ("OnOffhandItemChangedServerEvent", _onOffhandChanged)):
        item.GetUserDataInEvent(name)
        ListenForEvent(name, _EVENTS, handler)


def _onCarriedChanged(args):
    """背包一格变了（事件在变之前发，带着变化后的物品）。"""
    playerId, slot = args.get("playerId"), args.get("slot")
    if playerId and isinstance(slot, int):
        CARRIED.changed(playerId, (PLAYER_KIND, slot), args.get("newItemDict"))


def _onArmorChanged(args):
    """盔甲位一格换了。"""
    playerId, slot = args.get("playerId"), args.get("slot")
    if playerId and isinstance(slot, int) and 0 <= slot < WORN_OFFHAND:
        CARRIED.changed(playerId, (WORN, slot), args.get("newArmorDict"))


def _onOffhandChanged(args):
    """副手换了。"""
    if args.get("playerId"):
        CARRIED.changed(args.get("playerId"), (WORN, WORN_OFFHAND), args.get("newItemDict"))


# ---------------------------------------------------------------- 宿主


class Player(Host):
    """按玩家存放（见模块说明）。"""

    clock = ONLINE

    def keyFor(self, playerId, key):
        return key if key is not None else playerId

    def backend(self, key):
        return _engine().ExtraDataBackend(key)

    def forgetsOnLeave(self, playerId, key):
        """这位玩家离开时，放在他身上的实例不再留着（再进来时从他的数据重读）。"""
        return key == playerId

    def save(self, backend):
        """数据就在玩家实体上，会话存档时与玩家数据一起存。"""


class World(Host):
    """按世界存放（见模块说明）。clock 给 ALWAYS 时能放机器、一直走。"""

    def __init__(self, access=None, visitors=False, clock=None):
        Host.__init__(self, access, visitors)
        if clock is not None:
            self.clock = clock

    def keyFor(self, playerId, key):
        return key

    def backend(self, key):
        return _engine().levelBackend()

    def prefix(self, storageKey, key):
        return "%s@%s" % (storageKey, key)


class Item(World):
    """
    按物品存放（见模块说明）。items 是绑定的物品名；idKey 是物品附加数据里记编号的那一项（缺省 dc_uid）。
    使用方以前已经用自己的键给物品记了编号、内容按"存储键@编号"存在世界上的，传那个键：已有的物品与存档照常认。
    places 是找那件物品的地方（容器种类，按先后找；缺省类属性：玩家背包，主手那一格最先看）：给 (PLAYER_KIND, WORN) 就也找
    盔甲位与副手。找、读、写、锁、写编号都经下面的方法（位置写成 (容器种类, 格)），模组自己的地方改写 stacksAt / readAt /
    writeAt。
    """

    clock = CARRIED
    places = (PLAYER_KIND,)

    def __init__(self, items, idKey=ITEM_ID_KEY, access=None, visitors=False, places=None):
        if not items:
            raise ValueError("an item host needs the bound item names")
        if not isinstance(idKey, _TEXT) or not idKey:
            raise ValueError("an item host needs a non-empty id key")
        World.__init__(self, access, visitors)
        self.items = tuple(items)
        self.idKey = idKey
        if places is not None:
            self.places = tuple(places)
        self._places = {}   # (玩家, 实例键) -> 打开时那件物品所在的位置（锁住的那一格）

    def keyFor(self, playerId, key):
        """打开方没给实例键时用手上那件（heldPlace）绑定物品的编号，还没有编号就先写上一个。"""
        if key is not None:
            return key
        place = self.heldPlace(playerId)
        stack = self.readAt(playerId, place) if place is not None else None
        if not stack or stack.get("newItemName") not in self.items:
            return None
        return itemUid(stack, self.idKey) or self.tag(playerId, place, stack)

    def accepts(self, key, stack):
        return itemUid(stack, self.idKey) != key

    def heldPlace(self, playerId):
        """手上那一格的位置（缺省主手：背包的选中格）；取不到时为 None。"""
        selected = _engine().selectedSlot(playerId)
        return (PLAYER_KIND, selected) if 0 <= selected < 9 else None

    def locate(self, playerId, key):
        """
        那件物品（附加数据里记着这个编号）在这位玩家身上的哪里：(容器种类, 格)；先看手上那一格，再按 places 的先后找；
        不在时为 None。
        """
        held = self.heldPlace(playerId)
        if held is not None and held[0] in self.places and itemUid(self.readAt(playerId, held), self.idKey) == key:
            return held
        for kind in self.places:
            for index, stack in enumerate(self.stacksAt(playerId, kind)):
                if itemUid(stack, self.idKey) == key:
                    return (kind, index)
        return None

    def stacksAt(self, playerId, kind):
        """一个地方的全部格子（找那件物品用）：玩家背包 36 格、身上穿戴的 5 格（盔甲 4 格与副手）；别的为空。"""
        if kind == PLAYER_KIND:
            return _engine().PlayerInventory(playerId).read()
        if kind == WORN:
            return [WornSlots.ENGINE.worn(playerId, index) for index in range(WORN_SIZE)]
        return []

    def readAt(self, playerId, place):
        """位置 place 那一格现在的物品（带附加数据）；读不了时为 None。"""
        kind, index = place
        if kind == PLAYER_KIND and 0 <= index < PLAYER_SIZE:
            return _engine().inventorySlot(playerId, index)
        if kind == WORN and 0 <= index < WORN_SIZE:
            return WornSlots.ENGINE.worn(playerId, index)
        return None

    def writeAt(self, playerId, place, stack):
        """把 stack 写进位置 place 那一格，返回写完读回的（核对用）；写不了时为 None。"""
        kind, index = place
        if kind == PLAYER_KIND and 0 <= index < PLAYER_SIZE:
            return _engine().PlayerInventory(playerId).write({index: stack}).get(index)
        if kind == WORN and 0 <= index < WORN_SIZE:
            WornSlots.ENGINE.setWorn(playerId, index, stack)
            return WornSlots.ENGINE.worn(playerId, index)
        return None

    def tag(self, playerId, place, stack):
        """给 place 那一件写上新的编号（附加数据的 idKey），返回编号；写不进去时为 None。主手那一件经引擎换掉手上的。"""
        if place == self.heldPlace(playerId) and place[0] == PLAYER_KIND:
            return _engine().tagHeld(playerId, stack, self.idKey)
        uid = uuid.uuid4().hex
        user = dict(stack.get("userData") or {})
        user[self.idKey] = {"__type__": NBT_STRING, "__value__": uid}
        return uid if itemUid(self.writeAt(playerId, place, dict(stack, userData=user)), self.idKey) == uid else None

    def lockedCells(self, playerId, key):
        """那件物品所在的那一格（locate）；不在这位玩家身上时不锁。"""
        place = self.locate(playerId, key)
        if place is None:
            self._places.pop((playerId, key), None)
            return []
        self._places[(playerId, key)] = place
        return [place]

    def stillValid(self, playerId, key):
        """那件物品还在锁住的那一格（每刻读这一格）；打开时它不在这位玩家身上的不查。"""
        place = self._places.get((playerId, key))
        return place is None or itemUid(self.readAt(playerId, place), self.idKey) == key

    def onViewers(self, key, viewers):
        """不再看着的玩家：忘掉那位玩家锁住的那一格。"""
        for entry in [entry for entry in self._places if entry[1] == key and entry[0] not in viewers]:
            del self._places[entry]


class InItem(Item):
    """
    物品内存放（潜影盒式，见模块说明）。实例键照样是物品上记的编号（认出是哪一件、挡住放进它自己里面），内容在那件物品的
    附加数据里（ItemBackend）。打开时那件物品要在这位玩家身上（places）：手上那件，或打开方给的编号对得上的那件。
    同一个编号（创造模式复制出来的）同一时间只给一位玩家开；实例没人看时不留在最近用过的里（物品会被复制、被别处改，
    下次打开重新从物品读）。内容越多，物品的附加数据越大，每次操作整件写回、同步给客户端：适合几十格以内的。
    """

    clock = None
    cacheable = False

    def __init__(self, items, idKey=ITEM_ID_KEY, access=None, visitors=False, places=None):
        Item.__init__(self, items, idKey, access, visitors, places)
        self._where = {}     # 实例键 -> (玩家, 位置)：打开时那件物品在哪
        self._viewing = {}   # 实例键 -> 看着它的玩家

    def keyFor(self, playerId, key):
        """手上那件（还没有编号就先写上），或打开方给的编号对得上的那件；别的玩家正看着同一个编号时不给。"""
        key = Item.keyFor(self, playerId, key)
        place = self.locate(playerId, key) if key is not None else None
        if place is None or self._viewing.get(key, playerId) != playerId:
            return None
        self._where[key] = (playerId, place)
        return key

    def where(self, key):
        """(玩家, 位置)：那件物品打开时在哪（位置是 (容器种类, 格)）；没在开的为 None。"""
        return self._where.get(key)

    def backend(self, key):
        return ItemBackend(self, key)

    def prefix(self, storageKey, key):
        return storageKey   # 后端就是这一件物品

    def onViewers(self, key, viewers):
        """
        记下谁在看。打开时记的位置不随没人看而忘掉：重开（Service.reopen）在没人看的那一下之后按同一个实例键重建实例，
        不再经 keyFor；位置每次打开都重记，留着的只是旧的一条。
        """
        Item.onViewers(self, key, viewers)
        if viewers:
            self._viewing[key] = viewers[0]
        else:
            self._viewing.pop(key, None)


class ItemBackend(Storage.Backend):
    """
    物品附加数据里的后端（InItem）：值存成那件物品附加数据里的 NBT 字符串。读写的是宿主记着的那一格（经宿主的 readAt /
    writeAt），那一格里已经不是那件物品（编号对不上）时读到 None、写不进去（记一行日志）。改动先记着，save() 时整件写回
    那一格：一次操作写一次。
    """

    def __init__(self, host, key):
        self.host = host
        self.key = key
        self._pending = {}   # 名字 -> 值（None 为删掉）

    def _found(self):
        """(玩家, 位置, 那件物品)；不在宿主记着的那一格里时为 None。"""
        where = self.host.where(self.key)
        stack = self.host.readAt(where[0], where[1]) if where is not None else None
        if stack is None or itemUid(stack, self.host.idKey) != self.key:
            return None
        return where[0], where[1], stack

    def get(self, key):
        if key in self._pending:
            return self._pending[key]
        found = self._found()
        return userText(found[2], key) if found is not None else None

    def set(self, key, value):
        self._pending[key] = value

    def delete(self, key):
        self._pending[key] = None

    def save(self):
        if not self._pending:
            return
        pending, self._pending = self._pending, {}
        found = self._found()
        if found is None:
            log("item %s left its slot before its contents were written back" % self.key)
            return
        playerId, place, stack = found
        user = dict(stack.get("userData") or {})
        for name, value in pending.items():
            if value is None:
                user.pop(name, None)
            else:
                user[name] = {"__type__": NBT_STRING, "__value__": value}
        wanted = dict(stack, userData=user)
        actual = self.host.writeAt(playerId, place, wanted)
        if not Items.sameKind(actual, wanted):
            log("cannot write the contents back into item %s" % self.key)


def log(message):
    """标准库记一行日志（带使用方的名字，几个模组各带一份库时分得清）。"""
    print("[dolorContainer:%s] %s" % (HOST, message))


class Transient(Host):
    """不存（见模块说明）。"""

    stores = False

    def keyFor(self, playerId, key):
        return key if key is not None else playerId

    def backend(self, key):
        return Storage.MemoryBackend()   # 只有玩家临时格，它们跟着手持物存在玩家数据里

    def save(self, backend):
        """内存里的，没有要存的。"""
