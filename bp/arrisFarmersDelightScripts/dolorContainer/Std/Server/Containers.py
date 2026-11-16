# -*- coding: utf-8 -*-
"""
标准库：常用容器种类在服务端的存法（docs/ARCHITECTURE.md 第 3.2 节；种类见 Std/Containers.py）。

- 玩家临时格（TEMPORARY）：会话保管，属于这位查看者；改了由会话存进玩家数据（服务器在界面开着时崩溃，下次进游戏退回），
  关界面时退回背包。
- 实例存储（STORAGE）：容器实例里的那一份（Server/Registry.ContainerInstance），所有查看者共用，改了推给其他查看者。
- 虚拟（VIRTUAL）：不放东西，只放算出的格子，内容不发给客户端（客户端自己算）。
- 身上穿戴的（WORN）：看界面的玩家自己的盔甲 4 格与副手，经引擎读写（EngineSlots：一次请求里读过的记住，写完重读核对，
  对不上整条撤回；每刻对一遍）。
  引擎在头这一格什么都收（整组也收），身、腿、脚只收部位对得上的盔甲，副手只收允许放副手的（盾、箭、烟花、地图、不死图腾、
  鹦鹉螺壳，整组也收）；别的写不进去。界面上收什么、一格几个由格子类型管（Parts/Inventory）。
- EngineSlots 是经引擎读写的格子的基类（实体装备、实体物品栏、方块自己的格子也用它，Std/Entity/Server.py、
  Std/Block/Server.py）。
引擎在用到时才导入；离线测试换掉 ENGINE（身上穿戴的读写）。
"""
from ...Common import Items
from ...Server import Containers as Kinds
from ...Server.Containers import Container, register, same
from ..Containers import STORAGE, TEMPORARY, VIRTUAL, WORN, WORN_OFFHAND, WORN_SIZE


class TemporaryContainer(Container):
    held = True
    returnsOnClose = True
    order = 2

    def __init__(self, session, spec):
        Container.__init__(self, session, spec)
        self.slots = {}

    def read(self, index):
        return self.slots.get(index)

    def items(self, start, end):
        return sorted((index, stack) for index, stack in self.slots.items() if start <= index < end)

    def write(self, changes):
        written = {}
        for index, stack in changes.items():
            old = self.slots.get(index)
            if not same(stack, old):
                written[index] = (old, stack)
        for index, (old, new) in written.items():
            if Items.isEmpty(new):
                self.slots.pop(index, None)
            else:
                self.slots[index] = new
        return written

    def heldStacks(self):
        return [self.slots[index] for index in sorted(self.slots) if not Items.isEmpty(self.slots[index])]

    def clear(self):
        self.slots.clear()

    def handOver(self):
        slots, self.slots = self.slots, {}
        return slots

    def takeOver(self, slots):
        self.slots = dict(slots)


class StorageContainer(Container):

    def __init__(self, session, spec):
        Container.__init__(self, session, spec)
        self.instance = session.instance
        self.cid = spec.cid

    def backing(self):
        return self.instance, self.cid

    def read(self, index):
        return self.instance.get(self.cid, index)

    def items(self, start, end):
        return self.instance.items(self.cid, start, end)

    def highestUsed(self):
        return self.instance.highestUsed(self.cid)

    def accepts(self, stack):
        return self.instance.accepts(stack)

    def write(self, changes):
        written = {}
        for index, stack in changes.items():
            old = self.instance.get(self.cid, index)
            if not same(stack, old):
                written[index] = (old, stack)
        for index, (old, new) in written.items():
            self.instance.set(self.cid, index, new)
        return written


class VirtualContainer(Container):
    synced = False


