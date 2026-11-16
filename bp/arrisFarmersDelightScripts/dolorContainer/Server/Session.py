# -*- coding: utf-8 -*-
"""
服务端会话：一位玩家打开的一个界面（docs/ARCHITECTURE.md 第 4 节）。界面模型声明的每个容器在这里由按种类登记的工厂
接上真的（Server/Containers）：玩家背包、手持物在内核，临时格、实例存储、虚拟容器在标准库。会话只经容器对象读写，
不认识具体的种类。格子内容怎么发给客户端由每个容器的同步方式定（Common/Sync），会话同样只调用它的方法。

处理一条操作请求：校验 -> 核对客户端声明的格子内容 -> 在工作副本上执行操作 -> 提交（按容器的先后写，写入可能失败的
在前，一个写不进去就撤回前面写过的、整条不生效）-> 保存 -> 回应答。动作请求（Common/Actions）走同一条提交路径，
调用之前由这里集中校验（handleCall）。每位查看者的状态（界面模型的 viewerState）每个会话各一份（viewer），
不存档，只发给这位查看者自己。所有与引擎打交道的事都经注入的对象完成：

    inventory：read() -> 36 格列表；readSlot(下标) -> 一格；write({下标: 物品堆}) -> {下标: 实际物品堆}；
               drop(物品堆) 丢进世界；canDrop() -> 玩家现在能不能往世界里丢东西；
               mayOpenContainers() -> 照游戏的规矩玩家现在能不能用容器（动作执行前查，宿主的 visitors 为真时不查）
    cursorStore：get() / set(物品堆) 持久化手持物（崩溃后下次进游戏退回背包）
    heldStore：get() -> [物品堆] / set([物品堆]) 持久化会话保管的东西（临时格；同上；没有这种容器的界面可以不给）
    save()：把这位玩家的数据交给引擎存档
    send(kind, message)：发给这个会话的客户端
    machines：Machines.Machines（实例是机器时：打开与每次操作之前推进到现在，操作之后重定唤醒；不是机器可以不给）
    limiter：limiter(花费) -> 这条请求放不放行（限频：操作与动作每条问一次，花费是它们声明的 cost，不放行时拒绝，错误码 rate；
               不给时不限）
    registry：Registry.Registry（界面模型有附加容器时用它接上别的实例；没有附加容器可以不给）

实例里的存储改了，提交后推给看着那份存储的所有别的会话：打开着这个实例的，以及把它作为附加容器接上的（容器的
backing，各自换成自己的容器名）。有每刻要检查的容器（附加容器：附加的宿主还有效没有）的会话由服务端每刻调用 tick。

本模块不依赖引擎，离线可测。
"""
import collections
import copy

from ..Common import Actions, Collections, Data, Items, Ops, Protocol, Rules, Schema, Slots, Sync
from ..Common.Collections import PLAYER_SIZE
from . import Containers
from .Hosts import Host

HOST_GONE = Protocol.CLOSE_HOST_GONE   # 动作执行前发现宿主对这位玩家不再有效：回这个错误码，服务端随后关掉会话


class _State(Rules.SlotState):
    """一次请求看到的状态：按容器读。"""

    def __init__(self, session, dropAllowed=None):
        self.session = session
        self.playerId = session.playerId
        self.menu = session.menu
        self.structure = session.structure
        self.containers = session.containers
        self.viewer = session.viewer
        self._dropAllowed = dropAllowed   # 用到时才问（丢东西的请求才用到）
        self._data = None                 # 规则读到的界面数据：用到时才算一次
        self._scopes = {}                 # 界面数据按范围算好的原始值（一次请求里每个范围只算一次）
        self._creative = None

    @property
    def creative(self):
        if self._creative is None:
            self._creative = bool(self.session.inventory.creative())
        return self._creative

    def dataValue(self, name):
        data = self._data
        if data is None:
            data = self._data = {}
        if name not in data:
            data[name] = self.session.ruleData(name, self._scopes)
        return data[name]

    def read(self, key):
        return self.containers[key[0]].read(key[1])

    def highestUsed(self, cid):
        return self.containers[cid].highestUsed()

    def findKind(self, cid, stack):
        return self.containers[cid].findKind(stack)

    def freeIndex(self, cid):
        return self.containers[cid].freeIndex()

    def closedCollections(self):
        return self.session.closedCollections()

    def lockedCells(self):
        return self.session.locked

    def accepts(self, ref, stack):
        collection = self.structure.get(ref[0])
        if not self.containers[collection.cid].accepts(stack):
            return False
        return self.session.menu.accepts(ref, stack)

    def canDrop(self, stack):
        if not Rules.SlotState.canDrop(self, stack):
            return False
        if callable(self._dropAllowed):
            self._dropAllowed = bool(self._dropAllowed())
        return self._dropAllowed is not False


