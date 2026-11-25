# -*- coding: utf-8 -*-
"""FortuneDrops - 农夫乐事的作物、野生作物、沙地灌木被玩家打掉时补上时运多掉的那几个（服务端）

规则在 Shared/Rules/FortuneBonus.py（JE 战利品表的 apply_bonus）；战利品表照常掉不带时运的那一份，这里在 DestroyBlockEvent
（方块已经没了、掉落已经出来）里读手上工具的时运等级，按规则在方块中心再掉几个。创造模式不补。
"""
import random

from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, System, GetCarriedItem
from .Helpers.Items import GetItemType
from .Helpers.Player import IsCreative
from ..Shared.Rules import FortuneBonus


def _droppedNames(entityIds):
    names = []
    for entityId in entityIds or ():
        item = compFactory.CreateItem(levelId).GetDroppedItem(entityId) or {}
        names.append(item.get("newItemName") or item.get("itemName"))
    return names


@registerHandler("DestroyBlockEvent", match=FortuneBonus.TABLE)
def OnDestroyWithFortune(args):
    playerId = args.get("playerId")
    if not playerId or IsCreative(playerId):
        return
    held = GetCarriedItem(playerId, True)
    level = FortuneBonus.fortuneLevel(held)
    if level <= 0:
        return
    extra = FortuneBonus.bonus(args["fullName"], held["newItemName"], GetItemType(held), level, _droppedNames(args.get("dropEntityIds")),
                               random)
    if extra is not None:
        pos = (args["x"] + 0.5, args["y"] + 0.5, args["z"] + 0.5)
        System.CreateEngineItemEntity({"itemName": extra[0], "count": extra[1], "auxValue": 0}, args["dimensionId"], pos)
