# -*- coding: utf-8 -*-
"""
服务端接线：会话管理、客户端可调的端点、生命周期事件。对外的入口见 Api.py。

端点只信框架注入的调用者 ID；每位玩家同一时间最多一个会话；请求按令牌桶限频（操作与动作的限频由会话在校验时问）。
几个模组各带一份本库时，同一位玩家同一时间只开一个容器：打开前经 Common.Shared 让别的使用方关掉它开着的。
高频事件（背包变化、逐刻刷新、拾取）只在用得着时监听：没开容器的这份库不占它们。
机器（Server/Machines.py）：时钟走着或有唤醒排着时数引擎每推进一刻的事件；机器的时钟由宿主给（Server/Hosts.py），
登记机器时接上，玩家进出游戏时转告它。
"""
import time

import mod.server.extraServerApi as serverApi

from ...QuModLibs.Server import AllowCall, Call, InjectHttpPlayerId, Listen, ListenForEvent, TickEvent, \
    UnListenForEvent
from .. import HOST
from ..Common import Collections, Modules, Ops, Protocol, Schema, Shared
from ..Common.RateLimit import TokenBucket
from ..Std.Server import Defaults  # noqa: F401  库自带的缺省实现（原版操作、容器种类……）随之登记
from . import Containers as ContainerKinds, Engine, Machines, Registry, Storage
from .Session import HOST_GONE, Session, recoverLeftover

CLIENT_ENDPOINT = "dolorContainerOnMessage"
_EVENTS = object()   # 动态监听的名字空间：QuModLibs 按（名字空间，函数名）给监听起名、引擎按名字回调，不带名字空间时
                     # 同一个模组里同名的处理函数（库里的、使用方的）会串成一个
RATE_CAPACITY, RATE_PER_SECOND = 60, 30   # 每位玩家的请求令牌：最多攒这么多，每秒补这么多（Api.setRateLimit 可改）
_bucket = TokenBucket(capacity=RATE_CAPACITY, rate=RATE_PER_SECOND)
_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
Modules.addEngineImporter(serverApi.ImportModule)   # 可选件用到才载入（Common/Modules.py）：importlib 还没载入时经引擎导入

# 原版箱子类界面在玩家受到生物造成的伤害时关闭（这几种伤害来源算"生物造成"）。
# 自动关闭之后 5 秒内不再自动关闭，这 5 秒从最近一次这类伤害算起（界面没开时挨的打也算）：
# 持续挨打时重新打开的界面不会被反复关掉。来源与冷却可改（Api.setHurtClose，存在 Manager 上）。
HURT_CLOSE_CAUSES = frozenset(("entity_attack", "projectile", "entity_explosion", "magic", "sonic_boom", "mace_smash"))
HURT_CLOSE_COOLDOWN = 5.0
_lastMobHurt = {}
_players = set(serverApi.GetPlayerList() or ())   # 在线玩家：受伤事件里判断是不是玩家，不必每次向引擎要列表


def log(message):
    print("[dolorContainer:%s] %s" % (HOST, message))


def _backendFor(host, key):
    return host.backend(key)