class Session(object):

    def __init__(self, sessionId, playerId, instance, inventory, cursorStore, rules, send, save, heldStore=None,
                 machines=None, limiter=None, registry=None):
        self.id = sessionId
        self.playerId = playerId
        self.instance = instance
        self.menu = instance.menu
        self.structure = structure = instance.structure
        self.inventory = inventory
        self.cursorStore = cursorStore
        self.heldStore = heldStore
        self.rules = rules
        self.send = send
        self.save = save
        self.machines = machines if instance.menu.machine else None
        self.limiter = limiter
        self.registry = registry
        self.next = None   # 动作或格子的 onChanged 要求的切换或重开，端点回了应答之后做
        self.profile = None   # 客户端的界面档（开屏后与切换界面档后报来，格子操作的请求也带着）；还没报时为 None
        self.cursor = None
        self.closed = False
        self.dataSent = {}   # 上次发给客户端的界面数据（线上写法）
        self.viewer = _initialViewer(self.menu, instance, playerId)   # 每位查看者的状态 {名字: 值}
        self.viewerSent = {}   # 上次发给客户端的每位查看者状态（线上写法）
        self.containers = collections.OrderedDict((cid, Containers.create(self, spec))
                                                  for cid, spec in structure.containers.items())
        self.syncs = dict((cid, Sync.create(spec)) for cid, spec in structure.containers.items())
        self._writeOrder = sorted(self.containers, key=lambda cid: self.containers[cid].order)
        self._held = [self.containers[cid] for cid in sorted(self.containers) if self.containers[cid].held]
        # 关界面时要把东西退回背包的容器（玩家临时格）
        self._returning = [cid for cid, container in self.containers.items() if container.returnsOnClose]
        # 格子类型要知道东西被拿走的集合（改写了 onTake 的，例如熔炉的产物格）、内容变了的集合（改写了 onChanged 的，装备格）
        self._takers = set(name for name, collection in structure.collections.items()
                           if _overrides(collection.slot, "onTake", Slots.SlotType))
        self._changers = set(name for name, collection in structure.collections.items()
                             if _overrides(collection.slot, "onChanged", Slots.SlotType))
        self.locked = _lockedCells(structure, instance.type.host.lockedCells(playerId, instance.key))
        self._ticking = [cid for cid, container in self.containers.items() if container.ticks]
        self._backed = {}   # (实例的 id, 存储容器名) -> [自己的容器名]：别的会话改了那份存储时换成自己的容器格
        self._rebuildBacking()
        instance.viewers.add(self)

    # ---------------------------------------------------------------- 开屏

    def recoverCursor(self):
        """上次没退回的手持物与会话保管的东西（服务器在界面开着时崩溃留下的）先退回背包。"""
        recoverLeftover(self.inventory, self.cursorStore, self.rules, self.save, self.heldStore)

    def openMessage(self):
        if self.machines is not None:
            self.machines.refresh(self.instance, exclude=self)   # 先推进到现在（别的查看者也看到），再整份发给自己
        payloads = {}
        for cid, container in self.containers.items():
            if container.synced:
                payloads[cid], shown = self.syncs[cid].opened(container)
                container.told(shown)
        containerType = self.instance.type
        message = {
            "s": self.id, "type": containerType.typeId,
            "title": _titleWire(containerType.titleFor(self.instance.key, self.instance.params)),
            "menu": containerType.menuName, "params": self.instance.params, "drop": bool(self.inventory.canDrop()),
            "pid": self.playerId,
            "sync": Protocol.encodeSync(payloads, self.structure), "d": self.takeData(),
        }
        viewer = self.takeViewer()
        if viewer:
            message["v"] = viewer
        if self.locked:
            message["lock"] = [[self.structure.containerId(cid), index] for cid, index in sorted(self.locked)]
        if self.inventory.creative():
            message["cr"] = True   # 创造模式（客户端预测装备格的绑定诅咒时用）
        return message

    @property
    def checksHost(self):
        """宿主改写了 stillValid：服务端每刻问 hostValid。"""
        return _overrides(self.instance.type.host, "stillValid", Host)

    def hostValid(self):
        """宿主对这位玩家还有效没有（Host.stillValid）。"""
        return bool(self.instance.type.host.stillValid(self.playerId, self.instance.key))

    # ---------------------------------------------------------------- 请求

    def matches(self, data):
        """请求是不是发给这个会话的：会话还开着，请求里的会话编号对得上。"""
        return not self.closed and isinstance(data, dict) and data.get("s") == self.id

    def handleAction(self, data):
        """执行一条操作请求，返回应答（ack 消息）。请求本身不成立时也回应答，带错误码。"""
        if self.limiter is not None and not self.limiter(Ops.costOf(data)):
            return self.reject(data, "rate")
        try:
            requestId, op, expects, profile = Ops.parseRequest(data, self.structure)
        except Ops.BadRequest as error:
            return self.reject(data, error.code)
        self.profile = profile
        if self.machines is not None:
            # 机器先推进到现在：客户端看到的若已过时，下面按指纹拒绝，应答带上现在的内容
            self.machines.refresh(self.instance)
        self._begin()
        state = _State(self, self.inventory.canDrop)
        workspace = Rules.Workspace(state, self.rules)
        involved = list(expects) + Ops.involvedRefs(op)
        for ref, fingerprint in expects.items():
            if Items.fingerprint(workspace.get(ref)) != fingerprint:
                return self._ack(requestId, False, self._current(state, involved), "stale")
        try:
            Ops.apply(workspace, op, profile)
        except Rules.RuleError as error:
            return self._ack(requestId, False, self._current(state, involved), error.code)
        committed = self._commit(workspace, keepPush=True)
        if committed is None:
            self._begin()
            return self._ack(requestId, False, self._current(_State(self), involved), "write_failed")
        try:
            for key, stack in self._current(state, involved).items():
                committed.setdefault(key, stack)   # 没变的格子：操作前后一样
            if self.machines is not None:
                self.machines.schedule(self.instance)   # 放进了燃料、拿走了产物：下一个事件跟着变
            return self._ack(requestId, True, committed)
        finally:
            self.instance.endPush()

    def handleCall(self, data):
        """
        执行一条动作请求（Common/Actions），返回应答（ack 消息）。调用动作之前集中校验：会话开着、限频、动作是这个界面模型的
        且参数合格（没声明的参数不收）、宿主对这位玩家仍有效（不再有效时错误码 host_gone，服务端随后关掉会话）、
        玩家仍有权限（宿主的 canOpen），最后是动作自己的条件。动作在工作副本上改格子、在实例状态里改别的：成了整体提交，
        没成（抛 Actions.Refused 或规则错误、写不进去）格子与实例状态都不改。成了时应答带动作的返回值（"r"）。
        """
        if self.closed:
            return self.reject(data, "closed")
        if self.limiter is not None and not self.limiter(Actions.costOf(data, self.menu.actions)):
            return self.reject(data, "rate")
        try:
            requestId, action, args = Actions.parseCall(data, self.menu.actions, self.structure)
        except Actions.BadRequest as error:
            return self.reject(data, error.code)
        host, key = self.instance.type.host, self.instance.key
        if not host.stillValid(self.playerId, key):
            return self._ack(requestId, False, {}, HOST_GONE)
        if not (host.visitors or self.inventory.mayOpenContainers()) or not host.canOpen(self.playerId, key):
            return self._ack(requestId, False, {}, "denied")
        if self.machines is not None:
            self.machines.refresh(self.instance)
        self._begin()
        ctx = ActionContext(self, Rules.Workspace(_State(self, self.inventory.canDrop), self.rules))
        # 动作没成时回到调用之前：实例状态记 repr（与写回的写法一样，比深拷贝快，只在要回去时才读回），这位查看者的状态很小
        saved = (self.instance.snapshot(), copy.deepcopy(self.viewer))
        try:
            if action.condition is not None and not action.condition(self.menu, ctx, *args):
                raise Actions.Refused("condition")
            result = action.handler(self.menu, ctx, *args)
        except (Actions.Refused, Rules.RuleError) as error:
            self._rollback(saved)
            return self._ack(requestId, False, {}, error.code)
        committed = self._commit(ctx.ws, keepPush=True)
        if committed is None:
            self._rollback(saved)
            self._begin()
            return self._ack(requestId, False, {}, "write_failed")
        try:
            if self.machines is not None:
                self.machines.schedule(self.instance)
            message = self._ack(requestId, True, committed)
        finally:
            self.instance.endPush()
        if result is not None:
            message["r"] = result
        self.next = ctx.next   # 端点回了应答再做（Service.dolorContainerCall）
        return message

    # ---------------------------------------------------------------- 给规则、动作、钩子用的公开部分

    def read(self, ref):
        """
        格子 ref 现在的内容（服务端确认过的，不算这一次请求里还没提交的改动：那些用工作副本 ws.get 读）。算出的格子
        按现在的内容算，内容来自界面数据的格子读界面数据；没有这一格时为 None。
        """
        structure = self.structure
        if ref[0] in structure.derivers:
            return structure.derived(ref, self.read, self.viewer)
        shown = structure.dataBacked.get(ref[0])
        if shown is not None:
            return (self.ruleData(shown) or {}).get(ref[1])
        key = structure.locate(ref)
        return self.containers[key[0]].read(key[1]) if key is not None else None

    def creative(self):
        """这位玩家现在是不是创造模式（每次问引擎）。"""
        return bool(self.inventory.creative())

    def giveExperience(self, amount):
        """
        给这位玩家 amount 点经验（熔炉拿走产物、砂轮、交易）：怎么给由宿主的 giveExperience 定，缺省照原版在玩家身上
        生成经验球。不大于 0 时什么都不做。
        """
        if amount > 0:
            self.instance.type.host.giveExperience(self, int(amount))

    def setProfile(self, profile):
        """客户端报来的界面档（Collections.PROFILES 之一；端点已经校验过）。"""
        self.profile = profile

    def reject(self, data, code):
        """不处理这条请求（例如限频）时的应答。"""
        requestId = data.get("id") if isinstance(data, dict) and isinstance(data.get("id"), int) else 0
        return self._ack(requestId, False, {}, code)

    def handleRequest(self, cid, query):
        """应答拉取（req）：交给容器 cid 的同步方式，返回 update 消息；查询不合格时抛 BadRequest。"""
        container = self.containers[cid]
        if not container.synced:
            raise Ops.BadRequest("bad_container")
        payload, shown = self.syncs[cid].requested(container, query)
        container.told(shown)
        return {"s": self.id, "sync": Protocol.encodeSync({cid: payload}, self.structure)}

    def refresh(self):
        """别处改了容器（例如背包）：各容器与上次告诉客户端的比，把不一样的格子推过去。"""
        if self.closed:
            return
        changes = {}
        for cid, container in self.containers.items():
            changes.update(((cid, index), stack) for index, stack in container.refresh().items())
        if changes:
            self.send("update", {"s": self.id, "sync": self._sync(changes)})

    @property
    def ticking(self):
        """有每刻要检查的容器（附加容器、经引擎读写的格子），或界面数据要每隔几刻再算（界面模型的 dataEvery）：服务端每刻调用 tick。"""
        return bool(self._ticking) or bool(self.menu.dataEvery)

    def tick(self, number=0):
        """
        每刻（number 是服务端数到的第几刻）：容器各自检查（附加容器接上、断开），变了的格子与每位查看者状态（附加容器的开关）
        推给客户端；界面模型写了 dataEvery 的，逢它的倍数的刻再算界面数据，变了的一起推。
        """
        if self.closed:
            return
        changes, touched = {}, False
        for cid in self._ticking:
            values = self.containers[cid].tick()
            if values is not None:
                touched = True
                changes.update(((cid, index), stack) for index, stack in values.items())
        if touched:
            self._rebuildBacking()
        every = self.menu.dataEvery
        data = self.takeData() if every and number % every == 0 else None
        viewer = self.takeViewer()
        if changes or data or viewer:
            message = {"s": self.id, "sync": self._sync(changes)}
            if data:
                message["d"] = data
            if viewer:
                message["v"] = viewer
            self.send("update", message)

    def storageKeys(self, instance, storageCid, values):
        """别的会话改了实例 instance 里的存储 storageCid（{下标: 物品堆}）：换成自己的容器格；自己没接着它时为空。"""
        out = {}
        for cid in self._backed.get((id(instance), storageCid), ()):
            out.update(((cid, index), stack) for index, stack in values.items())
        return out

    def containerChanged(self, changes):
        """
        实例变了：同一实例的其他会话改了共用的容器，或机器推进了（{容器格: 物品堆}，可以为空）。
        把格子与变了的界面数据推给自己的客户端。
        """
        if self.closed:
            return
        data, viewer = self.takeData(), self.takeViewer()
        if changes or data or viewer:
            message = {"s": self.id, "sync": self._sync(changes)}
            if data:
                message["d"] = data
            if viewer:
                message["v"] = viewer
            self.send("update", message)

    def takeData(self):
        """
        界面数据按字段类型编码，跟上次发的比，返回要发的那些（线上写法），并记作已发。没有界面数据的界面模型为空。
        范围是 SHARED、PANEL 的由界面模型的 dataValues 算，VIEWER 的由 viewerValues 按这位查看者算；PANEL 的只在它的面板
        对这位查看者开着时发，面板关着时忘掉发过的值（再打开时整份补发）。
        字段类型可以要求同样的值也再发（会动的数：同样的起点与速度也可能是新的一段）。发的写法由字段类型给（Data.Field.message：
        增量的列表与映射只发改动，没发过的整份发）。
        """
        fields = self.menu.data
        if not fields:
            return {}
        panelData = self.structure.panelData
        opened, switches = {}, {}
        changed = {}
        push = self.instance.pushing   # 推送的一轮里几位查看者共用：数据只算一次、编码一次，同样的上次写法只比一次
        wires = push.setdefault("wires", {}) if push is not None else None
        messages = push.setdefault("messages", {}) if push is not None else None
        for values, scopes, shared in ((self.instance.sharedData(), (Data.SHARED, Data.PANEL), True),
                                       (self.menu.allViewerValues(self.instance, self.viewer), (Data.VIEWER,), False)):
            for name, value in (values or {}).items():
                field = fields.get(name)
                if field is None or field.scope not in scopes:
                    raise ValueError("menu %s has no %s data field %r (declare it in data with that scope)"
                                     % (self.menu.menuName, "/".join(scopes), name))
                if field.scope == Data.PANEL:
                    panel = panelData[name]
                    if panel not in opened:
                        opened[panel] = self.panelOpen(panel, switches)
                    if not opened[panel]:
                        self.dataSent.pop(name, None)
                        continue
                if shared and wires is not None:
                    wire = wires.get(name, Data.MISSING)
                    if wire is Data.MISSING:
                        wire = wires[name] = field.encode(value)
                else:
                    wire = field.encode(value)
                previous = self.dataSent.get(name, Data.MISSING)
                if shared and messages is not None:
                    known = messages.get((name, id(previous)))
                    if known is None or known[0] is not previous:
                        send = previous != wire or field.again(wire)
                        known = messages[(name, id(previous))] = (previous, send,
                                                                  field.message(previous, wire) if send else None)
                    if known[1]:
                        self.dataSent[name] = wire
                        changed[name] = known[2]
                elif previous != wire or field.again(wire):
                    self.dataSent[name] = wire
                    changed[name] = field.message(previous, wire)
        return changed

    def ruleData(self, name, scopes=None):
        """
        规则读的界面数据 name（Rules.SlotState.dataValue）：原始值按字段类型编码再解码，与客户端读到的写法一样
        （每格数据是 {格号: 值}）。范围是 VIEWER 的按这位查看者算；没有这个数据或这一次没给值时为字段的空值。
        scopes 是一次请求里按范围记着的原始值（给了就用它、没有时算好记进去）。
        """
        field = self.menu.data.get(name)
        if field is None:
            return None
        scope = Data.VIEWER if field.scope == Data.VIEWER else Data.SHARED
        values = scopes.get(scope) if scopes is not None else None
        if values is None:
            if scope == Data.VIEWER:
                values = self.menu.allViewerValues(self.instance, self.viewer) or {}
            else:
                values = self.instance.sharedData()
            if scopes is not None:
                scopes[scope] = values
        if name not in values:
            return field.empty
        return field.decode(field.encode(values[name]))

    def panelOpen(self, name, values=None):
        """面板 name 对这位查看者开着没有：开关是每位查看者的状态时看会话里的，是界面数据时现算（values 是算过的缓存）。"""
        panel = self.structure.panels[name]
        return panel.opens(self._switchValue(panel.switch, {} if values is None else values))

    def closedCollections(self):
        """对这位查看者停用的集合：面板关着的、断开了的附加容器上的；都没有时为空。"""
        values = {}
        return self.structure.closedCollections(lambda panel: panel.opens(self._switchValue(panel.switch, values)),
                                                self.viewer)

    def _switchValue(self, name, values):
        if name in self.menu.viewerState:
            return self.viewer.get(name)
        scope = self.menu.data[name].scope
        if scope not in values:
            values[scope] = (self.menu.allViewerValues(self.instance, self.viewer) or {}) if scope == Data.VIEWER \
                else self.instance.sharedData()
        return values[scope].get(name)

    def takeViewer(self):
        """每位查看者的状态按字段类型编码，跟上次发的比，返回要发的那些（线上写法），并记作已发。"""
        fields = self.menu.viewerState
        if not fields:
            return {}
        changed = {}
        for name, field in fields.items():
            wire = field.encode(self.viewer[name])
            if name not in self.viewerSent or self.viewerSent[name] != wire:
                self.viewerSent[name] = changed[name] = wire
        return changed

    # ---------------------------------------------------------------- 关闭

    def close(self, reason, notify=None, dropCursor=False):
        """
        关闭会话：手持物与要退回的容器里的东西退回背包（放不下的丢在脚下）；dropCursor 为真时手持物与会话保管的东西
        整堆丢在原地（死亡且背包已经掉落时）。通知客户端关界面，原因在 Protocol.SILENT 里的不通知（notify 可以另给）。
        """
        if notify is None:
            notify = reason not in Protocol.SILENT
        if self.closed:
            return
        self._closing(reason)
        if dropCursor:
            self._dropHeld()
        self._returnHeld()
        self.closed = True
        self._release()
        self.instance.viewers.discard(self)
        if self.machines is not None:
            self.machines.schedule(self.instance)   # 没人看了就不再唤醒
        if notify:
            self.send("close", {"s": self.id, "reason": reason})

    def opened(self):
        """会话装上了（服务端服务在开屏消息之前调）：界面模型与部件改写了的 onOpen 依次调用，改的实例状态写回。"""
        hooks = self.menu.hooksFor("onOpen")
        if hooks:
            for owner in hooks:
                owner.onOpen(self)
            self.instance.flush()
            self.save()

    def _closing(self, reason):
        """会话要结束了（关、切换、玩家离开）：界面模型与部件改写了的 onClose 依次调用，改的实例状态写回。"""
        hooks = self.menu.hooksFor("onClose")
        if hooks:
            for owner in hooks:
                owner.onClose(self, reason)
            self.instance.flush()
            self.save()

    def reopenAfter(self, params=None):
        """
        应答之后按新的参数重开这个容器（格子类型的 onChanged 里用：装卸升级这类改了结构的格子改动；动作里用 ctx.reopen）。
        看着这个实例的人都重开（Service.reopen）。
        """
        self.next = ("reopen", params)

    def handOver(self, structure):
        """
        切换到结构为 structure 的另一个会话（Service 的 switchTo / reopen）：手持物交过去；会话保管的容器（玩家临时格）在
        新结构里还有同名、同种、同样格数的就把东西交过去，没有的照关界面退回背包（放不下的丢在脚下）。这个会话随之关上，
        不通知客户端（新会话的开屏消息让客户端换界面）。交过去的东西在新会话存下之前还记在玩家数据里（崩溃时照常退回）。
        返回 (手持物, {容器名: {下标: 物品堆}})。
        """
        self._closing(Protocol.CLOSE_SWITCH)
        keep = [cid for cid, container in self.containers.items()
                if container.held and _sameContainer(self.structure.containers[cid], structure.containers.get(cid))]
        returning = [cid for cid in self._returning if cid not in keep]
        if any(self.containers[cid].heldStacks() for cid in returning):
            self._begin(everything=True)
            workspace = Rules.Workspace(_State(self), self.rules)
            Rules.returnItems(workspace, returning)
            if self._commit(workspace) is None:
                for cid in returning:
                    for stack in self.containers[cid].heldStacks():
                        self.inventory.drop(stack)
                    self.containers[cid].clear()
                self._saveHeld()
                self.save()
        carried = dict((cid, self.containers[cid].handOver()) for cid in keep)
        cursor, self.cursor = self.cursor, None
        self.closed = True
        self._release()
        self.instance.viewers.discard(self)
        if self.machines is not None:
            self.machines.schedule(self.instance)
        return cursor, carried

    def adopt(self, cursor, carried):
        """接过上一个会话交出的手持物与临时格里的东西（handOver 的返回），存进玩家数据。"""
        self.setCursor(cursor)
        for cid, slots in carried.items():
            self.containers[cid].takeOver(slots)
        self._saveHeld()
        self.save()

    def abandon(self):
        """玩家已经不在世界里：不碰背包，手持物与会话保管的东西留在持久化里，下次进游戏退回。"""
        self._closing(Protocol.CLOSE_LEAVE)
        self.closed = True
        self._release()
        self.instance.viewers.discard(self)

    def setCursor(self, stack):
        """改手持物并持久化。"""
        self.cursor = Items.normalize(stack)
        self.cursorStore.set(self.cursor)

    # ---------------------------------------------------------------- 内部

    def _rollback(self, saved):
        """动作没成：实例状态与这位查看者的状态回到调用之前（saved 是 (实例状态的快照, 查看者状态的副本)）。"""
        self.instance.restore(saved[0])
        if self.viewer != saved[1]:
            self.viewer.clear()
            self.viewer.update(saved[1])

    def _begin(self, everything=False):
        for container in self.containers.values():
            container.begin(everything)

    def _release(self):
        """会话结束：容器放开会话之外拿着的东西（附加容器接着的实例）。"""
        for container in self.containers.values():
            container.release()

    def _rebuildBacking(self):
        backed = {}
        for cid, container in self.containers.items():
            backing = container.backing()
            if backing is not None:
                backed.setdefault((id(backing[0]), backing[1]), []).append(cid)
        self._backed = backed

    def _heldStacks(self):
        stacks = []
        for container in self._held:
            stacks.extend(container.heldStacks())
        return stacks

    def _saveHeld(self):
        if self.heldStore is not None:
            self.heldStore.set(self._heldStacks())

    def _dropHeld(self):
        held = [self.cursor] + self._heldStacks()
        if all(Items.isEmpty(stack) for stack in held):
            return
        for stack in held:
            if not Items.isEmpty(stack):
                self.inventory.drop(stack)
        self.setCursor(None)
        for container in self._held:
            container.clear()
        self._saveHeld()
        self.save()

    def _returnHeld(self):
        """手持物与要退回的容器里的东西退回背包；背包写不进去时整堆丢在脚下，不让东西凭空消失。"""
        if Items.isEmpty(self.cursor) and not self._heldStacks():
            self.setCursor(None)
            return
        self._begin(everything=True)
        workspace = Rules.Workspace(_State(self), self.rules)
        Rules.returnCursor(workspace)
        Rules.returnItems(workspace, self._returning)
        if self._commit(workspace) is None:
            self._dropHeld()

    def _commit(self, workspace, keepPush=False):
        """
        提交工作副本：按容器的先后写，一个写不进去就把前面写过的撤回、什么都不提交，返回 None。改了的推给别的会话（一轮
        推送）；keepPush 为真时成了以后这一轮不结束，调用方回了应答再 instance.endPush()（应答里的界面数据与推给别人的共用）。
        """
        grouped = {}
        for (cid, index), stack in workspace.changes.items():
            grouped.setdefault(cid, {})[index] = stack
        done, committed, before, stored, heldChanged = [], {}, {}, {}, False
        for cid in self._writeOrder:
            if cid not in grouped:
                continue
            container = self.containers[cid]
            written = container.write(grouped[cid])
            if written is None:
                for other, result in reversed(done):
                    other.revert(result)
                return None
            done.append((container, written))
            for index, (old, new) in written.items():
                committed[(cid, index)], before[(cid, index)] = new, old
            backing = container.backing() if written else None
            if backing is not None:
                stored.setdefault(backing, {}).update((index, new) for index, (old, new) in written.items())
            heldChanged = heldChanged or (container.held and bool(written))
        attached = set(instance for instance, _ in stored if instance is not self.instance)   # 写过的附加实例
        try:
            # 部件在格子之外的改动（铁砧扣经验、交易记账）与格子类型的钩子（熔化记账）：格子写好之后、写回存档之前，
            # 钩子改的实例状态随这次一起存下
            for function in workspace.after:
                function()
            if self._takers:
                self._notifyTaken(before, committed)
            if self._changers:
                self._notifyChanged(before, committed)
        finally:
            self.instance.flush()
            wrote = [instance for instance in attached if instance.flush()]
            if heldChanged:
                self._saveHeld()
            for stack in workspace.drops:
                self.inventory.drop(stack)
            self.save()   # 存档由后端判断：没写过东西的不存（Server/Engine.ExtraDataBackend）
            for instance in wrote:
                instance.type.host.save(instance.backend)
        self.instance.beginPush()
        pushed = False
        try:
            self._notifyStored(stored)
            pushed = True
        finally:
            if not (keepPush and pushed):
                self.instance.endPush()   # 推送抛了异常时这一轮也结束（调用方不会再结束它）
        return committed

    def _notifyStored(self, stored):
        """
        改了的实例存储推给看着那份存储的别的会话（打开着那个实例的、把它作为附加容器接上的）；界面模型有界面数据时，
        打开着这个实例的别的会话都推一次（数据可能变了）。每个会话收一条。
        """
        recipients = {}
        for (instance, storageCid), values in stored.items():
            for viewer in list(instance.viewers) + list(instance.attachedViewers):
                if viewer is not self:
                    recipients.setdefault(viewer, {}).update(viewer.storageKeys(instance, storageCid, values))
        if self.menu.data:
            for viewer in self.instance.viewers:
                if viewer is not self:
                    recipients.setdefault(viewer, {})
        others = set(instance for instance, _ in stored if instance is not self.instance)
        for instance in others:
            instance.beginPush()   # 附加着的实例的查看者：同样一轮里只算一次
        try:
            for viewer, changes in recipients.items():
                viewer.containerChanged(changes)
        finally:
            for instance in others:
                instance.endPush()

    def _notifyTaken(self, before, after):
        """格子少了东西（被拿走、转走、丢出）：告诉要知道的格子类型拿走了什么（熔炉的产物格据此给经验）。"""
        for key, old in before.items():
            if Items.isEmpty(old):
                continue
            new = after.get(key)
            taken = Items.count(old) - (0 if Items.isEmpty(new) else Items.count(new))
            if taken <= 0:
                continue
            for name, index in self.structure.refsAt(key):
                if name in self._takers:
                    self.structure.get(name).slot.onTake(self, (name, index), Items.withCount(old, taken))
                    break

    def _notifyChanged(self, before, after):
        """格子的内容变了：告诉要知道的格子类型（装备格据此作用到宿主）。同一个容器格属于几个这种集合时各告诉一次。"""
        for key, old in before.items():
            new = after.get(key)
            for name, index in self.structure.refsAt(key):
                if name in self._changers:
                    self.structure.get(name).slot.onChanged(self, (name, index), old, new)

    def _current(self, state, refs):
        """几个格子现在的内容（拒绝请求时发给客户端更正）：按容器格；不同步的容器（算出的格子）客户端自己算，不发。"""
        out = {}
        for ref in refs:
            key = self.structure.locate(ref)
            if key is not None and self.containers[key[0]].synced:
                out[key] = state.read(key)
        return out

    def _sync(self, changes):
        """{容器格: 物品堆} -> 线上的 sync：按容器交给同步方式（不同步的容器不发），记作已发。"""
        grouped = {}
        for (cid, index), stack in changes.items():
            grouped.setdefault(cid, {})[index] = stack
        payloads = {}
        for cid, values in grouped.items():
            container = self.containers[cid]
            if container.synced:
                container.told(values)
                payloads[cid] = self.syncs[cid].changed(container, values)
        return Protocol.encodeSync(payloads, self.structure)

    def _ack(self, requestId, ok, changes, error=None):
        """
        应答：改了（或要更正）的格子、错误码；成了时带上变了的界面数据（被拒的不算：数据的变化由提交与机器推进推过来），
        变了的每位查看者状态总是带上。
        """
        message = {"s": self.id, "id": requestId, "ok": ok, "sync": self._sync(changes)}
        if error:
            message["err"] = error
        data = self.takeData() if ok else None
        if data:
            message["d"] = data
        viewer = self.takeViewer()
        if viewer:
            message["v"] = viewer
        return message


