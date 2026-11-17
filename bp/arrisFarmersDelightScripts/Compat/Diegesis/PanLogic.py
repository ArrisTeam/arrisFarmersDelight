# -*- coding: utf-8 -*-
"""PanLogic - 煎锅站点的服务端逻辑：放进锅、颠锅翻面、全拿出来（服务端）

对应 Hands-On Delight：station/SkilletLogic.java + SkilletStation.java。锅里的东西照旧在方块实体数据 cookingDict，站点的 pan 槽组
经 PanSlots 绑在上面（FD 原样的右键放料、煎锅自己的 tick、手工煎制、没人开站点时路过的人，读写的都是同一份）；两面进度在
Server/HandFrying.py 的 PanHand 里（站点关了它还在：接着煎、等着翻；存进方块实体，重启也在）。潜行右键是 FD 原来的玩法。
- 放：JE 的 place {"one", "from"}：光标栈的一叠放进锅（one 为真放一个，左键整叠、右键一个；from 是背包格号时放的是背包那一格的一叠，
  托盘里空手 Shift 点就是这样，JE 的 onInventoryShiftClick），煎得了的、同一种、最多一批 16 件、锅里没泡水才放得进
  （SkilletCooking.takes / place），放不进的回 refused 给大家看弹开。库自己的 QUICK_MOVE（前置包没有 onInventoryShiftClick 钩子的老版本走它）
  规则同一份（mayPlace + 槽组的 accepts / 上限）；放进来的从此两面分开煎（_placed）。库的 PICKUP 碰不到锅里的东西（mayTake 恒为假：
  内核对非空槽先问 mayTake，所以光标栈放进有东西的锅也只能走 place）。开站那一下主手拿着煎得了的东西：整叠直接放进去（JE 的 onOpen：右键放料不比不开站点慢）。
- 取：take {}，锅里的东西（生的、半熟的、煎好的）全进背包，放不下掉脚下。
- 颠：toss {"strength"}，食物翻个面（离上次颠不到 0.4 秒、锅里是煎好的或空的不算）；被拒回 untossed 给大家（JE 的 EFFECT_UNTOSSED）。
表现一律走 PanLook 广播（Server/PanLook.py，附近所有人包括本人）：placed、refused、tossed、untossed、taken、fried；站点自己不发 effect。
"""
import copy
import time

from ...Server import HandFrying, PanLook
from ...Server.Helpers import PanContents
from ...Server.Helpers.BlockItems import PublishSkillet
from ...Server.Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetCarriedItem, SetCarriedItem
from ...Shared.Rules import PanStation as Rules
from ...Shared.Rules.HandsOn import Frying

REACH = 6.0
WINDOW = 36                      # 背包窗口的格数（0-8 快捷栏）
INTS = (int, type(2 ** 64))      # py2 的 int / long（客户端发来的整数可能是 long）


def _index(value, size):
    """客户端发来的序号：0 <= 整数 < size 才算，别的（负数、小数、字符串、布尔）都当没有。"""
    return int(value) if isinstance(value, INTS) and not isinstance(value, bool) and 0 <= value < size else None


def _count(item):
    return (item.get("count") or 0) if item else 0


