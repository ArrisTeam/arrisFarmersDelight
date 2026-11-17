# -*- coding: utf-8 -*-
"""BoardGive - 砧板站点在一个动作里动玩家的东西：从光标栈或背包格拿一叠、给厨师东西、扣工具耐久（服务端）

对应 HoD 的 BoardLogic.putBack / give / 工具那一格的写回（765-782、509-515）。都经 logic.ctx（光标栈 + 36 格背包窗口，Manager 在动作结束时
一并写回）；背包放不下的 append 到 logic.dropped，掉在玩家脚下。副手不在背包窗口里，直接经引擎写。
"""
from ...Server.Helpers.Engine import compFactory, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound

INVENTORY = 36
HAND = "hand"
INV = "inv"
OFFHAND = "offhand"


def addToWindow(kit, window, item, maxStackOf):
    """放进背包窗口：先并入同种未满的栈、再放进空格，都按格号（Inventory.add）；返回放不下的余量或 None。"""
    items = kit.Items
    rest, size = item, maxStackOf(item)
    for index in range(len(window)):
        there = window[index]
        if there is None or not items.sameItem(there, rest):
            continue
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


def give(logic, item):
    """给厨师：按物品的最大堆叠拆开（一份饼干 8 个，16 份超过一叠），背包放不下的掉在脚下（BoardLogic.give）。"""
    if not item or (item.get("count") or 0) <= 0:
        return
    items, ctx = logic.kit.Items, logic.ctx
    left, size = int(item["count"]), max(1, ctx.maxStackOf(item))
    while left > 0:
        part = items.withCount(item, min(size, left))
        left -= size
        rest = addToWindow(logic.kit, ctx.inventory, part, ctx.maxStackOf)
        if rest is not None:
            logic.dropped.append(rest)


def sourceOf(logic, slot):
    """手上这叠从哪来：slot 为 None 是光标栈，否则是背包第 slot 格（Shift 点托盘、右键开站时主手拿着的）；没有（越界、空）返回 None。"""
    ctx = logic.ctx
    if slot is None:
        return ctx.getHand()
    return ctx.inventory[slot] if isinstance(slot, int) and not isinstance(slot, bool) and 0 <= slot < INVENTORY else None


def take(logic, slot, count):
    """从那一叠里拿走 count 个（putBack：剩下的放回原处）。"""
    ctx, items = logic.ctx, logic.kit.Items
    if slot is None:
        ctx.setHand(items.shrink(ctx.getHand(), count))
    else:
        ctx.inventory[slot] = items.shrink(ctx.inventory[slot], count)


def selectedSlot(playerId):
    """玩家选中的快捷栏格（0-8）；读不到是 -1。"""
    return compFactory.CreateItem(playerId).GetSelectSlotId()


def offhandOf(playerId):
    return compFactory.CreateItem(playerId).GetPlayerItem(ItemPosType.OFFHAND, 0, True)


def putTool(logic, where, tool):
    """用过的工具写回光标栈 / 背包窗口里它来的地方（动作作废时跟着窗口一起丢）。工具那一格先写，产物后给：坏了的刀留空，产物别落进去被盖掉
    （HoD 的次序）。where 是 (HAND,) / (INV, 格) / (OFFHAND,)；副手不在窗口里，这里不碰，见 settleTool。tool 是 None 表示用坏了。"""
    ctx = logic.ctx
    if where[0] == HAND:
        ctx.setHand(tool)
    elif where[0] == INV:
        ctx.inventory[where[1]] = tool


def settleTool(logic, playerId, where, tool, broke):
    """用过的工具直接写进引擎的那一半：副手里的刀、刀碎的声音。动作里撤不回来的事：前面哪一步抛了异常，动作作废，站点和背包窗口放回原样，
    已经写进副手的刀却放不回去（刀磨损了或没了、产物没出）。所以它是动作的最后一步，调用方在别的都做完之后才调。"""
    if where[0] == OFFHAND:
        compFactory.CreateItem(playerId).SetEntityItem(ItemPosType.OFFHAND, tool, 0)
    if broke:
        ToAllPlayerPlaySound(logic.station.dimensionId, logic.station.pos, "random.break")