class Manager(object):

    def __init__(self):
        self.registry = Registry.Registry(_backendFor, Engine.RULES)
        self.machines = Machines.Machines(self.registry, lambda on: _listenTicks(on), self.registry.release)
        self.sessions = {}
        self.dirty = set()
        self.ticking = set()   # 有每刻要检查的容器（附加容器）的会话（会话结束时拿掉）
        self.validating = set()   # 宿主改写了 stillValid 的会话：每刻问一次，不再有效就关掉（会话结束时拿掉）
        self._clocks = []    # 登记过的机器用到的时钟
        self._clocked = set()   # 接上了时钟的容器类型：机器，以及有后台行为的
        self._behaviorEvents = set()   # 后台行为要的、已经在监听的引擎事件
        self._nextId = 1
        self._watching = False
        self.hurtCauses = HURT_CLOSE_CAUSES        # 算"生物造成"的伤害来源（受伤关界面只看这些）
        self.hurtCooldown = HURT_CLOSE_COOLDOWN    # 自动关闭之后多少秒内不再自动关闭
        self._hurtListening = False

    def send(self, playerId, kind, message):
        Call(playerId, CLIENT_ENDPOINT, kind, message)

    def players(self):
        """在线玩家。"""
        return list(_players)

    # ---------------------------------------------------------------- 容器类型与机器的时钟

    def register(self, containerType):
        self.registry.register(containerType)
        if containerType.menu(self.registry.itemRules).machine:
            self._attachClock(containerType)
        if containerType.closeOnHurt and not self._hurtListening:
            # 有要受伤关闭的容器类型才监听受伤事件（冷却从界面没开时挨的打算起，所以从这时起一直听）
            self._hurtListening = True
            ListenForEvent("ActorHurtServerEvent", _EVENTS, _onHurt)
        return containerType

    def addBehavior(self, typeId, behavior):
        """
        给容器类型加后台行为（Machines.Behavior）：宿主要有时钟（实例的时钟走着时才跑），不是机器的类型这时接上时钟；
        行为要的引擎事件在这时才监听。
        """
        containerType = self.registry.get(typeId)
        if containerType is None:
            raise ValueError("container type %s is not registered" % typeId)
        if containerType.host.clock is None:
            raise ValueError("a background behavior needs a host with a clock: %s" % typeId)
        self.machines.addBehavior(typeId, behavior)
        self._attachClock(containerType)
        for event in behavior.events:
            if event not in self._behaviorEvents:
                self._behaviorEvents.add(event)
                ListenForEvent(event, _EVENTS, _behaviorHandler(event))

    def _attachClock(self, containerType):
        clock = containerType.host.clock
        if clock is None or containerType.typeId in self._clocked:
            return
        self._clocked.add(containerType.typeId)
        if clock not in self._clocks:
            self._clocks.append(clock)
        clock.attach(self, containerType)

    def playerJoined(self, playerId):
        for clock in self._clocks:
            clock.playerJoined(self, playerId)

    def playerLeft(self, playerId):
        """玩家要离开（这时还能读他的状态）：他身上带着的机器与按他存放的机器停下，推进到现在存下来。"""
        for clock in self._clocks:
            clock.playerLeft(self, playerId)

    # ---------------------------------------------------------------- 打开与关闭

    def openHeld(self, playerId):
        """
        打开玩家手上那件物品绑定的容器（宿主服务几个容器类型时打开哪个由宿主的 typeFor 定，实例键由宿主定，例如物品上记的
        编号）。返回是否打开。
        """
        stack = Engine.heldItem(playerId)
        typeId = self.registry.itemTypes.get(stack["newItemName"]) if stack else None
        if typeId is not None:
            typeId = self.registry.get(typeId).host.typeFor(playerId, None)
        return typeId is not None and self.open(playerId, typeId)

    def open(self, playerId, typeId, key=None, params=None):
        """
        为玩家打开某个容器实例（key 为 None 时由宿主定；params 是界面模型这一次的参数，不给时用登记时的），返回是否打开。
        已经开着别的（包括别的模组的）就先关掉。
        """
        target = self._target(playerId, typeId, key)
        if target is None:
            return False
        self._end(playerId, Protocol.CLOSE_REOPEN)
        Shared.claim(("server", playerId), HOST, self._release, log)
        instance = self._instance(target, params)
        if instance is None:
            Shared.unclaim(("server", playerId), HOST)
            return False
        session = self._session(playerId, instance)
        session.recoverCursor()
        self._install(playerId, session)
        self.send(playerId, "open", session.openMessage())
        return True

    def switchTo(self, playerId, typeId, key=None, params=None):
        """
        把玩家开着的容器换成另一个（另一种宿主或界面模型，页签这类）：手持物跟过去，临时格按新结构里还在不在决定交过去
        还是退回背包；客户端换界面不关上再打开。没开着时就是 open；换到同一个实例就是 reopen。返回是否换了。
        """
        old = self.sessions.get(playerId)
        if old is None:
            return self.open(playerId, typeId, key, params)
        target = self._target(playerId, typeId, key)
        if target is None:
            return False
        if target == old.instance.handle:
            return self.reopen(playerId, params)
        instance = self._instance(target, params)
        if instance is None:
            return False
        cursor, carried = old.handOver(instance.structure)
        self._forget(old)
        self.registry.viewersChanged(old.instance, self._invalidated)
        self.registry.release(old.instance)
        self._switched(playerId, self._session(playerId, instance), cursor, carried)
        return True

    def reopen(self, playerId, params=None):
        """
        按新的参数重开玩家开着的容器（宿主的状态变得影响结构：升级、换页）：看着这个实例的人都重开（实例只有一个结构），
        各自的手持物与临时格照 switchTo 的规矩交接。新参数建不出界面模型时什么都不动。返回是否重开了。
        """
        session = self.sessions.get(playerId)
        if session is None:
            return False
        old = session.instance
        try:
            structure = old.type.menu(self.registry.itemRules, params).structure
        except (TypeError, ValueError) as error:
            log("cannot reopen %s %r with %r: %s" % (old.type.typeId, old.key, params, error))
            return False
        viewers = [viewer for viewer in list(old.viewers) if self.sessions.get(viewer.playerId) is viewer]
        handed = [(viewer, viewer.handOver(structure)) for viewer in viewers]
        for viewer in viewers:
            self._forget(viewer)
        self.registry.viewersChanged(old, self._invalidated)
        self.registry.release(old)
        instance = self._instance((old.type.typeId, old.key), params)
        for viewer, (cursor, carried) in handed:
            if instance is None:
                # 存档读不了：照崩溃后的规矩把手持物与交出的东西退回背包，关掉界面
                self.sessions.pop(viewer.playerId, None)
                Shared.unclaim(("server", viewer.playerId), HOST)
                recoverLeftover(viewer.inventory, viewer.cursorStore, Engine.RULES, viewer.save, viewer.heldStore)
                self.send(viewer.playerId, "close", {"s": viewer.id, "reason": Protocol.CLOSE_REOPEN_FAILED})
            else:
                self._switched(viewer.playerId, self._session(viewer.playerId, instance), cursor, carried)
        self._watch()
        return instance is not None

    def updateInstance(self, typeId, key, change):
        """
        宿主在会话之外改一个实例（方块收到红石信号、漏斗往里送东西这类）：实例没加载时读出来；机器先推进到现在；
        change(实例) 里改格子（instance.set）与实例状态；改完写回存储、推给看着的人（与机器推进一样），没人看时放回缓存。
        时钟记着的类型（机器）改过的实例与打开过的一样记下，时钟照常走（漏斗往没人打开过的酿造台里送东西，它要自己酿）。
        返回 change 的返回值。类型没登记时抛 ValueError。
        """
        containerType = self.registry.get(typeId)
        if containerType is None:
            raise ValueError("container type %s is not registered" % typeId)
        if typeId in self._clocked:
            containerType.host.clock.track(self, (typeId, key))
        return self.machines.update(typeId, key, change)

    def peekInstance(self, typeId, key, reader):
        """只读一个实例（Api.peekInstance）：没加载时读出来，用完放回缓存。类型没登记时抛 ValueError。"""
        if self.registry.get(typeId) is None:
            raise ValueError("container type %s is not registered" % typeId)
        loaded = self.registry.loaded((typeId, key))
        instance = loaded if loaded is not None else self.registry.instance(typeId, key)
        try:
            return reader(instance)
        finally:
            if loaded is None:
                self.registry.release(instance)

    def discard(self, typeId, key, spill):
        """
        实例的宿主没了（方块被挖掉、炸掉这类）：看着它的会话关掉（手持物与临时格照常退回），实例存储里的东西逐件交给
        spill(物品堆)（方块宿主让它们掉在原地），存储与实例状态清空，记着的这个实例忘掉（同一个地方再放一个方块时从空的读起）。
        实例读不出来（存档版本更新、参数对不上）时只关会话、忘掉它。
        """
        live = self.registry.loaded((typeId, key))
        if live is not None:
            self._invalidated(live)
        try:
            if self.registry.hasData(typeId, key):
                self.registry.empty(typeId, key, spill)
            else:
                self.registry.drop((typeId, key))   # 没存过东西（没打开过的方块）：不用读出来清
        except (Storage.StorageError, ValueError, TypeError) as error:
            log("cannot empty %s %r: %s" % (typeId, key, error))
        if typeId in self._clocked:
            self.registry.get(typeId).host.clock.untrack(self, (typeId, key))

    def _target(self, playerId, typeId, key):
        """
        (类型, 实例键)：类型登记过、玩家照游戏的规矩能用容器（宿主的 visitors 为真时不查）、宿主给出实例键并且让这位玩家
        打开；不行时为 None。游戏的规矩在宿主给实例键之前查（物品宿主给键时会往物品上写编号）。
        """
        containerType = self.registry.get(typeId)
        if containerType is None:
            return None
        host = containerType.host
        if not host.visitors and not Engine.mayOpenContainers(playerId):
            return None
        key = host.keyFor(playerId, key)
        if key is None or not host.canOpen(playerId, key):
            return None
        return typeId, key

    def _instance(self, target, params):
        try:
            instance = self.registry.instance(target[0], target[1], params)
        except (Storage.StorageError, ValueError, TypeError) as error:
            # 存档读不了（例如更新的版本存的）、别人正用别的参数看着、参数建不出界面模型：不打开，免得把它写坏
            log("cannot open %s %r: %s" % (target[0], target[1], error))
            return None
        if instance.type.typeId in self._clocked:
            instance.type.host.clock.track(self, instance.handle)
        return instance

    def _session(self, playerId, instance):
        sessionId, self._nextId = self._nextId, self._nextId + 1
        return Session(sessionId, playerId, instance, Engine.PlayerInventory(playerId), Engine.CursorStore(playerId),
                       Engine.RULES, lambda kind, message: self.send(playerId, kind, message),
                       self._saver(playerId, instance), Engine.HeldStore(playerId), self.machines,
                       lambda cost=1.0: _bucket.allow(playerId, time.time(), cost), self.registry)

    def _install(self, playerId, session):
        """
        会话开起来：记下，有附加容器、宿主要每刻查有效性的每刻检查，告诉宿主看的人变了，按需监听事件，调界面模型的 onOpen
        （在开屏消息之前）。
        """
        self.sessions[playerId] = session
        if session.ticking:
            self.ticking.add(session)
        if session.checksHost:
            self.validating.add(session)
        self.registry.viewersChanged(session.instance, self._invalidated)
        self._watch()
        session.opened()

    def _forget(self, session):
        """会话结束：不再每刻检查它。"""
        self.ticking.discard(session)
        self.validating.discard(session)

    def _invalidated(self, instance):
        """宿主报了失效事件（Host.watch）：看着这个实例的会话都关掉，手持物与临时格退回。"""
        for viewer in list(instance.viewers):
            if self.sessions.get(viewer.playerId) is viewer:
                self.close(viewer.playerId, HOST_GONE)

    def _switched(self, playerId, session, cursor, carried):
        """切换出来的新会话：接过手持物与临时格，客户端换界面（开屏消息带 switch）。"""
        session.adopt(cursor, carried)
        self._install(playerId, session)
        self.dirty.discard(playerId)
        message = session.openMessage()
        message["switch"] = True
        self.send(playerId, "open", message)

    def _release(self, key):
        """别的模组的容器要为这位玩家打开：关掉这边的（手持物退回背包，通知客户端关界面）。"""
        self.close(key[1], Protocol.CLOSE_REPLACED)

    def close(self, playerId, reason, notify=None, dropCursor=False):
        """
        关掉玩家开着的容器（原因见 Common/Protocol 的 CLOSE_*，SILENT 里的不通知客户端）：手持物与临时格退回背包；
        dropCursor 为真时整堆丢在原地（死了且背包已经掉光时）。没开着时返回 False。
        """
        if not self._end(playerId, reason, notify, dropCursor):
            return False
        self._watch()
        return True

    def _end(self, playerId, reason, notify=None, dropCursor=False):
        session = self.sessions.pop(playerId, None)
        if session is None:
            return False
        Shared.unclaim(("server", playerId), HOST)
        session.close(reason, notify, dropCursor)
        self._forget(session)
        self.registry.viewersChanged(session.instance, self._invalidated)
        self.registry.release(session.instance)
        self.dirty.discard(playerId)
        return True

    def abandon(self, playerId):
        session = self.sessions.pop(playerId, None)
        if session is not None:
            Shared.unclaim(("server", playerId), HOST)
            session.abandon()
            self._forget(session)
            self.registry.viewersChanged(session.instance, self._invalidated)
            self.registry.release(session.instance)
        self.registry.forget(playerId)
        self.dirty.discard(playerId)
        _bucket.forget(playerId)
        self._watch()

    def _watch(self):
        """背包变化与逐刻刷新只在有会话开着时监听。"""
        watching = bool(self.sessions)
        if watching == self._watching:
            return
        self._watching = watching
        if watching:
            ListenForEvent("InventoryItemChangedServerEvent", _EVENTS, _onInventoryChanged)
            ListenForEvent(TickEvent, _EVENTS, _onTick)
            # 动态监听下一刻才生效：这之间背包变了也要推给客户端，第一刻整个对一遍
            self.dirty.update(self.sessions)
        else:
            UnListenForEvent("InventoryItemChangedServerEvent", _EVENTS, _onInventoryChanged)
            UnListenForEvent(TickEvent, _EVENTS, _onTick)

    def _saver(self, playerId, instance):
        player = Engine.ExtraDataBackend(playerId)
        host, backend = instance.type.host, instance.backend

        def save():
            player.save()
            host.save(backend)
        return save

    def session(self, playerId, data):
        """端点用：调用者当前的会话，且与请求里的会话编号一致。"""
        session = self.sessions.get(playerId)
        return session if session is not None and session.matches(data) else None


