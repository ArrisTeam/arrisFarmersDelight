# -*- coding: utf-8 -*-
"""
客户端镜像：服务端确认过的"底层"加上还没确认的预测请求。

输入一个操作时，在当前看到的状态（底层 + 已有预测）上用同一套规则执行，立即显示结果，同时生成请求发给服务端。
收到应答：服务端给出的格子写进底层，去掉这条请求，剩下的请求在新底层上重放；被拒的那条不再重放。
别处的改动（update）只改底层，然后重放。所以界面上看到的永远是"服务端已确认 + 自己刚做、还在路上的"。

界面模型按开屏消息里的名字与参数在客户端再建一份（见 Common.Menus），预测与服务端跑同一份规则。
底层按容器格存（与服务端同步的单位），每个容器的内容按它的同步方式（Common/Sync）写进来：例如按窗口拉取的容器可能还没
拉全，没拉到的格子当作空格，拉到之后底层更新，预测随之更正。算出的格子（工作台的产物）不同步，按别的格子现算。

界面数据（Common/Data）与这位查看者的状态（界面模型的 viewerState）也在这里：服务端确认过的值，加上还没应答的
可预测动作（Common/Actions）在上面改的。动作的应答到了就去掉它，剩下的可预测动作在新的值上重算：成了的以服务端的值为准，
没成的自然撤回。按查看者算的格子读显示的那一份查看者状态。
请求编号由格子操作与动作共用。
纯逻辑，不依赖引擎。
"""
import time

from ..Common import Actions, Items, Menus, Ops, Protocol, Rules, Sync


class MenuMissing(Exception):
    """开屏消息里的界面模型在客户端没有登记（登记它的模块只在服务端导入了）。"""


class _Base(Rules.SlotState):
    """服务端确认过的状态：{容器: {下标: 物品堆}}，每个容器另有它的同步方式（客户端那一半）。"""

    def __init__(self, structure, accepts):
        self.structure = structure
        self.slots = dict((cid, {}) for cid, spec in structure.containers.items() if spec.info.holdsItems)
        self.syncs = dict((cid, Sync.create(spec)) for cid, spec in structure.containers.items())
        self._accepts = accepts
        self.locked = frozenset()   # 锁住的容器格（开屏消息的 lock）

    def lockedCells(self):
        return self.locked

    def read(self, key):
        slots = self.slots.get(key[0])
        return slots.get(key[1]) if slots is not None else None

    def highestUsed(self, cid):
        return self.syncs[cid].highestUsed(self.slots.get(cid, {}))

    def findKind(self, cid, stack):
        return self.syncs[cid].findKind(self.slots.get(cid, {}), stack)

    def freeIndex(self, cid):
        return self.syncs[cid].freeIndex(self.slots.get(cid, {}))

    def accepts(self, ref, stack):
        return self._accepts(ref, stack)

    def apply(self, cid, payload):
        """服务端发来的一个容器的载荷写进来（不放东西的容器不收）。"""
        slots = self.slots.get(cid)
        if slots is not None:
            self.syncs[cid].apply(slots, payload)


