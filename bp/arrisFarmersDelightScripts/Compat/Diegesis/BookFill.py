# -*- coding: utf-8 -*-
"""BookFill - 食谱书的"放料"：从背包把一道菜的料放进锅、摆上砧板（服务端）

客户端的书（BookSources.py）发 bookFill {"key", "sets"}，sets 是 1 或 16（HoD：点一下放一份、Shift 点放一批）。
键、份数都只当请求看：配方按键在服务端重新查，料从服务端读到的背包里拿。
- 锅：背包里凑得出份数最多的写法，凑几份放几份（最多 sets 份）；锅里有这道菜用不上的料时不放；放不下的退回背包；
- 砧板：摆盘的菜一层层摆上去（底座在前），每层 sets 件，摆完就做成（HoD：书里点的菜，层一凑齐就做这道，不等加料）；
  板上有别的东西时不摆。
创造模式不扣背包（与放料抽屉一致）。返回提示键（不放时）或 None。
"""
from . import DishBoard
from ...Server.Helpers import BoardDish as Store
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import compFactory, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Shared.Rules import DishStation
from ...Shared.Rules import PotStation
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


def fillPot(logic, playerId, key, sets, maxStackOf):
    recipe = Books.potRecipe(key)
    if recipe is None:
        return "no_recipe"
    station = logic.station
    inventory = _inventory(playerId)
    kinds = Books.bestKinds(recipe.get("Recipe") or (), _pool(inventory))
    if kinds is None:
        return "missing"
    before = PotContainer.inputs(station.dimensionId, station.pos)
    if any(PotStation.keyOf(item) not in kinds for item in before if PotStation.keyOf(item)):
        return "pot_busy"
    count = Books.setsOf(kinds, _pool(inventory), setsOf(sets))
    cells, placedAny = before, False
    for kind, each in sorted(Books.needOf(kinds).items()):
        cells, placed = PotStation.placeStack(cells, Books.stack(kind[0], kind[1], each * count), maxStackOf(kind))
        if placed > 0:
            placedAny = True
            _take(playerId, inventory, kind, placed)
    if not placedAny:
        return "full"
    cells, rest = PotStation.layout(cells, maxStackOf) or (cells, [])
    PotContainer.setInputs(station.dimensionId, station.pos, before, cells)
    for stack in rest:
        GiveOrDropItem(playerId, stack, station.dimensionId)
    logic.hand.clock.feedByHand()
    ToAllPlayerPlaySound(station.dimensionId, station.pos, "random.splash")
    return None


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
    count = Books.setsOf(kinds, _pool(inventory), setsOf(sets))
    layers = []
    for kind in kinds:
        layers.append(Store.stack({"newItemName": kind[0], "newAuxValue": kind[1]}, _take(playerId, inventory, kind, count)))
    station = logic.station
    Store.save(station.dimensionId, station.pos, blockEntityData, layers)
    ToAllPlayerPlaySound(station.dimensionId, station.pos, "dig.wood")
    if DishStation.completed(kinds) is not None:
        DishBoard.finish(logic, playerId, blockEntityData, layers)
    return None
