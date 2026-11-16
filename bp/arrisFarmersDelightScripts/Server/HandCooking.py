# -*- coding: utf-8 -*-
"""HandCooking - 厨锅的烹饪计时：FD 原样一份一份煮，或厨师在工位放的料等勺子、搅着整批一起煮（服务端）

移植自 Hands-On Delight 的 station/PotCooking.java；规则内核在 Shared/Rules/HandsOn（PotCooking、StirSkill、PotBonus、Spoon）。
每口锅一份 PotHand（计时、评星、勺子），第一次 tick 时建、方块没了删，只活在内存里；存档里只有 FD 原本的 timer
和奖励零头 handsOnBonus。没人碰过的锅、漏斗等自动化放进来的料、厨师走开 AWAY 秒之后，都按 FD 原样自己煮
（每份 COOK_SECONDS 秒）；站点开着时（Compat/Diegesis/PotLogic.py 每刻 attend）厨师放的料要搅才煮，
整批按 1.5 / sqrt(份数) 的速度一起煮好，搅出的星星多送份数。
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


class PotHand(object):
    """一口锅的手工烹饪状态。"""

    def __init__(self):
        self.clock = PotCooking.PotClock(realTime=True)     # 这里的服务器钟是 time.time()
        self.spoon = Spoon()
        self.spoonAt = (0.0, 0.0)        # 勺尖最后的位置（世界朝向，-1..1），给旁观的人看
        self.dish = None                 # 锅里的料现在能做的菜（物品字典）或 None
        self.heated = False
        self.batch = 0                   # 这批能一起煮几份（0：不能煮）
        self.mode = PotCooking.FD_WAY    # 上一步的煮法
        self.served = 0                  # 搅着出锅的批数（站点看它变了就报星）


_hands = {}
_made = {}


def handOf(dimensionId, blockPos, blockEntityData=None):
    """这口锅的 PotHand，没有就建一份（从方块实体数据读回 FD 的计时和奖励零头）。"""
    key = (dimensionId, tuple(blockPos))
    hand = _hands.get(key)
    if hand is None:
        hand = _hands[key] = PotHand()
        if blockEntityData is not None:
            hand.clock.restore(False, blockEntityData["handsOnBonus"] or 0.0)
            timer = blockEntityData["timer"]
            if isinstance(timer, (int, float)) and 0.0 <= timer <= COOK_SECONDS:
                hand.clock.cookTime = COOK_SECONDS - timer
    return hand


def forget(dimensionId, blockPos):
    _hands.pop((dimensionId, tuple(blockPos)), None)


def cook(hand, dimensionId, blockPos, blockEntityData, slots, now, dt):
    """锅的一步（Server/CookingPot.py 的 tick 调用）：推进 dt 秒，煮好就出锅。slots 是 6 个食材格。"""
    clock = hand.clock
    clock.watchFood(PotStation.foodCount(slots))
    meal, pushItems = CookingPotRules.matchRecipe(slots) if any(slots) else (None, None)
    hand.dish = meal
    hand.heated = blockEntityData["heatEnable"] is True
    if not (meal and hand.heated):
        hand.batch = 0
        clock.cookTime = 0.0
        blockEntityData["timer"] = COOK_SECONDS
        return
    ready = PotContainer.preview(blockEntityData)
    maxStack = PotContainer.maxStackOf(meal["newItemName"], meal["newAuxValue"])
    same = not ready or ready["newItemName"] == meal["newItemName"]
    mealCount = ready.get("count", 0) if same else 0
    hand.batch = PotCooking.batchOf(PotStation.servingsLeft(slots), mealCount, 1, maxStack, same)
    if hand.batch <= 0:
        return                           # 预览槽满了或装着别的菜：等它被盛走，计时停在原处
    hand.mode = clock.advance(now, dt, COOK_SECONDS, hand.batch)
    if hand.mode != PotCooking.WAITING and clock.finished(COOK_SECONDS):
        PotContainer.cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItems)
        if hand.mode == PotCooking.STIRRED:
            _serveTheBatch(hand, dimensionId, blockPos, blockEntityData, slots, meal, pushItems, mealCount + 1, maxStack, now)
        else:
            clock.cookTime = 0.0
    blockEntityData["timer"] = max(0.0, COOK_SECONDS - clock.cookTime)


def _serveTheBatch(hand, dimensionId, blockPos, blockEntityData, slots, meal, pushItems, mealCount, maxStack, now):
    """搅着的一批出了第一份：整批跟着出锅，星星多送的份数一起进预览槽（PotCooking.serveTheBatch）。"""
    plan = hand.clock.serve(now, mealCount, 1, maxStack)
    if plan.cooked > 1:
        PotContainer.cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItems, plan.cooked - 1)
    if plan.extraItems > 0:
        PotContainer.addMeals(blockEntityData, meal, plan.extraItems)
    blockEntityData["handsOnBonus"] = hand.clock.bonusCarried
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