class ActionContext(object):
    """
    动作执行时拿到的东西：playerId（谁）、instance（实例）、state（实例状态：界面模型自己定内容，只放简单值）、
    viewer（这位查看者的状态 {名字: 值}，界面模型的 viewerState）、ws（工作副本：改格子与格子操作一样，成了整体提交）、
    session（会话：read、creative、giveExperience……）、profile（客户端的界面档，还没报来时为 None）。
    """

    def __init__(self, session, workspace):
        self.session = session
        self.profile = session.profile
        self.playerId = session.playerId
        self.instance = session.instance
        self.viewer = session.viewer
        self.ws = workspace
        self.next = None   # 应答之后要做的切换：("switch", 类型, 实例键, 参数) 或 ("reopen", 参数)

    @property
    def state(self):
        return self.instance.state

    def switchTo(self, typeId, key=None, params=None):
        """应答之后把这位查看者换到另一个容器（页签这类：手持物跟过去，见 Service.switchTo）。"""
        self.next = ("switch", typeId, key, params)

    def reopen(self, params=None):
        """应答之后按新的参数重开这个容器（结构变了：升级、换页；看着这个实例的人都重开，见 Service.reopen）。"""
        self.next = ("reopen", params)


def _titleWire(title):
    """标题的线上写法：字符串照旧（语言文件的键或文字），别的按可本地化的文字（Data.Lang）编码。"""
    if Schema.isText(title):
        return title
    return Data.Lang().encode(title)