Shared.forgetHost(HOST, "server")   # 重新载入时，上一次载入的登记已经失效
_manager = Manager()


def manager():
    return _manager


# ---------------------------------------------------------------- 客户端可调的端点


@AllowCall
@InjectHttpPlayerId
def dolorContainerAct(playerId, data):
    session = _manager.session(playerId, data)
    if session is None:
        _noSession(playerId, data)
        return
    _manager.send(playerId, "ack", session.handleAction(data))
    _afterReply(playerId, session)


@AllowCall
@InjectHttpPlayerId
def dolorContainerCall(playerId, data):
    """动作（Common/Actions）：校验由会话集中做；宿主对这位玩家不再有效时回了应答就关掉会话。"""
    session = _manager.session(playerId, data)
    if session is None:
        _noSession(playerId, data)
        return
    message = session.handleCall(data)
    _manager.send(playerId, "ack", message)
    if message.get("err") == HOST_GONE:
        _manager.close(playerId, HOST_GONE)
        return
    _afterReply(playerId, session)


def _afterReply(playerId, session):
    """
    回了应答之后做会话登记的切换或重开（动作里的 ctx.switchTo / ctx.reopen，格子类型 onChanged 里的 session.reopenAfter）：
    先回应答，客户端按顺序先认这一下，再换界面。
    """
    step, session.next = session.next, None
    if step is not None and _manager.sessions.get(playerId) is session:
        if step[0] == "switch":
            _manager.switchTo(playerId, step[1], step[2], step[3])
        else:
            _manager.reopen(playerId, step[1])


