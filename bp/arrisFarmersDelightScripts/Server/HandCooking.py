# -*- coding: utf-8 -*-
"""HandCooking - 厨锅的烹饪计时：FD 原样一份一份煮，或厨师在工位放的料等勺子、搅着整批一起煮（服务端）

移植自 Hands-On Delight 的 station/PotCooking.java；规则内核在 Shared/Rules/HandsOn（PotCooking、StirSkill、PotBonus、Spoon）。
每口锅一份 PotHand（计时、评星、勺子），第一次 tick 时建、方块没了删，只活在内存里；存档里只有 FD 原本的 timer
和奖励零头 handsOnBonus、料是不是手放的 handsOnByHand、煮了几份 potUsed。没人碰过的锅、漏斗等自动化放进来的料、
厨师走开 AWAY 秒之后，都按 FD 原样自己煮（每份按配方表的 CookTime x 配置倍率 cooking_pot_time，缺省 10 秒，和 JE 一致）；
站点开着时（Compat/Diegesis/PotLogic.py 每刻 attend）厨师放的料要搅才煮（stirring_required），整批按 1.5 / sqrt(份数)
的速度一起煮好，搅出的星星多送份数。不煮的时候（没热源、没有配方、成品放不下）进度每刻掉 2 刻（FD 的 cookingTick）。
"""
from .Helpers import PotContainer
from .Helpers.Engine import compFactory
from ..Shared.Rules import CookingPot as CookingPotRules
from ..Shared.Rules import PotStation
from ..Shared.Rules.HandsOn import PotCooking
from ..Shared.Rules.HandsOn.PotBonus import openStars
from ..Shared.Rules.HandsOn.Spoon import Spoon
from ..Shared.Rules.HandsOn.StirSkill import clampSpoon

COOK_SECONDS = PotStation.COOK_SECONDS
MADE_KEY = "arrisFD_potMade"     # 玩家 ExtraData：{成品名: 盛出过几份}，开第 2、3 颗星用
BY_HAND_KEY = "handsOnByHand"    # 方块实体数据：锅里的料是不是厨师在工位放的（PotCooking.byHand 随锅存档）
BONUS_KEY = "handsOnBonus"       # 方块实体数据：前几批没凑够整份的奖励零头
FD_MEAL_LIMIT = 64               # FD 的 canCook：成品格（ItemStackHandler）最多容 64 个，比一堆的上限大


class PotHand(object):
    """一口锅的手工烹饪状态。"""

    def __init__(self):
        self.clock = PotCooking.PotClock(realTime=True)     # 这里的服务器钟是 time.time()
        self.spoon = Spoon()
        self.spoonAt = (0.0, 0.0)        # 勺尖最后的位置（世界朝向，-1..1），给旁观的人看
        self.dish = None                 # 锅里的料现在能做的菜（物品字典）或 None
        self.heated = False
        self.batch = 0                   # 这批能一起煮几份（0：不能煮）
        self.total = COOK_SECONDS        # 这道菜一份煮多久（秒，配方表的 CookTime x 配置倍率）
        self.mode = PotCooking.FD_WAY    # 上一步的煮法
        self.served = 0                  # 搅着出锅的批数（站点看它变了就报星）
        self.lastOpen = 1                # 最后一次算出的开放星数（锅里没有可做的菜时界面接着显示它，PotLogic.refresh）


_hands = {}
_made = {}


def handOf(dimensionId, blockPos, blockEntityData=None):
    """这口锅的 PotHand，没有就建一份（从方块实体数据读回 FD 的计时、料是不是手放的和奖励零头）。"""
    key = (dimensionId, tuple(blockPos))
    hand = _hands.get(key)
    if hand is None:
        hand = _hands[key] = PotHand()
        if blockEntityData is not None:
            hand.clock.restore(blockEntityData[BY_HAND_KEY] is True, blockEntityData[BONUS_KEY] or 0.0)
            timer, total = blockEntityData["timer"], blockEntityData["timerTotal"] or COOK_SECONDS
            if isinstance(timer, (int, float)) and 0.0 <= timer <= total:
                hand.total = float(total)
                hand.clock.cookTime = hand.total - timer
    return hand


def forget(dimensionId, blockPos):
    _hands.pop((dimensionId, tuple(blockPos)), None)


def _keepByHand(clock, blockEntityData):
    """料是不是手放的随锅存档：变了才写（PotCooking.save / load）。"""
    if (blockEntityData[BY_HAND_KEY] is True) != clock.byHand:
        blockEntityData[BY_HAND_KEY] = clock.byHand