def _sameContainer(spec, other):
    """新结构里的 other 与 spec 是同一种、同样格数的容器（切换时临时格里的东西能交过去）。"""
    return other is not None and other.kind == spec.kind and other.size == spec.size


def _initialViewer(menu, instance, playerId):
    """每位查看者状态的初值：各字段的空值，再按界面模型的 viewerInitial 改（只能改声明过的）。"""
    fields = menu.viewerState
    if not fields:
        return {}
    state = dict((name, field.empty) for name, field in fields.items())
    for name, value in (menu.allViewerInitial(instance, playerId) or {}).items():
        if name not in fields:
            raise ValueError("menu %s has no viewer state %r (declare it in viewerState)" % (menu.menuName, name))
        state[name] = value
    return state


class _InventoryOnly(Rules.SlotState):
    """只有背包与手持物（退回遗留的东西时用）。"""

    structure = Collections.Structure().player().finish()

    def __init__(self, inventory, cursor):
        self.inventory = inventory
        self.cursor = cursor

    def read(self, key):
        return self.inventory[key[1]] if key[0] == "player" else self.cursor


def recoverLeftover(inventory, cursorStore, rules, save, heldStore=None):
    """
    玩家进游戏、打开容器时：上次没退回的手持物与会话保管的东西（服务器在界面开着时崩溃留下的）退回背包，
    先手持物、后保管的，每一堆都先补同种堆、再填空格；放不下的丢在脚下。返回退回了没有。
    """
    leftovers = [Items.normalize(cursorStore.get())]
    if heldStore is not None:
        leftovers.extend(Items.normalize(stack) for stack in heldStore.get() or ())
    leftovers = [stack for stack in leftovers if stack is not None]
    if not leftovers:
        return False
    slots = inventory.read()
    current, drops = list(slots), []
    for stack in leftovers:
        workspace = Rules.Workspace(_InventoryOnly(current, stack), rules)
        Rules.returnCursor(workspace)
        for (cid, index), changed in workspace.changes.items():
            if cid == "player":
                current[index] = changed
        drops.extend(workspace.drops)
    changes = dict((index, current[index]) for index in range(PLAYER_SIZE) if not Containers.same(current[index], slots[index]))
    actual = inventory.write(changes) if changes else {}
    if any(not Containers.same(actual.get(index), stack) for index, stack in changes.items()):
        inventory.write(dict((index, slots[index]) for index in changes))
        drops = leftovers
    for stack in drops:
        inventory.drop(stack)
    cursorStore.set(None)
    if heldStore is not None:
        heldStore.set([])
    save()
    return True


def _lockedCells(structure, places):
    """
    宿主要锁住的格子（Host.lockedCells：[(容器种类, 格)]）-> 这个界面里锁住的容器格：界面里那种容器的那一格（格号在容器的
    格数里）；界面里没有那种容器的不锁。
    """
    cells = set()
    for place in places or ():
        if not isinstance(place, (tuple, list)) or len(place) != 2 or not isinstance(place[1], int):
            continue
        kind, index = place
        for cid, spec in structure.containers.items():
            if spec.kind == kind and index >= 0 and (spec.size is None or index < spec.size):
                cells.add((cid, index))
    return frozenset(cells)


def _overrides(obj, name, base):
    """obj 的类改写了 base 的方法 name（py2 的未绑定方法要取出函数再比）。"""
    mine, original = getattr(type(obj), name), getattr(base, name)
    return getattr(mine, "__func__", mine) is not getattr(original, "__func__", original)