def _noSession(playerId, data):
    """请求的会话不是调用者现在开着的：让客户端关掉它以为开着的那个。"""
    _manager.send(playerId, "close", {"s": data.get("s") if isinstance(data, dict) else 0,
                                      "reason": Protocol.CLOSE_NO_SESSION})


@AllowCall
@InjectHttpPlayerId
def dolorContainerReq(playerId, data):
    """客户端按容器的同步方式拉取（例如按窗口拉取的一段）。"""
    session = _manager.session(playerId, data)
    if session is None or not _bucket.allow(playerId, time.time(), 0.25):
        return
    try:
        _, cid, query = Protocol.parseReq(data, session.structure)
        message = session.handleRequest(cid, query)
    except Ops.BadRequest:
        return
    _manager.send(playerId, "update", message)


@AllowCall
@InjectHttpPlayerId
def dolorContainerProfile(playerId, data):
    """客户端报它的界面档（开屏后、界面开着时切换了界面档后各一次）：会话记下（Session.profile）。"""
    session = _manager.session(playerId, data)
    if session is None or not _bucket.allow(playerId, time.time(), 0.25):
        return
    profile = data.get("p")
    if Schema.isText(profile) and profile in Collections.PROFILES:
        session.setProfile(Schema.text(profile))


@AllowCall
@InjectHttpPlayerId
def dolorContainerClose(playerId, data):
    if _manager.session(playerId, data) is not None:
        _manager.close(playerId, Protocol.CLOSE_CLIENT)


