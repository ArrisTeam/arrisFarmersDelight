# -*- coding: utf-8 -*-
"""PotLogic - 厨锅站点的服务端逻辑：槽位规则、搅拌评星、整批出锅、盛出、取回、照书放料（服务端）

对应 Hands-On Delight：station/PotLogic.java。锅里的东西照旧在厨锅的容器格和预览槽里（Server/Helpers/PotContainer.py）：
站点的槽组 ingredients（容器格 0-5）和 served（容器格 7）经 ContainerSlots 直接绑在上面，点击、Shift 点击、拖过多格、双击聚拢
都由前置包的动作处理（光标栈在服务端，见 Shared/Actions），这里只管规则：
    mayPlace   凑得成菜的料和别的东西都收，只有盛菜的容器不收（PotStation.mayPlace）；served 什么也放不进
    onSlotChanged  食材格变了：下一刻按它做的那道菜把料摆开（shareOut），并记"料是手放的"（feedByHand）
    onTaken    从 served 取走的算盛出：记做过几份、给经验
计时、评星、勺子在 Server/HandCooking.py 的 PotHand 里：站点关了它们还在，厨师走开 2 秒后锅按 FD 原样自己煮。
站点开着时厨师手里拿着这道菜的容器、锅里有煮好的菜：开站被拒，FD 原样盛一份（PotServe.serveByHand）。自定义动作：
    stir      {"x", "z", "at"}  勺尖的位置（方块中心为原点、世界朝向、-1..1）和厨师的钟（秒）；缺 x / z 当 0，别人握着勺子时不算
    scoop     {"all", "from_inventory"}  盛一份 / 盛到没有，容器从光标栈或背包来（PotScoop.scoop）
    take_back {}  最后一个沉着的食材格退给玩家（PotScoop.takeBack）
    bookFill  {"key", "sets"}  食谱书里点的菜：从背包放 1 / 16 份整份的料（BookFill.fillPot）
表现事件：served {"grade", "bonus"}（整批出锅）、scooped {"count"}（盛出）；控件和数据见 PotSync.py，世界外观广播见 Server/PotLook.py。
"""
import time

from . import BookFill, PotScoop, PotSync
from ...Server import HandCooking, PotLook, PotServe
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import GetBlockEntityData
from ...Server.Helpers.Player import GiveOrDropItem
from ...Shared.Rules import CookingPot as CookingPotRules
from ...Shared.Rules import PotStation as Rules

REACH = 6.0
PUBLISH_SECONDS = 0.25           # 站点数据（锅里的菜、几份、还要几秒……）每秒同步 4 次；控件每刻写、变了才发


