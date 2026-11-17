# -*- coding: utf-8 -*-
"""CookingPotItem - 厨锅拆下来带着锅里的菜，放回去菜还在（服务端）

JE：厨锅的战利品表用 copy_meal 把盛出格里那叠菜写进掉落的厨锅物品（BlockEntityTag），放下时方块实体从物品里读回来；
食材格、容器格、成品格里的东西照常掉出来；创造模式拆不出物品（菜也就没了）。
基岩版：方块的战利品表改成空的，厨锅物品由这里在方块没了的时候掉——带着菜的把菜记在物品的 extraId 里、悬停文字写进 customTips
（规则见 Shared/Rules/PotItem.py）；放置前（ServerEntityTryPlaceBlockEvent，这时还看得到手里的物品）记下它带的菜，
方块实体建好时写进预览槽。活塞推着走的厨锅不算拆（那一格这时是移动中的方块）。
"""
import time

from .EventRegistry import registerHandler
from .Helpers import PotContainer
from .Helpers.Engine import compFactory, levelId, System, GetBlockName, GetCarriedItem
from .Helpers.Player import IsCreative
from ..Shared.Rules import PotItem
from ..Shared.Rules.SkilletRules import BreakMarks

# 活塞推动时原来那一格先变成这种方块
_MOVING = ("minecraft:moving_block", "minecraft:movingBlock", "minecraft:movingblock")
_pending = PotItem.Pending()
_creativeBreaks = BreakMarks()


@registerHandler("ServerEntityTryPlaceBlockEvent", match=PotItem.POT)
def OnTryPlacePot(args):
    # 手里这口锅带着菜：记下来，方块实体建好时写进去（放置被别的处理函数取消的话，这笔记录过几秒自己作废）。
    # 每次试放都先把这一格上一次的记录清掉：带菜的锅放置被取消、几秒内又在同一格放了一口空锅，空锅不能拿到那份菜（带菜的那口还在背包里，等于复制）
    key = (args["dimensionId"], args["x"], args["y"], args["z"])
    _pending.take(key, time.time())
    held = GetCarriedItem(args["entityId"], True)
    if not held or held.get("newItemName") != PotItem.POT:
        return
    meal = PotItem.mealOf(held.get("extraId") or "")
    if meal:
        _pending.put(key, meal, time.time())


def attachPending(blockEntityData, dimensionId, blockPos):
    """方块实体建好了：把刚放下去的那口锅带的菜放进预览槽。"""
    meal = _pending.take((dimensionId,) + tuple(blockPos), time.time())
    if meal:
        PotContainer.setPreview(blockEntityData, meal)


@registerHandler("ServerPlayerTryDestroyBlockEvent", match=PotItem.POT)
def OnTryBreakPot(args):
    # 创造模式的玩家拆厨锅：JE 的战利品表只在非创造时结算，不掉厨锅（方块真没了时在 dropPot 里认这笔记录）
    if IsCreative(args["playerId"]):
        _creativeBreaks.put((args["dimensionId"], args["x"], args["y"], args["z"]), time.time())


def beingMoved(blockPos, dimensionId):
    """这口锅是被活塞推走的（那一格这时是移动中的方块），不是拆掉了。"""
    return GetBlockName(blockPos, dimensionId) in _MOVING


def dropPot(blockEntityData, dimensionId, blockPos):
    """厨锅没了：掉一口厨锅物品，锅里那叠菜跟着它走（JE 的 copy_meal）；创造模式拆的不掉；被活塞推走的不算。"""
    if beingMoved(blockPos, dimensionId):
        return
    meal = PotContainer.preview(blockEntityData) if blockEntityData else {}
    if meal:
        PotContainer.setPreview(blockEntityData, None)
    if _creativeBreaks.take((dimensionId,) + tuple(blockPos), time.time()):
        return
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(meal["newItemName"], meal.get("newAuxValue") or 0) if meal else None
    item = PotItem.itemOf(meal, (info or {}).get("itemName"))
    System.CreateEngineItemEntity(item, dimensionId, (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5))
