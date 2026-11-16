# -*- coding: utf-8 -*-
"""
容器类型登记与容器实例。

容器类型是服务端登记的一种"可以打开的东西"：编号、用哪个界面模型（名字与参数，见 Common.Menus）、标题、
宿主（Server/Hosts：实例键、后端、存储键、绑定的物品、机器的时钟都由它定）、存储键前缀、服务端才有的放入规则、
受伤时是否关闭。界面模型描述格子（容器、集合、规则、去向），容器类型决定这些格子放在什么东西上。
容器实例是某一份具体的存储（例如某位玩家的次元背包），由 (类型, 实例键) 确定，按界面模型声明的实例存储容器建：
不设上限的用分页存储，有格数的合在一个附加键里；实例状态（机器的状态、动作改的东西）另占一个键。
实例存储带存档版本：容器类型的 version 比存档记的新时，第一次读出前按 migrations 逐版迁移（Storage.migrate，I8）。
存储后端由使用方注入（服务端按宿主取，测试接内存表），本模块不依赖引擎。
"""
import ast
import collections

from ..Common import Bundles, Menus
from . import Storage


class ContainerType(object):
    """
    typeId：带命名空间的编号，例如 "arris_dimbag:bag"；
    title：界面标题（语言文件的键，或直接是文字）；也可以是函数 title(实例键, 参数)，按实例给（见 titleFor）；
    menu / params：界面模型的名字与参数（界面模型要在两端都登记过）；
    host：宿主（Server/Hosts.Host，库带的见 Std/Server/Hosts.py：Player、World、Item、Transient）；
    storageKey：存储键前缀，默认用 typeId（几个实例共用后端的宿主再接上实例键，见宿主的 prefix）；
    accepts：accepts(stack) -> bool，实例存储收不收这种东西（只在服务端；放进来的是收纳袋时，袋里的东西逐个检查）；
    closeOnHurt：玩家受到生物造成的伤害时关闭界面（与原版箱子一样），默认是；也可以是函数 closeOnHurt(会话, 伤害来源) -> 关不关
    （马式"携带版关、经典版不关"：看 session.profile）；伤害来源与冷却见 Api.setHurtClose。登记了要关的类型才监听受伤事件；
    version / migrations：实例存储的存档版本（缺省 1）与迁移函数 {旧版本: migrate(backend, prefix)}：改了存法（例如
    界面模型的存储容器从不设上限改成有格数）就把 version 加一，并给上一版写一个迁移函数，把这个前缀下的键改成新的写法；
    实例第一次读出时从存档记的版本（没记的是 1）逐版迁移，已有存档不丢东西。
    界面模型是机器（熔炉这类）时，它的时钟是宿主的时钟。
    paramsFor：paramsFor(实例键) -> 参数或 None，按宿主的状态挑界面模型这一次的参数（女仆按背包种类、大箱子 6 行）：
    打开时没给参数、机器推进、附加这类按实例键取实例时问它，给 None 时用登记时的参数。
    instanceClass：这种实例的类（缺省 ContainerInstance；改写存法、实例状态的写法时派生它）。
    """

    def __init__(self, typeId, title, menu, params=None, host=None, accepts=None, storageKey=None, closeOnHurt=True,
                 version=1, migrations=None, paramsFor=None, instanceClass=None):
        if ":" not in typeId:
            raise ValueError("container type id needs a namespace: %r" % (typeId,))
        if host is None:
            raise ValueError("a container type needs a host: %s" % typeId)
        if Menus.get(menu) is None:
            raise ValueError("menu %s is not registered (import the module that registers it first)" % menu)
        migrations = dict(migrations or {})
        missing = [step for step in range(1, int(version)) if step not in migrations]
        if int(version) < 1 or missing:
            raise ValueError("container type %s at version %r has no migration from %r" % (typeId, version, missing))
        self.typeId = typeId
        self.title = title
        self.menuName = menu
        self.params = dict(params or {})
        self.host = host
        self.accepts = accepts
        self.storageKey = storageKey or typeId
        self.closeOnHurt = closeOnHurt
        self.version = int(version)
        self.migrations = migrations
        self.paramsFor = paramsFor
        self.instanceClass = instanceClass or ContainerInstance

    def titleFor(self, key, params):
        """
        这个实例打开时的标题（开屏消息里发给客户端）：title 是函数时问它，不然就是 title。字符串当语言文件的键查（查不到时
        原样显示）；要拼的、要原样显示的（实体的自定名字）写成可本地化的文字（Data.Lang 的值：列表 [文字, ...] 原样接起来，
        {"t": 键, "w": [参数, ...]} 按语言填好），客户端按玩家的语言拼。子类可以改写。
        """
        return self.title(key, params) if callable(self.title) else self.title

    def menu(self, itemRules, params=None):
        """服务端这一份界面模型（同样的名字与参数只建一次）；params 不给时用登记时的参数。"""
        built = Menus.create(self.menuName, self.params if params is None else params, Menus.SERVER, itemRules)
        if not self.host.stores and any(spec.info.stored for spec in built.structure.containers.values()):
            raise ValueError("a container that stores nothing cannot have storage containers: %s" % self.typeId)
        if built.machine and self.host.clock is None:
            raise ValueError("a machine needs a host with a clock: %s" % self.typeId)
        return built


