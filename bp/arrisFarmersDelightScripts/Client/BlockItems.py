# -*- coding: utf-8 -*-
"""BlockItems - 砧板 / 煎锅 / 炉灶上的物品：用客户端掉落物渲染（客户端）

取代旧版的 arris:item_display 服务端实体，做法同机械动力的置物台：服务端在方块上的东西变了时广播
（Server/Helpers/BlockItems.py -> 本模块的 OnBlockItems），方块实体在本端加载时按方块实体数据自己补一次；
摆法在 Shared/Rules/BlockDisplay.py，姿态换算在 Shared/Rules/ItemPose.py。掉落物是纯客户端渲染，每个客户端各画各的。
加载事件可能重复触发、服务端 SetBlockNew 放的方块客户端不发加载事件（机械动力的实机记录）：渲染一律先清后画（幂等），
内容一律以广播为准。站点自己画某个方块上的东西时（煎锅站点要让食物翻面）用 hide 让本端先不画，还原时按最后一份内容重画。
"""
from ..QuModLibs.Client import AllowCall, Listen
from .Engine import compFactory, levelId, unwrapDeep, blockEntityExData
from ..Shared.Data.Cooking import StoveList
from ..Shared.Rules import BlockDisplay, ItemPose

BOARD_BLOCKS = ("arris:cutting_board",)
SKILLET_BLOCKS = ("arris:skillet",)
_shown = {}        # (维度, 坐标) -> [掉落物 id]
_last = {}         # (维度, 坐标) -> (kind, items)：最后一份内容
_hidden = set()    # 站点在画、本端不画的方块
_itemTypes = {}    # (名字, aux) -> 物品类型


def kindOf(blockName):
    if blockName in BOARD_BLOCKS:
        return BlockDisplay.KIND_BOARD
    if blockName in SKILLET_BLOCKS:
        return BlockDisplay.KIND_SKILLET
    if blockName in StoveList:
        return BlockDisplay.KIND_STOVE
    return None


def _currentDimension():
    return compFactory.CreateGame(levelId).GetCurrentDimension()


def _itemType(item):
    key = (item.get("newItemName"), item.get("newAuxValue") or 0)
    if key not in _itemTypes:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}
        _itemTypes[key] = info.get("itemType") or ""
    return _itemTypes[key]


def clear(dimensionId, pos):
    itemComp = compFactory.CreateItem(levelId)
    for entityId in _shown.pop((dimensionId, tuple(pos)), ()):
        itemComp.DeleteClientDropItemEntity(entityId)


def clearAll():
    for key in list(_shown):
        clear(key[0], key[1])
    _last.clear()


def hide(dimensionId, pos, hidden):
    """hidden=True：本端不画这个方块上的东西（内容照常记着）；False：按最后一份内容重画。"""
    key = (dimensionId, (int(pos[0]), int(pos[1]), int(pos[2])))
    if hidden:
        _hidden.add(key)
        clear(key[0], key[1])
    elif key in _hidden:
        _hidden.discard(key)
        if key in _last:
            show(key[0], key[1], _last[key][0], _last[key][1])


def show(dimensionId, pos, kind, items):
    """按摆法画出这个方块上的物品（先清掉旧的）。"""
    pos = (int(pos[0]), int(pos[1]), int(pos[2]))
    clear(dimensionId, pos)
    _last[(dimensionId, pos)] = (kind, items)
    if dimensionId != _currentDimension() or (dimensionId, pos) in _hidden:
        return
    itemComp = compFactory.CreateItem(levelId)
    shown = []
    for placement in BlockDisplay.layout(kind, items, _itemType, pos):
        center = (pos[0] + placement.center[0], pos[1] + placement.center[1], pos[2] + placement.center[2])
        if placement.flat:
            matrix = ItemPose.flatMatrix(placement.direction[0], placement.direction[1])
        else:
            matrix = ItemPose.uprightMatrix(placement.direction[0], placement.direction[1], placement.roll)
        pivot = ItemPose.pivotFor(center, matrix, placement.scale)
        entityId = itemComp.AddDropItemToWorld(placement.item, dimensionId, pivot, 0, 0)
        if entityId:
            itemComp.SetDropItemTransform(entityId, pivot, ItemPose.engineEuler(matrix), float(placement.scale))
            shown.append(entityId)
    if shown:
        _shown[(dimensionId, pos)] = shown


def _itemsFromExData(kind, exData):
    if kind == BlockDisplay.KIND_BOARD:
        return {"0": unwrapDeep(exData.get("cuttingDict"))}
    if kind == BlockDisplay.KIND_SKILLET:
        return {"0": unwrapDeep(exData.get("cookingDict"))}
    items = {}
    for index in range(len(BlockDisplay.STOVE_SLOTS)):
        slot = unwrapDeep(exData.get(str(index)))
        items[str(index)] = slot.get("itemDict") if isinstance(slot, dict) else None
    return items


@Listen("ModBlockEntityLoadedClientEvent")
def OnBlockEntityLoaded(args):
    kind = kindOf(args["blockName"])
    if kind is None:
        return
    pos = (args["posX"], args["posY"], args["posZ"])
    show(args["dimensionId"], pos, kind, _itemsFromExData(kind, blockEntityExData(pos)))


@Listen("ModBlockEntityRemoveClientEvent")
def OnBlockEntityRemoved(args):
    pos = (args["posX"], args["posY"], args["posZ"])
    clear(args["dimensionId"], pos)
    _last.pop((args["dimensionId"], pos), None)


@Listen("DimensionChangeClientEvent")
def OnDimensionChange(args=None):
    clearAll()


@AllowCall
def OnBlockItems(payload):
    # 服务端广播给全体客户端：别的维度的不画（show 里按当前维度过滤）
    if isinstance(payload, dict) and payload.get("kind") and isinstance(payload.get("items"), dict):
        show(payload["dimensionId"], payload["pos"], payload["kind"], payload["items"])
