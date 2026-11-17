# -*- coding: utf-8 -*-
"""StoveSwap - 炉灶点着 / 熄灭时换成另一个方块，烤位上的东西、手放的进度和朝向原样带过去（服务端）

JE 的 ignite / extinguish 只改方块状态 LIT，方块实体不动（AbstractStoveBlock.java:144-164：setBlock 同一个方块），东西、烤到哪都在。
基岩版点着的是 arris:stove、熄着的是 arris:stove_extinguish（Shared/Rules/GrillBlocks），换方块名等于换方块实体，数据不会跟着走，所以这里：
1. 换之前把炉灶自己的键（六个烤位、cookingIndex、手放的进度 handGrill）拍一份快照，朝向（direction 状态）也读出来（已经有等着写的快照就接着用它）；
2. SetBlockNew 换名字，朝向写回去（RopeFences 的门开关是同一个做法）；
3. 快照写进新的方块实体：方块实体已经在了就当场写，还没有就等 ServerPlaceBlockEntityEvent（Stove.OnServerStoveCreate）或炉灶的下一步（Stove.OnStoveTick），
   谁先到谁写（SkilletItem.attachPending 同一个思路）；PENDING_SECONDS 秒还写不上（新方块实体一直没建出来）就把快照里的东西丢在炉灶位置，不让东西凭空没了。
换方块时引擎会给旧方块发 BlockRemoveServerEvent，Stove.OnStoveRemove 会把烤位上的东西全丢出来、忘掉手放的进度和广播记录：这一下用 claims 挡住
（只认这个位置、旧 / 新两个名字、GUARD_SECONDS 内最多两次）。换完的 SETTLE_SECONDS 里炉灶每一步重发一遍世界外观（settling）：
客户端的方块实体在换方块时重建、场景跟着重建，先到的广播可能被盖掉。引擎的事件先后没法离线验证，所以两种先后（事件在 SetBlockNew 里同步到、晚一刻到）都兜住。
"""
import time

from . import HandGrill
from .Helpers.BlockItems import PublishStove
from .Helpers.Engine import compFactory, levelId, System, GetBlockEntityData, GetBlockName
from .Helpers.Placement import FacingOfAux
from ..Shared.Rules import GrillStation

KEYS = tuple(str(place) for place in range(GrillStation.PLACES)) + ("cookingIndex", HandGrill.SAVE_KEY)
GUARD_SECONDS = 0.5        # 换方块引发的移除事件，这么久以内算换方块自己的
SETTLE_SECONDS = 1.0       # 换完之后重发世界外观多久
PENDING_SECONDS = 5.0      # 快照等新方块实体多久，再等不到就丢在地上
_swaps = {}                # (维度, 坐标) -> Swap
_TEXT = type(u"")


class Swap(object):
    """一次换方块：old / new 是换之前 / 之后的方块名，data 是还没写进新方块实体的快照（写了是 None），at 是换的时刻，removals 是还能认几次移除事件。"""

    def __init__(self, old, new, data, at):
        self.old, self.new, self.data, self.at, self.removals = old, new, data, at, 2


def _pos(blockPos):
    return (int(blockPos[0]), int(blockPos[1]), int(blockPos[2]))


