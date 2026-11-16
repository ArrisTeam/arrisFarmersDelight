# -*- coding: utf-8 -*-
"""BoardInv - 砧板站点客户端问引擎的几件事：物品类型、是不是刀、选中的快捷栏格、副手（客户端）

从 BoardView.py 拆出来。物品类型和刀的判断要和服务端（Server/Helpers/Items 的 GetItemType / IsKnife）一致：盘装的食物方块当食物，
刀是登记在 knifeList 里的或带 arris:knife 标签的（客户端读不到标签时只认前者）。
选中的快捷栏格在客户端叫 GetSlotId（GetSelectSlotId 只有服务端有），副手用 GetOffhandItem（文档里客户端物品组件的这两个）。
"""
from ...Client.Engine import compFactory, levelId, playerId
from ...Shared.Data.Cutting import knifeList
from ...Shared.Data.Food import platePackagedFoodDict

_types, _tags = {}, {}


def typeOf(item):
    """物品类型（引擎的 itemType；盘装的食物方块当食物，同服务端的 GetItemType）。"""
    name = item["newItemName"]
    if name in platePackagedFoodDict:
        return "food"
    key = (name, int(item.get("newAuxValue") or 0))
    if key not in _types:
        _types[key] = (compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}).get("itemType") or ""
    return _types[key]


def isKnife(name):
    """刀：登记在 knifeList 里的，或带 arris:knife 物品标签的（客户端读不到标签时只认前者）。"""
    if name in knifeList:
        return True
    if name not in _tags:
        reader = getattr(compFactory.CreateItem(levelId), "GetItemTags", None)
        _tags[name] = "arris:knife" in ((reader(name) if reader is not None else None) or [])
    return _tags[name]


def selectedSlot():
    """本人选中的快捷栏格（0-8）；读不到是 -1。"""
    slot = compFactory.CreateItem(playerId).GetSlotId()
    return slot if isinstance(slot, int) else -1


def offhand():
    """副手拿着的物品；没有是 None。"""
    item = compFactory.CreateItem(playerId).GetOffhandItem()
    return item if item and item.get("newItemName") and (item.get("count") or 0) > 0 else None
