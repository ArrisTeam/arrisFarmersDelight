# -*- coding: utf-8 -*-
"""
标准库：方块宿主（docs/ARCHITECTURE.md 第 3.1、3.12 节）与引擎方块容器的存法（种类见 Std/Block/Common.py）。

容器放在自定义方块上时，方块 JSON 里要有 netease:block_entity（实例存储与实例状态存在方块实体数据里，跟着方块与区块存档）；
也可以绑原版容器方块（箱子、木桶这类，方块名以 minecraft: 开头；一个宿主只绑一类），这时实例存储与实例状态存在世界上
（存储键@实例键），方块自己的格子用引擎方块容器（ENGINE_CONTAINER）。绑定的方块登记时就让引擎报它们的移除，原版方块
还让引擎报对它们的使用（不用在 JSON 里写 netease:listen_block_remove）。

    from ..dolorContainer.Std.Block import Server as Block
    Api.registerContainerType(Api.ContainerType("mymod:crate", "tile.mymod:crate.name", "mymod:crate",
                                                host=Block.Host(("mymod:crate",))))

- 实例键是 "维度:x:y:z"（blockKey），一个方块一份内容；几位玩家可以同时看同一个方块。
- 打开：对着绑定的方块使用（右键、触屏点）时打开，手里的东西不用出去（不放方块，也不扔雪球、不打开手里的书：自定义方块
  在客户端不算能交互的方块，引擎在客户端接着把手里的东西对空气使用，所以玩家进游戏时把绑定的方块名与放过的规则发给客户端，
  由 Std/Block/Client.py 在客户端取消那一下）；潜行并拿着东西时照原版不开（手里的东西照常用出去、放下）。按住使用键时引擎
  一直报使用事件，已经开着这个方块时不再开。也可以经接口打开：Api.openContainer(玩家, 类型, blockKey(维度, 坐标))，那里不是
  绑定的方块、玩家够不着时打不开。
- 宿主的子类可以改写的（缺省照上下文说的做）：
  passes（这一下使用放过不放过：照常用手里的东西、不开界面；缺省按类属性 sneakPasses 与 passItems，这两项随方块名发给客户端）、
  use（对着方块使用时做什么：返回 OPEN 打开、BLOCK 拦下、PASS 放过；讲台拿着书时是放上去）、attack（玩家攻击方块：生存模式
  开始挖、创造模式要挖掉时，缺省什么都不做；讲台是让书掉出来）、removed（方块没了：缺省内容掉出、清空；潜影盒式保留内容、
  扳手拆机改写它）、spill（掉出一堆东西）、blockMatches / reachOf / inReach（有效性的三步：方块对不对、交互距离、够不够得着；
  远程终端、多方块的包围盒改写它们）、invalidate（实例键失效：关掉看着的界面）。讲台宿主见 Std/Block/Lecterns.py。
- 有效：方块还在、玩家在同一维度、眼睛离方块中心不超过引擎给这位玩家的交互距离（服务端认的上限：生存 7 格、
  创造 12 格，网易接口改过的照改过的）。原版容器界面在客户端按当前的输入方式关得近一点（键鼠 5.7 格、手柄 5.6 格、
  触屏 6.7 格），这里在服务端查，用的是服务端的上限。不再有效时界面关上。
- 方块没了（挖掉、炸掉、命令换掉）：看着的界面关上，实例存储里的内容照原版箱子掉在方块里（每格从方块里随机一点掉出，一次
  10–30 个、不超过一组，带一点向上的初速度），记着的内容清掉（同一个地方再放一个方块时是空的）；原版方块自己的格子由引擎
  照原版掉。方块所在的区块卸载时看着的界面也关上（原版方块由每刻的有效性检查关上）。
- 存在哪（构造参数 storage）：缺省自定义方块存在方块实体数据里（STORE_BLOCK），原版方块存在世界上（STORE_WORLD）；没有
  方块实体的自定义方块写 STORE_WORLD（不然写不进去，记一行日志）。构造参数 clock 换机器的时钟（缺省 CHUNKS）。
- 界面模型的参数按方块给时写在容器类型上（ContainerType(paramsFor=...)，例如大箱子用 6 行的界面）；containerSize(实例键)
  是方块自己有几格。
- 引擎方块容器（ENGINE_CONTAINER，EngineContainer）：格子经引擎读写，一次请求里读过的记住，写完重读核对，对不上（越界、
  超过堆叠上限被截）恢复原样、整条撤回；潜影盒不收潜影盒。别处改了（原版界面、漏斗、别的模组）按引擎的容器改动事件推给
  客户端：只在有这种容器开着时监听，改动发生在那个方块或相邻的方块（大箱子的另一半）上时，下一刻整个对一遍；另外每秒对一遍
  兜底。接别处的方块（合成站旁边的箱子、存储网络里的一格）：派生 EngineContainer、改写位置（placeOf）与格数（sizeOf），
  登记成自己的容器种类（见 EngineContainer）。
引擎在用到时才导入；离线测试换掉 ENGINE（方块、玩家位置、交互距离、方块实体数据、潜行、创造模式、生成掉落物、容器格子、
事件登记）与 _api。
"""
import random

