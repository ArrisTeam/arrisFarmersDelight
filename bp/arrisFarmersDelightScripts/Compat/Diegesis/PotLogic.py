# -*- coding: utf-8 -*-
"""PotLogic - 厨锅站点的服务端逻辑：放料、取回、搅拌评星、整批出锅、盛出（服务端）

对应 Hands-On Delight：station/PotLogic.java。锅里的东西照旧在厨锅的容器格和预览槽里（Server/Helpers/PotContainer.py），
计时、评星、勺子在 Server/HandCooking.py 的 PotHand 里：站点关了它们还在，厨师走开 2 秒后锅按 FD 原样自己煮。
潜行右键照旧打开 FD 的厨锅界面。客户端动作：
    stir  {"x", "z", "at"}  勺尖的位置（以方块中心为原点、世界朝向、-1..1）和厨师的钟（秒）；别人正握着勺子时不算
    add   {"slot": 0..8}    把快捷栏第 slot 格整叠放进锅（只收配方里有的食材），按配方摆开
    take  {"slot": 0..5}    取回锅里第 slot 格那种料
    scoop {}                盛出煮好的菜：产出格里装好的直接拿，预览槽里的用背包里的容器装
表现事件：drawer {"items"}（只发给本人：快捷栏里能下锅的料）、served {"grade", "bonus"}、scooped {}、hint {"key"}（只发给本人）。
同步的数据见 PotSync.py。
"""
import copy
import time

from . import PotSync
from ...Server import HandCooking
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import compFactory, GetBlockEntityData, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Shared.Rules import PotStation as Rules

REACH = 6.0
PUBLISH_SECONDS = 0.25           # 进度、星星、旁观者看到的勺子：每秒同步 4 次
DRAWER_SECONDS = 0.5             # 快捷栏变了（捡到东西、换了格子）多久内跟上


def _isIndex(value, size):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < size


