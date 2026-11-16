# -*- coding: utf-8 -*-
"""GrillLogic - 炉灶站点的服务端逻辑：槽位规则、摆上烤架、逐件翻面、取下、告诉客户端每件两面烤到哪了（服务端）

对应 Hands-On Delight：station/StoveLogic.java 与 StoveCooking.java 的 place / turn / take。烤位上的东西照旧在方块实体数据 "0".."5"
（Server/Stove.py）：站点的 grill 槽组经 StoveSlots 绑在上面，两面进度在 Server/HandGrill.py 的 StoveHand 里（站点关了它还在）。
潜行右键是 FD 原来的玩法。光标栈（手上拿着的那叠）由前置包管：
    槽规则   烤得了的才收（蛋不收：HoD 的 NOT_ON_GRILL），上面盖着东西不收，一格一件；烤位不能用内核的点击取走（mayTake 假，
             取走和翻面都是下面的动作）；内核的点击放上去的（Shift 点托盘里的食物 = 每个空位一件）从此两面分开烤
    开站     右键时主手拿着烤得了的食物：马上整叠摆到每个空位上，放不下的留在手里（JE 的 onOpen：不比不开站点慢）
自定义动作（和 JE 的 ACTION_PLACE / TURN / TAKE 一样）：
    place {"one", "place", "from"}  手上这叠（或背包第 from 格）：缺省每个空位摆一件；one 为真只摆 place 那一个位置；放不上去弹回
    turn  {"place"}                 这个烤位上的那件翻个面（离这件上次翻不到 0.3 秒、已经烤好的不算）
    take  {"place"}                 取下这个烤位上的那件（生的、半熟的、烤好的）进背包，放不下掉在脚下
表现事件：placed {"places"}（摆上去的位置）、refused {"stack"}、turned {"place", "up"}（翻过来之后朝上那面烤到哪）/ unturned {"place"}、taken {"place", "stack"}、grilled {"place", "stack"}（两面都烤好了）。
站点数据：down / up / hand 三个长 6 的列表（贴灶台那面、朝上那面烤到哪，手放的），每刻重算、变了才发。
"""
import time

from . import GrillOpen
from ...Server import HandGrill
from ...Server.Helpers.BlockItems import PublishStove
from ...Server.Helpers.Engine import GetBlockEntityData, GetCarriedItem, SetCarriedItem
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.StoveSlots import StoveSlots
from ...Server.Stove import EnsureStoveData
from ...Shared.Rules import GrillStation as Rules, StoveCover
from ...Shared.Rules.HandsOn import Frying, Grill

REACH = 6.0
INTS = (int, type(2 ** 64))      # py2 的 int / long（客户端发来的整数可能是 long）
WINDOW = 36                      # 背包窗口的格数（0-8 快捷栏）


def _wire(item):
    if not item or not item.get("newItemName"):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item.get("count") or 1}


def _index(value, size):
    """客户端发来的序号：0 <= 整数 < size 才算，别的（负数、小数、字符串、布尔）都当没有。"""
    return int(value) if isinstance(value, INTS) and not isinstance(value, bool) and 0 <= value < size else None


def _toWindow(kit, window, item, maxStackOf):
    """放进背包窗口（Inventory.add：先并入同种未满的栈，再放进空格，都按格号）；返回放不下的余量或 None。"""
    items, rest, size = kit.Items, item, maxStackOf(item)
    for index in range(len(window)):
        there = window[index]
        if there is not None and items.sameItem(there, rest):
            moved = min(size - items.countOf(there), items.countOf(rest))
            if moved > 0:
                window[index] = items.grow(there, moved)
                rest = items.shrink(rest, moved)
                if rest is None:
                    return None
    for index in range(len(window)):
        if window[index] is None:
            moved = min(size, items.countOf(rest))
            window[index] = items.withCount(rest, moved)
            rest = items.shrink(rest, moved)
            if rest is None:
                return None
    return rest


class GrillLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类和 kit 只在运行时拿得到）。"""

    kit = None           # 前置包的服务端 Api（register 里放进去）

    def __init__(self, station):
        super(GrillLogicMixin, self).__init__(station)
        self.hand = None
        self._publishStove = False
        station.state.bindSlots(Rules.GROUP_GRILL, StoveSlots(station.dimensionId, station.pos, Rules.PLACES, HandGrill.COOK_TIMER))

    # ---------------------------------------------------------------- 钩子

    def onOpen(self, playerId):
        data = self._blockData()
        if data is None:
            return False
        EnsureStoveData(data)            # /setblock、结构放出的炉灶没走放置事件
        self.hand = HandGrill.handOf(self.station.dimensionId, self.station.pos, data)
        if not self.station.users:
            del self.hand.just[:]        # 没人在时烤好的那几件早就过去了：不要等人开站才叮一声
        self._layHeld(playerId)
        self._flush()
        return True

    def mayPlace(self, ref, item):
        return ref[0] == Rules.GROUP_GRILL and Rules.mayPlace(item) and not self._covered()

    def mayTake(self, ref):
        return False                     # 取走和翻面都走自定义动作：左键点一件是翻面，不是拿起

    def onSlotChanged(self, ref):
        """内核自己的点击改了一个烤位（Shift 点托盘里的食物放上去）：放上去的从此两面分开烤。"""
        if ref[0] == Rules.GROUP_GRILL and self.hand is not None:
            if self.station.state.getItem(ref) is not None:
                self._laid(ref[1], self.actor)
            else:
                self.hand.grill.farmersDelightsWay(ref[1])
            self._publishStove = True

    def onCustomAction(self, playerId, name, data):
        if self.hand is None:
            return False
        if name == "place":
            self._place(playerId, data.get("one") is True, _index(data.get("place"), Rules.PLACES), data.get("from"))
        elif name == "turn":
            self._turn(playerId, _index(data.get("place"), Rules.PLACES))
        elif name == "take":
            self._take(playerId, _index(data.get("place"), Rules.PLACES))
        else:
            return False
        self._flush()
        return True

    def tick(self, dt):
        hand = self.hand
        if hand is None:
            return
        while hand.just:
            place = hand.just.pop(0)
            item = self.station.state.getItem((Rules.GROUP_GRILL, place))
            self.station.effect("grilled", {"place": place, "stack": _wire(item)})
            ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "random.pop")
        self._flush()

    # ---------------------------------------------------------------- 动作

    def _place(self, playerId, one, place, fromRaw):
        """手上这叠（from 是背包格号时那一格）摆到烤架上：每个空位一件，或只摆 place（StoveLogic.place / StoveCooking.place）。"""
        ctx, fromSlot = self.ctx, _index(fromRaw, WINDOW)
        if fromRaw is not None and fromSlot is None:
            return                       # from 不是背包里的格号：什么也不做
        carried = ctx.inventory[fromSlot] if fromSlot is not None else ctx.getHand()
        if carried is None:
            return
        laid = self._laidPlaces(carried, place if one and place is not None else -1)
        if not laid:
            self.station.effect("refused", {"stack": dict(_wire(carried), count=1)})
            return
        rest = self._lay(carried, laid, playerId)
        if fromSlot is not None:
            ctx.inventory[fromSlot] = rest
        else:
            ctx.setHand(rest)
        self.station.effect("placed", {"places": laid})
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    def _turn(self, playerId, place):
        item = self.station.state.getItem((Rules.GROUP_GRILL, place)) if place is not None else None
        turned = place is not None and HandGrill.turn(self.hand, playerId, place, time.time(), item)
        if turned:
            self.station.effect("turned", {"place": place, "up": Frying.syncStep(self.hand.grill.up(place))})
        else:
            self.station.effect("unturned", {"place": -1 if place is None else place})

    def _take(self, playerId, place):
        ref = (Rules.GROUP_GRILL, place)
        item = self.station.state.getItem(ref) if place is not None else None
        if item is None:
            return
        item = dict(item)
        self.station.state.setItem(ref, None)
        self.hand.grill.farmersDelightsWay(place)
        rest = _toWindow(self.kit, self.ctx.inventory, item, self.ctx.maxStackOf)
        if rest is not None:
            self.dropped.append(rest)
        self._publishStove = True
        self.station.effect("taken", {"place": place, "stack": _wire(item)})
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    def _layHeld(self, playerId):
        """右键时主手拿着烤得了的食物：整叠摆到每个空位上（JE 的 onOpen 里的 onInventoryShiftClick）。放不下的留在手里。"""
        held = GetCarriedItem(playerId, True)
        if held is None:
            return
        laid = self._laidPlaces(held, -1)
        if laid:
            SetCarriedItem(playerId, self._lay(held, laid, playerId))
            self.station.effect("placed", {"places": laid})
            ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    def _laidPlaces(self, carried, place):
        """carried 这叠能摆在哪些位置（StoveCooking.place 的规划）：烤得了、上面没盖东西，才摆；place 为 -1 是每个空位一件（够这叠的件数为止）。"""
        if not Rules.canGrill(carried.get("newItemName")) or self._covered():
            return []
        occupied = [self.station.state.getItem((Rules.GROUP_GRILL, at)) is not None for at in range(Rules.PLACES)]
        return Grill.laidPlaces(occupied, place, self.kit.Items.countOf(carried))

    def _lay(self, carried, places, playerId):
        """每个位置摆一件，返回这叠剩下的（空了是 None）。"""
        items = self.kit.Items
        for place in places:
            self.station.state.setItem((Rules.GROUP_GRILL, place), items.withCount(carried, 1))
            self._laid(place, playerId)
        self._publishStove = True
        return items.shrink(carried, len(places))

    def _laid(self, place, playerId):
        """这个位置刚摆上了一件：FD 的计时作废，从此两面分开烤、等着翻（StoveCooking.place）。"""
        self.hand.grill.farmersDelightsWay(place)
        self.hand.grill.layByHand(place)
        self.hand.cook = playerId

    # ---------------------------------------------------------------- 同步

    def _blockData(self):
        return GetBlockEntityData(self.station.dimensionId, self.station.pos)

    def _covered(self):
        """炉灶上面盖着东西（锅、煎锅、别的方块，Shared/Rules/StoveCover）：烤架是它们的，什么也不收
        （开站前服务端复查用同一个答案，GrillOpen）。"""
        return GrillOpen.isCovered(self.station.dimensionId, self.station.pos)

    def _flush(self):
        """世界里的展示（烤位上的东西变了才广播）和站点数据（每刻重算，变了才发）。"""
        data = self._blockData()
        if data is None:
            return
        if self._publishStove:
            self._publishStove = False
            PublishStove(self.station.dimensionId, self.station.pos, data)
        grill, state = self.hand.grill, self.station.state
        down, up, byHand = [], [], []
        for place in range(Rules.PLACES):
            here = state.getItem((Rules.GROUP_GRILL, place)) is not None
            down.append(Frying.syncStep(grill.down(place)) if here else 0.0)
            up.append(Frying.syncStep(grill.up(place)) if here else 0.0)
            byHand.append(bool(grill.byHand(place)) and here)
        state.setData({"down": down, "up": up, "hand": byHand})


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点（站点声明两端同一份，见 GrillStation.buildSchema）。
    炉灶站点要前置包 API 2（光标栈随状态同步、站点逻辑的 ctx / dropped）：太旧的前置包上炉灶照旧走经典玩法，返回 None。"""
    if getattr(api, "API_VERSION", 0) < 2:
        return None
    logicClass = type("StoveLogic", (GrillLogicMixin, api.StationLogic), {"kit": api})
    stationType = api.StationType(Rules.STATION_ID, Rules.STOVE_BLOCKS, logicClass, schema=Rules.buildSchema(api), reach=REACH)
    stationType.canOpen = GrillOpen.opensStation     # 服务端开站前复查（K30）；老版本的前置包不读这个属性，行为同从前
    api.registerStation(stationType)
    return logicClass