def cook(hand, dimensionId, blockPos, blockEntityData, slots, now, dt):
    """锅的一步（Server/CookingPot.py 的 tick 调用）：推进 dt 秒，煮好就出锅。slots 是 6 个食材格。"""
    clock = hand.clock
    clock.watchFood(PotStation.foodCount(slots))
    _keepByHand(clock, blockEntityData)
    for item in clock.forgotten(now):                    # 厨师走的那一刻没人取的余料：照 FD 掉在锅边
        PotContainer.spill(dimensionId, blockPos, item)
    meal, pushItems = CookingPotRules.matchRecipe(slots) if any(slots) else (None, None)
    hand.dish = meal
    hand.heated = blockEntityData["heatEnable"] is True
    hand.total = PotCooking.timeFor(CookingPotRules.cookSecondsOf(meal["newItemName"])) if meal else COOK_SECONDS
    ready = PotContainer.preview(blockEntityData)
    same = not (meal and ready) or ready["newItemName"] == meal["newItemName"]
    mealCount = ready.get("count", 0) if same else 0
    perServing = (meal.get("count") or 1) if meal else 1
    maxStack = PotContainer.maxStackOf(meal["newItemName"], meal["newAuxValue"]) if meal else 64
    if not (meal and hand.heated and same and mealCount + perServing <= max(FD_MEAL_LIMIT, maxStack)):
        hand.batch = 0                                   # 没热源、没有配方、成品放不下（别的菜 / 满 64）：不煮，进度往回掉
        hand.mode = PotCooking.WAITING
        clock.fall(dt)
        _writeTimer(blockEntityData, max(0.0, hand.total - clock.cookTime), hand.total)
        return
    hand.batch = PotCooking.batchOf(PotStation.servingsLeft(slots), mealCount, perServing, maxStack, same)
    hand.mode = clock.advance(now, dt, hand.total, hand.batch)
    if hand.mode != PotCooking.WAITING and clock.finished(hand.total):
        keep = lambda item: clock.keepLeftover(item, now)     # noqa: E731 - 余料：厨师在场就留给他
        PotContainer.cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItems, sink=keep)
        if hand.mode == PotCooking.STIRRED:
            _serveTheBatch(hand, dimensionId, blockPos, blockEntityData, slots, meal, pushItems, mealCount + perServing,
                           maxStack, now)
        else:
            clock.cookTime = 0.0
    _writeTimer(blockEntityData, max(0.0, hand.total - clock.cookTime), hand.total)


def _writeTimer(blockEntityData, left, total):
    """FD 的进度字段：timer 是这一份还剩几秒，timerTotal 是一份总共几秒（界面按两者之比画箭头）。"""
    blockEntityData["timer"] = left
    if blockEntityData["timerTotal"] != total:
        blockEntityData["timerTotal"] = total


def _serveTheBatch(hand, dimensionId, blockPos, blockEntityData, slots, meal, pushItems, mealCount, maxStack, now):
    """搅着的一批出了第一份：整批跟着出锅，星星多送的份数一起进预览槽（PotCooking.serveTheBatch）。"""
    plan = hand.clock.serve(now, mealCount, meal.get("count") or 1, maxStack)
    if plan.cooked > 1:
        keep = lambda item: hand.clock.keepLeftover(item, now)     # noqa: E731
        PotContainer.cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItems, plan.cooked - 1, keep)
    if plan.extraItems > 0:
        PotContainer.addMeals(blockEntityData, meal, plan.extraItems)
    blockEntityData[BONUS_KEY] = hand.clock.bonusCarried
    hand.served += 1


def stir(hand, playerId, now, x, z, at=None):
    """playerId 把勺尖搅到 (x, z)（-1..1）。别人正握着勺子返回 False。"""
    taken = PotCooking.stirStroke(hand.clock, hand.spoon, playerId, now, x, z, hand.heated, hand.batch,
                                  openStarsOf(playerId, hand.dish), at)
    if taken:
        hand.spoonAt = (clampSpoon(x), clampSpoon(z))
    return taken


def madeOf(playerId, dishName):
    cache = _made.get(playerId)
    if cache is None:
        raw = compFactory.CreateExtraData(playerId).GetExtraData(MADE_KEY)
        cache = _made[playerId] = dict(raw) if isinstance(raw, dict) else {}
    return int(cache.get(dishName) or 0)


def addMade(playerId, dishName, count):
    total = madeOf(playerId, dishName) + count
    _made[playerId][dishName] = total
    compFactory.CreateExtraData(playerId).SetExtraData(MADE_KEY, dict(_made[playerId]))
    return total


def openStarsOf(playerId, dish):
    """playerId 做这道菜能开几颗星（第一次 1 颗，盛出满 8 份 2 颗，满 32 份 3 颗）。"""
    if not playerId or not dish:
        return 1
    return openStars(madeOf(playerId, dish["newItemName"]))
