# -*- coding: utf-8 -*-
"""PanLogic - 煎锅站点的服务端逻辑：放料、颠锅翻面、取出，告诉客户端两面煎到哪了（服务端）

对应 Hands-On Delight：station/SkilletLogic.java。锅里的东西照旧在方块实体数据 cookingDict（Server/Skillet.py），
两面进度在 Server/HandFrying.py 的 PanHand 里（站点关了它还在：接着煎、等着翻）。潜行右键是 FD 原来的玩法。客户端动作：
    place {"slot": 0..8}   把快捷栏第 slot 格（能煎的）放进锅：锅里只放同一种、最多 16 个；手放的从此两面分开煎
    toss  {"strength"}     颠锅：食物翻个面（离上次颠不到 0.4 秒不算，回 untossed 给本人）
    take  {}               锅里的东西（生的、半熟的、煎好的）全拿回背包
表现事件：drawer {"items"}（只发给本人）、tossed {"strength"}、untossed {}（只发给本人）、fried {"item"}、hint {"key"}（只发给本人）。
站点数据：item 锅里的东西、done 是否已煎好、byHand、down / up 两面进度（1/32 一档）、batch、heated、oneSided。
"""
import copy
import time

from ...Server import HandFrying
from ...Server.Helpers.BlockItems import PublishSkillet
from ...Server.Helpers.Engine import compFactory, levelId, GetBlockEntityData, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Server.Skillet import COOK_TIMER
from ...Shared.Rules import PanStation as Rules
from ...Shared.Rules.HandsOn import Frying

REACH = 6.0
PUBLISH_SECONDS = 0.25
DRAWER_SECONDS = 0.5
HOTBAR = 9


def _wire(item):
    if not item or not item.get("newItemName") or (item.get("count") or 0) <= 0:
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def _isIndex(value, size):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < size


def _same(a, b):
    return (a.get("newItemName"), a.get("newAuxValue") or 0) == (b.get("newItemName"), b.get("newAuxValue") or 0)


class PanLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类只在运行时拿得到）。"""

    def __init__(self, station):
        super(PanLogicMixin, self).__init__(station)
        self.hand = None
        self._fried = 0
        self._sincePublish = 0.0
        self._sinceDrawer = 0.0
        self._drawers = {}

    def onOpen(self, playerId):
        data = self._blockData()
        if data is None:
            return False
        self.hand = HandFrying.handOf(self.station.dimensionId, self.station.pos)
        self._fried = self.hand.fried
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
        elif name == "toss":
            self._toss(playerId, data.get("strength"))
        elif name == "take":
            self._take(playerId)
        else:
            return False
        self._sendDrawer(playerId)
        self._publish()
        return True

    def tick(self, dt):
        if self.hand is None:
            return
        if self.hand.fried != self._fried:
            self._fried = self.hand.fried
            data = self._blockData()
            self.station.effect("fried", {"item": _wire(data["cookingDict"] if data else None)})
            ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "random.pop")
            self._publish(data)
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
        if not item or not Rules.canFry(item.get("newItemName")) or data is None:
            self.station.effect("hint", {"key": "not_food"}, only=playerId)
            return
        inPan = data["cookingDict"]
        if inPan and not _same(inPan, item):
            self.station.effect("hint", {"key": "other_food"}, only=playerId)
            return
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(item["newItemName"], item.get("newAuxValue") or 0) or {}
        moved = Frying.placeCount(item["count"], inPan["count"] if inPan else 0, info.get("maxStackSize") or 64)
        if moved <= 0:
            self.station.effect("hint", {"key": "full"}, only=playerId)
            return
        pan = copy.deepcopy(inPan or item)
        pan["count"] = (inPan["count"] if inPan else 0) + moved
        data["cookingDict"] = pan
        PublishSkillet(self.station.dimensionId, self.station.pos, pan)
        self.hand.frying.layByHand()
        self.hand.cook = playerId
        if not IsCreative(playerId):
            left = copy.deepcopy(item)
            left["count"] -= moved
            itemComp.SetPlayerAllItems({(ItemPosType.INVENTORY, slot): left if left["count"] > 0 else None})
        sound = "ambient.skillet.addfood" if data["heatEnable"] is True else "armor.equip_leather"
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, sound)

    def _toss(self, playerId, strength):
        data = self._blockData()
        item = data["cookingDict"] if data else None
        if HandFrying.toss(self.hand, playerId, time.time(), item):
            force = float(strength) if isinstance(strength, (int, float)) and not isinstance(strength, bool) else 0.5
            self.station.effect("tossed", {"strength": max(0.0, min(1.0, force))})
            ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")
        elif item:
            self.station.effect("untossed", {}, only=playerId)

    def _take(self, playerId):
        data = self._blockData()
        item = data["cookingDict"] if data else None
        if not item:
            return
        GiveOrDropItem(playerId, copy.deepcopy(item), self.station.dimensionId)
        data["cookingDict"] = None
        data["cookTimer"] = COOK_TIMER
        PublishSkillet(self.station.dimensionId, self.station.pos, None)
        self.hand.frying.farmersDelightsWay()
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")

    # ---------------------------------------------------------------- 同步

    def _blockData(self):
        return GetBlockEntityData(self.station.dimensionId, self.station.pos)

    def _sendDrawer(self, playerId):
        """快捷栏里能煎的东西（别的格子空着）；和上次发的一样就不发。"""
        itemComp = compFactory.CreateItem(playerId)
        items = []
        for slot in range(HOTBAR):
            item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
            items.append(_wire(item) if item and Rules.canFry(item.get("newItemName")) else {})
        if self._drawers.get(playerId) != items:
            self._drawers[playerId] = items
            self.station.effect("drawer", {"items": items}, only=playerId)

    def _publish(self, data=None):
        self._sincePublish = 0.0
        data = data if data is not None else self._blockData()
        if data is None:
            return
        item, frying = data["cookingDict"], self.hand.frying
        name = item.get("newItemName") if item else None
        self.station.state.setData({
            "item": _wire(item),
            "done": bool(name) and not Rules.canFry(name),
            "byHand": frying.byHand,
            "down": Frying.syncStep(frying.down),
            "up": Frying.syncStep(frying.up),
            "batch": max(1, min((item.get("count") or 1) if item else 1, Frying.BATCH)),
            "heated": data["heatEnable"] is True,
            "oneSided": bool(name) and Rules.isOneSided(name),
        })


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点。"""
    logicClass = type("SkilletLogic", (PanLogicMixin, api.StationLogic), {})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.PAN_BLOCKS, logicClass, reach=REACH))
    return logicClass
