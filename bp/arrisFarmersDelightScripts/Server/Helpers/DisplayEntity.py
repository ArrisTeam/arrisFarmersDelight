# -*- coding: utf-8 -*-
"""DisplayEntity - 砧板 / 煎锅 / 炉灶上展示物品用的 arris:item_display 实体（服务端）

展示实体免伤害 / 免传送 / 免药水效果的守卫在 Server/DisplayGuard.py，不要删。
实体的 variant 决定展示姿态：0 = 食物（平放）、1 = 方块、2 = 其它（工具等）。
"""
import copy
import random

from .Engine import compFactory, System, ItemPosType
from .Items import GetItemType
from .Placement import FacingOfAux
from ...Shared.Data.Cutting import CuttingBoardDict
from ...Shared.Rules.Placement import ENTITY_FACE

DISPLAY_ENTITY = "arris:item_display"

# 炉灶 6 个烤位相对方块角的 (x, z)
STOVE_SLOT_OFFSETS = [(0.25, 0.27), (0.5, 0.27), (0.75, 0.27), (0.25, 0.73), (0.5, 0.73), (0.75, 0.73)]


def _variantOf(itemDict):
    if not itemDict:
        return 0
    itemType = GetItemType(itemDict)
    entry = CuttingBoardDict.get((itemDict["newItemName"], itemDict["newAuxValue"]))
    if entry is not None and entry.get("type") is not None:
        itemType = entry["type"]
    if not itemType or itemType == "food":
        return 0
    if itemType == "block":
        return 1
    return 2


GetDisplayEntityCarriedItemType = _variantOf


def _spawn(itemDict, pos, facing, dimensionId):
    entityId = System.CreateEngineEntityByTypeStr(DISPLAY_ENTITY, pos, ENTITY_FACE[facing], dimensionId)
    compFactory.CreateItem(entityId).SetEntityItem(ItemPosType.CARRIED, itemDict, 0)
    compFactory.CreateEntityDefinitions(entityId).SetVariant(int(_variantOf(itemDict)))
    return entityId


def StoveDisplayEntity(itemDict, playerId, data):
    """在炉灶 cookingIndex 那个烤位上放一个小号展示实体，并记下该烤位的数据。"""
    itemDict["count"] = 1
    blockEntityData = data["blockEntityData"]
    x, y, z = data["blockPos"]
    if blockEntityData["cookingIndex"] >= len(STOVE_SLOT_OFFSETS):
        blockEntityData["cookingIndex"] = 0
    cookingIndex = blockEntityData["cookingIndex"]
    dx, dz = STOVE_SLOT_OFFSETS[cookingIndex]
    entityId = System.CreateEngineEntityByTypeStr(DISPLAY_ENTITY, (x + dx, y + 0.953, z + dz),
                                                  ENTITY_FACE[FacingOfAux(data["blockAuxValue"])], data["dimensionId"])
    compFactory.CreateEntityEvent(entityId).TriggerCustomEvent(entityId, "arris:set_small")
    displayEntityDict = blockEntityData["displayEntityDict"]
    displayEntityDict[str(cookingIndex)] = entityId
    blockEntityData["displayEntityDict"] = displayEntityDict
    blockEntityData[str(cookingIndex)] = {"itemDict": itemDict, "cookTimer": 7}
    compFactory.CreateItem(entityId).SetEntityItem(ItemPosType.CARRIED, itemDict, 0)
    compFactory.CreateEntityDefinitions(entityId).SetVariant(int(_variantOf(itemDict)))


def SkilletDisplayCount(count):
    """煎锅上叠放的展示实体个数：1 个物品 1 层，2-16 两层，之后每 16 个加一层，最多 5 层。"""
    if count <= 0:
        return 0
    if count == 1:
        return 1
    return min(5, 2 + (count - 1) // 16)


def SkilletDisplayEntity(itemDict, playerId, data):
    """按数量在煎锅里叠放若干展示实体（每层稍微错开），实体 id 列表记进方块实体数据。"""
    x, y, z = data["blockPos"]
    facing = FacingOfAux(data["blockAuxValue"])
    displayEntityList = []
    step = -0.037
    for _ in range(SkilletDisplayCount(itemDict["count"])):
        step += 0.037
        displayDict = copy.deepcopy(itemDict)
        displayDict["count"] = 1
        pos = (x + random.uniform(0.43, 0.57), y + step, z + random.uniform(0.43, 0.57))
        displayEntityList.append(_spawn(displayDict, pos, facing, data["dimensionId"]))
    data["blockEntityData"]["displayEntityList"] = displayEntityList


def CuttingBoardDisplayEntity(itemDict, playerId, data):
    """砧板中央放一个展示实体，id 记进方块实体数据。"""
    x, y, z = data["blockPos"]
    entityId = _spawn(copy.deepcopy(itemDict), (x + 0.5, y, z + 0.5), FacingOfAux(data["blockAuxValue"]), data["dimensionId"])
    data["blockEntityData"]["displayEntityId"] = entityId