class EngineSlots(Container):
    """
    经引擎读写的格子（身上穿戴的、实体装备、实体物品栏、方块自己的格子）：一次请求里读过的格子记住（begin 时丢掉，同一格
    不重复向引擎读）；写完重读核对，对不上恢复原样、整条撤回；越界的整条撤回；每刻对一遍（不用记住的），与告诉过客户端的
    不同的推出去（别处改了：实体自己捡了东西、盔甲掉了耐久）。子类给 ownerOf(会话)（读写的是谁：实体编号、玩家、方块的位置）、
    sizeOf(谁, 容器说明)（有几格，缺省是类属性 size）与 getSlot(谁, 格) / setSlot(谁, 格, 物品堆)（向引擎读写一格）。
    """

    order = 0
    ticks = True
    size = 0
    shares = True   # 每刻对一遍时，同一刻里同一类、同一个主人的容器（几位玩家看着同一个方块、同一只实体）共用读到的格子；
                    # getSlot 不只看主人与格号的子类写 False

    def __init__(self, session, spec):
        Container.__init__(self, session, spec)
        self.owner = self.ownerOf(session)
        self.size = self.sizeOf(self.owner, spec)
        self.known = [None] * self.size
        self._cache = {}   # 这一次请求里读过的格子：下标 -> 物品堆

    def ownerOf(self, session):
        raise NotImplementedError

    def sizeOf(self, owner, spec):
        """有几格（缺省是类属性 size）。"""
        return self.size

    def getSlot(self, owner, index):
        raise NotImplementedError

    def setSlot(self, owner, index, stack):
        raise NotImplementedError

    def begin(self, everything=False):
        self._cache = {}

    def read(self, index):
        if not 0 <= index < self.size:
            return None
        cache = self._cache
        if index not in cache:
            cache[index] = self.getSlot(self.owner, index)
        return cache[index]

    def items(self, start, end):
        out = []
        for index in range(max(0, start), min(end, self.size)):
            stack = self.read(index)
            if stack:
                out.append((index, stack))
        return out

    def write(self, changes):
        if any(not 0 <= index < self.size for index in changes):
            return None
        written = {}
        for index, stack in changes.items():
            old = self.read(index)
            if not same(stack, old):
                written[index] = (old, stack)
        owner, cache = self.owner, self._cache
        for index, (old, new) in written.items():
            self.setSlot(owner, index, new)
        for index, (old, new) in written.items():
            cache[index] = actual = self.getSlot(owner, index)   # 写完重读核对：引擎截掉、拒收的对不上
            if not same(actual, new):
                self.revert(written)
                return None
        return written

    def revert(self, written):
        owner, cache = self.owner, self._cache
        for index, (old, new) in written.items():
            self.setSlot(owner, index, old)
            cache.pop(index, None)

    def told(self, values):
        for index, stack in values.items():
            if 0 <= index < self.size:
                self.known[index] = stack

    def tick(self):
        """整个向引擎读一遍（不用请求里记住的），与告诉过客户端的不同的返回去推。"""
        return self.tickSlots(range(self.size))

    def tickSlots(self, indexes):
        """只把这几格向引擎读一遍（别处改了哪几格知道时），与告诉过客户端的不同的返回去推。"""
        self._cache = {}
        changes = {}
        for index in indexes:
            if not 0 <= index < self.size:
                continue
            current = self._fresh(index)
            self._cache[index] = current
            if not same(current, self.known[index]):
                changes[index] = current
        return changes or None

    def _fresh(self, index):
        """
        这一刻从引擎读到的第 index 格：shares 为真时，服务端每刻检查的那一轮里同一类、同一个主人的容器只读一次（检查之外照常读）。
        """
        tick = Kinds.ticking[0]
        if not self.shares or tick is None:
            return self.getSlot(self.owner, index)
        key = (type(self), self.owner, index)
        try:
            hash(key)
        except TypeError:
            return self.getSlot(self.owner, index)   # 主人不能做键：不共用
        if _shared[0] != tick:
            _shared[0], _shared[1] = tick, {}
        reads = _shared[1]
        if key not in reads:
            reads[key] = self.getSlot(self.owner, index)
        return reads[key]


class WornContainer(EngineSlots):
    """身上穿戴的（见模块说明）：看界面的玩家自己的盔甲与副手。"""

    size = WORN_SIZE

    def ownerOf(self, session):
        return session.playerId

    def getSlot(self, playerId, index):
        return ENGINE.worn(playerId, index)

    def setSlot(self, playerId, index, stack):
        ENGINE.setWorn(playerId, index, stack)


_shared = [None, {}]   # [刻数, {(容器的类, 主人, 格): 物品堆}]：这一刻里引擎格子读到的（EngineSlots._fresh）


register(TEMPORARY, TemporaryContainer)
register(STORAGE, StorageContainer)
register(VIRTUAL, VirtualContainer)
register(WORN, WornContainer)


class _Engine(object):
    """真实引擎（用到时才导入；只能在服务端线程调用）：玩家的盔甲栏（0–3）与副手（WORN_OFFHAND）。"""

    def __init__(self):
        self._positions = None
        self._items = {}   # 玩家 -> 物品组件（每刻都读，建一次）

    def _slot(self, index):
        if self._positions is None:
            import mod.server.extraServerApi as serverApi
            self._positions = serverApi.GetMinecraftEnum().ItemPosType
        positions = self._positions
        return (positions.OFFHAND, 0) if index == WORN_OFFHAND else (positions.ARMOR, index)

    def _item(self, playerId):
        comp = self._items.get(playerId)
        if comp is None:
            import mod.server.extraServerApi as serverApi
            if len(self._items) > 256:
                self._items.clear()
            comp = self._items[playerId] = serverApi.GetEngineCompFactory().CreateItem(playerId)
        return comp

    def worn(self, playerId, index):
        posType, slot = self._slot(index)
        return Items.normalize(self._item(playerId).GetPlayerItem(posType, slot, True))

    def setWorn(self, playerId, index, stack):
        from ...Server import Engine
        posType, slot = self._slot(index)
        self._item(playerId).SetEntityItem(posType, Engine.toEngine(stack) if not Items.isEmpty(stack) else None, slot)


ENGINE = _Engine()