from ...Common import Items
from ...Server import Storage
from ...Server.Containers import register
from ...Server.Hosts import Host as _Host
from ..Server.Containers import EngineSlots
from ..Server.Hosts import BLOCK, OPEN, PASS, TrackedClock, Watchers, log, verdict  # noqa: F401  BLOCK 给改写 use 的子类用
from ..Slots import holdsUnnestable, unnestable
from .Common import ENGINE_CONTAINER

try:
    _TEXT = (str, unicode)  # noqa: F821
except NameError:
    _TEXT = (str,)

ITEM_WIDTH = 0.25        # 原版掉落物的宽：掉出的位置离方块边至少半个宽
SPILL_CHUNK = (10, 30)   # 原版箱子、木桶被破坏时一个掉落物的数量范围
SPILL_SPEED = 0.05       # 初速度的随机部分（正态分布的标准差）
SPILL_LIFT = 0.2         # 初速度向上的部分

VANILLA = "minecraft:"   # 原版方块名的前缀
FULL_CHECK_TICKS = 20    # 引擎方块容器没收到改动事件时也每这么多刻整个对一遍
PAIRED = ("minecraft:chest", "minecraft:trapped_chest")   # 会连成大箱子的方块：改动事件的格号对不上时整个对一遍

STORE_BLOCK = "block"   # 实例存储与状态存在方块实体数据里（跟着方块与区块存档）
STORE_WORLD = "world"   # 存在世界上（存储键@实例键）

_EVENTS = object()   # 动态监听的名字空间：QuModLibs 按（名字空间，函数名）给监听起名、引擎按名字回调，不带名字空间时
                     # 同一个模组里同名的处理函数（库里的、使用方的）会串成一个
_hosts = {}           # 方块名 -> 宿主
_installed = [False]  # 使用方块、对方块用物品、开始挖、要挖掉、移除、区块卸载、客户端加载完七个事件监听过没有
_live = [False]       # 真的接上了引擎（离线测试预先把 _installed 设为真，就不登记方块）
_opened = {}          # (维度, x, y, z) -> 盯着那个方块的引擎方块容器（watch）
_unwritable = set()   # 写不进方块实体数据、记过日志的方块 (维度, (x, y, z))
_parsed = {}          # 实例键 -> parseKey 的结果（开着的界面每刻都要解析）
_attacking = [False]  # 开始挖、要挖掉两个事件监听过没有（有宿主改写了 attack 才听）


def blockKey(dimension, pos):
    """方块的实例键："维度:x:y:z"。"""
    return "%d:%d:%d:%d" % (dimension, pos[0], pos[1], pos[2])


def parseKey(key):
    """实例键 -> (维度, (x, y, z))；不是方块的实例键时为 None。"""
    if not isinstance(key, _TEXT):
        return None
    found = _parsed.get(key, _parsed)
    if found is not _parsed:
        return found
    parts = key.split(":")
    found = None
    if len(parts) == 4:
        try:
            numbers = [int(part) for part in parts]
            found = numbers[0], tuple(numbers[1:])
        except ValueError:
            found = None
    if len(_parsed) > 1024:
        _parsed.clear()
    _parsed[key] = found
    return found


def _empty(held):
    return not held or held.get("newItemName") in (None, "", "minecraft:air") or not held.get("count", 1)


def scatter(count, limit, rand):
    """
    照原版箱子被破坏时一格东西怎么掉：同一格的都从方块里随机一点掉出（x、z 在 0.125–0.875，y 在 0–0.75），一次掉
    10–30 个（不超过剩下的、不超过一组 limit），每个掉落物带一点随机的初速度。返回 [(数量, 方块里的位置, 初速度)]。
    """
    spread = 1.0 - ITEM_WIDTH
    offset = (rand.random() * spread + ITEM_WIDTH / 2, rand.random() * spread, rand.random() * spread + ITEM_WIDTH / 2)
    out = []
    while count > 0:
        amount = min(count, rand.randint(*SPILL_CHUNK), limit)
        motion = (rand.gauss(0, SPILL_SPEED), rand.gauss(0, SPILL_SPEED) + SPILL_LIFT, rand.gauss(0, SPILL_SPEED))
        out.append((amount, offset, motion))
        count -= amount
    return out


