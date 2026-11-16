# -*- coding: utf-8 -*-
"""Straw - 刀具收割：草丛 / 高草丛 / 沙地灌木 / 成熟麦子 / 成熟稻穗额外掉稻草，刀收成熟稻穗得稻米（服务端）

JE 的 straw_from_* 战利品修改器只在拿 straw_harvesters 标签（刀）破坏时生效；概率表在 Shared/Data/Farming.py 的
STRAW_SOURCES，判定在 Shared/Rules/StrawRules.py。是不是刀沿用 Helpers/Items.IsKnife（knifeList 加上 arris:knife 标签）。
稻穗的战利品表按 JE 掉 rice_panicle；拿刀收时（rice_panicles.json 里 match_tool 刀的那一支）换成稻米。
"""
from .EventRegistry import registerHandler
from .Helpers.Engine import System, DestroyEntity, GetCarriedItem
from .Helpers.Items import IsKnife
from .Helpers.Player import IsCreative
from ..Shared.Data.Farming import STRAW_SOURCES
from ..Shared.Rules.StrawRules import strawChance
from ..Shared.Rules.Ticks import probability

RIPE_PANICLE = "arris:rice_upper_crop_stage3"


def _heldKnife(playerId):
    """玩家手里拿着刀（创造模式没有掉落，不算）。"""
    if IsCreative(playerId):
        return False
    held = GetCarriedItem(playerId)
    return bool(held) and IsKnife(held["newItemName"])


def _dropAt(args, itemName):
    pos = (args["x"] + 0.5, args["y"], args["z"] + 0.5)
    System.CreateEngineItemEntity({"itemName": itemName, "count": 1, "auxValue": 0}, args["dimensionId"], pos)


@registerHandler("DestroyBlockEvent", match=STRAW_SOURCES)
def OnDestroyStrawSource(args):
    if not _heldKnife(args["playerId"]):
        return
    if probability(strawChance(STRAW_SOURCES, args["fullName"], args.get("auxData"))):
        _dropAt(args, "arris:straw")


@registerHandler("DestroyBlockEvent", match=RIPE_PANICLE)
def OnDestroyRipePanicle(args):
    # 刀收成熟的稻穗：掉的是稻米，不是稻穗（战利品表已经掉了稻穗，拦下换掉）
    if not _heldKnife(args["playerId"]):
        return
    for entityId in args.get("dropEntityIds") or []:
        DestroyEntity(entityId)
    _dropAt(args, "arris:rice")