def _isNumber(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e9


def _maxStack(kind):
    return PotContainer.maxStackOf(kind[0], kind[1])


class PotLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类只在运行时拿得到）。"""

    def __init__(self, station):
        super(PotLogicMixin, self).__init__(station)
        self.hand = None
        self._served = 0
        self._sincePublish = 0.0
        self._sinceDrawer = 0.0
        self._drawers = {}

    # ---------------------------------------------------------------- 钩子

    def onOpen(self, playerId):
        data = self._blockData()
        if data is None:
            return False
        now = time.time()
        self.hand = HandCooking.handOf(self.station.dimensionId, self.station.pos, data)
        self.hand.spoon.open(playerId, now)
        self.hand.clock.attend(now)
        self._served = self.hand.served
        self._drawers.pop(playerId, None)
        self._sendDrawer(playerId)
        self._publish(data)
        return True

    def onClose(self, playerId):
        self._drawers.pop(playerId, None)

    def onCustomAction(self, playerId, name, data):
        if self.hand is None:
            return False
        if name == "stir":
            return self._stir(playerId, data)
        if name == "add":
            self._add(playerId, data.get("slot"))
        elif name == "take":
            self._take(playerId, data.get("slot"))
        elif name == "scoop":
            self._scoop(playerId)
        else:
            return False
        self._sendDrawer(playerId)
        self._publish()
        return True

    def tick(self, dt):
        hand = self.hand
        if hand is None:
            return
        now = time.time()
        hand.clock.attend(now)
        saved = hand.clock.takeSaved(now)
        if saved > 0:
            self._giveBackSaved(saved)
        if hand.served != self._served:
            self._served = hand.served
            self.station.effect("served", {"grade": hand.clock.grade, "bonus": hand.clock.bonus})
            self._publish()
        self._sincePublish += dt
        if self._sincePublish >= PUBLISH_SECONDS:
            self._publish()
        self._sinceDrawer += dt
        if self._sinceDrawer >= DRAWER_SECONDS:
            self._sinceDrawer = 0.0
            for playerId in list(self.station.users):
                self._sendDrawer(playerId)

    # ---------------------------------------------------------------- 动作

    def _stir(self, playerId, data):
        x, z, at = data.get("x"), data.get("z"), data.get("at")
        if _isNumber(x) and _isNumber(z):
            HandCooking.stir(self.hand, playerId, time.time(), float(x), float(z), float(at) if _isNumber(at) else None)
        return True                      # 别人握着勺子也不回滚：旁观的勺子会按同步的位置走

    def _add(self, playerId, slot):
        if not _isIndex(slot, PotSync.HOTBAR):
            return
        itemComp = compFactory.CreateItem(playerId)
        item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
        kind = Rules.keyOf(item)
        if kind is None or not Rules.isIngredient(kind):
            self.station.effect("hint", {"key": "not_food"}, only=playerId)
            return
        before = PotContainer.inputs(self.station.dimensionId, self.station.pos)
        cells, placed = Rules.placeStack(before, item, _maxStack(kind))
        if placed <= 0:
            self.station.effect("hint", {"key": "full"}, only=playerId)
            return
        cells, rest = Rules.layout(cells, _maxStack) or (cells, [])
        PotContainer.setInputs(self.station.dimensionId, self.station.pos, before, cells)
        if not IsCreative(playerId):
            left = copy.deepcopy(item)
            left["count"] -= placed
            itemComp.SetPlayerAllItems({(ItemPosType.INVENTORY, slot): left if left["count"] > 0 else None})
            for stack in rest:
                GiveOrDropItem(playerId, stack, self.station.dimensionId)
        self.hand.clock.feedByHand()
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "random.splash")

    def _take(self, playerId, slot):
        if not _isIndex(slot, Rules.INPUT_SLOTS):
            return
        before = PotContainer.inputs(self.station.dimensionId, self.station.pos)
        cells, taken = Rules.takeKind(before, slot)
        if not taken:
            return
        cells, rest = Rules.layout(cells, _maxStack) or (cells, [])
        PotContainer.setInputs(self.station.dimensionId, self.station.pos, before, cells)
        for stack in taken + rest:
            GiveOrDropItem(playerId, stack, self.station.dimensionId)
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    def _scoop(self, playerId):
        dimensionId, pos = self.station.dimensionId, self.station.pos
        data = self._blockData()
        if data is None:
            return
        served, ready = PotContainer.resultItem(dimensionId, pos), PotContainer.preview(data)
        meal, given = served or ready, 0
        if served:
            GiveOrDropItem(playerId, copy.deepcopy(served), dimensionId)
            PotContainer.setResultItem(dimensionId, pos, None)
            given += served["count"]
        if ready and (not served or ready["newItemName"] == served["newItemName"]):
            count = self._takeVessels(playerId, ready, ready["count"])
            if count > 0:
                self._give(playerId, ready, count)
                ready["count"] -= count
                PotContainer.setPreview(data, ready)
                PotContainer.dropExperience(ready["newItemName"], count, pos, dimensionId)
                given += count
            elif not served:
                self.station.effect("hint", {"key": "need_vessel"}, only=playerId)
        if given > 0:
            HandCooking.addMade(playerId, meal["newItemName"], given)
            ToAllPlayerPlaySound(dimensionId, pos, "bucket.fill_water")
            self.station.effect("scooped", {})

    def _takeVessels(self, playerId, meal, wanted):
        """从背包里拿盛这道菜的容器（只比物品名，与锅自己装碗一致），返回拿到几个；不要容器的菜全给。"""
        vessel = PotSync.vesselOf(meal)
        if not vessel or IsCreative(playerId):
            return wanted
        itemComp = compFactory.CreateItem(playerId)
        changed, got = {}, 0
        for index, item in enumerate(itemComp.GetPlayerAllItems(ItemPosType.INVENTORY, True) or []):
            if got < wanted and item and item.get("newItemName") == vessel[0] and item.get("count", 0) > 0:
                used = min(item["count"], wanted - got)
                item["count"] -= used
                got += used
                changed[(ItemPosType.INVENTORY, index)] = item if item["count"] > 0 else None
        if changed:
            itemComp.SetPlayerAllItems(changed)
        return got

    def _giveBackSaved(self, saved):
        """星星省下的料套数还给厨师（他还在工位才给，PotClock.takeSaved 已判断）。"""
        cook = self.hand.spoon.holder
        if cook not in self.station.users:
            return
        before = PotContainer.inputs(self.station.dimensionId, self.station.pos)
        cells = [copy.deepcopy(cell) for cell in before]
        for cell in cells:
            if Rules.keyOf(cell):
                back = min(saved, cell["count"])
                GiveOrDropItem(cook, dict(copy.deepcopy(cell), count=back), self.station.dimensionId)
                cell["count"] -= back
        PotContainer.setInputs(self.station.dimensionId, self.station.pos, before, cells)

    def _give(self, playerId, sample, count):
        size = max(1, PotContainer.maxStackOf(sample["newItemName"], sample.get("newAuxValue") or 0))
        while count > 0:
            stack = {"newItemName": sample["newItemName"], "newAuxValue": sample.get("newAuxValue") or 0, "count": min(size, count)}
            GiveOrDropItem(playerId, stack, self.station.dimensionId)
            count -= stack["count"]

    # ---------------------------------------------------------------- 方块实体数据与同步

    def _blockData(self):
        return GetBlockEntityData(self.station.dimensionId, self.station.pos)

    def _sendDrawer(self, playerId):
        """快捷栏里能下锅的料；和上次发的一样就不发。"""
        items = PotSync.drawerItems(playerId)
        if self._drawers.get(playerId) != items:
            self._drawers[playerId] = items
            self.station.effect("drawer", {"items": items}, only=playerId)

    def _publish(self, data=None):
        self._sincePublish = 0.0
        data = data if data is not None else self._blockData()
        if data is not None:
            self.station.state.setData(PotSync.stationData(self.station.dimensionId, self.station.pos, data, self.hand,
                                                           time.time()))


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点。"""
    logicClass = type("CookingPotLogic", (PotLogicMixin, api.StationLogic), {})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.POT_BLOCKS, logicClass, reach=REACH))
    return logicClass
