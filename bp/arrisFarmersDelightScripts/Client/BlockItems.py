# -*- coding: utf-8 -*-
"""BlockItems - 砧板 / 煎锅 / 炉灶上的物品：用客户端掉落物渲染（客户端）

取代旧版的 arris:item_display 服务端实体，做法同机械动力的置物台：服务端在方块上的东西变了时广播
（Server/Helpers/BlockItems.py -> 本模块的 OnBlockItems），方块实体在本端加载时按方块实体数据自己补一次；
摆法在 Shared/Rules/BlockDisplay.py，姿态换算在 Shared/Rules/ItemPose.py。掉落物是纯客户端渲染，每个客户端各画各的。
加载事件可能重复触发、服务端 SetBlockNew 放的方块客户端不发加载事件（机械动力的实机记录）：渲染一律先清后画（幂等），
内容一律以广播为准。站点自己画某个方块上的东西时（煎锅站点要让食物翻面）用 hide 让本端先不画，还原时按最后一份内容重画。
"""
from ..QuModLibs.Client import AllowCall, Listen
from .Engine import addDropItem, compFactory, levelId, unwrapDeep, blockEntityExData
from ..Shared.Data.Cutting import knifeList
from ..Shared.Rules import BlockDisplay, BoardStation, GrillBlocks, ItemPose, PotModelMath, StoveFacing
from ..Shared.Rules.HandsOn import BoardScene

BOARD_BLOCKS = ("arris:cutting_board",)
SKILLET_BLOCKS = ("arris:skillet",)
KNIFE_TAG = "arris:knife"
_shown = {}        # (维度, 坐标) -> [掉落物 id]
_last = {}         # (维度, 坐标) -> (kind, items)：最后一份内容
_hidden = set()    # 站点在画、本端不画的方块
_itemInfo = {}     # (名字, aux) -> (物品类型, 一叠最多几个)
_knifeTags = {}    # 物品名 -> 带不带 arris:knife 标签


def kindOf(blockName):
    if blockName in BOARD_BLOCKS:
        return BlockDisplay.KIND_BOARD
    if blockName in SKILLET_BLOCKS:
        return BlockDisplay.KIND_SKILLET
    if GrillBlocks.isGrill(blockName):          # 点着的（StoveList）和熄着的炉灶：烤架上的东西摆法一样（JE 的渲染器不看 LIT）
        return BlockDisplay.KIND_STOVE
    return None


def _currentDimension():
    return compFactory.CreateGame(levelId).GetCurrentDimension()


def _info(item):
    key = (item.get("newItemName"), item.get("newAuxValue") or 0)
    if key not in _itemInfo:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}
        _itemInfo[key] = (info.get("itemType") or "", info.get("maxStackSize") or 64)
    return _itemInfo[key]


def _itemType(item):
    return _info(item)[0]


def _maxStack(item):
    return _info(item)[1]


def isKnife(name):
    """刀：登记在 knifeList 里的，或带 arris:knife 物品标签的（客户端读不到标签时只认前者）。砧板站点（Compat/Diegesis/BoardView）问的也是它：
    插着的刀站点里画成什么、没开站时画成什么，用的是同一个答案（BoardStation.Env.isCarving）。"""
    if name in knifeList:
        return True
    if name not in _knifeTags:
        reader = getattr(compFactory.CreateItem(levelId), "GetItemTags", None)
        _knifeTags[name] = KNIFE_TAG in ((reader(name) if reader is not None else None) or [])
    return _knifeTags[name]


_boardEnv = BoardStation.Env(isKnife, _itemType)      # 板上的东西是不是插着的工具：站点里的画面（BoardView 的 Env）问的是同一件事


