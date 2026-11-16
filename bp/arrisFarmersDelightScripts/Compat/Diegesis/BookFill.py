# -*- coding: utf-8 -*-
"""BookFill - 食谱书的"放料"：从背包把一道菜的料放进锅、摆上砧板（服务端）

客户端的书（BookSources.py）发 bookFill {"key", "sets"}，sets 是 1 或 16（HoD：点一下放一份、Shift 点放一批）。
键、份数都只当请求看：配方按键在服务端重新查，料从服务端读到的背包里拿。
- 锅（fillPot，HoD 的 StationRecipes.fill）：背包里凑得出份数最多的写法，整份整份地放（最多 sets 份，装不进格子的那一份不放）；
  锅里有这种写法用不上的料时不放；放进去的料按这道菜摆开，书里点的这道成了锅的选择（wanted）；料从站点的背包窗口里扣
  （和点击动作同一份事务），创造模式照扣（HoD 不分）；放进去了返回 True；
- 砧板（fillDish）：摆盘的菜一层层摆上去（底座在前），每层 sets 件，摆完就做成（HoD：书里点的菜，层一凑齐就做这道，不等加料）；
  板上有别的东西时不摆。创造模式不扣背包（与放料抽屉一致）。返回提示键（不放时）或 None。
"""
from . import DishBoard
from ...Server.Helpers import BoardDish as Store
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import compFactory, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import IsCreative
from ...Shared.Rules import DishStation
from ...Shared.Rules import PotLayout
from ...Shared.Rules import StationBooks as Books

INVENTORY_SLOTS = 36


def setsOf(value):
    """客户端给的份数夹到 1..16。"""
    return max(1, min(DishStation.BATCH, int(value))) if isinstance(value, int) and not isinstance(value, bool) else 1


def _inventory(playerId):
    items = compFactory.CreateItem(playerId).GetPlayerAllItems(ItemPosType.INVENTORY, True) or []
    return [(slot, item) for slot, item in enumerate(items[:INVENTORY_SLOTS]) if item and item.get("count", 0) > 0]


def _pool(inventory):
    pool = {}
    for _slot, item in inventory:
        kind = (item["newItemName"], item.get("newAuxValue") or 0)
        pool[kind] = pool.get(kind, 0) + item["count"]
    return pool


def _take(playerId, inventory, kind, count):
    """从背包的若干格里凑 count 件 kind 扣掉（创造模式不扣）；返回扣掉的件数。"""
    taken, changes = 0, {}
    for slot, item in inventory:
        if taken >= count or (item["newItemName"], item.get("newAuxValue") or 0) != kind or item["count"] <= 0:
            continue
        moved = min(item["count"], count - taken)
        item["count"] -= moved
        taken += moved
        changes[(ItemPosType.INVENTORY, slot)] = dict(item) if item["count"] > 0 else None
    if changes and not IsCreative(playerId):
        compFactory.CreateItem(playerId).SetPlayerAllItems(changes)
    return taken


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
    plan = PotLayout.planFill(recipe.get("Recipe") or (), held, _windowPool(window), setsOf(sets), maxStackOf)
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
    ToAllPlayerPlaySound(station.dimensionId, station.pos, "random.splash")
    return True


def fillDish(logic, playerId, key, sets, blockEntityData):
    variants = Books.dishOf(key)
    if not variants:
        return "no_recipe"
    if blockEntityData is None or Store.hasAny(blockEntityData) or logic._boardItem(blockEntityData):
        return "board_busy"
    inventory = _inventory(playerId)
    kinds = Books.bestKinds([[slot[0] for slot in Books.dishWay(dish)] for dish in variants], _pool(inventory))
    if kinds is None:
        return "missing"
    dish = DishStation.completed(kinds)
    keeps = dish["keeps"] if dish is not None else ()        # 原样留下的配料（面团的水桶）：放一件就够做全部的份数
    count = Books.setsOf([kind for kind in kinds if kind[0] not in keeps], _pool(inventory), setsOf(sets))
    layers = []
    for kind in kinds:
        amount = 1 if kind[0] in keeps else count
        layers.append(Store.stack({"newItemName": kind[0], "newAuxValue": kind[1]}, _take(playerId, inventory, kind, amount)))
    station = logic.station
    Store.save(station.dimensionId, station.pos, blockEntityData, layers)
    ToAllPlayerPlaySound(station.dimensionId, station.pos, "dig.wood")
    if dish is not None:
        DishBoard.finish(logic, playerId, blockEntityData, layers)
    return None
