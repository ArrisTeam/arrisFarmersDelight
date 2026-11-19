# -*- coding: utf-8 -*-
"""BlockItems - 砧板 / 煎锅 / 炉灶上展示的物品：广播给客户端各自渲染，清理旧版展示实体（服务端）

取代旧版的 arris:item_display 服务端实体（见 Shared/Rules/BlockDisplay.py）：方块上的东西变了就 Call("*") 广播一次，
客户端按维度过滤、用客户端掉落物画（Client/BlockItems.py）；区块重新加载或玩家刚进服时，客户端按方块实体数据自己补一次。
旧存档里方块实体数据记着的展示实体（displayEntityId / displayEntityList / displayEntityDict）用 DropLegacyDisplays 删掉；
世界里残留的 arris:item_display 加载时由 Server/DisplayGuard.py 删掉。
"""
from .Engine import Call, DestroyEntity
from ...Shared.Rules.BlockDisplay import DISH_KEY, KIND_BOARD, KIND_SKILLET, KIND_STOVE, STOVE_SLOTS, layerKey

ENDPOINT = "OnBlockItems"
_record = {"payloads": None}   # 自检时打开：记下发出的载荷


def _wire(item):
    if not item or (item.get("count") or 0) <= 0 or not item.get("newItemName"):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue", 0) or 0, "count": item["count"]}


def Publish(dimensionId, blockPos, kind, items, carved=None):
    """items：{"槽": 物品或 None}。carved（只有砧板用）：板上那件是不是插着的（True / False；None 不带：客户端照老办法推断）。"""
    payload = {"dimensionId": dimensionId, "pos": [int(blockPos[0]), int(blockPos[1]), int(blockPos[2])], "kind": kind,
               "items": dict((str(slot), _wire(item)) for slot, item in items.items())}
    if carved is not None:
        payload["carved"] = bool(carved)
    if _record["payloads"] is not None:
        _record["payloads"].append(payload)
    Call("*", ENDPOINT, payload)


def PublishBoard(dimensionId, blockPos, item, carved=None):
    Publish(dimensionId, blockPos, KIND_BOARD, {"0": item}, carved if item else None)


def PublishBoardDish(dimensionId, blockPos, layers, dish):
    """砧板摆盘：层（底座在前）和做好的那叠；都没有就是清空。"""
    items = {"0": None, DISH_KEY: dish}
    for index, layer in enumerate(layers or []):
        items[layerKey(index)] = layer
    Publish(dimensionId, blockPos, KIND_BOARD, items)


def PublishSkillet(dimensionId, blockPos, item):
    Publish(dimensionId, blockPos, KIND_SKILLET, {"0": item})


def PublishStove(dimensionId, blockPos, blockEntityData):
    items = {}
    for index in range(len(STOVE_SLOTS)):
        slot = blockEntityData[str(index)]
        items[str(index)] = slot.get("itemDict") if slot else None
    Publish(dimensionId, blockPos, KIND_STOVE, items)


def DropLegacyDisplays(blockEntityData):
    """旧版记在方块实体数据里的展示实体：删掉实体、清掉键（只做一次，之后这些键都是 None）。"""
    entityId = blockEntityData["displayEntityId"]
    if entityId:
        DestroyEntity(entityId)
        blockEntityData["displayEntityId"] = None
    entityList = blockEntityData["displayEntityList"]
    if entityList:
        for entityId in entityList:
            DestroyEntity(entityId)
        blockEntityData["displayEntityList"] = None
    entityDict = blockEntityData["displayEntityDict"]
    if entityDict:
        for entityId in entityDict.values():
            if entityId:
                DestroyEntity(entityId)
        blockEntityData["displayEntityDict"] = None


def startRecording():
    """测试用：开始记录广播。"""
    _record["payloads"] = []


def stopRecording():
    """测试用：停止记录，返回记下的载荷。"""
    payloads, _record["payloads"] = _record["payloads"] or [], None
    return payloads