class BlockDataBackend(Storage.Backend):
    """
    方块实体数据里的后端：值只存 str。改动当场写进方块实体，跟着区块存档（不用另存）；方块所在的区块没加载、方块没有
    方块实体时读到 None、写不进去（宿主只在方块还在时给出实例键；写不进去时每个方块记一行日志：方块 JSON 没写
    netease:block_entity 的，宿主要用 storage=STORE_WORLD）。
    """

    def __init__(self, dimension, pos):
        self.dimension = dimension
        self.pos = pos

    def get(self, key):
        data = ENGINE.blockData(self.dimension, self.pos)
        value = data[key] if data is not None else None
        if isinstance(value, _TEXT) and not isinstance(value, str):
            value = value.encode("utf-8")   # Python 2 读回的可能是 unicode
        return value if isinstance(value, str) else None

    def set(self, key, value):
        data = ENGINE.blockData(self.dimension, self.pos)
        if data is not None:
            data[key] = value
        elif (self.dimension, tuple(self.pos)) not in _unwritable:
            _unwritable.add((self.dimension, tuple(self.pos)))
            log("cannot write into the block entity data at %s: the block has none (give its host storage=STORE_WORLD) "
                "or its chunk is not loaded" % blockKey(self.dimension, self.pos))

    def delete(self, key):
        data = ENGINE.blockData(self.dimension, self.pos)
        if data is not None:
            data[key] = None


# ---------------------------------------------------------------- 引擎方块容器


class EngineContainer(EngineSlots):
    """
    引擎方块容器（见模块说明）：缺省是打开的实例键那个方块自己的格子（不是方块的实例键时读到的都是空、写不进去）。
    要接别处的方块（合成站旁边的箱子、存储网络里的一格），派生它、改写下面几项（缺省照旧），按自己的名字登记成容器种类
    （两端 Collections.registerKind，服务端 Server/Containers.register(种类, 类)），界面模型照常声明这种容器：
    - placeOf(会话, 容器说明)：格子在哪个方块，(维度, x, y, z)；None 为没有格子；
    - sizeOf(位置, 容器说明)：有几格（缺省是界面模型声明的格数；比方块多出来的读到空、写不进）；
    - refuses(物品堆)：方块不收的东西（缺省照原版潜影盒：潜影盒里不收潜影盒，收纳袋里装着的也算）；
    - fullCheckTicks（类属性）：没收到改动事件时也每这么多刻整个对一遍；
    - changedAt(位置, 格)：引擎报那个方块的那一格改了：缺省是自己的方块时下一刻只对那一格（会连成大箱子的方块、别的方块
      整个对一遍）；存储网络这类按位置换算格号的改写它。
    开着时盯着所在的方块（watch）：引擎报它与相邻方块的容器改动时下一刻对一遍；盯别的方块（存储网络的每一格）
    同样调 watch(容器, 位置)，关上时 release 放开盯过的全部。
    """

    fullCheckTicks = FULL_CHECK_TICKS

    def __init__(self, session, spec):
        EngineSlots.__init__(self, session, spec)
        place = self.place
        name = ENGINE.blockName(place[0], place[1:]) if place is not None else None
        self.shulker = place is not None and unnestable(name)
        self.paired = name in PAIRED
        self.dirty = True             # 下一刻整个对一遍
        self.dirtySlots = set()       # 下一刻只对这几格
        self._sinceCheck = 0
        watch(self)

    @property
    def place(self):
        """格子所在的方块 (维度, x, y, z)（placeOf 给的；没有为 None）。"""
        return self.owner

    def ownerOf(self, session):
        return self.placeOf(session, self.spec)

    def placeOf(self, session, spec):
        """格子在哪个方块：缺省是会话打开的实例键那个方块（不是方块的实例键时为 None）。"""
        place = parseKey(session.instance.key)
        return (place[0],) + tuple(place[1]) if place is not None else None

    def sizeOf(self, place, spec):
        """有几格：缺省是界面模型声明的格数，没有方块时为 0。"""
        return spec.size if place is not None else 0

    def refuses(self, stack):
        """
        方块不收的东西：缺省照原版潜影盒——不能互相装的盒子（Std/Slots.addUnnestable 登记表）里不收这种盒子，收纳袋里
        装着的也算。
        """
        return self.shulker and holdsUnnestable(stack)

    def accepts(self, stack):
        return not self.refuses(stack)

    def getSlot(self, place, index):
        return ENGINE.containerItem(place[0], place[1:], index)

    def setSlot(self, place, index, stack):
        ENGINE.setContainerItem(place[0], place[1:], index, stack)

    def changedAt(self, place, slot):
        """引擎报方块 place 的第 slot 格改了（见类说明）。"""
        if place == self.place and not self.paired and isinstance(slot, int) and 0 <= slot < self.size:
            self.dirtySlots.add(slot)
        else:
            self.dirty = True

    def tick(self):
        """收到过改动事件（或到了兜底的那一刻）时对一遍（知道是哪几格时只对那几格），与告诉过客户端的不同的推出去。"""
        self._sinceCheck += 1
        if self.dirty or self._sinceCheck >= self.fullCheckTicks:
            self.dirty, self._sinceCheck, self.dirtySlots = False, 0, set()
            return EngineSlots.tick(self)
        if not self.dirtySlots:
            return None
        slots, self.dirtySlots = sorted(self.dirtySlots), set()
        return self.tickSlots(slots)

    def release(self):
        unwatch(self)


