# -*- coding: utf-8 -*-
"""BoardTools - 砧板站点用的工具与物品：找刀、扣耐久、认物品类型和最大耐久（服务端）

对应 HoD 的 BoardLogic.chop 里挑工具的那段（471-482）和 Cutting.toolSlot（195-210）。
刀是谁：光标栈上拿着的、切得了板上这样东西的；光标栈空着，就是背包里第一个切得了的：选中的快捷栏格、副手、再 0..35 按序。
光标栈上拿着别的东西（不是切它的工具）时，不去背包里找：和 HoD 一样当没有刀。
"""
import copy

from . import BoardGive
from ...Server.Helpers.Engine import compFactory, levelId
from ...Server.Helpers.Items import GetItemType, IsKnife
from ...Shared.Rules import CuttingStation as Rules
from ...Shared.Rules.BoardStation import Env


def envFor(logic):
    """这个站点里问"是不是工具、能不能放"用的 Env：刀的标签、物品类型问引擎，最大堆叠问光标栈上下文（动作之外的默认 64）。"""
    ctx = logic.ctx
    return Env(IsKnife, GetItemType, ctx.maxStackOf if ctx is not None else None)


def findTool(logic, playerId, onBoard):
    """chop 用哪把工具：((来处, ...), 物品) 或 None。来处见 BoardGive.writeTool。"""
    env, ctx = envFor(logic), logic.ctx
    hand = ctx.getHand()
    if hand is not None:
        return ((BoardGive.HAND,), hand) if env.cutsWith(onBoard, hand) else None
    selected = BoardGive.selectedSlot(playerId)
    candidates = [((BoardGive.INV, selected), ctx.inventory[selected])] if 0 <= selected < 9 else []
    candidates.append(((BoardGive.OFFHAND,), BoardGive.offhandOf(playerId)))
    candidates += [((BoardGive.INV, index), ctx.inventory[index]) for index in range(BoardGive.INVENTORY)]
    for where, tool in candidates:
        if tool and tool.get("count", 0) > 0 and env.cutsWith(onBoard, tool):
            return where, tool
    return None


def maxDurability(tool):
    """工具的最大耐久；不会损坏的是 0（引擎的物品字典里不会坏的东西 durability 也读作 0，所以要问物品信息）。"""
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(tool["newItemName"], tool.get("newAuxValue") or 0) or {}
    return info.get("maxDurability") or 0


def usesLeft(tool):
    """工具还能切几件；不会损坏的返回 None（不限）。"""
    return Rules.toolLeft(tool, maxDurability(tool))


def worn(tool, uses):
    """用了 uses 次之后的工具：(新的物品或 None（坏了）, 是不是坏了)。不会损坏的原样。"""
    if usesLeft(tool) is None:
        return tool, False
    after = copy.deepcopy(tool)
    after["durability"] = tool["durability"] - uses
    return (None, True) if after["durability"] <= 0 else (after, False)