class _View(Rules.SlotState):
    """底层加上预测改动后的状态（界面显示的就是它）。"""

    def __init__(self, base, changes, tops, viewer, mirror):
        self.base = base
        self.structure = base.structure
        self.changes = changes   # {容器格: 物品堆}
        self.tops = tops         # {容器: 末尾下标}，算上预测
        self.viewer = viewer     # 显示的这位查看者的状态（镜像就地更新它）
        self._mirror = mirror    # 面板关着的集合、界面数据都按镜像显示的算
        self.creative = mirror.creative
        self.playerId = mirror.playerId
        self.menu = mirror.menu

    def clientValue(self, name):
        return self._mirror.clientValue(name)

    def closedCollections(self):
        return self._mirror.closedCollections()

    def dataValue(self, name):
        return self._mirror.dataValue(name, time.time())

    def lockedCells(self):
        return self.base.locked

    def read(self, key):
        if key in self.changes:
            return self.changes[key]
        return self.base.read(key)

    def get(self, ref):
        """格子 ref 显示什么（算出的格子按预测之后的内容算，内容来自界面数据的格子读显示的界面数据）。"""
        structure = self.structure
        if ref[0] in structure.derivers:
            return structure.derived(ref, self.get, self.viewer)
        shown = structure.dataBacked.get(ref[0])
        if shown is not None:
            return (self.dataValue(shown) or {}).get(ref[1])
        key = structure.locate(ref)
        return self.read(key) if key is not None else None

    def highestUsed(self, cid):
        return self.tops.get(cid, -1)

    def findKind(self, cid, stack):
        """先看预测改过的格子，再按底层的索引找（预测里那一格已经空了或换了种类时不算）。"""
        for (container, index), item in self.changes.items():
            if container == cid and Items.sameKind(item, stack):
                return index
        index = self.base.findKind(cid, stack)
        if index is not None and Items.sameKind(self.read((cid, index)), stack):
            return index
        return None

    def freeIndex(self, cid):
        """底层的空格与预测里空出来的格子里最前面的一个（预测里已经放了东西的往后找）。"""
        candidates = [index for (container, index), item in self.changes.items()
                      if container == cid and Items.isEmpty(item)]
        candidates.append(self.base.freeIndex(cid))
        for index in sorted(candidates):
            if Items.isEmpty(self.read((cid, index))):
                return index
        index = max(candidates) + 1
        while not Items.isEmpty(self.read((cid, index))):
            index += 1
        return index

    def accepts(self, ref, stack):
        return self.base.accepts(ref, stack)


class PredictView(object):
    """
    可预测的动作在客户端改的东西：data 是界面数据现在显示的值 {名字: 值}（没收到的是字段类型的空值），
    viewer 是这位查看者的状态 {名字: 值}。
    """

    def __init__(self, data, viewer):
        self.data = data
        self.viewer = viewer