register(ENGINE_CONTAINER, EngineContainer)


def containerSize(key):
    """实例键那个方块自己有几格（箱子 27、大箱子 54、漏斗 5……）；不是容器方块、不是方块的实例键时为 -1。"""
    place = parseKey(key)
    return ENGINE.containerSize(place[0], place[1]) if place is not None else -1


def watch(container, place=None):
    """
    让 container 盯着方块 place（(维度, x, y, z)；缺省是它的 place）：引擎报那个方块或相邻方块（大箱子的另一半）的容器改动时，
    把它的 dirty 设为真（引擎方块容器下一刻整个对一遍）。一个容器可以盯几个方块；只在有容器盯着时监听引擎的事件。
    """
    place = container.place if place is None else place
    if place is None:
        return
    if not _opened:
        ENGINE.listenChanges(onContainerChanged, True)
    _opened.setdefault(place, set()).add(container)
    watched = container.__dict__.setdefault("_watched", set())
    watched.add(place)


def unwatch(container, place=None):
    """不再让 container 盯着 place（缺省是它盯着的全部）；没有容器盯着了就不再监听引擎的事件。"""
    watched = container.__dict__.get("_watched", set())
    for spot in ([place] if place is not None else list(watched)):
        watched.discard(spot)
        containers = _opened.get(spot)
        if containers is None or container not in containers:
            continue
        containers.discard(container)
        if not containers:
            del _opened[spot]
            if not _opened:
                ENGINE.listenChanges(onContainerChanged, False)


def onContainerChanged(args):
    """
    引擎的容器改动事件：盯着那个方块的容器知道是哪一格（changedAt），盯着相邻方块（大箱子的另一半）的下一刻整个对一遍。
    """
    pos = args.get("pos")
    if not pos or len(pos) != 3:
        return
    dimension, (x, y, z) = args.get("dimensionId"), pos
    place = (dimension, x, y, z)
    for container in _opened.get(place, ()):
        changed = getattr(container, "changedAt", None)
        if changed is not None:
            changed(place, args.get("slot"))
        else:
            container.dirty = True
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for container in _opened.get((dimension, x + dx, y, z + dz), ()):
            container.dirty = True


# ---------------------------------------------------------------- 时钟


class ChunkClock(TrackedClock):
    """方块宿主的机器：方块所在的区块加载着时走（记着机器实例、离场补刻数，见 Std/Server/Hosts.TrackedClock）。"""

    def present(self, handle):
        place = parseKey(handle[1])
        return place is not None and ENGINE.chunkLoaded(place[0], place[1])

    def group(self, handle):
        place = parseKey(handle[1])
        return (place[0], place[1][0] >> 4, place[1][2] >> 4) if place is not None else None

    def start(self):
        ENGINE.listenChunkLoads(onChunkLoaded)


CHUNKS = ChunkClock()


# ---------------------------------------------------------------- 宿主


