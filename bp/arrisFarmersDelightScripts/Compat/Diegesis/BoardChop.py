# -*- coding: utf-8 -*-
"""BoardChop - 砧板站点的一刀：校验、落刀、最后一刀整叠切开（服务端）

对应 Hands-On Delight：station/BoardLogic.java 的 chop（456-523）。动作 chop {"mark": 刀口序号, "at": 板面 z, "at_x": 板面 x, "yaw": 操作者的方向}：
- 板上有东西、刀口序号正好是下一个、离上一刀不到 0.15 秒（3 刻）的拒绝（refused，客户端据此撤回画好的切口）；间隔从这一刻起算，工具不对也算；
- 刀是光标栈上切得了的，光标栈空着就是背包里第一个切得了的（BoardTools.findTool），找不到也拒绝；
- 不是最后一刀：发 chopped {at, spot, angle, tool, item}，所有人听到刀声；
- 最后一刀：重布刀口，整叠最多 16 件一件件切（每件结算一次产物、磨损一次工具，"耐久"附魔免掉的不磨，磨到工具坏了批就停），
  工具那一格先写回、产物后给厨师，板上剩下的留着；发 chopped 多带 count / done。创造模式不磨损。
"""
import time

from . import BoardGive, BoardTools
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import IsCreative
from ...Shared.Rules import CuttingStation as Rules

KNIFE_SOUND = "ambient.cutting_board.knife"
YAWS = (0, 90, 180, 270)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e6


def _at(value):
    return round(min(16.0, max(0.0, float(value))), 3)


def refuse(logic):
    logic.station.effect("refused", {})
    return True


def _look(logic, data, mark, tool, item):
    """chopped 的载荷：落在哪、哪一刀的线、什么工具、切的什么（客户端画碎屑和声音用）。at / at_x / yaw 来自客户端，只当画碎屑的位置，夹进板面。"""
    out = {"at": _at(data["at"]) if _number(data.get("at")) else 8.0, "spot": round(logic.cut.spots[mark], 4),
           "angle": round(logic.cut.angles[mark], 4), "tool": tool["newItemName"], "item": item["newItemName"],
           "yaw": data["yaw"] if data.get("yaw") in YAWS else 0}
    if _number(data.get("at_x")):
        out["at_x"] = _at(data["at_x"])
    return out


def chop(logic, playerId, data):
    """一个 chop 动作；总是算接受（拒绝靠 refused 事件让客户端撤回，不用整份状态重发）。"""
    station = logic.station
    item = logic.boardItem()
    mark = data.get("mark")
    if item is None or not isinstance(mark, int) or isinstance(mark, bool) or not 0 <= mark < logic.cut.plan.marks \
            or not logic.cut.accept(time.time(), mark, True):
        return refuse(logic)
    found = BoardTools.findTool(logic, playerId, item) if logic.recipe is not None else None
    if found is None:
        return refuse(logic)
    where, tool = found
    look = _look(logic, data, mark, tool, item)
    last = logic.cut.strike()
    ToAllPlayerPlaySound(station.dimensionId, station.pos, KNIFE_SOUND)
    if not last:
        station.effect("chopped", look)
        return True
    return _cutTheStack(logic, playerId, item, where, tool, look)


def _cutTheStack(logic, playerId, item, where, tool, look):
    """最后一刀（506-522）：整叠最多 16 件一起切开。"""
    wears = not IsCreative(playerId) and BoardTools.maxDurability(tool) > 0
    batch, spent = Rules.wearFor(item["count"], BoardTools.usesLeft(tool) if wears else None, Rules.unbreakingOf(tool))
    if batch <= 0:
        return refuse(logic)
    pieces = Rules.resultsFor(logic.recipe, batch, fortune=Rules.fortuneOf(tool))
    if wears:
        worn, broke = BoardTools.worn(tool, spent)
        BoardGive.writeTool(logic, playerId, where, worn, broke)
    for name, aux, count in pieces:
        BoardGive.give(logic, {"newItemName": name, "newAuxValue": aux, "count": count})
    rest = dict(item, count=item["count"] - batch)
    logic.setBoard(rest if rest["count"] > 0 else None)
    logic.restart()
    logic.station.effect("chopped", dict(look, count=batch, done=True))
    return True