class Mirror(object):

    def __init__(self, openMessage, rules, accepts=None, now=None):
        """accepts(ref, stack)：集合规则之外另加的规则（客户端能算的部分），不给时都收。"""
        self.rules = rules
        self.sessionId = openMessage["s"]
        self.dropAllowed = openMessage.get("drop", True) is not False   # 开屏时玩家能不能往世界里丢东西
        self.creative = openMessage.get("cr") is True                    # 开屏时玩家是不是创造模式
        self.playerId = openMessage.get("pid")                           # 本地玩家（规则的 ws.playerId）
        self.clientState = {}      # 客户端界面状态（客户端会话接上它那一份；规则经 ws.client 读）
        self.clientRevision = 0    # 客户端界面状态改一次加一（格子装饰依赖它时跟着重画）
        self.menu = Menus.create(openMessage.get("menu"), openMessage.get("params"), Menus.CLIENT, rules)
        if self.menu is None:
            raise MenuMissing(openMessage.get("menu"))
        self.structure = structure = self.menu.structure
        # 不设上限的容器：显示几格随最后一个非空格变，预测时要跟着算
        self._unsized = [cid for cid, spec in structure.containers.items() if spec.size is None]
        self.base = _Base(structure, accepts or (lambda ref, stack: True))
        self.base.menu = self.menu
        self.base.locked = _lockedCells(structure, openMessage.get("lock"))
        self._apply(openMessage)
        self.pending = []          # [(请求编号, 操作, 界面档)]
        self._nextId = 1
        empty = dict((name, field.empty) for name, field in self.menu.viewerState.items())
        self.confirmedViewer = dict(empty)   # 这位查看者的状态，服务端确认过的
        self.viewer = empty                  # 显示的（算上还没应答的预测）；按查看者算的格子读它，就地更新
        self.view = _View(self.base, {}, self._baseTops(), self.viewer, self)
        self.revision = 0          # 显示内容每变一次加一，界面据此判断要不要重画
        self.dataRevision = 0      # 界面数据或这位查看者的状态每变一次加一（格子装饰据此重画）
        self.lastChanges = {}      # 最近一次预测改了哪些容器格：{容器格: (之前, 之后)}，用于物品飞行动画
        self.data = {}             # 界面数据：名字 -> (值, 收到的时间)，服务端确认过的
        self.calls = []            # 还没应答的动作：[(请求编号, 动作, 参数, 回调)]
        self.predicted = {}        # 可预测的动作改过的界面数据：名字 -> (值, 改的时间)
        self._applyData(openMessage, _now(now))
        self._predict(_now(now))

    # ---------------------------------------------------------------- 读

    def get(self, ref):
        return self.view.get(ref)

    def displayed(self, ref, preview):
        """手势预览（{容器格: 物品堆}）叠在显示内容上之后，格子 ref 显示什么。"""
        if not preview:
            return self.view.get(ref)
        structure = self.structure
        if ref[0] in structure.derivers:
            return structure.derived(ref, lambda other: self.displayed(other, preview), self.viewer)
        if ref[0] in structure.dataBacked:
            return self.view.get(ref)
        key = structure.locate(ref)
        if key is None:
            return None
        return preview[key] if key in preview else self.view.read(key)

    def key(self, ref):
        """格子落在哪个容器格。"""
        return self.structure.locate(ref)

    def keyOrder(self, key):
        """容器格的先后（物品飞行按它配对）：按界面模型声明容器的顺序，同一容器里按下标。"""
        return (self.structure.containerId(key[0]), key[1])

    def size(self, name, extraTop=-1):
        """
        集合现在显示几格：有格数的就是格数（算出的集合的部件另给了 shown 时按它，不超过格数：切石机的配方随原料变）；
        不设上限的按预测之后的末尾格算，extraTop（集合内下标）当作也放了东西。
        """
        collection = self.structure.get(name)
        if collection is None:
            return 0
        part = self.structure.derivers.get(name)
        shown = getattr(part, "shown", None) if part is not None else None
        if shown is not None:
            return max(0, min(collection.size, int(shown(name, self.view.get, self.viewer))))
        if collection.size is not None:
            return collection.size
        top = max(self.view.highestUsed(collection.cid) - collection.offset, extraTop)
        return collection.sizer.visibleCount(top)

    def dataValue(self, name, now):
        """界面数据现在的值：由字段类型从值算（会动的数按时间往前算）；还没收到时是字段类型的空值，不是数据字段时为 None。"""
        field = self.menu.data.get(name)
        if field is None:
            return None
        entry = self.predicted.get(name) or self.data.get(name)
        if entry is None:
            return field.empty
        return field.current(entry[0], entry[1], now)

    def viewerValue(self, name):
        """这位查看者的状态现在显示的值（算上还没应答的预测）；不是声明过的名字为 None。"""
        return self.viewer.get(name)

    def panelOpen(self, name, now=None):
        """面板 name 现在开着没有（按显示的每位查看者状态或界面数据算）；没有这个面板时为 False。"""
        panel = self.structure.panels.get(name)
        return panel is not None and panel.opens(self._switchValue(panel.switch, _now(now)))

    def closedCollections(self, now=None):
        """停用的集合（面板关着的、断开了的附加容器上的）：预测时工作副本问它。"""
        now = _now(now)
        return self.structure.closedCollections(lambda panel: panel.opens(self._switchValue(panel.switch, now)),
                                                self.viewer)

    def _switchValue(self, name, now):
        return self.viewer.get(name) if name in self.menu.viewerState else self.dataValue(name, now)

    def clientValue(self, name):
        """客户端界面状态现在的值（没改过时是字段的空值；界面模型没有这个名字时为 None）。"""
        field = self.menu.clientState.get(name)
        return self.clientState.get(name, field.empty) if field is not None else None

    def contents(self, cid):
        """
        容器 cid 现在显示的格子：服务端确认过的加上还没应答的预测，{下标: 物品堆}（只有非空的；没有预测时是镜像自己那份，
        不要改它）。
        """
        slots = self.base.slots.get(cid, {})
        changes = self.predictedSlots(cid)
        if not changes:
            return slots
        slots = dict(slots)
        for index, stack in changes.items():
            if Items.isEmpty(stack):
                slots.pop(index, None)
            else:
                slots[index] = stack
        return slots

    def predictedSlots(self, cid):
        """容器 cid 里预测改了、还没应答的格子：{下标: 物品堆或 None}。"""
        return dict((index, stack) for (container, index), stack in self.view.changes.items() if container == cid)

    def syncOf(self, cid):
        """容器 cid 的同步方式（客户端那一半，Common/Sync；同步方式自己的东西，例如列表增量的修订号）。"""
        return self.base.syncs.get(cid)

    def wants(self, cid, start, end, now):
        """界面要显示容器 cid 的 [start, end)：它的同步方式还要向服务端拉的话返回查询，否则 None。"""
        return self.base.syncs[cid].wants(start, end, now)

    # ---------------------------------------------------------------- 本地操作

    def predict(self, op, profile):
        """在当前显示的状态上执行操作并生成请求；操作什么都没改变时返回 None（不发请求）。"""
        workspace = Rules.Workspace(self.view, self.rules)
        try:
            done = Ops.apply(workspace, op, profile)
        except Rules.RuleError:
            return None
        if not done and not workspace.changes:
            return None
        structure = self.structure
        expects = [(ref, Items.fingerprint(self.view.get(ref))) for ref in Ops.involvedRefs(op)
                   if structure.get(ref[0]) is not None]
        Ops.checkExpects(op, expects)   # 声明的格子太多：在改显示之前报错
        requestId, self._nextId = self._nextId, self._nextId + 1
        self.pending.append((requestId, op, profile))
        self.lastChanges = dict((key, (self.view.read(key), stack)) for key, stack in workspace.changes.items())
        self._applyToView(workspace)
        request = Ops.encodeRequest(requestId, op, expects, profile, structure)
        request["s"] = self.sessionId
        return request

    def call(self, name, args=(), now=None, done=None):
        """
        发动作（Common/Actions）：args 是线上写法的参数，按动作的参数格式先在这边查一遍。动作不是这个界面模型的、
        参数不对时返回 None（不发）。可预测的动作先在显示的界面数据上改。done(成没成, 返回值) 在应答到了时调用（没成时第二个参数
        是错误码）。
        返回请求（带会话编号）。
        """
        action = self.menu.actions.get(name)
        if action is None:
            return None
        try:
            values = action.parseArgs(list(args), self.structure)
        except Actions.BadRequest:
            return None
        requestId, self._nextId = self._nextId, self._nextId + 1
        self.calls.append((requestId, action, values, done))
        if action.predict is not None:
            self._predict(_now(now))
        request = Actions.encodeCall(requestId, name, action.encodeArgs(values, self.structure))
        request["s"] = self.sessionId
        return request

    def preview(self, op, profile):
        """只算不记：返回执行后会变成什么样（{容器格: 物品堆}），用于拖动分配与按住时的实时预览。"""
        workspace = Rules.Workspace(self.view, self.rules)
        try:
            Ops.apply(workspace, op, profile)
        except Rules.RuleError:
            return {}
        return dict(workspace.changes)

    # ---------------------------------------------------------------- 服务端消息

    def onAck(self, ack, now=None):
        now = _now(now)
        self._apply(ack)
        self._applyData(ack, now)
        requestId = ack.get("id")
        ok = bool(ack.get("ok"))
        self.pending = [entry for entry in self.pending if entry[0] != requestId]
        answered = [entry for entry in self.calls if entry[0] == requestId]
        self.calls = [entry for entry in self.calls if entry[0] != requestId]
        self._replay()
        self._predict(now)
        for _, _, _, done in answered:
            if done is not None:
                done(ok, ack.get("r") if ok else ack.get("err"))
        return ok

    def onUpdate(self, update, now=None):
        """别处的改动或拉取的应答。"""
        now = _now(now)
        self._apply(update)
        self._applyData(update, now)
        self._replay()
        self._predict(now)

    def dropPending(self):
        """放弃所有未确认的预测（例如关界面时）。"""
        self.pending = []
        self.calls = []
        self._replay()
        self._predict(_now(None))

    # ---------------------------------------------------------------- 内部

    def _apply(self, message):
        """服务端消息里各容器的载荷写进底层。"""
        for cid, payload in Protocol.decodeSync(message, self.structure).items():
            self.base.apply(cid, payload)

    def _applyData(self, message, now):
        """
        服务端消息里的界面数据与这位查看者的状态按字段类型解码（不认识的、解不开的丢掉）。界面数据按字段类型的 receive 接在
        现在的值上（增量的列表与映射只发了改动）。
        """
        for key, fields, store, timed in (("d", self.menu.data, self.data, True),
                                          ("v", self.menu.viewerState, self.confirmedViewer, False)):
            for name, wire in (message.get(key) or {}).items():
                field = fields.get(name)
                if field is None:
                    continue
                try:
                    if timed:
                        value = field.receive(store[name][0] if name in store else None, wire)
                    else:
                        value = field.decode(wire)
                except (TypeError, ValueError, IndexError, KeyError, AttributeError):
                    continue
                store[name] = (value, now) if timed else value
                self.dataRevision += 1

    def _predict(self, now):
        """
        可预测的动作在确认过的界面数据上按顺序重算一遍（应答到了、服务端的值变了都重算）。改成与确认过的一样的不算预测；
        一直预测成同一个值的保留原来的时间（会动的数不从头走）。预测本身出错时跳过那一个：请求照样发，以服务端为准。
        """
        fields = self.menu.data
        predicting = [entry for entry in self.calls if entry[1].predict is not None]
        predicted, shown = {}, self.confirmedViewer
        if predicting:
            confirmed = dict((name, self.data[name][0] if name in self.data else field.empty)
                             for name, field in fields.items())
            view = PredictView(dict(confirmed), dict(self.confirmedViewer))
            for _, action, values, _ in predicting:
                try:
                    action.predict(self.menu, view, *values)
                except Exception:  # noqa: BLE001
                    continue
            for name, value in view.data.items():
                if name not in fields or value == confirmed.get(name):
                    continue
                previous = self.predicted.get(name)
                predicted[name] = previous if previous is not None and previous[0] == value else (value, now)
            shown = dict((name, view.viewer.get(name)) for name in self.menu.viewerState)
        changed = predicted != self.predicted or shown != self.viewer
        self.predicted = predicted
        if shown != self.viewer:
            self.viewer.clear()
            self.viewer.update(shown)
        if changed:
            self.revision += 1
            self.dataRevision += 1

    def _baseTops(self):
        return dict((cid, self.base.highestUsed(cid)) for cid in self._unsized)

    def _applyToView(self, workspace):
        changes = dict(self.view.changes)
        changes.update(workspace.changes)
        tops = dict(self.view.tops)
        for cid in self._unsized:
            tops[cid] = workspace.highestUsed(cid)
        self.view = _View(self.base, changes, tops, self.viewer, self)
        self.revision += 1

    def _replay(self):
        self.view = _View(self.base, {}, self._baseTops(), self.viewer, self)
        kept = []
        for requestId, op, profile in self.pending:
            workspace = Rules.Workspace(self.view, self.rules)
            try:
                Ops.apply(workspace, op, profile)
            except Rules.RuleError:
                continue
            kept.append((requestId, op, profile))
            self._applyToView(workspace)
        self.pending = kept
        self.revision += 1


def _lockedCells(structure, wire):
    """开屏消息的 lock（[[容器编号, 下标], ...]）-> 锁住的容器格；写错的项不要。"""
    cells = set()
    for entry in wire or ():
        if isinstance(entry, (list, tuple)) and len(entry) == 2 and all(isinstance(value, int) for value in entry):
            cid = structure.containerName(entry[0])
            if cid is not None:
                cells.add((cid, entry[1]))
    return frozenset(cells)


def _now(now):
    return time.time() if now is None else now
