# -*- coding: utf-8 -*-
"""BoardLogic - 切菜板站点的服务端逻辑：放上一叠、按刀口一刀刀切、最后一刀切透整叠、取回（服务端）

对应 Hands-On Delight：station/BoardLogic.java。站点只是交互层：板上的东西照旧存在方块实体数据 cuttingDict
（带数量，≤ CuttingStation.BOARD_LIMIT），展示实体照旧，所以潜行右键的经典玩法、破坏掉落都不受影响。
刀口进度只在站点实例里：最后一个人离开就重新布刀口（与 HoD 一致）。客户端动作：
    place {}         板是空的：把主手那叠（最多 BOARD_LIMIT 个）放上去
    use {"mark": i}  板上有能切的东西：背包 / 副手 / 主手里有合适的工具就落第 i 刀（只认下一刀，两刀间隔 ≥ 0.15 秒），
                     没有工具就取回（HoD：没有可用的刀时点食材 = 取回）
    take {}          取回板上的东西
    lay {"slot": i}  快捷栏第 i 格放上砧板：能切的照切菜放，能打底 / 能接着往上放的走摆盘（DishBoard.py）
板上有摆盘的东西时 use 交给 DishBoard.click（做成、拿走或全拿回来）。
表现事件：tool {"item": 将用的工具名或 ""}、drawer {"items"}、hint {"key"}（都只发给本人）、chop {"mark", "last"}、plated {"item"}。
"""
import copy
import time

from ...Server.Helpers.BlockItems import DropLegacyDisplays, PublishBoard
from ...Server.Helpers import BoardDish as DishStore
from ...Server.Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetCarriedItem, SetCarriedItem
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Shared.Data.Cutting import CuttingBoardDict
from . import BoardTools, BookFill, DishBoard
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
        self._sinceDrawer = 0.0
        self._drawers = {}

    # ---------------------------------------------------------------- 钩子

    def onOpen(self, playerId):
        if self._blockData() is None:
            return False
        if not self._started:
            self._started = True
            self._restart(self._boardItem())
        self._toolHint(playerId)
        self._drawers.pop(playerId, None)
        self._sendDrawer(playerId)
        return True

    def onClose(self, playerId):
        self._drawers.pop(playerId, None)

    def onCustomAction(self, playerId, name, data):
        board = self._blockData()
        if name == "lay" and board is not None and _isMark(data.get("slot")) and 0 <= data["slot"] < DishBoard.HOTBAR:
            key = DishBoard.lay(self, playerId, data["slot"], board)
            accepted = key is None
            if key:
                self.station.effect("hint", {"key": key}, only=playerId)
            self._publish()
        elif name == "bookFill":
            key = BookFill.fillDish(self, playerId, data.get("key"), data.get("sets"), board)
            accepted = key is None
            if key:
                self.station.effect("hint", {"key": key}, only=playerId)
            self._publish()
        elif name == "use" and board is not None and DishStore.hasAny(board):
            accepted = DishBoard.click(self, playerId, board)
            self._publish()
        elif name == "place":
            accepted = self._place(playerId)
        elif name == "use":
            accepted = self._use(playerId, data.get("mark"))
        elif name == "take":
            accepted = self._take(playerId)
        else:
            return False
        self._toolHint(playerId)
        self._sendDrawer(playerId)
        return accepted

    def tick(self, dt):
        """板上的东西被经典玩法 / 别的途径改了：跟着重布刀口。"""
        self._sinceDrawer += dt
        if self._sinceDrawer >= RECHECK_SECONDS * 2.0:
            self._sinceDrawer = 0.0
            for playerId in list(self.station.users):
                self._sendDrawer(playerId)
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
        tool = BoardTools.findTool(playerId, self.recipe) if self.recipe is not None else None
        if tool is None:
            return self._take(playerId)
        if not _isMark(mark) or not self.cut.accept(time.time(), mark, True):
            return False
        last = self.cut.strike()
        ToAllPlayerPlaySound(self.station.dimensionId, self.station.pos, "ambient.cutting_board.knife")
        self.station.effect("chop", {"mark": mark, "last": last, "item": item["newItemName"]})
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
            for name, aux, count in Rules.resultsFor(self.recipe, batch, fortune=Rules.fortuneOf(toolItem)):
                BoardTools.give(playerId, self.station.dimensionId, name, aux, count)
            if wears:
                BoardTools.wearTool(playerId, self.station.dimensionId, self.station.pos, where, toolItem, batch)
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
        board = self._blockData()
        item = self._boardItem(board)
        dish = DishBoard.fields(board) if board is not None else {"layers": [], "dish": {}, "ready": "", "readyName": ""}
        self.station.state.setData(dict(dish, **{
            "item": _wireItem(item) if item else {},
            "cuttable": self.recipe is not None,
            "marks": self.cut.marks,
            "plan": self.cut.plan.marks if self.recipe is not None else 0,
            "style": self.cut.plan.style,
            "spots": [float(v) for v in self.cut.spots],
            "angles": [float(v) for v in self.cut.angles],
            "stroke": Rules.strokeOf(self.recipe) if self.recipe is not None else "",
        }))

    def _sendDrawer(self, playerId):
        """快捷栏里现在能放上砧板的（DishBoard.drawerItems）；和上次发的一样就不发。"""
        board = self._blockData()
        items = DishBoard.drawerItems(playerId, board, self._boardItem(board)) if board is not None else [{}] * DishBoard.HOTBAR
        if self._drawers.get(playerId) != items:
            self._drawers[playerId] = items
            self.station.effect("drawer", {"items": items}, only=playerId)

    def _toolHint(self, playerId):
        tool = BoardTools.findTool(playerId, self.recipe) if self.recipe is not None else None
        self.station.effect("tool", {"item": tool[1]["newItemName"] if tool else ""}, only=playerId)


def register(api):
    """前置包在场时调用：把 mixin 和前置包的 StationLogic 拼成逻辑类并登记站点。"""
    logicClass = type("CuttingBoardLogic", (BoardLogicMixin, api.StationLogic), {})
    api.registerStation(api.StationType(Rules.STATION_ID, Rules.BOARD_BLOCKS, logicClass, reach=REACH))
    return logicClass
