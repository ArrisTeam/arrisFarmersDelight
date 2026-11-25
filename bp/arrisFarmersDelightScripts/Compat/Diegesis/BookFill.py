# -*- coding: utf-8 -*-
"""BookFill - 食谱书的"放料"：从背包把一道菜的料放进锅（服务端）

客户端的书（BookSources.py）发 bookFill {"key", "sets"}，sets 是 1 或 16（HoD：点一下放一份、Shift 点放一批）。
键、份数都只当请求看：配方按键在服务端重新查，料从服务端读到的背包里拿。
- 锅（fillPot，HoD 的 StationRecipes.fill）：背包里凑得出份数最多的写法，整份整份地放（最多 sets 份，装不进格子的那一份不放）；
  锅里有这种写法用不上的料时不放；放进去的料按这道菜摆开，书里点的这道成了锅的选择（wanted）；料从站点的背包窗口里扣
  （和点击动作同一份事务），创造模式照扣（HoD 不分）；放进去了返回 True。不放声音：HoD 的 fill 没有，料落水的声音由各客户端的到达动画放。
砧板摆盘的书（HoD 的 pick / fill）在 BoardAssemble.fill。
"""
from ...Server.Helpers import PotContainer
from ...Shared.Rules import DishStation
from ...Shared.Rules import PotLayout
from ...Shared.Rules import StationBooks as Books


def setsOf(value):
    """客户端给的份数夹到 1..16。"""
    return max(1, min(DishStation.BATCH, int(value))) if isinstance(value, int) and not isinstance(value, bool) else 1


def _windowPool(window):
    """背包窗口里每种料有几件：{(物品名, aux): 件数}。"""
    pool = {}
    for item in window:
        if item and item.get("count", 0) > 0:
            kind = (item["newItemName"], item.get("newAuxValue") or 0)
            pool[kind] = pool.get(kind, 0) + item["count"]
    return pool


def _takeFromWindow(window, kind, amount):
    """从背包窗口按格号扣 amount 件 kind；返回扣了几件。"""
    taken = 0
    for index in range(len(window)):
        item = window[index]
        if taken >= amount:
            break
        if item is None or (item["newItemName"], item.get("newAuxValue") or 0) != kind:
            continue
        used = min(item["count"], amount - taken)
        window[index] = dict(item, count=item["count"] - used) if item["count"] > used else None
        taken += used
    return taken


def fillPot(logic, playerId, key, sets, maxStackOf):
    recipe = Books.potRecipe(key)
    if recipe is None:
        return False
    station, window = logic.station, logic.ctx.inventory
    before = PotContainer.inputs(station.dimensionId, station.pos)
    held = dict(PotLayout.kindsOf(before))
    plan = PotLayout.planFillFor(recipe, held, _windowPool(window), setsOf(sets), maxStackOf)
    if plan is None:
        return False
    each, count = plan
    totals = dict(held)
    for kind in sorted(each):
        _takeFromWindow(window, kind, each[kind] * count)
        totals[kind] = totals.get(kind, 0) + each[kind] * count
    kinds = [(kind, totals[kind]) for kind in [kind for kind, _total in PotLayout.kindsOf(before)] + sorted(set(each) - set(held))]
    cells, rest = PotLayout.lay(PotLayout.cellsOf(before), kinds, each, maxStackOf)
    PotContainer.setInputs(station.dimensionId, station.pos, before, cells)
    logic.dropped.extend(rest)
    logic.wanted = key
    logic.hand.clock.feedByHand()
    return True
