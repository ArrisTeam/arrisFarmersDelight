# -*- coding: utf-8 -*-
"""BoardChop - 砧板站点的一刀：校验、落刀、最后一刀整叠切开（服务端）

对应 Hands-On Delight：station/BoardLogic.java 的 chop（456-523）。动作 chop {"mark": 刀口序号, "at": 板面 z, "at_x": 板面 x, "yaw": 操作者的方向}：
- 板上有东西、刀口序号正好是下一个（还得在这件东西的刀口数以内）、离上一刀不到 0.15 秒（3 刻）的拒绝（refused，客户端据此撤回画好的切口）；
  间隔从这一刻起算，工具不对也算；有层时板上的不是等着切的，也拒绝；
- 配方现查（logic.recipe 是 tick 每 0.25 秒复查一次的缓存，外面的人在两次复查之间换了板就是上一件东西的）：板上的 key 和 logic.itemKey 对不上、
  或缓存的配方不是现查的那个，就重布刀口（logic.restart()）、这一刀不算；产物按现查的配方算；
- 刀是光标栈上切得了的，光标栈空着就是背包里第一个切得了的（BoardTools.findTool），找不到也拒绝；
- 不是最后一刀：发 chopped {at, spot, angle, tool, item, stroke, block, yields}，开着站点的人和附近旁观的人（BoardEmit）各自按 Shared/Rules/BoardSounds 放刀声
  （刀、斧削皮、剪刀、被切材质的击打声分着来，服务端不再放一个固定的）；
- 最后一刀：重布刀口，整叠最多 16 件一件件切（每件结算一次产物、磨损一次工具，"耐久"附魔免掉的不磨，磨到工具坏了批就停），
  工具那一格先写回、产物后给厨师，板上剩下的留着；发 chopped 多带 count / done。创造模式不磨损。
"""
import time

from . import BoardGive, BoardTools
from .BoardEmit import emit
from ...Server.Helpers.Player import IsCreative
from ...Shared.Rules import CuttingStation as Rules
from ...Shared.Rules.BoardStation import keyOf

YAWS = (0, 90, 180, 270)
MOST_YIELDS = 4                    # chopped 里带几种产物的名字（客户端认材质用）


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1.0e6


def _at(value):
    return round(min(16.0, max(0.0, float(value))), 3)


def _name(value):
    """事件走线格式只收 str：py2 里下游包加的配方、引擎给的名字可能是 unicode。"""
    return value.encode("utf-8") if not isinstance(value, str) and hasattr(value, "encode") else value


def refuse(logic):
    emit(logic, "refused", {})                 # 和别的事件一样：开着站点的人收 effect、旁观的人收广播（被拒的敲击声人人听得到）
    return True


def _look(logic, data, mark, tool, item, recipe):
    """chopped 的载荷：落在哪、哪一刀的线、什么工具、切的什么、怎么切（刀 / 削皮 / 劈 / 砸 / 铲 / 撬 / 剪）、是不是方块、切出什么（客户端放声音、飞碎屑用）。
    at / at_x / yaw 来自客户端，只当画碎屑的位置，夹进板面。"""
    out = {"at": _at(data["at"]) if _number(data.get("at")) else 8.0, "spot": round(logic.cut.spots[mark], 4),
           "angle": round(logic.cut.angles[mark], 4), "tool": _name(tool["newItemName"]), "item": _name(item["newItemName"]),
           "yaw": data["yaw"] if data.get("yaw") in YAWS else 0, "stroke": Rules.strokeOf(recipe),
           "block": logic.env().typeOf(item) == "block", "yields": [_name(entry["itemName"]) for entry in recipe["itemList"]][:MOST_YIELDS]}
    if _number(data.get("at_x")):
        out["at_x"] = _at(data["at_x"])
    return out


def chop(logic, playerId, data):
    """一个 chop 动作；总是算接受（拒绝靠 refused 事件让客户端撤回，不用整份状态重发）。"""
    item = logic.boardItem()
    mark = data.get("mark")
    recipe = logic.env().recipeOf(item) if item is not None else None       # 现查：缓存的 logic.recipe 可能是上一件东西的
    if item is not None and (keyOf(item) != logic.itemKey or logic.recipe is not recipe):
        logic.restart()                  # 板在两次复查之间被换了：刀口和配方都是旧的，这一刀不算（HoD 每刻都查）
        return refuse(logic)
    if recipe is None or logic.layers() or not isinstance(mark, int) or isinstance(mark, bool) \
            or not 0 <= mark < min(logic.cut.plan.marks, len(logic.cut.spots)) or not logic.cut.accept(time.time(), mark, True):
        return refuse(logic)
    found = BoardTools.findTool(logic, playerId, item)
    if found is None:
        return refuse(logic)
    where, tool = found
    look = _look(logic, data, mark, tool, item, recipe)
    if not logic.cut.strike():
        emit(logic, "chopped", look)
        return True
    return _cutTheStack(logic, playerId, item, recipe, where, tool, look)


def _cutTheStack(logic, playerId, item, recipe, where, tool, look):
    """最后一刀（506-522）：整叠最多 16 件一起切开；产物按现查的配方算。"""
    wears = not IsCreative(playerId) and BoardTools.maxDurability(tool) > 0
    batch, spent = Rules.wearFor(item["count"], BoardTools.usesLeft(tool) if wears else None, Rules.unbreakingOf(tool))
    if batch <= 0:
        logic.restart()                  # 工具已经没有耐久（或板上没有可切的）：刀口落满了不重布的话，以后每一刀都被拒
        return refuse(logic)
    pieces = Rules.resultsFor(recipe, batch, fortune=Rules.fortuneOf(tool))
    if wears:
        worn, broke = BoardTools.worn(tool, spent)
        BoardGive.writeTool(logic, playerId, where, worn, broke)
    for name, aux, count in pieces:
        BoardGive.give(logic, {"newItemName": name, "newAuxValue": aux, "count": count})
    rest = dict(item, count=item["count"] - batch)
    logic.setBoard(rest if rest["count"] > 0 else None)
    logic.restart()
    emit(logic, "chopped", dict(look, count=batch, done=True))
    return True