# ---------------------------------------------------------------- 按需监听的事件


def _onInventoryChanged(args):
    playerId = args.get("playerId")
    if playerId in _manager.sessions and playerId not in Engine.writing:
        _manager.dirty.add(playerId)


def _onSimTick(args=None):
    _manager.machines.onTick()


def _behaviorHandler(event):
    """后台行为要的事件的处理函数：每个事件一个，名字各不相同（动态监听按函数名起名）。"""
    def handler(args):
        _manager.machines.dispatch(event, args)
    handler.__name__ = "_onBehaviorEvent_%s" % event
    return handler


_ticking = [False]   # 现在监听着引擎每推进一刻的事件没有


def _listenTicks(on):
    """
    机器要数刻时监听引擎每推进一刻的事件，不要时撤掉。不要的那一下多半就在这个事件的处理里（最后一个唤醒处理完），
    在事件处理里撤掉同一个事件的监听不稳妥，所以下一帧再看：那时还是不要才撤。
    """
    if on and not _ticking[0]:
        _ticking[0] = True
        ListenForEvent("OnSimTickServerEvent", _EVENTS, _onSimTick)
    elif not on and _ticking[0]:
        _game.AddTimer(0.0, _stopTicks)


def _stopTicks():
    if _ticking[0] and not _manager.machines.listening:
        _ticking[0] = False
        UnListenForEvent("OnSimTickServerEvent", _EVENTS, _onSimTick)