def _boardOffset(pos):
    """板底座中间离方块中心的量（方块分数）：FD 的板底座 x 1..12、柄在旁边，中心在方块自己坐标的 (6.5, 8)，随方块朝向转。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(pos)
    dx, dz = PotModelMath.localToWorld(PotModelMath.facingOf(block[1] if block else 0), BoardScene.BASE_X - 8.0, BoardScene.BASE_Z - 8.0)
    return (dx / 16.0, dz / 16.0)


def _facingYaw(pos):
    """方块的朝向（度）：炉灶的烤位和每件的转角（FD 的 DefaultStoveRenderer 按 FACING 转）、砧板和煎锅上的食物（FD 的 CuttingBoardRenderer / SkilletRenderer 按 FACING 转）、
    砧板上插着的工具（renderItemCarved 按 FACING 转）都跟着方块转；方块读不到按 aux 0。"""
    block = compFactory.CreateBlockInfo(levelId).GetBlock(pos)
    return StoveFacing.yawOfAux(block[1] if block else 0)


def itemsAt(dimensionId, pos):
    """这个方块上最后一份内容的 {"槽": 物品}，没有记录是 {}（别的客户端模块只想知道上面有什么，比如点着的炉灶上哪几格有东西、冒不冒烟）。"""
    last = _last.get((dimensionId, (int(pos[0]), int(pos[1]), int(pos[2]))))
    return last[1] if last else {}


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


def release(dimensionId, pos):
    """这个方块没了（场景收掉、拆了）：忘掉它最后一份内容和"本端不画"的标记，以后别的东西放在这个位置不会被误当成还在隐藏。"""
    key = (dimensionId, (int(pos[0]), int(pos[1]), int(pos[2])))
    clear(key[0], key[1])
    _last.pop(key, None)
    _hidden.discard(key)


def _layoutOf(kind, items, pos):
    """这个方块上的东西怎么摆（Shared/Rules/BlockDisplay.layout）：三种方块都要朝向和一叠最多几个，砧板还要站点里板底座的偏移和"是不是插着的工具""画成方块还是平躺的图标"。"""
    offset = _boardOffset(pos) if kind == BlockDisplay.KIND_BOARD else (0.0, 0.0)
    flag = items.get(BoardStation.CARVED)             # 板上那件是不是插着的（服务端的 IsItemCarved 标记；没有 = 老存档，照老办法推断）
    return BlockDisplay.layout(kind, items, _itemType, pos, offset, _facingYaw(pos), lambda item: _boardEnv.isCarving(item, flag), _boardEnv.isBlock,
                               _maxStack)


def show(dimensionId, pos, kind, items):
    """按摆法画出这个方块上的物品（先清掉旧的）。"""
    pos = (int(pos[0]), int(pos[1]), int(pos[2]))
    clear(dimensionId, pos)
    _last[(dimensionId, pos)] = (kind, items)
    if dimensionId != _currentDimension() or (dimensionId, pos) in _hidden:
        return
    itemComp = compFactory.CreateItem(levelId)
    shown = []
    for placement in _layoutOf(kind, items, pos):
        center = (pos[0] + placement.center[0], pos[1] + placement.center[1], pos[2] + placement.center[2])
        if placement.flat:
            matrix = ItemPose.flatMatrix(placement.direction[0], placement.direction[1])
        else:
            matrix = ItemPose.uprightMatrix(placement.direction[0], placement.direction[1], placement.roll)
        pivot = ItemPose.pivotFor(center, matrix, placement.scale)
        entityId = addDropItem(placement.item, dimensionId, pivot)
        if entityId:
            itemComp.SetDropItemTransform(entityId, pivot, ItemPose.engineEuler(matrix), float(placement.scale))
            shown.append(entityId)
    if shown:
        _shown[(dimensionId, pos)] = shown


def _itemsFromExData(kind, exData):
    if kind == BlockDisplay.KIND_BOARD:
        items = {"0": unwrapDeep(exData.get("cuttingDict")), BlockDisplay.DISH_KEY: unwrapDeep(exData.get("dishDone"))}
        carved = unwrapDeep(exData.get(BoardStation.CARVED_DATA))
        if carved is not None:
            items[BoardStation.CARVED] = bool(carved)
        layers = unwrapDeep(exData.get("dishLayers"))
        for index, layer in enumerate(layers if isinstance(layers, list) else []):
            items[BlockDisplay.layerKey(index)] = layer
        return items
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
        items = payload["items"]
        if payload.get("carved") is not None:
            items[BoardStation.CARVED] = bool(payload["carved"])       # 砧板：板上那件是不是插着的（服务端的 IsItemCarved 标记）
        show(payload["dimensionId"], payload["pos"], payload["kind"], items)
