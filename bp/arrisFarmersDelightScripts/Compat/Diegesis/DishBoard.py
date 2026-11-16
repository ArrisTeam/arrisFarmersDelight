# -*- coding: utf-8 -*-
"""DishBoard - 砧板站点的摆盘：放底座、一层层往上放、凑成菜、拿走（服务端）

对应 Hands-On Delight 的 assembly（BoardDishes / Assembling）；规则在 Shared/Rules/DishStation.py，存档在
Server/Helpers/BoardDish.py。BoardLogic 把摆盘相关的动作交给这里：
    lay   快捷栏第 slot 格放上砧板：空板时能切的照切菜放（一叠最多 16 个），能打底的开始摆盘；摆盘中放成下一层
    click 点砧板：做好了就拿走；凑成了菜（还能接着加料的那种）就做成；没凑成就全拿回来
一层是一叠，做一份每层用一件：底座最多 16 个，之后的层最多拿底座那么多（多拿也做不了更多份；两个煎蛋的三明治
第二层还要留蛋）；做成时多出来的料、空容器（桶、玻璃瓶、碗）还给厨师。
"""
import copy

from ...Server.Helpers import BoardDish as Store
from ...Server.Helpers.BlockItems import PublishBoard
from ...Server.Helpers.Engine import compFactory, levelId, ItemPosType
from ...Server.Helpers.Fx import ToAllPlayerPlaySound
from ...Server.Helpers.Player import GiveOrDropItem, IsCreative
from ...Shared.Data.Cutting import CuttingBoardDict
from ...Shared.Rules import CuttingStation
from ...Shared.Rules import DishStation as Rules

HOTBAR = 9


def kindOf(item):
    return (item["newItemName"], item.get("newAuxValue") or 0) if item and item.get("newItemName") else None


def _wire(item):
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def _keys(layers):
    return [kindOf(layer) for layer in layers]


def give(playerId, dimensionId, item):
    """按最大堆叠拆开给（饼干一份 8 个，16 份就超过一叠）。"""
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(item["newItemName"], item.get("newAuxValue") or 0) or {}
    size, left = max(1, info.get("maxStackSize") or 64), int(item["count"])
    while left > 0:
        GiveOrDropItem(playerId, Store.stack(item, min(size, left)), dimensionId)
        left -= min(size, left)


def drawerItems(playerId, blockEntityData, cutting):
    """快捷栏里现在能放上砧板的：空板 = 能切的或能打底的；摆盘中 = 能当下一层的；切菜中、做好了 = 没有。"""
    layers = Store.layersOf(blockEntityData)
    if cutting or Store.dishOf(blockEntityData):
        return [{}] * HOTBAR
    keys, items = _keys(layers), []
    itemComp = compFactory.CreateItem(playerId)
    for slot in range(HOTBAR):
        item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
        kind = kindOf(item)
        fits = kind is not None and ((not keys and (kind in CuttingBoardDict or Rules.isBase(kind)))
                                     or (keys and Rules.fitsNext(keys, kind)))
        items.append(_wire(item) if fits else {})
    return items


def lay(logic, playerId, slot, blockEntityData):
    """快捷栏第 slot 格放上砧板。返回提示键（不收时）或 None。"""
    station = logic.station
    itemComp = compFactory.CreateItem(playerId)
    item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
    kind, layers = kindOf(item), Store.layersOf(blockEntityData)
    if kind is None or Store.dishOf(blockEntityData) or logic._boardItem(blockEntityData):
        return "only_food"
    if not layers and kind in CuttingBoardDict:
        board = Store.stack(item, min(item["count"], CuttingStation.BOARD_LIMIT))
        moved = board["count"]
        blockEntityData["cuttingDict"] = board
        PublishBoard(station.dimensionId, station.pos, board)
        logic._restart(board)
    elif (not layers and Rules.isBase(kind)) or (layers and Rules.fitsNext(_keys(layers), kind)):
        moved = min(item["count"], layers[0]["count"] if layers else Rules.BATCH)
        layers.append(Store.stack(item, moved))
        Store.save(station.dimensionId, station.pos, blockEntityData, layers)
    else:
        return "no_layer" if layers else "only_food"
    if not IsCreative(playerId):
        left = copy.deepcopy(item)
        left["count"] -= moved
        itemComp.SetPlayerAllItems({(ItemPosType.INVENTORY, slot): left if left["count"] > 0 else None})
    ToAllPlayerPlaySound(station.dimensionId, station.pos, "dig.wood")
    if layers and Rules.autoFinishes(_keys(layers)):
        finish(logic, playerId, blockEntityData, layers)
    return None


def click(logic, playerId, blockEntityData):
    """点砧板（板上有摆盘的东西时）。返回 False 表示板上没有摆盘的东西。"""
    station = logic.station
    dish = Store.dishOf(blockEntityData)
    if dish:
        give(playerId, station.dimensionId, dish)
        Store.save(station.dimensionId, station.pos, blockEntityData, None)
        ToAllPlayerPlaySound(station.dimensionId, station.pos, "armor.equip_leather")
        return True
    layers = Store.layersOf(blockEntityData)
    if not layers:
        return False
    if Rules.completed(_keys(layers)) is not None:
        finish(logic, playerId, blockEntityData, layers)
    else:
        Store.giveBack(playerId, station.dimensionId, station.pos, blockEntityData)
    return True


def finish(logic, playerId, blockEntityData, layers):
    """凑成了：做几份 = 最薄的一层（最多 16）；多出来的料、空容器还给厨师，成品留在板上等人拿。"""
    station = logic.station
    dish = Rules.completed(_keys(layers))
    made = Rules.rounds([layer["count"] for layer in layers])
    for layer in layers:
        if layer["count"] > made:
            give(playerId, station.dimensionId, Store.stack(layer, layer["count"] - made))
    if dish.get("extras"):                   # 有序配方结果数组里退还的容器（桶、玻璃瓶、碗），一份退一套
        for name, aux, count in dish["extras"]:
            give(playerId, station.dimensionId, {"newItemName": name, "newAuxValue": aux, "count": count * made})
    else:
        container = Rules.containerOf(dish["result"][0])
        if container:
            give(playerId, station.dimensionId, {"newItemName": container["itemName"],
                                                 "newAuxValue": container.get("auxValue", 0), "count": made})
    result = {"newItemName": dish["result"][0], "newAuxValue": dish["result"][1], "count": made * dish["count"]}
    Store.save(station.dimensionId, station.pos, blockEntityData, None, result)
    ToAllPlayerPlaySound(station.dimensionId, station.pos, "random.pop")
    station.effect("plated", {"item": _wire(result)})


def fields(blockEntityData):
    """站点数据里摆盘的部分：layers、dish、ready（凑成了但还能接着加料时的成品名）、readyName（它的显示名）。"""
    layers, dish = Store.layersOf(blockEntityData), Store.dishOf(blockEntityData)
    done = Rules.completed(_keys(layers)) if layers else None
    ready = done["result"][0] if done is not None else ""
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(done["result"][0], done["result"][1]) if done else None
    return {"layers": [_wire(layer) for layer in layers], "dish": _wire(dish) if dish else {}, "ready": ready,
            "readyName": (info or {}).get("itemName") or ""}