def _plain(value):
    """复制一份，元组换成列表、py2 的 unicode 换成 str（键和值都转）：方块实体数据只收这些，也不让快照跟着旧方块实体的缓存走。"""
    if isinstance(value, dict):
        return dict((_plain(key), _plain(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, _TEXT) and _TEXT is not str:
        return value.encode("utf-8")
    return value


def snapshot(blockEntityData):
    """炉灶自己的键的快照；没有的键不列（/setblock 放出来、没走过放置事件的炉灶什么都没有）。"""
    kept = {}
    for key in KEYS:
        value = blockEntityData[key] if blockEntityData else None
        if value is not None:
            kept[key] = _plain(value)
    return kept


def _directionOf(blockPos, dimensionId):
    """方块的朝向（direction 状态 0 南 1 西 2 北 3 东）：优先读状态，读不到再用 aux。"""
    states = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId)
    if states and "direction" in states:
        return states["direction"]
    return FacingOfAux((compFactory.CreateBlockInfo(levelId).GetBlockNew(blockPos, dimensionId) or {}).get("aux") or 0)


def swap(dimensionId, blockPos, newName, now=None):
    """把 blockPos 上的炉灶换成 newName（点着 <-> 熄着），东西、手放的进度、朝向原样带过去。换成了返回 True（没换成什么都没变）。"""
    now = time.time() if now is None else now
    blockPos = _pos(blockPos)
    key = (dimensionId, blockPos)
    oldName = GetBlockName(blockPos, dimensionId)
    if oldName == newName:
        return False
    previous = _swaps.get(key)
    carried = previous.data if previous is not None and previous.data is not None else snapshot(GetBlockEntityData(dimensionId, blockPos))
    direction = _directionOf(blockPos, dimensionId)
    record = _swaps[key] = Swap(oldName, newName, carried, now)
    if not compFactory.CreateBlockInfo(levelId).SetBlockNew(blockPos, {"name": newName}, 0, dimensionId):
        _swaps.pop(key, None)
        if previous is not None:
            _swaps[key] = previous
        return False
    states = compFactory.CreateBlockState(levelId).GetBlockStates(blockPos, dimensionId) or {}
    states["direction"] = direction
    compFactory.CreateBlockState(levelId).SetBlockStates(blockPos, states, dimensionId)
    apply(dimensionId, blockPos)
    compFactory.CreateGame(levelId).AddTimer(PENDING_SECONDS, _giveUp, key, record)
    return True


def apply(dimensionId, blockPos):
    """新方块实体建好了：把快照写进去（只写一次），再把世界里的展示发给客户端。写了返回 True；没有等着写的、方块实体还没有、
    位置上还不是换成的那个方块，什么也不做返回 False。"""
    record = _swaps.get((dimensionId, _pos(blockPos)))
    if record is None or record.data is None:
        return False
    data = GetBlockEntityData(dimensionId, blockPos)
    if not data or GetBlockName(blockPos, dimensionId) != record.new:
        return False
    for name, value in record.data.items():
        data[name] = value
    record.data = None
    PublishStove(dimensionId, blockPos, data)
    return True


def claims(dimensionId, blockPos, fullName, now):
    """这个移除事件是换方块引发的吗（Stove.OnStoveRemove 先问）：是就别丢东西、别忘记录。每次换最多认两次（旧方块的、新方块的）。"""
    record = _swaps.get((dimensionId, _pos(blockPos)))
    if record is None or record.removals <= 0 or fullName not in (record.old, record.new) or now - record.at > GUARD_SECONDS:
        return False
    record.removals -= 1
    return True


def settling(dimensionId, blockPos, now):
    """刚换完方块、快照已经写进去了：这一秒里炉灶每一步重发世界外观（Stove.OnStoveTick）。"""
    record = _swaps.get((dimensionId, _pos(blockPos)))
    return record is not None and record.data is None and 0.0 <= now - record.at < SETTLE_SECONDS


def _giveUp(key, record):
    """PENDING_SECONDS 到了：记录收掉；快照还没写进去（新方块实体一直没建出来）就把烤位上的东西丢在炉灶位置。"""
    if _swaps.get(key) is not record:
        return
    del _swaps[key]
    if record.data is None:
        return
    for place in range(GrillStation.PLACES):
        slot = record.data.get(str(place))
        item = slot.get("itemDict") if isinstance(slot, dict) else None
        if item and item.get("newItemName"):
            System.CreateEngineItemEntity(item, key[0], (key[1][0] + 0.5, key[1][1] + 0.5, key[1][2] + 0.5))