class Host(_Host):
    """
    方块宿主（见模块说明）。blocks 是绑定的方块名；一个方块名只能绑一个宿主。access、visitors 见 Server/Hosts.Host
    （主人放下方块时记，见 Std/Server/Access.py）。clock：界面模型是机器时的时钟（缺省 CHUNKS：方块所在的区块加载着时走）；
    storage：实例存储与状态存在哪（STORE_BLOCK / STORE_WORLD，缺省自定义方块存方块实体数据、原版方块存世界上）。
    类属性 sneakPasses、passItems 是缺省的放过规则（见 passes）。
    """

    clock = CHUNKS
    sneakPasses = True   # 潜行并拿着东西时放过（照原版：用的是手里的东西）
    passItems = ()       # 拿着这些东西（物品名）时放过：不开界面，照常用手里的东西（拿桶点不开界面这类）

    def __init__(self, blocks, access=None, visitors=False, clock=None, storage=None):
        if not blocks:
            raise ValueError("a block host needs the bound block names")
        _Host.__init__(self, access, visitors)
        self.blocks = tuple(blocks)
        vanilla = set(name.startswith(VANILLA) for name in self.blocks)
        if len(vanilla) > 1:
            raise ValueError("a block host binds either vanilla blocks or custom blocks, not both: %r" % (self.blocks,))
        self.vanilla = vanilla.pop()
        if clock is not None:
            self.clock = clock
        self.storage = storage or (STORE_WORLD if self.vanilla else STORE_BLOCK)
        if self.storage not in (STORE_BLOCK, STORE_WORLD):
            raise ValueError("block host storage must be STORE_BLOCK or STORE_WORLD: %r" % (storage,))
        for name in self.blocks:
            if _hosts.get(name, self) is not self:
                raise ValueError("block %s is already bound to another block host" % name)
        for name in self.blocks:
            _hosts[name] = self
        self._watched = Watchers()   # 有人看着的实例键 -> 失效时调用的函数（区块卸载时关界面）
        _install()
        if _overrides(self, "attack"):
            _listenAttacks()
        if _live[0]:
            for name in self.blocks:
                ENGINE.listenBlock(name, self.vanilla)
            tellClients(ENGINE.players())

    def keyFor(self, playerId, key):
        """打开方给的实例键：那里是绑定的方块、玩家够得着时才行。"""
        place = parseKey(key)
        if place is None or not self.blockMatches(place) or not self.inReach(playerId, place):
            return None
        return blockKey(*place)

    def stillValid(self, playerId, key):
        place = parseKey(key)
        return place is not None and self.blockMatches(place) and self.inReach(playerId, place)

    def blockMatches(self, place):
        """place（(维度, (x, y, z))）上是不是绑定的方块（区块没加载时读到空气，也不是）。"""
        return ENGINE.blockName(place[0], place[1]) in self.blocks

    def reachOf(self, playerId):
        """玩家的交互距离（服务端认的上限：生存 7 格、创造 12 格，网易接口改过的照改过的）。"""
        return ENGINE.reach(playerId)

    def inReach(self, playerId, place):
        """
        玩家够得着 place：在同一维度，眼睛离方块中心不超过 reachOf。远程终端（不限距离）、多方块（按包围盒量）改写它。
        """
        dimension, pos = place
        at = ENGINE.playerAt(playerId)
        if at is None or at[0] != dimension:
            return False
        reach = self.reachOf(playerId)
        eye = at[1]
        offsets = [eye[axis] - (pos[axis] + 0.5) for axis in range(3)]
        return sum(offset * offset for offset in offsets) <= reach * reach

    def backend(self, key):
        if self.storage == STORE_WORLD:
            return ENGINE.levelBackend()
        dimension, pos = parseKey(key)
        return BlockDataBackend(dimension, pos)

    def prefix(self, storageKey, key):
        return "%s@%s" % (storageKey, key) if self.storage == STORE_WORLD else storageKey

    def save(self, backend):
        """存在方块实体数据里的改动当场写进去，跟着区块存档；存在世界上的要存。"""
        if self.storage == STORE_WORLD:
            backend.save()

    def watch(self, key, onInvalid):
        return self._watched.add(key, onInvalid)

    def invalidate(self, key):
        """实例键 key 失效了（方块所在的区块要卸载）：看着它的界面关上。改写 watch 的子类一并改写它。"""
        self._watched.fire(key)

    def passes(self, playerId, held, sneaking):
        """
        对着绑定的方块使用、手里拿着 held（物品字典，不是空手才问）时放过不放过：放过时不开界面、不拦下，照常用手里的东西
        （放方块、倒水）。缺省：潜行并拿着东西（sneakPasses），或拿着 passItems 里的东西。客户端照这两项取消手里东西的使用
        （它们随方块名发过去）；改写本方法另加的规则客户端不知道，对着自定义方块时手里的东西在客户端照样不出去。
        """
        return bool(self.sneakPasses and sneaking) or held.get("newItemName") in self.passItems

    def use(self, playerId, typeId, key, event=None):
        """
        玩家对着绑定的方块使用（没有放过；已经开着这个方块时不问）：返回 OPEN 打开容器（缺省）、BLOCK 拦下（不开，手里的东西
        也不用出去）、PASS 放过（原版方块照常交互；自定义方块时手里的东西在客户端照样不出去，见 passes）；真假也收（真为
        打开，假为拦下）。event 是引擎的使用事件的参数（只读：手里的东西 itemDict、点的面 face、点的位置 clickX/Y/Z）。
        子类改写它做别的事（讲台拿着书时放上去）。
        """
        return OPEN

    def attack(self, playerId, typeId, key, creative):
        """
        玩家攻击绑定的方块：生存模式开始挖时（creative 为假），创造模式要挖掉时（creative 为真）。返回真时这一下不挖掉方块
        （只对创造模式有用：生存模式开始挖之后照常挖）。缺省什么都不做。
        """
        return False

    def removed(self, typeId, key, place):
        """
        绑定的方块没了（挖掉、炸掉、命令换掉；宿主服务的每个容器类型各调一次，place 是 (维度, (x, y, z))）：缺省照原版
        箱子——经 Api.discardInstance 关掉看着的界面，实例存储里的东西逐件经 spill 掉出，清空并忘掉这个实例。潜影盒式保留
        内容（写进掉落物）、扳手拆机改写它；只想换个掉法改写 spill。
        """
        _api().discardInstance(typeId, key, lambda stack: self.spill(key, place, stack))

    def spill(self, key, place, stack):
        """掉出一堆东西（方块没了、讲台的书）：缺省照原版箱子被破坏时，从方块里随机一点掉出。"""
        ENGINE.spill(place[0], place[1], stack)