class ContainerInstance(object):
    """
    一份具体的存储：界面模型的每个实例存储容器一份。不设上限的用分页存储（第一个沿用 prefix，存档与以前的版本相同，
    别的用 prefix/容器名）；有格数的合在一个附加键里（prefix:x），种类登记了有格数的存法时（Storage.registerStore 的
    sized）各用各的（prefix/容器名）。store(容器名) 取各用各的那一份存储。
    """

    @staticmethod
    def storedIn(backend, prefix, menu):
        """
        后端里有没有这个前缀的实例数据（实例状态、存储；与 __init__ 的存法一致）。登记了别的存法的存储不知道怎么存，当作有。
        改写存法的实例类一并改写它。
        """
        if backend.get("%s:m" % prefix) or backend.get("%s:x" % prefix):
            return True
        first = True
        for spec in menu.structure.containers.values():
            if not spec.info.stored:
                continue
            factory = Storage.storeFor(spec.kind, sized=spec.size is not None)
            if factory is None:
                continue   # 合在一起存的：上面看过了
            if not (isinstance(factory, type) and issubclass(factory, Storage.PagedStore)):
                return True
            own = spec.size is None and first
            if backend.get("%s:meta" % (prefix if own else "%s/%s" % (prefix, spec.cid))):
                return True
            first = first and not own
        return False

    def __init__(self, containerType, key, backend, prefix, menu, isRunning=None, params=None):
        self.type = containerType
        self.key = key
        self.params = dict(containerType.params if params is None else params)   # 界面模型这一次的参数
        self.handle = (containerType.typeId, key)
        self.backend = backend
        self.menu = menu
        self.structure = menu.structure
        self.paged = {}       # 容器名 -> 各用各的存储（不设上限的，与种类登记了有格数存法的）
        self.compact = None   # 别的有格数的合在一起
        first = True
        for spec in self.structure.containers.values():
            if not spec.info.stored:
                continue
            factory = Storage.storeFor(spec.kind, sized=spec.size is not None)
            if factory is not None:
                own = spec.size is None and first
                self.paged[spec.cid] = factory(backend, prefix if own else "%s/%s" % (prefix, spec.cid))
                first = first and not own
            elif self.compact is None:
                self.compact = Storage.GroupStore(backend, prefix)
        self.viewers = set()            # 打开着它的会话
        self.attachedViewers = set()    # 把它作为附加容器接上的会话（Collections.Structure.attach）
        self.unwatch = None             # 盯着宿主的失效事件时：不再盯着时调用的函数（Registry.viewersChanged）
        self.toldViewers = []           # 上次告诉宿主的查看者（玩家 ID，排好序）
        self._isRunning = isRunning
        self._stateKey = "%s:m" % prefix
        self._state = None          # 实例状态：用到时才从后端读
        self._savedText = ""        # 实例状态上次写回（或读出）时的 repr，空串为没有：写回时按它判断变了没有
        self._changes = None
        self._push = None           # 推送的一轮里（beginPush 到 endPush）算过的界面数据，见 sharedData

    @property
    def state(self):
        """实例状态（机器的状态、动作改的东西）：界面模型自己定内容，只放简单值。第一次用到时从后端读。"""
        if self._state is None:
            text = self.backend.get(self._stateKey)
            self._state = ast.literal_eval(text) if text else {}
            self._savedText = repr(self._state) if self._state else ""
        return self._state

    def snapshot(self):
        """实例状态现在的样子（repr 写法，与写回的一样）：动作没成时经 restore 回到它。"""
        state = self.state
        return repr(state) if state else ""

    def restore(self, snapshot):
        """实例状态回到 snapshot 时的样子（没变时不动）。"""
        state = self.state
        if (repr(state) if state else "") == snapshot:
            return
        state.clear()
        if snapshot:
            state.update(ast.literal_eval(snapshot))

    def beginPush(self):
        """
        开始一轮推送（推给看着的人、应答一条请求）：这一轮里界面数据只算一次、编码一次（sharedData；会话的 takeData 共用）。
        一轮里不改实例；可以套着调，最外面的 endPush 结束这一轮。
        """
        if self._push is None:
            self._push = {"depth": 0}
        self._push["depth"] += 1

    def endPush(self):
        push = self._push
        if push is not None:
            push["depth"] -= 1
            if push["depth"] <= 0:
                self._push = None

    @property
    def pushing(self):
        """推送的这一轮里记着的东西（不在一轮里时为 None）：界面数据、各数据的线上写法与要发的消息。"""
        return self._push

    def sharedData(self):
        """界面模型对这个实例的界面数据（allDataValues：范围是 SHARED、PANEL 的）：推送的一轮里只算一次。"""
        push = self._push
        if push is None:
            return self.menu.allDataValues(self) or {}
        values = push.get("values")
        if values is None:
            values = push["values"] = self.menu.allDataValues(self) or {}
        return values

    @property
    def running(self):
        """机器的时钟现在走不走（不是机器时为 False）。"""
        return bool(self._isRunning and self._isRunning(self.handle))

    def beginChanges(self):
        """开始记下实例存储的改动（机器推进时用：推进完把改了的格子推给查看者）。"""
        self._changes = {}

    def endChanges(self):
        """结束记录，返回 {容器格: 物品堆}。"""
        changes, self._changes = self._changes or {}, None
        return changes

    def store(self, cid):
        """容器 cid 各用各的存储（不设上限的、种类登记了有格数存法的）；合在一起存的、不跟着实例存的为 None。"""
        return self.paged.get(cid)

    def get(self, cid, index):
        store = self.paged.get(cid)
        if store is not None:
            return store.get(index)
        return self.compact.get(cid, index) if self.compact is not None else None

    def set(self, cid, index, stack):
        store = self.paged.get(cid)
        if store is not None:
            store.set(index, stack)
        elif self.compact is not None:
            self.compact.set(cid, index, stack)
        if self._changes is not None:
            self._changes[(cid, index)] = stack
        if self._push is not None:
            self._push = {"depth": self._push["depth"]}   # 一轮里改了格子：算过的不再算数

    def highestUsed(self, cid):
        store = self.paged.get(cid)
        return store.highestUsed() if store is not None else -1

    def items(self, cid, start, end):
        """[start, end) 里的非空格：[(下标, 物品堆), ...]。"""
        store = self.paged.get(cid)
        if store is not None:
            return store.items(start, end)
        if self.compact is None:
            return []
        return [(index, stack) for index, stack in self.compact.items(cid) if start <= index < end]

    def accepts(self, stack):
        """
        容器类型的服务端放入规则：收纳袋连同袋里一层层的东西都要收得下（不然装进收纳袋就能带进来）。
        宿主也要收（按物品存放的实例不收记着自己编号的那件物品：放进自己里面就再也打不开了）。
        """
        items = list(Bundles.walk(stack))
        host = self.type.host
        if not all(host.accepts(self.key, item) for item in items):
            return False
        return self.type.accepts is None or all(self.type.accepts(item) for item in items)

    def flush(self):
        """
        改动写回后端：存储的脏页、有格数的那一份、实例状态（repr 与上次写回的一样就不写）。返回写了没有（存储的 flush 返回
        None 的当作写了）；会话据此决定要不要存档。
        """
        wrote = False
        for store in self.paged.values():
            written = store.flush()
            wrote = wrote or written is None or bool(written)
        if self.compact is not None:
            wrote = bool(self.compact.flush()) or wrote
        if self._state is not None:
            text = repr(self._state) if self._state else ""
            if text != self._savedText:
                if text:
                    self.backend.set(self._stateKey, text)
                else:
                    self.backend.delete(self._stateKey)
                self._savedText = text
                wrote = True
        return wrote