def _wire(item):
    if not item or not item.get("newItemName") or _count(item) <= 0:
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def _strength(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value:
        return max(0.0, min(1.0, float(value)))
    return 0.5


class PanLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类和 kit 只在运行时拿得到）。"""

    kit = None           # 前置包的服务端 Api（register 里放进去）

    def __init__(self, station):
        super(PanLogicMixin, self).__init__(station)
        self.hand = None
        self._count = 0
        station.state.bindSlots(Rules.GROUP_PAN, PanContents.PanSlots(station.dimensionId, station.pos))

    # ---------------------------------------------------------------- 钩子

    def onOpen(self, playerId):
        station = self.station
        data = GetBlockEntityData(station.dimensionId, station.pos)
        if data is None:
            return False
        self.hand = HandFrying.handOf(station.dimensionId, station.pos, data)
        self._count = _count(PanContents.itemOf(station.dimensionId, station.pos))
        self._fromHand(playerId, data)
        return True

    def mayPlace(self, ref, item):
        station = self.station
        return (ref[0] == Rules.GROUP_PAN and Rules.mayPlace(station.state.getItem(ref), item)
                and not PanContents.isWaterlogged(station.dimensionId, station.pos))

    def mayTake(self, ref):
        return False         # 全拿出来走 take（它要重置两面进度）；双击聚拢也不会把锅里的东西收走

    def onSlotChanged(self, ref):
        """库的点击改了 pan 槽：多了东西 = 放进来了，从此手工煎。"""
        if ref[0] != Rules.GROUP_PAN or self.hand is None:
            return
        station = self.station
        data = GetBlockEntityData(station.dimensionId, station.pos)
        count = _count(PanContents.itemOf(station.dimensionId, station.pos))
        if count > self._count and self.actor:
            self._placed(self.actor, data)
        self._count = count
        self._look(data)

    def onCustomAction(self, playerId, name, data):
        if self.hand is None:
            return False
        if name == "place":
            self._place(playerId, data.get("one") is True, data.get("from"))
        elif name == "toss":
            self._toss(playerId, data.get("strength"))
        elif name == "take":
            self._take(playerId)
        else:
            return False
        self._look(GetBlockEntityData(self.station.dimensionId, self.station.pos))
        return True

    # ---------------------------------------------------------------- 动作

    def _placed(self, playerId, data):
        """放进来了（站点的点击或开站时主手的）：从此两面分开煎，记一笔、告诉大家。"""
        station = self.station
        self.hand.frying.layByHand()
        self.hand.cook = playerId
        HandFrying.save(self.hand, data)
        PanLook.event(station.dimensionId, station.pos, "placed", {})

    def _place(self, playerId, one, fromRaw=None):
        """光标栈上的一叠（或背包第 from 格的一叠）放进锅：一个或整叠，放满一批为止；放不进去的（锅里是别的、煎好的、满了、泡着水）回 refused
        （SkilletCooking.place）。from 不是背包里的格号：什么也不做。"""
        station, ctx = self.station, self.ctx
        fromSlot = _index(fromRaw, WINDOW)
        if fromRaw is not None and fromSlot is None:
            return
        hand = ctx.inventory[fromSlot] if fromSlot is not None else ctx.getHand()
        if not hand:
            return
        inPan = PanContents.itemOf(station.dimensionId, station.pos)
        moved = 0
        if Rules.mayPlace(inPan, hand) and not PanContents.isWaterlogged(station.dimensionId, station.pos):
            moved = Frying.placeCount(hand["count"], _count(inPan), ctx.maxStackOf(hand), one)
        if moved <= 0:
            PanLook.event(station.dimensionId, station.pos, "refused", {"stack": _wire(dict(hand, count=1))})
            return
        merged = copy.deepcopy(inPan or hand)
        merged["count"] = _count(inPan) + moved
        PanContents.PanSlots(station.dimensionId, station.pos).set(0, merged)
        rest = self.kit.Items.shrink(hand, moved)
        if fromSlot is not None:
            ctx.inventory[fromSlot] = rest
        else:
            ctx.setHand(rest)
        self._count = merged["count"]
        self._placed(playerId, GetBlockEntityData(station.dimensionId, station.pos))

    def _fromHand(self, playerId, data):
        """开站这一下主手拿着煎得了的东西：整叠（最多放满一批）直接放进锅里。"""
        station = self.station
        carried = GetCarriedItem(playerId, True)
        inPan = PanContents.itemOf(station.dimensionId, station.pos)
        if not carried or not Rules.mayPlace(inPan, carried) or PanContents.isWaterlogged(station.dimensionId, station.pos):
            return
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(carried["newItemName"], carried.get("newAuxValue") or 0) or {}
        moved = Frying.placeCount(carried["count"], _count(inPan), info.get("maxStackSize") or 64)
        if moved <= 0:
            return
        merged = copy.deepcopy(inPan or carried)
        merged["count"] = _count(inPan) + moved
        PanContents.PanSlots(station.dimensionId, station.pos).set(0, merged)
        left = copy.deepcopy(carried)
        left["count"] -= moved
        SetCarriedItem(playerId, left if left["count"] > 0 else None)
        self._count = merged["count"]
        self._placed(playerId, data)

    def _toss(self, playerId, strength):
        station = self.station
        data = GetBlockEntityData(station.dimensionId, station.pos)
        item = data["cookingDict"] if data else None
        if HandFrying.toss(self.hand, playerId, time.time(), item):
            HandFrying.save(self.hand, data)
            PanLook.event(station.dimensionId, station.pos, "tossed", {"strength": _strength(strength)})
        elif item:
            PanLook.event(station.dimensionId, station.pos, "untossed", {})

    def _take(self, playerId):
        """锅里的东西全进厨师的背包窗口（放不下的掉在脚下），两面进度清零。"""
        station = self.station
        data = GetBlockEntityData(station.dimensionId, station.pos)
        item = data["cookingDict"] if data else None
        if not item or _count(item) <= 0:
            return
        taken = copy.deepcopy(item)
        rest = self._toWindow(taken)
        if rest is not None:
            self.dropped.append(rest)
        data["cookingDict"] = None
        PanContents.restartTimer(data)
        PublishSkillet(station.dimensionId, station.pos, None)
        self.hand.frying.farmersDelightsWay()
        HandFrying.save(self.hand, data)
        self._count = 0
        PanLook.event(station.dimensionId, station.pos, "taken", {"stack": _wire(taken)})

    def _toWindow(self, item):
        """放进背包窗口：先并入同种未满的栈、再放进空格，都按格号（Inventory.add）；返回放不下的余量或 None。"""
        items, window, maxStackOf = self.kit.Items, self.ctx.inventory, self.ctx.maxStackOf
        rest, size = item, maxStackOf(item)
        for fillEmpty in (False, True):
            for index in range(len(window)):
                there = window[index]
                if rest is None:
                    return None
                if (there is None) != fillEmpty or (not fillEmpty and not items.sameItem(there, rest)):
                    continue
                moved = min(size - items.countOf(there), items.countOf(rest))
                if moved > 0:
                    window[index] = items.withCount(rest, moved) if fillEmpty else items.grow(there, moved)
                    rest = items.shrink(rest, moved)
        return rest

    def _look(self, data):
        """世界外观马上发（不等锅的下一步）。"""
        if data is not None:
            PanLook.tick(self.station.dimensionId, self.station.pos, data, self.hand, time.time())


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点（站点声明两端同一份，见 PanStation.buildSchema）。"""
    logicClass = type("SkilletLogic", (PanLogicMixin, api.StationLogic), {"kit": api})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.PAN_BLOCKS, logicClass, schema=Rules.buildSchema(api), reach=REACH))
    return logicClass