# ---------------------------------------------------------------- 事件


def _install():
    if _installed[0]:
        return
    _installed[0] = True
    from ....QuModLibs.Server import ListenForEvent
    ListenForEvent("ServerBlockUseEvent", _EVENTS, onUse)
    ListenForEvent("ServerItemUseOnEvent", _EVENTS, onItemUseOn)
    ListenForEvent("BlockRemoveServerEvent", _EVENTS, onRemoved)
    ListenForEvent("ChunkAcquireDiscardedServerEvent", _EVENTS, onChunkDiscarded)
    ListenForEvent("ClientLoadAddonsFinishServerEvent", _EVENTS, onClientReady)
    _live[0] = True


def _listenAttacks():
    """开始挖、要挖掉两个事件：有宿主改写了 attack 时才听（缺省的什么都不做）。"""
    if _attacking[0] or not _live[0]:
        return
    _attacking[0] = True
    from ....QuModLibs.Server import ListenForEvent
    ListenForEvent("StartDestroyBlockServerEvent", _EVENTS, onStartDestroy)
    ListenForEvent("ServerPlayerTryDestroyBlockEvent", _EVENTS, onTryDestroy)


def _overrides(obj, name):
    """宿主的类改写了方块宿主的方法 name（py2 的未绑定方法要取出函数再比）。"""
    mine, original = getattr(type(obj), name), getattr(Host, name)
    return getattr(mine, "__func__", mine) is not getattr(original, "__func__", original)


def _api():
    from ...Server import Api
    return Api


def _alreadyOpen(api, playerId, host, key):
    """玩家开着的是不是这个宿主在 key 上的容器（宿主服务的哪个类型都算）。"""
    opened = api.openedContainer(playerId)
    return opened is not None and opened[1] == key and opened[0] in host.types


def tellClients(playerIds):
    """
    把绑定的方块名与放过的规则告诉这些玩家的客户端（Std/Block/Client.py：对着它们使用时手里的东西不用出去）：
    {方块名: [潜行并拿着东西时放过, [拿着就放过的物品名]]}。
    """
    rules = dict((name, [bool(host.sneakPasses), sorted(host.passItems)]) for name, host in _hosts.items())
    for playerId in playerIds:
        ENGINE.tellClient(playerId, rules)


def onClientReady(args):
    """玩家的客户端加载完了（进游戏）：告诉它绑定的方块名。"""
    if args.get("playerId"):
        tellClients([args.get("playerId")])


