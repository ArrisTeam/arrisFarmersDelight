# -*- coding: utf-8 -*-
"""GrillLogic - 炉灶站点的服务端逻辑：摆上灶台、逐件翻面、取下，告诉客户端每件两面烤到哪了（服务端）

对应 Hands-On Delight：station/StoveLogic.java。烤位上的东西照旧在方块实体数据 "0".."5"（Server/Stove.py），
两面进度在 Server/HandGrill.py 的 StoveHand 里（站点关了它还在）。潜行右键是 FD 原来的玩法。客户端动作：
    place {"slot": 0..8}   把快捷栏第 slot 格（能烤的）每个空烤位摆一件；手放的从此两面分开烤
    turn  {"place": 0..5}  把这个烤位上的那件翻个面（离这件上次翻不到 0.3 秒不算）
    take  {"place": 0..5}  取下这个烤位上的那件（生的、半熟的、烤好的）
表现事件：drawer {"items"}（只发给本人）、turned {"place"}、grilled {}、hint {"key"}（只发给本人）。
站点数据：slots 六项，每项 {item, done, byHand, down, up, oneSided}（空烤位是 {}）。
"""
import copy
import time

from ...Server import HandGrill
from ...Server.Helpers.BlockItems import PublishStove
from ...Server.Helpers.Engine import compFactory, GetBlockEntityData, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Server.Stove import EnsureStoveData
from ...Shared.Rules import GrillStation as Rules
from ...Shared.Rules.HandsOn import Grill

REACH = 6.0
PUBLISH_SECONDS = 0.25
DRAWER_SECONDS = 0.5
HOTBAR = 9


def _wire(item):
    if not item or not item.get("newItemName"):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": 1}


def _isIndex(value, size):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < size


class GrillLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类只在运行时拿得到）。"""

    def __init__(self, station):
        super(GrillLogicMixin, self).__init__(station)
        self.hand = None
        self._finished = 0
        self._sincePublish = 0.0
        self._sinceDrawer = 0.0
        self._drawers = {}

    def onOpen(self, playerId):
        data = self._blockData()
        if data is None:
            return False
        EnsureStoveData(data)            # /setblock、结构放出的炉灶没走放置事件
        self.hand = HandGrill.handOf(self.station.dimensionId, self.station.pos)
        self._finished = self.hand.finished
        self._drawers.pop(playerId, None)
        self._sendDrawer(playerId)
        self._publish(data)
        return True

    def onClose(self, playerId):
        self._drawers.pop(playerId, None)

    def onCustomAction(self, playerId, name, data):
        if self.hand is None:
            return False
        if name == "place":
            self._place(playerId, data.get("slot"))
        elif name == "turn":
            self._turn(playerId, data.get("place"))
        elif name == "take":
            self._take(playerId, data.get("place"))
        else:
            return False
        self._sendDrawer(playerId)
        self._publish()
        return True

    def tick(self, dt):
        if self.hand is None:
            return
        if self.hand.finished != self._finished:
            self._finished = self.hand.finished
            self.station.effect("grilled", {})
            ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "random.pop")
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

    def _place(self, playerId, slot):
        if not _isIndex(slot, HOTBAR):
            return
        itemComp = compFactory.CreateItem(playerId)
        item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
        data = self._blockData()
        if not item or not Rules.canGrill(item.get("newItemName")) or data is None:
            self.station.effect("hint", {"key": "not_food"}, only=playerId)
            return
        occupied = [HandGrill.slotItem(data, place) is not None for place in range(Rules.PLACES)]
        creative = IsCreative(playerId)
        laid = Grill.laidPlaces(occupied, -1, item["count"])     # 创造模式也只摆这一叠的件数（实机：不限时一下铺满六格）
        if not laid:
            self.station.effect("hint", {"key": "full"}, only=playerId)
            return
        for place in laid:
            one = copy.deepcopy(item)
            one["count"] = 1
            data[str(place)] = {"itemDict": one, "cookTimer": HandGrill.COOK_TIMER}
            self.hand.grill.farmersDelightsWay(place)
            self.hand.grill.layByHand(place)
        self.hand.cook = playerId
        if not creative:
            left = copy.deepcopy(item)
            left["count"] -= len(laid)
            itemComp.SetPlayerAllItems({(ItemPosType.INVENTORY, slot): left if left["count"] > 0 else None})
        PublishStove(self.station.dimensionId, self.station.pos, data)
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    def _turn(self, playerId, place):
        data = self._blockData()
        if data is None or not _isIndex(place, Rules.PLACES):
            return
        if HandGrill.turn(self.hand, playerId, place, time.time(), HandGrill.slotItem(data, place)):
            self.station.effect("turned", {"place": place})

    def _take(self, playerId, place):
        data = self._blockData()
        if data is None or not _isIndex(place, Rules.PLACES):
            return
        item = HandGrill.slotItem(data, place)
        if item is None:
            return
        GiveOrDropItem(playerId, copy.deepcopy(item), self.station.dimensionId)
        data[str(place)] = {"itemDict": None, "cookTimer": HandGrill.COOK_TIMER}
        self.hand.grill.farmersDelightsWay(place)
        PublishStove(self.station.dimensionId, self.station.pos, data)
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    # ---------------------------------------------------------------- 同步

    def _blockData(self):
        return GetBlockEntityData(self.station.dimensionId, self.station.pos)

    def _sendDrawer(self, playerId):
        """快捷栏里能烤的东西（别的格子空着）；和上次发的一样就不发。"""
        itemComp = compFactory.CreateItem(playerId)
        items = []
        for slot in range(HOTBAR):
            item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
            shown = _wire(item) if item and Rules.canGrill(item.get("newItemName")) else {}
            if shown:
                shown["count"] = item["count"]
            items.append(shown)
        if self._drawers.get(playerId) != items:
            self._drawers[playerId] = items
            self.station.effect("drawer", {"items": items}, only=playerId)

    def _publish(self, data=None):
        self._sincePublish = 0.0
        data = data if data is not None else self._blockData()
        if data is None:
            return
        grill, slots = self.hand.grill, []
        for place in range(Rules.PLACES):
            item = HandGrill.slotItem(data, place)
            name = item["newItemName"] if item else None
            slots.append({
                "item": _wire(item), "done": bool(name) and not Rules.canGrill(name), "byHand": grill.byHand(place),
                "down": Grill.syncStep(grill.down(place)), "up": Grill.syncStep(grill.up(place)),
                "oneSided": bool(name) and Rules.isOneSided(name),
            } if item else {})
        self.station.state.setData({"slots": slots})


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点。"""
    logicClass = type("StoveLogic", (GrillLogicMixin, api.StationLogic), {})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.STOVE_BLOCKS, logicClass, reach=REACH))
    return logicClass
