# -*- coding: utf-8 -*-
"""
机器：随时间变化的实例（熔炉这类，界面模型的 machine 为真；docs/ARCHITECTURE.md 第 5 节）。

不逐刻推进：实例在用到时（打开、操作、时钟停走、看着的人该看到变化的那一刻）按事件一下子推到现在，
推进本身由界面模型做（advance 往前推几刻，nextEvent 说再过几刻会有看得见的变化，见 Common.Menus）。

时间按游戏刻算：本模块数服务端每推进一刻发的事件，只在有机器的时钟走着、或排着唤醒时才数。单人游戏暂停时引擎不发，
机器跟着停；服务器卡得一帧补几刻时只发一次，机器跟着慢一点。机器的时钟走不走由宿主的时钟定（Server/Hosts.Clock，
库带的见 Std/Server/Hosts.py、Std/Block、Std/Entity），时钟走起来与停下时调用 resume / pause。
时钟走着的实例记一个锚点（上次推进时的刻数），推进时按"现在 - 锚点"推进，再把锚点挪到现在；停走之前先推进到停的那一刻。
读不了实例时（方块所在的区块正要卸载）用 suspend：不推进，交出走过的刻数，下次 resume 时交回来一并算上；时钟定期用
advance 推进并存档。锚点只在内存里：服务器重启后从时钟重新走起算；崩溃前没来得及推进的那一段不算，不会凭空多算。

有人看着、时钟走着时，在下一个事件那一刻唤醒一次：推进，把改了的格子与界面数据推给每位查看者，再定下一次。没人看着就不唤醒。

后台行为（Behavior，C51：磁铁、自动进食、搬运这类不在界面里的事）登记在容器类型上，实例的时钟走着时才跑：按间隔的
排进唤醒（不逐刻空转），按事件的由服务端在登记了这种事件时才监听、来了交给 dispatch。跑之前机器先推进到现在，跑完存下来、
把改了的格子推给看着的人。
本模块不依赖引擎：数刻与后台行为要的事件由服务端接进来。
"""
import heapq
import zlib


def _spread(handle, index):
    """按实例与行为错开第一次的那个数（每次运行都一样，不随解释器的散列变）。"""
    return zlib.crc32(repr((tuple(handle), index)).encode("utf-8")) & 0xffffffff


class Behavior(object):
    """
    后台行为（见模块说明），用 Api.addBehavior(容器类型, 行为) 登记。interval 不为 None 时每隔这么多刻跑一次；events 是要的
    引擎事件名，事件来了时 targets(事件名, 参数) 给出要跑的实例（(类型, 实例键) 的列表），其中时钟走着的才跑。
    run(context) 做事：context.instance 是实例（机器已推进到现在），改格子用 instance.set / instance.state，改完由库存下来、
    推给看着的人；context.event、context.args 是这一次的事件（按间隔跑时为 None），context.tick 是现在的刻数。
    """

    interval = None
    events = ()

    def targets(self, event, args):
        return ()

    def run(self, context):
        pass


class BehaviorContext(object):
    """后台行为跑一次时拿到的东西（见 Behavior）。"""

    def __init__(self, instance, tick, event=None, args=None):
        self.instance = instance
        self.handle = instance.handle
        self.tick = tick
        self.event = event
        self.args = args