def _isNumber(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e9


def _maxStack(kind):
    return PotContainer.maxStackOf(kind[0], kind[1])


class PotLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类和 kit 只在运行时拿得到）。"""

    kit = None           # 前置包的服务端 Api（register 里放进去）

    def __init__(self, station):
        super(PotLogicMixin, self).__init__(station)
        self.hand = None
        self.wanted = None            # 书里最后点的那道（配方序号）：锅里的料还做得成它时就是锅的选择，锅空了就忘
        self._unsorted = False
        self._served = 0
        self._sincePublish = 0.0
        self._dishName = None
        dimensionId, pos = station.dimensionId, station.pos
        station.state.bindSlots(Rules.GROUP_INGREDIENTS, PotContainer.ContainerSlots(dimensionId, pos, 0, Rules.INPUT_SLOTS))
        station.state.bindSlots(Rules.GROUP_SERVED, PotContainer.ContainerSlots(dimensionId, pos, PotContainer.RESULT_SLOT, 1))

    # ---------------------------------------------------------------- 钩子

    def onOpen(self, playerId):
        station = self.station
        data = GetBlockEntityData(station.dimensionId, station.pos)
        if data is None:
            return False
        if PotServe.serveByHand(playerId, station.dimensionId, station.pos):
            return False                  # 手里拿着这道菜的容器、锅里有煮好的菜：FD 原样盛一份，不开站点（HoD 的 opens）
        now = time.time()
        self.hand = HandCooking.handOf(station.dimensionId, station.pos, data)
        self.hand.spoon.open(playerId, now)
        self.hand.clock.attend(now)
        self._served = self.hand.served
        self._refresh(now, data, True)
        return True

    def onRemoved(self):
        PotLook.attend(self.station.dimensionId, self.station.pos, [])

    def mayPlace(self, ref, item):
        return ref[0] == Rules.GROUP_INGREDIENTS and Rules.mayPlace(item)

    def onSlotChanged(self, ref):
        self._sincePublish = PUBLISH_SECONDS          # 锅里的东西变了：下一刻就重算站点数据（它能做哪道菜、沉着哪几格）
        if ref[0] == Rules.GROUP_INGREDIENTS:
            self._unsorted = True
            if self.hand is not None:
                self.hand.clock.feedByHand()

    def onTaken(self, ref, item):
        if ref[0] == Rules.GROUP_SERVED and item and self.actor:
            station = self.station
            PotServe.served(self.actor, station.dimensionId, GetBlockEntityData(station.dimensionId, station.pos), item,
                            item.get("count") or 1)

    def userData(self, playerId):
        """只给他自己的几项：他盛出过几份这道菜、每道菜各盛出过几份（食谱书上的星星）、勺子在不在他手里。"""
        if self.hand is None:
            return None
        return {"made": HandCooking.madeOf(playerId, self._dishName) if self._dishName else 0,
                "made_all": HandCooking.madeMap(playerId), "here": self.hand.spoon.holder == playerId}

    def onCustomAction(self, playerId, name, data):
        if self.hand is None:
            return False
        if name == "stir":
            return self._stir(playerId, data)
        if name == "scoop":
            PotScoop.scoop(self, playerId, data)
        elif name == "take_back":
            PotScoop.takeBack(self, playerId)
        elif name == "bookFill":
            BookFill.fillPot(self, playerId, data.get("key"), data.get("sets"), _maxStack)
        else:
            return False
        self._refresh(time.time(), None, True)
        return True

    def tick(self, dt):
        hand = self.hand
        if hand is None:
            return
        now = time.time()
        hand.clock.attend(now)
        station = self.station
        PotLook.attend(station.dimensionId, station.pos, station.users)
        if self._unsorted:
            self._unsorted = False
            self._shareOut()
        self._giveBack(now)
        landed = hand.served != self._served
        if landed:
            self._served = hand.served
            station.effect("served", {"grade": hand.clock.grade, "bonus": hand.clock.bonus})
        self._sincePublish += dt
        self._refresh(now, None, landed)

    # ---------------------------------------------------------------- 搅

    def _stir(self, playerId, data):
        x, z, at = data.get("x"), data.get("z"), data.get("at")
        now = time.time()
        taken = HandCooking.stir(self.hand, playerId, now, float(x) if _isNumber(x) else 0.0, float(z) if _isNumber(z) else 0.0,
                                 float(at) if _isNumber(at) else None)
        if taken:
            station = self.station
            self._refresh(now, None, False)
            PotLook.stroke(station.dimensionId, station.pos, GetBlockEntityData(station.dimensionId, station.pos), self.hand, now)
        return True                       # 别人握着勺子也不回滚：旁观的勺子会按同步的位置走

    # ---------------------------------------------------------------- 摆料、退料

    def _shareOut(self):
        """食材格变了之后，料按它做的那道菜摆开（PotLogic.shareOut）：装不下的退给厨师。"""
        station = self.station
        before = PotContainer.inputs(station.dimensionId, station.pos)
        if not any(Rules.keyOf(item) for item in before):
            self.wanted = None
        found = CookingPotRules.matchIndex(before)
        laid = Rules.layout(before, _maxStack, self.wanted, found, bool(station.users))
        if laid is None:
            return
        PotContainer.setInputs(station.dimensionId, station.pos, before, laid[0])
        for stack in laid[1]:
            size, count = max(1, _maxStack((stack["newItemName"], stack.get("newAuxValue") or 0))), stack["count"]
            while count > 0:
                self._handOver(dict(stack, count=min(size, count)))
                count -= size

    def _cookOrFirst(self):
        """东西该给谁：厨师（勺子在他手里）还在站点就给他，否则给站点里的第一位；没有人返回 None。"""
        users = list(self.station.users)
        cook = self.hand.spoon.holder if self.hand else None
        return cook if cook in users else (users[0] if users else None)

    def _handOver(self, item):
        station, to = self.station, self._cookOrFirst()
        if to is None:
            PotContainer.spill(station.dimensionId, station.pos, item)
        else:
            GiveOrDropItem(to, item, station.dimensionId)

    def _giveBack(self, now):
        """星星省下的料套数还给厨师（他还在工位才给，PotClock.takeSaved 已判断）；用料剩下的空容器也交给他。"""
        clock = self.hand.clock
        saved = clock.takeSaved(now)
        if saved > 0:
            self._giveBackSaved(saved)
        for item in clock.takeLeftovers():
            self._handOver(item)

    def _giveBackSaved(self, saved):
        station, cook = self.station, self.hand.spoon.holder
        if cook not in station.users:
            return
        before = PotContainer.inputs(station.dimensionId, station.pos)
        cells = [dict(cell) for cell in before]
        for cell in cells:
            if Rules.keyOf(cell):
                back = min(saved, cell["count"])
                GiveOrDropItem(cook, dict(cell, count=back), station.dimensionId)
                cell["count"] -= back
        PotContainer.setInputs(station.dimensionId, station.pos, before, cells)

    # ---------------------------------------------------------------- 控件与数据

    def _refresh(self, now, data, publish):
        """控件每刻写（变了才发）；站点数据 publish 为真或每 PUBLISH_SECONDS 重算一次。"""
        for name, value in PotSync.controls(self.hand, now).items():
            self.station.state.setControl(name, value)
        if publish or self._sincePublish >= PUBLISH_SECONDS:
            self._sincePublish = 0.0
            station = self.station
            data = data if data is not None else GetBlockEntityData(station.dimensionId, station.pos)
            if data is not None:
                items = station.state.getItems(Rules.GROUP_INGREDIENTS)
                shared = PotSync.sharedData(data, self.hand, items)
                self._dishName = PotSync.dishNameOf(shared)
                station.state.setData(shared)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点（站点声明两端同一份，见 PotStation.buildSchema）。"""
    logicClass = type("CookingPotLogic", (PotLogicMixin, api.StationLogic), {"kit": api})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.POT_BLOCKS, logicClass, schema=Rules.buildSchema(api), reach=REACH))
    return logicClass