def _onTick(args=None):
    _tickNumber[0] += 1
    ContainerKinds.ticking[0] = _tickNumber[0]
    try:
        _checkSessions()
    finally:
        ContainerKinds.ticking[0] = None


_tickNumber = [0]


def _checkSessions():
    if _manager.validating:
        for session in list(_manager.validating):
            if session.closed:
                _manager.validating.discard(session)
            elif not session.hostValid():
                _manager.close(session.playerId, HOST_GONE)
    if _manager.ticking:
        for session in list(_manager.ticking):
            if session.closed:
                _manager.ticking.discard(session)
            else:
                session.tick(_tickNumber[0])
    if not _manager.dirty:
        return
    dirty, _manager.dirty = _manager.dirty, set()
    for playerId in dirty:
        session = _manager.sessions.get(playerId)
        if session is not None:
            session.refresh()


def _onTryTouch(args):
    """刚从容器界面丢出的东西：原版 2 秒内谁都捡不起来（见 Engine.THROW_SECONDS）。"""
    delay = Engine.thrownPickupDelay(args.get("entityId"))
    if delay > 0:
        args["cancel"] = True
        args["pickupDelay"] = delay


_touchWatching = [False]


def _onThrown():
    """丢出了东西：监听拾取事件，到不可拾取期结束再看要不要撤掉。"""
    if not _touchWatching[0]:
        _touchWatching[0] = True
        ListenForEvent("ServerPlayerTryTouchEvent", _EVENTS, _onTryTouch)
    _game.AddTimer(Engine.THROW_SECONDS + 0.1, _purgeThrown)


