# -*- coding: utf-8 -*-
"""BoardLogic - 切菜板站点的服务端逻辑：放上一叠、按刀口一刀刀切、最后一刀切透整叠、取回（服务端）

对应 Hands-On Delight：station/BoardLogic.java。站点只是交互层：板上的东西照旧存在方块实体数据 cuttingDict
（带数量，≤ CuttingStation.BOARD_LIMIT），展示实体照旧，所以潜行右键的经典玩法、破坏掉落都不受影响。
刀口进度只在站点实例里：最后一个人离开就重新布刀口（与 HoD 一致）。客户端动作：
    place {}         板是空的：把主手那叠（最多 BOARD_LIMIT 个）放上去
    use {"mark": i}  板上有能切的东西：背包 / 副手 / 主手里有合适的工具就落第 i 刀（只认下一刀，两刀间隔 ≥ 0.15 秒），
                     没有工具就取回（HoD：没有可用的刀时点食材 = 取回）
    take {}          取回板上的东西
表现事件：tool {"item": 将用的工具名或 ""}（只发给本人）、chop {"mark", "last"}、hint {"key"}（只发给本人）。
"""
import copy
import time

from ...Server.Helpers.BlockItems import DropLegacyDisplays, PublishBoard
from ...Server.Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetCarriedItem, SetCarriedItem, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Items import GetItemType, IsKnife
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Shared.Data.Cutting import CuttingBoardDict
from ...Shared.Rules import CuttingStation as Rules
from ...Shared.Rules.HandsOn import Cutting

REACH = 6.0
RECHECK_SECONDS = 0.25


def _key(item):
    return (item["newItemName"], item.get("newAuxValue", 0))


def _wireItem(item):
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue", 0), "count": item["count"]}


def _isMark(value):
    return isinstance(value, int) and not isinstance(value, bool)


