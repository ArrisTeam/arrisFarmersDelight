# -*- coding: utf-8 -*-
"""SkilletItem - 煎锅物品：潜行才放成方块、方块记住那一件煎锅、拆掉原样掉回（服务端）

JE：SkilletItem.place（不潜行不放，右键走手持烹饪，见 SkilletHand）、updateCustomBlockEntityTag + SkilletBlockEntity.skilletStack
（放下去的那件连耐久、附魔、名字一起存在方块里，火焰附加会缩短方块煎东西的时间）、CopySkilletFunction（拆掉时战利品表把存着的
那件原样掉出来；创造模式没有战利品）。
放置本身还是 Server/ItemToBlock.py 那一份（与派共用）：这里在它前面挡一道潜行判断，放好后把那件煎锅记进方块实体数据 "skilletItem"。
方块的战利品表是空的（bp/loot_tables/air_loot.json），掉落全在这里：Skillet.py 的 BlockRemoveServerEvent 处理调 dropStored。
旧存档 / 命令放出来的煎锅没有 "skilletItem"：火焰附加按 0 级，拆掉掉一把新的。
"""
import time

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, System, GetBlockEntityData, GetBlockName, GetCarriedItem
from .Helpers.Player import IsCreative
from .ItemToBlock import OnPlaceItemAsBlock
from ..Shared.Rules import SkilletRules as Rules
from ..Shared.Rules.Placement import placePositions

AIR = "minecraft:air"
STORED_KEY = "skilletItem"
# 放下去之后方块实体可能还没建好：记着，等放置事件（或放置后的直接读取）到了再写进去
_PENDING_SECONDS = 5.0
_PENDING_LIMIT = 32
_pending = {}      # (维度, 坐标) -> (记进去的那件煎锅, 过期时间)
_creativeBreaks = Rules.BreakMarks()


def _itemName(args):
    return args["itemDict"]["newItemName"]


def _remember(dimensionId, blockPos, stored, now):
    if len(_pending) >= _PENDING_LIMIT:
        for oldKey in [key for key, entry in _pending.items() if entry[1] < now]:
            del _pending[oldKey]
    _pending[(dimensionId, tuple(blockPos))] = (stored, now + _PENDING_SECONDS)


def attachPending(blockEntityData, dimensionId, blockPos):
    """方块实体建好了：把刚放下去的那件煎锅记进去（只记一次，放置事件和放置之后的直接读取谁先到谁记）。"""
    entry = _pending.pop((dimensionId, tuple(blockPos)), None)
    if entry is not None and entry[1] >= time.time():
        blockEntityData[STORED_KEY] = entry[0]


def fireAspectOf(blockEntityData):
    """方块里那件煎锅的火焰附加等级（没存过是 0）。"""
    return Rules.fireAspectLevel(blockEntityData[STORED_KEY]) if blockEntityData else 0


# 优先级 98.5：排在野生作物检查（99）之后、ItemToBlock（98）之前，ItemToBlock 不会再看到煎锅
@registerHandler("ServerItemUseOnEvent", match=Rules.SKILLET_ITEM, keyOf=_itemName, priority=98.5)
def OnUseSkilletItem(args):
    # JE SkilletItem.place：只有潜行才放成方块；不潜行什么都不放（手持烹饪由 SkilletHand 管），ItemToBlock 也别当普通方块物品放
    playerId = args["entityId"]
    if compFactory.CreatePlayer(playerId).isSneaking() is not True:
        return True
    held = GetCarriedItem(playerId, True) or args["itemDict"]
    dimensionId = args["dimensionId"]
    setPos = placePositions(args["x"], args["y"], args["z"])[args["face"]]
    wasAir = GetBlockName(setPos, dimensionId) == AIR
    _remember(dimensionId, setPos, Rules.storeItem(held), time.time())
    OnPlaceItemAsBlock(args)
    if wasAir and GetBlockName(setPos, dimensionId) == Rules.SKILLET_BLOCK:
        blockEntityData = GetBlockEntityData(dimensionId, setPos)
        if blockEntityData:
            attachPending(blockEntityData, dimensionId, setPos)
    else:
        _pending.pop((dimensionId, tuple(setPos)), None)
    return True


@registerHandler("ServerPlayerTryDestroyBlockEvent", match=Rules.SKILLET_BLOCK)
def OnTryBreakSkillet(args):
    # 创造模式的玩家拆煎锅：JE 战利品表只在非创造时结算，所以不掉煎锅（方块真没了时在 dropStored 里认这笔记录）
    if IsCreative(args["playerId"]):
        _creativeBreaks.put((args["dimensionId"], args["x"], args["y"], args["z"]), time.time())


def dropStored(blockEntityData, dimensionId, blockPos):
    """JE CopySkilletFunction：拆掉时把存着的那件煎锅原样掉出来（没存过掉一把新的）；创造模式拆不掉。"""
    if _creativeBreaks.take((dimensionId,) + tuple(blockPos), time.time()):
        return
    item = Rules.restoreItem(blockEntityData[STORED_KEY] if blockEntityData else None)
    System.CreateEngineItemEntity(item, dimensionId, (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5))