def _nothing():
    pass


def storagePrefix(containerType, key):
    """
    一个实例在存储后端里的键前缀，由宿主定：后端只属于这一个实例（按玩家存放）时只用 storageKey；
    几个实例共用后端（按世界、按物品存放）时要接上实例键，不然同一类型的实例（比如每一件背包）共用一份内容。
    """
    return containerType.host.prefix(containerType.storageKey, key)


class Registry(object):
    """
    backendFor(宿主, 实例键) -> Storage.Backend：给出后端（服务端注入，按宿主取）；itemRules：服务端的物品规则。
    实例在有人在看时常驻；没人看时（数据已经写回后端）留在最近用过的 RECENT_LIMIT 个里，重开时不用再读后端、
    解析存储页（打开次元背包时这一步占服务端的一半）。时钟走着的机器（后台行为、定期推进时要用）没人看时也一直留着，
    不占最近用过的名额，时钟停了（stopped）才放回最近用过的里。存储只经实例读写，留着的实例与后端一致。
    """

    RECENT_LIMIT = 8

    def __init__(self, backendFor, itemRules=None):
        self._backendFor = backendFor
        self.itemRules = itemRules
        self._types = {}
        self._instances = {}
        self._recent = collections.OrderedDict()
        self._kept = {}                # 时钟走着、没人看的实例
        self.itemTypes = {}            # 宿主绑定的物品名 -> 容器类型编号
        self.isRunning = None          # 机器的时钟走不走：isRunning((类型, 实例键))，由机器那边接上

    def register(self, containerType):
        """
        登记容器类型，登记成功后告诉它的宿主（Host.registered）。一个宿主可以服务几个类型；宿主绑定的物品只能属于一个宿主，
        itemTypes 记的是那个宿主最先登记的类型（手持使用时打开哪个由宿主的 typeFor 定）。
        """
        if containerType.typeId in self._types:
            raise ValueError("container type already registered: %s" % containerType.typeId)
        host = containerType.host
        for name in host.items:
            if name in self.itemTypes and self._types[self.itemTypes[name]].host is not host:
                raise ValueError("item %s is already bound to %s" % (name, self.itemTypes[name]))
        containerType.menu(self.itemRules)   # 现在就建一次：结构有问题时登记就报错
        self._types[containerType.typeId] = containerType
        for name in host.items:
            self.itemTypes.setdefault(name, containerType.typeId)
        host.registered(containerType)
        return containerType

    def get(self, typeId):
        return self._types.get(typeId)

    def types(self):
        return list(self._types.values())

    def loaded(self, handle):
        """已经建好、有人在看的实例（没有时为 None，不读后端）。"""
        return self._instances.get(handle)

    def instance(self, typeId, key, params=None):
        """
        (类型, 实例键) 的实例。params 是界面模型这一次的参数（不给时用登记时的）：留着的实例参数不同时换一个新的
        （存储照旧，只是界面模型的结构变了）；有人正用别的参数看着时不行，要先让他们重开（见 Service.reopen）。
        """
        containerType = self._types[typeId]
        if params is None and containerType.paramsFor is not None:
            params = containerType.paramsFor(key)
        params = dict(containerType.params if params is None else params)
        handle = (typeId, key)
        instance = self._instances.get(handle)
        if instance is not None and instance.params != params:
            raise ValueError("%s %r is open with other menu parameters; reopen its viewers first" % (typeId, key))
        if instance is None:
            instance = self._recent.pop(handle, None)
            if instance is None:
                instance = self._kept.pop(handle, None)
            if instance is not None and instance.params != params:
                instance = None   # 数据已经写回后端，按新的结构重新读
            if instance is None:
                backend = self._backendFor(containerType.host, key)
                prefix = storagePrefix(containerType, key)
                Storage.migrate(backend, prefix, containerType.version, containerType.migrations)
                instance = containerType.instanceClass(containerType, key, backend, prefix,
                                                       containerType.menu(self.itemRules, params), self._running, params)
            self._instances[handle] = instance
        return instance

    def _running(self, handle):
        return bool(self.isRunning and self.isRunning(handle))

    def release(self, instance):
        """
        没人看（也没有会话把它作为附加容器接着）时移到最近用过的里（超出上限的丢掉最久没用的）；宿主的 cacheable 为假时
        不留，下次打开重新从后端读。
        """
        if instance.viewers or instance.attachedViewers:
            return
        handle = (instance.type.typeId, instance.key)
        if self._instances.get(handle) is not instance:
            return   # 已经不记着它（宿主没了、换了参数）：记着的是后来建的那个，不动
        del self._instances[handle]
        if instance.type.host.cacheable:
            if self._running(handle):
                self._kept[handle] = instance
            else:
                self._remember(handle, instance)

    def stopped(self, handle):
        """机器的时钟停了（Machines.suspend）：留着的它放回最近用过的里（超出上限的照常淘汰）。"""
        instance = self._kept.pop(handle, None)
        if instance is not None:
            self._remember(handle, instance)

    def _remember(self, handle, instance):
        self._recent[handle] = instance
        while len(self._recent) > self.RECENT_LIMIT:
            self._recent.popitem(last=False)

    def viewersChanged(self, instance, onInvalid):
        """
        实例的查看者变了（会话开、关、切换之后由服务调用）：有人看着时盯着宿主的失效事件（Host.watch，失效时调用
        onInvalid(实例)），没人看了就不再盯；看的人与上次告诉宿主的不同时告诉它（Host.onViewers）。
        """
        host, key = instance.type.host, instance.key
        players = sorted(viewer.playerId for viewer in instance.viewers if not viewer.closed)
        if players and instance.unwatch is None:
            instance.unwatch = host.watch(key, lambda: onInvalid(instance)) or _nothing
        elif not players and instance.unwatch is not None:
            stop, instance.unwatch = instance.unwatch, None
            stop()
        if players != instance.toldViewers:
            instance.toldViewers = players
            host.onViewers(key, list(players))

    # ---------------------------------------------------------------- 附加容器（Server/Containers.AttachedContainer）

    def resolve(self, menu, spec, instance, playerId):
        """
        界面模型 menu 的附加容器 spec 对这位玩家接到哪：界面模型的 attachmentFor 给出 (类型, 实例键, 容器名)，宿主再给出
        实例键（keyFor）。给了 None、宿主不给键时返回 None（这一次接不上）；写错了（类型没登记、是机器、那个界面模型里
        没有这个存储容器或格数不同、接回打开的这个实例）抛 ValueError。返回 (类型, 实例键, 容器名)。
        """
        target = menu.attachmentFor(spec.cid, instance, playerId)
        if target is None:
            return None
        typeId, key, cid = target
        containerType = self._types.get(typeId)
        if containerType is None:
            raise ValueError("attached container %s: container type %r is not registered" % (spec.cid, typeId))
        other = containerType.menu(self.itemRules)
        if other.machine:
            raise ValueError("attached container %s: %s is a machine (machines cannot be attached)" % (spec.cid, typeId))
        theirs = other.structure.containers.get(cid)
        if theirs is None or not theirs.info.stored or theirs.size != spec.size:
            raise ValueError("attached container %s: %s has no storage container %r of size %r"
                             % (spec.cid, typeId, cid, spec.size))
        key = containerType.host.keyFor(playerId, key)
        if key is None:
            return None
        if (typeId, key) == instance.handle:
            raise ValueError("attached container %s: cannot attach the instance being opened" % spec.cid)
        return typeId, key, cid

    def valid(self, target, playerId):
        """附加的 (类型, 实例键, 容器名) 对这位玩家现在有效没有：宿主让他打开（canOpen），也还有效（stillValid）。"""
        host = self._types[target[0]].host
        return bool(host.canOpen(playerId, target[1]) and host.stillValid(playerId, target[1]))

    def attachInstance(self, target):
        """附加的实例（按登记时的参数）；有人正用别的参数看着它、存档读不了时为 None（下一刻再试）。"""
        try:
            return self.instance(target[0], target[1])
        except (Storage.StorageError, ValueError, TypeError):
            return None

    def hasData(self, typeId, key):
        """
        (类型, 实例键) 有没有东西要管：记着这个实例，或后端里有它的数据（实例状态、存储，见实例类的 storedIn）。宿主没了时
        （方块拆掉）没打开过的不用读出来清。
        """
        handle = (typeId, key)
        if handle in self._instances or handle in self._recent or handle in self._kept:
            return True
        containerType = self._types[typeId]
        params = containerType.paramsFor(key) if containerType.paramsFor is not None else None
        menu = containerType.menu(self.itemRules, params)
        return bool(containerType.instanceClass.storedIn(self._backendFor(containerType.host, key),
                                                         storagePrefix(containerType, key), menu))

    def drop(self, handle):
        """实例的宿主没了（Service.discard）：不论有没有人看着都不再记着它，下次用到时按后端重新读。"""
        self._instances.pop(handle, None)
        self._recent.pop(handle, None)
        self._kept.pop(handle, None)

    def empty(self, typeId, key, spill):
        """
        宿主没了的实例（Service.discard 先关掉看着它的会话）：实例存储里的东西逐件交给 spill(物品堆)，存储与实例状态清空、
        写回后端，然后不再记着它。实例读不出来（存档版本更新、参数对不上）时抛出原来的错误，同样不再记着它。
        """
        handle = (typeId, key)
        try:
            instance = self.instance(typeId, key)
        except (Storage.StorageError, ValueError, TypeError):
            self.drop(handle)
            raise
        for spec in instance.structure.containers.values():
            if not spec.info.stored:
                continue
            end = spec.size if spec.size is not None else instance.highestUsed(spec.cid) + 1
            for index, stack in instance.items(spec.cid, 0, end):
                spill(stack)
                instance.set(spec.cid, index, None)
        instance.state.clear()
        instance.flush()
        self.drop(handle)

    def forget(self, playerId):
        """玩家离开时：丢掉最近用过的里宿主说要丢的（Host.forgetsOnLeave：数据放在这位玩家身上的）。"""
        for handle in [handle for handle in self._recent
                       if self._types[handle[0]].host.forgetsOnLeave(playerId, handle[1])]:
            del self._recent[handle]

    def instances(self):
        return list(self._instances.values())