def _purgeThrown():
    if Engine.purgeThrown() == 0 and _touchWatching[0]:
        _touchWatching[0] = False
        UnListenForEvent("ServerPlayerTryTouchEvent", _EVENTS, _onTryTouch)


Engine.thrownHook[0] = _onThrown


# ---------------------------------------------------------------- 一直监听的事件（都不频繁，或处理得很快）


@Listen("AddServerPlayerEvent")
def _onPlayerAdded(args):
    _players.add(args.get("id"))


@Listen("PlayerIntendLeaveServerEvent")
def _onIntendLeave(args):
    # 在玩家最终存档之前：手持物退回背包并保存，进这次存档；他身上的机器停下
    playerId = args.get("playerId")
    _manager.close(playerId, Protocol.CLOSE_LEAVE)
    _manager.playerLeft(playerId)


@Listen("DelServerPlayerEvent")
def _onPlayerRemoved(args):
    playerId = args.get("id")
    _manager.abandon(playerId)
    _lastMobHurt.pop(playerId, None)
    _players.discard(playerId)


@Listen("PlayerDieEvent")
def _onDie(args):
    # 这个事件之前引擎已经按"保留物品栏"（全局规则或按玩家的设置）处理完背包：背包还在说明保留，手持物跟着退回背包；
    # 背包已经掉光了，手持物也丢在原地。按玩家的设置读不到，所以看背包里还有没有东西
    playerId = args.get("id")
    session = _manager.sessions.get(playerId)
    if session is None:
        return
    kept = Engine.keepInventoryRule() or any(session.inventory.read())
    _manager.close(playerId, Protocol.CLOSE_DEATH, dropCursor=not kept)


def _onHurt(args):
    """玩家受到生物造成的伤害（有要受伤关闭的容器类型时才监听）：开着的界面按容器类型的 closeOnHurt 关掉（冷却之内不关）。"""
    cause = args.get("cause")
    if cause not in _manager.hurtCauses:
        return
    playerId = args.get("entityId")
    if playerId not in _players:
        return
    now = time.time()
    last = _lastMobHurt.get(playerId)
    _lastMobHurt[playerId] = now
    session = _manager.sessions.get(playerId)
    if session is None or (last is not None and now - last < _manager.hurtCooldown):
        return
    rule = session.instance.type.closeOnHurt
    if rule(session, cause) if callable(rule) else rule:
        _manager.close(playerId, Protocol.CLOSE_HURT)


def setRateLimit(capacity, rate):
    """每位玩家的请求令牌：最多攒 capacity 个，每秒补 rate 个（操作、动作的花费见 Op.cost、Actions.action 的 cost）。"""
    if capacity <= 0 or rate <= 0:
        raise ValueError("rate limit needs a positive capacity and rate: %r %r" % (capacity, rate))
    _bucket.capacity, _bucket.rate = float(capacity), float(rate)


def setHurtClose(causes=None, cooldown=None):
    """受伤关界面：哪些伤害来源算生物造成（causes），自动关闭之后多少秒内不再关（cooldown）。不给的不变。"""
    if causes is not None:
        _manager.hurtCauses = frozenset(causes)
    if cooldown is not None:
        if cooldown < 0:
            raise ValueError("hurt close cooldown cannot be negative: %r" % (cooldown,))
        _manager.hurtCooldown = float(cooldown)


@Listen("DimensionChangeServerEvent")
def _onDimensionChange(args):
    _manager.close(args.get("playerId"), Protocol.CLOSE_DIMENSION)


@Listen("ClientLoadAddonsFinishServerEvent")
def _onJoin(args):
    playerId = args.get("playerId")
    if playerId:
        _players.add(playerId)
        recoverLeftover(Engine.PlayerInventory(playerId), Engine.CursorStore(playerId), Engine.RULES,
                        Engine.ExtraDataBackend(playerId).save, Engine.HeldStore(playerId))
        _manager.playerJoined(playerId)