class Machines(object):
    """
    registry：Registry.Registry；listen(on)：开始（on 为真）或停止数刻（服务端接上引擎每刻的事件，事件里调 onTick）；
    release(instance)：推进完不再用的实例交还（服务端接 Registry.release）。
    """

    def __init__(self, registry, listen=None, release=None):
        self.registry = registry
        self.tick = 0
        self._listen = listen
        self._release = release or (lambda instance: None)
        self._listening = False
        self._anchors = {}    # (类型, 实例键) -> 上次推进时的刻数；只有时钟走着的才有
        self._due = {}        # (类型, 实例键) -> 排着的唤醒在哪一刻
        self._heap = []       # (刻数, 序号, (类型, 实例键))
        self._serial = 0
        self._behaviors = {}  # 类型 -> [后台行为]
        self._runs = []       # 按间隔跑的后台行为：(刻数, 序号, (类型, 实例键), 行为的下标)
        self._nextRun = {}    # ((类型, 实例键), 行为的下标) -> 排着的刻数
        registry.isRunning = self.running

    # ---------------------------------------------------------------- 时钟

    def running(self, handle):
        return handle in self._anchors

    @property
    def listening(self):
        """现在要不要数刻。"""
        return self._listening

    def resume(self, handle, elapsed=0):
        """
        时钟开始走（物品进了背包、玩家上线、方块所在的区块加载了）。elapsed 是之前走过、还没推进的刻数（suspend 交出来的），
        这次一并算上。实例有人看着时把新的速度推给他们。
        """
        if handle in self._anchors:
            return
        self._anchors[handle] = self.tick - max(0, int(elapsed))
        for index, behavior in enumerate(self._behaviors.get(handle[0], ())):
            if behavior.interval:
                self._queue(handle, index, True)
        instance = self.registry.loaded(handle)
        if instance is not None:
            self.refresh(instance)
        self._sync()

    def pause(self, handle):
        """时钟停（物品离开背包、玩家下线）：先推进到现在、存下来，再停。"""
        if handle not in self._anchors:
            return
        typeId, key = handle
        if self.registry.get(typeId) is None:
            del self._anchors[handle]
            self._dropRuns(handle)
            self._sync()
            return
        instance = self.registry.instance(typeId, key)
        changes = self.catchUp(instance)
        del self._anchors[handle]
        self._dropRuns(handle)
        self.refresh(instance, changes)
        self._release(instance)
        self._sync()

    def suspend(self, handle):
        """
        时钟停，但现在读不了实例（方块所在的区块正要卸载、实体正要离开）：不推进，交出走过还没推进的刻数，下次 resume 时
        交回来；没在走时为 None。
        """
        anchor = self._anchors.pop(handle, None)
        if anchor is None:
            return None
        self._due.pop(handle, None)
        self._dropRuns(handle)
        self.registry.stopped(handle)
        self._sync()
        return self.tick - anchor

    def advance(self, handle):
        """时钟走着时推进到现在、存下来，看着的人推一次（时钟定期调用：服务器关掉、崩溃时少算的只是最后一段）。"""
        if handle not in self._anchors or self.registry.get(handle[0]) is None:
            return
        loaded = self.registry.loaded(handle)
        instance = loaded if loaded is not None else self.registry.instance(handle[0], handle[1])
        self.refresh(instance)
        if loaded is None:
            self._release(instance)

    def _dropRuns(self, handle):
        for entry in [entry for entry in self._nextRun if entry[0] == handle]:
            del self._nextRun[entry]

    def pauseAll(self):
        for handle in list(self._anchors):
            self.pause(handle)

    # ---------------------------------------------------------------- 推进

    def catchUp(self, instance):
        """把机器推进到现在并存下来，返回改了的容器格 {容器格: 物品堆}。时钟停着、不是机器时什么都不做。"""
        handle = instance.handle
        anchor = self._anchors.get(handle)
        if anchor is None or not instance.menu.machine:
            return {}
        elapsed = self.tick - anchor
        if elapsed <= 0:
            return {}
        self._anchors[handle] = self.tick
        instance.beginChanges()
        try:
            instance.menu.advanceAll(instance, elapsed)
        finally:
            changes = instance.endChanges()
        instance.flush()
        return changes

    def update(self, typeId, key, change):
        """
        宿主在会话之外改一个实例（Api.updateInstance）：实例没加载时读出来，机器先推进到现在，change(实例) 里改格子与实例状态，
        改完写回存储、写了东西时像一次操作那样经宿主存档（物品里存放的这时才写进物品）、推给看着的人、定下一次唤醒，没人看时
        放回缓存。返回 change 的返回值。
        """
        loaded = self.registry.loaded((typeId, key))
        instance = loaded if loaded is not None else self.registry.instance(typeId, key)
        changes = self.catchUp(instance)
        instance.beginChanges()
        try:
            result = change(instance)
        finally:
            changes.update(instance.endChanges())
            if instance.flush():
                instance.type.host.save(instance.backend)
            self.refresh(instance, changes)
            if loaded is None:
                self._release(instance)
        return result

    def refresh(self, instance, changes=None, exclude=None):
        """推进到现在，把格子与界面数据的变化推给每位查看者（exclude 除外），再定下一次唤醒。"""
        changes = dict(changes or {})
        changes.update(self.catchUp(instance))
        instance.beginPush()   # 一轮推送：几位查看者的界面数据只算一次
        try:
            for viewer in list(instance.viewers):
                if viewer is not exclude:
                    viewer.containerChanged(dict(changes))
        finally:
            instance.endPush()
        self.schedule(instance)
        return changes

    def schedule(self, instance):
        """有人看着、时钟走着时，按界面模型说的下一个事件定唤醒；否则撤掉排着的唤醒。"""
        handle = instance.handle
        delay = None
        if instance.viewers and handle in self._anchors and instance.menu.machine:
            delay = instance.menu.nextEventAll(instance)
        if delay is None:
            self._due.pop(handle, None)
        else:
            at = self.tick + max(1, int(delay))
            if self._due.get(handle) != at:
                self._due[handle] = at
                self._serial += 1
                heapq.heappush(self._heap, (at, self._serial, handle))
        self._sync()

    def onTick(self):
        """引擎推进了一刻。"""
        self.tick += 1
        heap = self._heap
        while heap and heap[0][0] <= self.tick:
            at, _, handle = heapq.heappop(heap)
            if self._due.get(handle) != at:
                continue
            del self._due[handle]
            instance = self.registry.loaded(handle)
            if instance is not None and instance.viewers:
                self.refresh(instance)
        if not self._due and heap:
            del heap[:]
        runs = self._runs
        while runs and runs[0][0] <= self.tick:
            at, _, handle, index = heapq.heappop(runs)
            if self._nextRun.get((handle, index)) != at:
                continue
            del self._nextRun[(handle, index)]
            if handle in self._anchors:
                self._run(handle, self._behaviors[handle[0]][index])
            if handle in self._anchors:
                self._queue(handle, index)
        if not self._nextRun and runs:
            del runs[:]
        if not self._anchors and not self._due:
            self._sync()

    # ---------------------------------------------------------------- 后台行为

    def addBehavior(self, typeId, behavior):
        """登记容器类型的后台行为（服务端在登记了它要的事件时监听）。时钟已经在走的实例按间隔排上。"""
        behaviors = self._behaviors.setdefault(typeId, [])
        behaviors.append(behavior)
        if behavior.interval:
            for handle in [handle for handle in self._anchors if handle[0] == typeId]:
                self._queue(handle, len(behaviors) - 1, True)

    def hasBehaviors(self, typeId):
        return bool(self._behaviors.get(typeId))

    def dispatch(self, event, args):
        """引擎事件：交给要它的后台行为，在它们给出的、时钟走着的实例上跑。"""
        for typeId, behaviors in list(self._behaviors.items()):
            for behavior in behaviors:
                if event not in behavior.events:
                    continue
                for handle in behavior.targets(event, args) or ():
                    if tuple(handle)[0] == typeId and tuple(handle) in self._anchors:
                        self._run(tuple(handle), behavior, event, args)

    def _queue(self, handle, index, start=False):
        """
        排上后台行为的下一次：每 interval 刻一次；刚开始排时（时钟走起来、登记行为）第一次按实例错开在 1 到 interval 刻里
        （许多台一起走起来时不挤在同一刻跑）。
        """
        interval = max(1, int(self._behaviors[handle[0]][index].interval))
        at = self.tick + (1 + _spread(handle, index) % interval if start else interval)
        self._nextRun[(handle, index)] = at
        self._serial += 1
        heapq.heappush(self._runs, (at, self._serial, handle, index))
        self._sync()

    def _run(self, handle, behavior, event=None, args=None):
        """跑一次后台行为：机器先推进到现在，跑完存下来、推给看着的人。"""
        if self.registry.get(handle[0]) is None:
            return
        loaded = self.registry.loaded(handle)
        instance = loaded if loaded is not None else self.registry.instance(handle[0], handle[1])
        changes = self.catchUp(instance)
        instance.beginChanges()
        try:
            behavior.run(BehaviorContext(instance, self.tick, event, args))
        finally:
            changes.update(instance.endChanges())
            instance.flush()
        self.refresh(instance, changes)
        if loaded is None:
            self._release(instance)

    def _sync(self):
        """有锚点、唤醒或排着的后台行为时数刻，都没有时不数。"""
        wanted = bool(self._anchors) or bool(self._due) or bool(self._nextRun)
        if wanted != self._listening:
            self._listening = wanted
            if self._listen is not None:
                self._listen(wanted)

