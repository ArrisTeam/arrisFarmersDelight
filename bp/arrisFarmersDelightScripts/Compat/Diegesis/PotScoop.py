# -*- coding: utf-8 -*-
"""PotScoop - 厨锅站点的盛出与取回：scoop、take_back（服务端）

对应 Hands-On Delight：station/PotLogic.java 的 scoop / scoopFromInventory / containerSlot / takeBack。都在玩家一个动作里做，
经 logic.ctx 动这位玩家的光标栈和背包窗口（Manager 在动作结束时一并写回），放不下的 append 到 logic.dropped 掉在他脚下。
    scoop {"all": bool, "from_inventory": bool}
        光标栈（手里）是这道菜的容器：每个动作盛一份，all 时盛到没菜或没容器；盛出来的菜在最后一个容器用完时顶替光标栈，
        否则进背包（放不下掉脚下）。from_inventory 是空手：光标栈得是空的，容器从背包里挑（选中的快捷栏格优先，然后 0 号格起按序），
        菜都进背包。每盛一份就算他做过一份、锅里记着的经验在第一份时一并给他（Server/PotServe.served）；
        盛了至少一份就发一次 scooped {"count"} 给站点里的所有人（附近没开站点的人收 PotLook 的同名事件）。
    take_back {}
        倒进去的、打进去的、化掉的东西（Shared/Data/PotSunk）空手点不到：最后一个装着它们的食材格整格退给玩家，一次一格。
"""
from ...Server import PotServe, PotLook
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import compFactory, GetBlockEntityData
from ...Shared.Rules import PotStation as Rules


def selectedSlot(playerId):
    """玩家选中的快捷栏格（0-8）；读不到是 -1。"""
    return compFactory.CreateItem(playerId).GetSelectSlotId()


def addToWindow(kit, window, item, maxStackOf):
    """放进背包窗口：先并入同种未满的栈、再放进空格，都按格号（Inventory.add）；返回放不下的余量或 None。
    kit 是前置包的服务端 Api（用它的 Items，和点击动作用的同一套物品比较）。"""
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


def _give(logic, item):
    """一份菜给玩家：进背包窗口，放不下掉脚下。"""
    rest = addToWindow(logic.kit, logic.ctx.inventory, item, logic.ctx.maxStackOf)
    if rest is not None:
        logic.dropped.append(rest)


def _useContainer(logic, name, fromInventory, selected):
    """用掉一个容器：返回 True 表示用上了；这一份菜该顶替光标栈时 logic 的光标栈已经清空（调用方接着放）。"""
    ctx, items = logic.ctx, logic.kit.Items
    if fromInventory:
        slot = Rules.containerSlot(ctx.inventory, selected, name)
        if slot < 0:
            return False
        ctx.inventory[slot] = items.shrink(ctx.inventory[slot], 1)
        return True
    hand = ctx.getHand()
    if hand is None or hand.get("newItemName") != name:
        return False
    ctx.setHand(items.shrink(hand, 1))
    return True


def scoop(logic, playerId, data):
    """一个 scoop 动作（见模块说明）。返回盛了几份。"""
    ctx, station = logic.ctx, logic.station
    dimensionId, pos = station.dimensionId, station.pos
    blockData = GetBlockEntityData(dimensionId, pos)
    fromInventory, everything = data.get("from_inventory") is True, data.get("all") is True
    if blockData is None or (fromInventory and ctx.getHand() is not None):
        return 0
    selected = selectedSlot(playerId) if fromInventory else -1
    count, first = 0, None
    while True:
        name = PotServe.vesselName(PotContainer.preview(blockData))
        if not name or not _useContainer(logic, name, fromInventory, selected):
            break
        dish = PotServe.takeServing(blockData)
        first, count = first or dish, count + 1
        if not fromInventory and ctx.getHand() is None:
            ctx.setHand(dish)                      # 最后一个容器用完了：盛出来的菜就在手里（Java 的 setCarried）
        else:
            _give(logic, dish)
        if not everything:
            break
    if count:
        PotServe.served(playerId, dimensionId, blockData, first, count)
        station.effect("scooped", {"count": count})
        PotLook.event(dimensionId, pos, "scooped", {"count": count}, skip=station.users)
    return count


def takeBack(logic, playerId):
    """一个 take_back 动作：最后一个沉着的食材格整格退给玩家，一次一格。返回退了没有。"""
    station = logic.station
    before = PotContainer.inputs(station.dimensionId, station.pos)
    for index in range(len(before) - 1, -1, -1):
        if not Rules.isSunk(Rules.keyOf(before[index])):
            continue
        stack = dict(before[index])
        after = list(before)
        after[index] = None
        PotContainer.setInputs(station.dimensionId, station.pos, before, after)
        size = max(1, logic.ctx.maxStackOf(stack))
        while stack["count"] > 0:
            piece = dict(stack)
            piece["count"] = min(size, stack["count"])
            stack["count"] -= piece["count"]
            _give(logic, piece)
        return True
    return False