class BoardLogicMixin(object):
    """和前置包的 StationLogic 拼成站点逻辑类（register 里用 type() 组装，基类只在运行时拿得到）。"""

    def __init__(self, station):
        super(BoardLogicMixin, self).__init__(station)
        self.cut = Cutting.BoardCut()
        self.recipe = None
        self.itemKey = None
        self.count = 0
        self._started = False
        self._sinceCheck = 0.0

    # ---------------------------------------------------------------- 钩子

    def onOpen(self, playerId):
        if self._blockData() is None:
            return False
        if not self._started:
            self._started = True
            self._restart(self._boardItem())
        self._toolHint(playerId)
        return True

    def onCustomAction(self, playerId, name, data):
        if name == "place":
            accepted = self._place(playerId)
        elif name == "use":
            accepted = self._use(playerId, data.get("mark"))
        elif name == "take":
            accepted = self._take(playerId)
        else:
            return False
        self._toolHint(playerId)
        return accepted

    def tick(self, dt):
        """板上的东西被经典玩法 / 别的途径改了：跟着重布刀口。"""
        self._sinceCheck += dt
        if self._sinceCheck < RECHECK_SECONDS:
            return
        self._sinceCheck = 0.0
        item = self._boardItem()
        if (_key(item) if item else None) != self.itemKey or (item["count"] if item else 0) != self.count:
            self._restart(item)

    # ---------------------------------------------------------------- 动作

    def _place(self, playerId):
        data = self._blockData()
        if data is None or self._boardItem(data):
            return False
        carried = GetCarriedItem(playerId, True)
        if not carried or _key(carried) not in CuttingBoardDict:
            self.station.effect("hint", {"key": "only_food"}, only=playerId)
            return False
        board = copy.deepcopy(carried)
        board["count"] = min(carried["count"], Rules.BOARD_LIMIT)
        if not IsCreative(playerId):
            rest = copy.deepcopy(carried)
            rest["count"] -= board["count"]
            SetCarriedItem(playerId, rest if rest["count"] > 0 else None)
        data["cuttingDict"] = board
        PublishBoard(self.station.dimensionId, self.station.pos, board)
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "dig.wood")
        self._restart(board)
        return True

    def _use(self, playerId, mark):
        data = self._blockData()
        item = self._boardItem(data)
        if not item:
            return False
        tool = self._findTool(playerId) if self.recipe is not None else None
        if tool is None:
            return self._take(playerId)
        if not _isMark(mark) or not self.cut.accept(time.time(), mark, True):
            return False
        last = self.cut.strike()
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "ambient.cutting_board.knife")
        self.station.effect("chop", {"mark": mark, "last": last})
        if last:
            self._cutTheStack(playerId, data, item, tool)
        else:
            self._publish()
        return True

    def _cutTheStack(self, playerId, data, item, tool):
        where, toolItem = tool
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(toolItem["newItemName"], toolItem.get("newAuxValue", 0))
        wears = not IsCreative(playerId) and bool(info) and (info.get("maxDurability") or 0) > 0
        batch = Cutting.batchSize(item["count"], Rules.toolLeft(toolItem) if wears else None)
        if batch > 0:
            for name, aux, count in Rules.resultsFor(self.recipe, batch):
                self._give(playerId, name, aux, count)
            if wears:
                self._wearTool(playerId, where, toolItem, batch)
        rest = copy.deepcopy(item)
        rest["count"] -= batch
        if rest["count"] > 0:
            data["cuttingDict"] = rest
            PublishBoard(self.station.dimensionId, self.station.pos, rest)
        else:
            self._clearBoard(data)
            rest = None
        self._restart(rest)

    def _take(self, playerId):
        data = self._blockData()
        item = self._boardItem(data)
        if not item:
            return False
        GiveOrDropItem(playerId, copy.deepcopy(item), self.station.dimensionId)
        self._clearBoard(data)
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "armor.equip_leather")
        self._restart(None)
        return True

    # ---------------------------------------------------------------- 工具与物品

    def _findTool(self, playerId):
        """按主手、副手、背包的顺序找第一件合适的工具：((格子类型, 下标), 物品) 或 None。"""
        itemComp = compFactory.CreateItem(playerId)
        candidates = [((ItemPosType.CARRIED, 0), itemComp.GetPlayerItem(ItemPosType.CARRIED, 0, True)),
                      ((ItemPosType.OFFHAND, 0), itemComp.GetPlayerItem(ItemPosType.OFFHAND, 0, True))]
        for slot, item in enumerate(itemComp.GetPlayerAllItems(ItemPosType.INVENTORY, True) or []):
            candidates.append(((ItemPosType.INVENTORY, slot), item))
        return Rules.pickTool(candidates, self.recipe, IsKnife, GetItemType)

    def _wearTool(self, playerId, where, toolItem, uses):
        """每切一件磨损一次；用坏了播放破碎声并清掉那一格（创造模式与不会损坏的工具由调用方排除）。"""
        tool = copy.deepcopy(toolItem)
        tool["durability"] -= uses
        broken = tool["durability"] <= 0
        if broken:
            ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "random.break")
        posType, slot = where
        itemComp = compFactory.CreateItem(playerId)
        if posType == ItemPosType.INVENTORY:
            if broken:
                itemComp.SetInvItemNum(slot, 0)
            else:
                itemComp.SetPlayerAllItems({(posType, slot): tool})
        else:
            itemComp.SetEntityItem(posType, None if broken else tool, 0)

    def _give(self, playerId, name, aux, count):
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(name, aux) or {}
        for size in Rules.stacks(count, info.get("maxStackSize") or 64):
            GiveOrDropItem(playerId, {"newItemName": name, "newAuxValue": aux, "count": size}, self.station.dimensionId)

    # ---------------------------------------------------------------- 方块实体数据与同步

    def _blockData(self):
        return GetBlockEntityData(self.station.dimensionId, self.station.pos)

    def _boardItem(self, data=None):
        data = data if data is not None else self._blockData()
        item = data["cuttingDict"] if data else None
        return item if item and item.get("count", 0) > 0 else None

    def _clearBoard(self, data):
        DropLegacyDisplays(data)
        data["cuttingDict"] = None
        PublishBoard(self.station.dimensionId, self.station.pos, None)

    def _restart(self, item):
        """板上换了东西（或刚开站）：重新查配方、重布刀口，并同步给使用者。"""
        self.itemKey = _key(item) if item else None
        self.count = item["count"] if item else 0
        self.recipe = CuttingBoardDict.get(self.itemKey) if item else None
        if self.recipe is not None:
            self.cut.restart(Rules.planFor(item["newItemName"], self.recipe))
        else:
            self.cut = Cutting.BoardCut()
        self._publish()

    def _publish(self):
        item = self._boardItem()
        self.station.state.setData({
            "item": _wireItem(item) if item else {},
            "cuttable": self.recipe is not None,
            "marks": self.cut.marks,
            "plan": self.cut.plan.marks if self.recipe is not None else 0,
            "style": self.cut.plan.style,
            "spots": [float(v) for v in self.cut.spots],
            "angles": [float(v) for v in self.cut.angles],
            "stroke": Rules.strokeOf(self.recipe) if self.recipe is not None else "",
        })

    def _toolHint(self, playerId):
        tool = self._findTool(playerId) if self.recipe is not None else None
        self.station.effect("tool", {"item": tool[1]["newItemName"] if tool else ""}, only=playerId)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点。"""
    logicClass = type("CuttingBoardLogic", (BoardLogicMixin, api.StationLogic), {})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.BOARD_BLOCKS, logicClass, reach=REACH))
    return logicClass