def onUse(args):
    """对着方块使用（引擎在按住使用键时一直报）：绑定的方块问宿主（passes、use），打开它的容器、拦下或放过。"""
    host = _hosts.get(args.get("blockName"))
    if host is None:
        return
    playerId = args.get("playerId")
    held = args.get("itemDict")
    if not _empty(held) and host.passes(playerId, held, ENGINE.sneaking(playerId)):
        return   # 放过（原版：潜行并拿着东西时用的是手里的东西）
    args["cancel"] = True
    key = blockKey(args.get("dimensionId"), (args.get("x"), args.get("y"), args.get("z")))
    typeId = host.typeFor(playerId, key)
    if typeId is None:
        return
    api = _api()
    if _alreadyOpen(api, playerId, host, key):
        return   # 已经开着这个方块了
    answer = verdict(host.use(playerId, typeId, key, args))
    if answer == OPEN:
        api.openContainer(playerId, typeId, key)
    elif answer == PASS:
        args["cancel"] = False


def onItemUseOn(args):
    """对着绑定的方块用手里的东西（放方块这类）：没有放过时拦下，照原版对着箱子右键只开箱子（使用事件里另外打开）。"""
    host = _hosts.get(args.get("blockName"))
    if host is None:
        return
    playerId, held = args.get("entityId"), args.get("itemDict")
    if _empty(held) or not host.passes(playerId, held, ENGINE.sneaking(playerId)):
        args["ret"] = True


def onStartDestroy(args):
    """生存模式开始挖方块：绑定的方块交给宿主的 attack（照原版讲台：开始挖时书就掉出来，照常接着挖）。"""
    pos = args.get("pos") or ()
    _attacked(args.get("blockName"), args.get("playerId"), args.get("dimensionId"), pos, False)


def onTryDestroy(args):
    """玩家要挖掉方块：创造模式时绑定的方块交给宿主的 attack，返回真时这一下不挖掉（生存模式开始挖时已经问过）。"""
    playerId = args.get("playerId")
    if args.get("fullName") not in _hosts or not ENGINE.creative(playerId):
        return
    if _attacked(args.get("fullName"), playerId, args.get("dimensionId"), (args.get("x"), args.get("y"), args.get("z")),
                 True):
        args["cancel"] = True


def _attacked(blockName, playerId, dimension, pos, creative):
    host = _hosts.get(blockName)
    if host is None or len(pos) != 3:
        return False
    key = blockKey(dimension, tuple(int(value) for value in pos))
    typeId = host.typeFor(playerId, key)
    if typeId is None:
        return False
    return bool(host.attack(playerId, typeId, key, creative))


def onRemoved(args):
    """绑定的方块没了：宿主服务的每个容器类型问一次它的 removed（缺省看着的界面关上，内容掉在原地，记着的内容清掉）。"""
    host = _hosts.get(args.get("fullName"))
    if host is None or not host.types:
        return
    dimension, pos = args.get("dimension"), (args.get("x"), args.get("y"), args.get("z"))
    key = blockKey(dimension, pos)
    for typeId in host.types:
        host.removed(typeId, key, (dimension, pos))


def onChunkLoaded(args):
    """区块加载了：里面记着的方块机器接着走（有方块机器时才监听；时钟存档一起存一次）。"""
    handles = CHUNKS.handlesIn((args.get("dimension"), args.get("chunkPosX"), args.get("chunkPosZ")))
    if not handles:
        return
    CHUNKS.hold()
    try:
        for handle in handles:
            CHUNKS.arrive(handle)
    finally:
        CHUNKS.flush()


def onChunkDiscarded(args):
    """区块要卸载：里面有人看着的绑定方块，界面关上；里面的方块机器停下、记下没推进的刻数。"""
    dimension = args.get("dimension")
    handles = CHUNKS.handlesIn((dimension, args.get("chunkPosX"), args.get("chunkPosZ")))
    if handles:
        CHUNKS.hold()
        try:
            for handle in handles:
                CHUNKS.leave(handle)
        finally:
            CHUNKS.flush()
    for entry in args.get("blockEntities") or ():
        host = _hosts.get(entry.get("blockName"))
        if host is not None:
            host.invalidate(blockKey(dimension, (entry.get("posX"), entry.get("posY"), entry.get("posZ"))))


# ---------------------------------------------------------------- 引擎


