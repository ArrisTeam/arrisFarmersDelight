# -*- coding: utf-8 -*-
"""Basket - 篮子（竹篮 / 木篮）把落在身体里和朝向那一格里的掉落物吸进去，照 JE 的 BasketBlockEntity（服务端）

篮子是 netease:block_chest（引擎的箱子），没有方块实体 tick，所以两条路一起走，共用 pull 与同一份冷却：
- 掉落物进了篮子这一格：OnEntityInsideBlockServerEvent（netease:on_entity_inside）当场吸；
- 每 POLL 秒从"已加载的全部实体"里挑出掉落物，看收集区（篮子自己那一格加上面一格）里有没有篮子，
  事件管不到的"篮子上面那一格"靠它；不登记篮子的坐标，/setblock、结构放出来的篮子照样吸。
规则（收集区、往 27 格里塞的次序、冷却）在 Shared/Rules/Basket.py；这里读写引擎。
邻居有红石信号时篮子不吸（JE 的 ENABLED 状态）；本模组的篮子只朝上开口，收集区取朝上的那一种。
"""
import time
import traceback

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, DestroyEntity, GetBlockName, GetEngineTypeStr, GetLoadedEntities
from ..Shared.Data.Blocks import basketList
from ..Shared.Rules import Basket as Rules

ITEM_ENTITY = "minecraft:item"
# 轮询间隔（秒）；JE 每刻都试，吸到一件之后冷却 8 刻，这里 5 刻一轮、冷却照 8 刻
POLL = 0.25
FACING = Rules.UP
DEFAULT_STACK = 64

_gate = Rules.Gate()
_timer = []


def _maxStackOf():
    """返回 maxStackOf(物品字典)：这种物品一堆最多几个（同一轮里查过的记下来）。"""
    cache = {}

    def maxStackOf(stack):
        key = (stack["newItemName"], stack.get("newAuxValue") or 0)
        if key not in cache:
            info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1])
            cache[key] = (info or {}).get("maxStackSize") or DEFAULT_STACK
        return cache[key]
    return maxStackOf


def _readSlots(dimensionId, pos):
    itemComp = compFactory.CreateItem(levelId)
    return [itemComp.GetContainerItem(pos, index, dimensionId, True) for index in range(Rules.SLOTS)]


def _powered(dimensionId, pos):
    """邻居有红石信号（弱充能、强充能都算）。"""
    return bool(compFactory.CreateRedStone(levelId).GetBlockPoweredState(pos, dimensionId))


def _replaceWithRest(entityId, rest, dimensionId):
    """JE 的 itemEntity.setItem(剩下的)：基岩版改不了掉落物的数量，删掉再在原处放一个。"""
    foot = compFactory.CreatePos(entityId).GetFootPos()
    DestroyEntity(entityId)
    if foot is not None:
        System.CreateEngineItemEntity(rest, dimensionId, foot)


def pull(dimensionId, pos, entityIds, now, taken=None):
    """照 JE updateHopper：不在冷却、没被红石锁、没满，才吸 entityIds 里的掉落物；吸进一整个就停并进冷却。

    taken 是这一轮已经被别的篮子吸走的实体 id（两个篮子的收集区叠在一起时，一个掉落物只给一个）。返回是否吸进了一整个。
    """
    key = (dimensionId, tuple(pos))
    if not _gate.ready(key, now):
        return False
    if _powered(dimensionId, pos):
        _gate.idle(key, now)
        return False
    maxStackOf = _maxStackOf()
    slots = _readSlots(dimensionId, pos)
    if Rules.isFull(slots, maxStackOf):
        _gate.idle(key, now)
        return False
    itemComp = compFactory.CreateItem(levelId)
    for entityId in entityIds:
        if taken is not None and entityId in taken:
            continue
        stack = itemComp.GetDroppedItem(entityId, True)
        if not stack or stack.get("count", 0) <= 0:
            continue
        slots, changed, rest = Rules.insertAll(slots, stack, maxStackOf)
        for index in changed:
            itemComp.SpawnItemToContainer(slots[index], index, pos, dimensionId)
        if rest is None:
            DestroyEntity(entityId)
            if taken is not None:
                taken.add(entityId)
            _gate.captured(key, now)
            return True
        if changed:
            _replaceWithRest(entityId, rest, dimensionId)
            if taken is not None:
                taken.add(entityId)
    _gate.idle(key, now)
    return False


def poll():
    """挑出所有掉落物，按它们碰到的篮子分组，每个篮子吸一轮；掉落物就在自己身体里的篮子先吸（再轮到够得着它的邻篮子）。"""
    now = time.time()
    groups = {}
    for entityId, info in (GetLoadedEntities() or {}).items():
        if info.get("identifier") != ITEM_ENTITY:
            continue
        foot = compFactory.CreatePos(entityId).GetFootPos()
        if foot is None:
            continue
        dimensionId = info.get("dimensionId", 0)
        for rank, cell in enumerate(Rules.basketCells(foot, FACING)):
            if GetBlockName(cell, dimensionId) in basketList:
                groups.setdefault((dimensionId, cell), []).append((rank, entityId))
    taken = set()
    for (dimensionId, cell), found in sorted(groups.items(), key=lambda entry: (min(entry[1])[0], entry[0])):
        pull(dimensionId, cell, [entityId for rank, entityId in sorted(found)], now, taken)
    _gate.prune(now)


def _poll():
    try:
        poll()
    except Exception:  # noqa: BLE001 - 定时器边界：出错只打印，下一轮接着来
        print("[arrisFarmersDelight] 篮子轮询出错")
        traceback.print_exc()


def _ensureTimer():
    if not _timer:
        _timer.append(compFactory.CreateGame(levelId).AddRepeatedTimer(POLL, _poll))


@registerHandler("ClientLoadAddonsFinishServerEvent")
def OnBasketPlayerJoin(args):
    _ensureTimer()


@registerHandler("OnEntityInsideBlockServerEvent", match=basketList)
def OnEntityInsideBasket(args):
    _ensureTimer()
    entityId = args["entityId"]
    if GetEngineTypeStr(entityId) != ITEM_ENTITY:
        return
    pos = (args["blockX"], args["blockY"], args["blockZ"])
    dimensionId = compFactory.CreateDimension(entityId).GetEntityDimensionId()
    pull(dimensionId, pos, [entityId], time.time())