class _Engine(object):
    """真实引擎（用到时才导入；只能在服务端线程调用）。引擎组件按（种类, 实体）建一次（开着的界面每刻都要用）。"""

    def __init__(self):
        self._random = random.Random()
        self._comps = {}

    @staticmethod
    def _api():
        import mod.server.extraServerApi as serverApi
        return serverApi

    def _comp(self, kind, entityId=None):
        """引擎组件 kind（CreatePos 这类的名字）：实体为 None 时是世界的。"""
        key = (kind, entityId)
        comp = self._comps.get(key)
        if comp is None:
            api = self._api()
            if len(self._comps) > 512:
                self._comps.clear()
            comp = self._comps[key] = getattr(api.GetEngineCompFactory(), kind)(
                api.GetLevelId() if entityId is None else entityId)
        return comp

    def blockName(self, dimension, pos):
        block = self._comp("CreateBlockInfo").GetBlockNew(tuple(pos), dimension)
        return block.get("name") if block else None

    def playerAt(self, playerId):
        """(维度, 眼睛的位置)；玩家不在了时为 None。"""
        eye = self._comp("CreatePos", playerId).GetPos()
        if not eye:
            return None
        return self._comp("CreateDimension", playerId).GetEntityDimensionId(), eye

    def reach(self, playerId):
        return self._comp("CreatePlayer", playerId).GetPlayerInteracteRange() or 0.0

    def blockData(self, dimension, pos):
        return self._comp("CreateBlockEntityData").GetBlockEntityData(dimension, tuple(pos))

    def sneaking(self, playerId):
        return bool(self._comp("CreatePlayer", playerId).isSneaking())

    def players(self):
        return list(self._api().GetPlayerList() or ())

    @staticmethod
    def tellClient(playerId, names):
        from ....QuModLibs.Server import Call
        Call(playerId, "dolorContainerBlocks", names)

    def creative(self, playerId):
        return self._comp("CreateGame").GetPlayerGameType(playerId) == self._api().GetMinecraftEnum().GameType.Creative

    def levelBackend(self):
        from ...Server import Engine
        return Engine.levelBackend()

    def listenBlock(self, name, vanilla):
        """让引擎报绑定方块的移除；原版方块还要报对它的使用（自定义方块本来就报）。"""
        api = self._api()
        factory, level = api.GetEngineCompFactory(), api.GetLevelId()
        if vanilla:
            factory.CreateBlockUseEventWhiteList(level).AddBlockItemListenForUseEvent(name)
        factory.CreateBlockInfo(level).ListenOnBlockRemoveEvent(name, True)

    def chunkLoaded(self, dimension, pos):
        from ...Server import Engine
        return Engine.chunkLoaded(dimension, pos)

    def listenChunkLoads(self, handler):
        from ....QuModLibs.Server import ListenForEvent
        ListenForEvent("ChunkLoadedServerEvent", _EVENTS, handler)

    def listenChanges(self, handler, on):
        from ....QuModLibs.Server import ListenForEvent, UnListenForEvent
        (ListenForEvent if on else UnListenForEvent)("ContainerItemChangedServerEvent", _EVENTS, handler)

    def containerSize(self, dimension, pos):
        size = self._comp("CreateItem").GetContainerSize(tuple(pos), dimension)
        return size if isinstance(size, int) else -1

    def containerItem(self, dimension, pos, index):
        return Items.normalize(self._comp("CreateItem").GetContainerItem(tuple(pos), index, dimension, True))

    def setContainerItem(self, dimension, pos, index, stack):
        """换掉一格（空的就清空）。超过堆叠上限的数量引擎截成上限，越界的格子写不进（写完重读核对）。"""
        from ...Server import Engine
        value = Engine.toEngine(stack) if not Items.isEmpty(stack) else {"count": 0}
        self._comp("CreateItem").SpawnItemToContainer(value, index, tuple(pos), dimension)

    def spill(self, dimension, pos, stack):
        """照原版箱子掉出一格东西（scatter），按原版堆叠数分开。"""
        from ...Server import Engine
        stack = Items.normalize(stack)
        if stack is None:
            return
        api = self._api()
        system = api.GetSystem("Minecraft", "game")
        factory = api.GetEngineCompFactory()
        for amount, offset, motion in scatter(Items.count(stack), Engine.RULES.baseMaxStack(stack), self._random):
            position = (pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2])
            entityId = system.CreateEngineItemEntity(Engine.toEngine(stack, amount), dimension, position)
            if entityId:
                factory.CreateActorMotion(entityId).SetMotion(motion)


ENGINE = _Engine()
