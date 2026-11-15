# -*- coding: utf-8 -*-
"""PotCooking - 厨锅批量烹饪计时、搅拌门控与 FD 原样兜底（双端）

移植自 Hands-On Delight 的 station/PotCooking.java（beforeCooking / keepTimeAt / timeFor / attend / watchFood）
与 station/PotLogic.java（speed / batch）。勺子归属见 Spoon。

烹饪只在锅被搅动时推进，放着不管进度停在原处。锅里的料作为一整批同时煮好、同时出锅，批越大越慢
（按份数的平方根，最多按 16 份算：16 份只要 4 倍时间，没人要搅一小时）。这是"手工烹饪"：厨师在工位放的料等勺子。
自动化放进来的料（漏斗、管道、锅自己的菜单），以及厨师走开之后他放的料，按 FD 原样一份一份自己煮，
让整合包里的自动化继续能用。星级奖励见 PotBonus，评星见 StirSkill。

时间一律是秒。原版逐刻累加 cookTime 并用 saved 攒小数；这里直接按 dt 连续累加，效果相同。
"""
import math

from .Mth import EPS, NEVER, TICK, clamp, isFinite, roundToTick, truncDiv
from .PotBonus import CARRY_CAP, servePlan
from .StirSkill import StirSkill

PACE = 1.5               # 一份的烹饪速度是 FD 原版的 1.5 倍
SLOWEST_BATCH = 16       # 批量再大也只按 16 份算慢
STIR_WINDOW = 2.0        # 原 STIR_TICKS = 40：一次搅动让锅"算被搅过"这么久，勺子停了它就停
AWAY = 2.0               # 原 AWAY = 40：厨师离开工位这么久后，他放的料按 FD 原样自己煮
HERE = 0.1               # 原 HERE = 2：厨师"此刻在工位"的判定（工位每刻上报一次，留一刻余量）

WAITING = 0              # advance 的结果：这一步不煮（厨师的料在等勺子）
FD_WAY = 1               # FD 原样：一份一份自己煮，每秒走一秒
STIRRED = 2              # 被搅着：整批按批量速度煮


def batchSpeed(batch):
    """一批 batch 份的烹饪速度（配方秒/秒）：1.5 / sqrt(clamp(batch, 1, 16))。"""
    return PACE / math.sqrt(clamp(batch, 1, SLOWEST_BATCH))


def timeFor(recipeSeconds, times=1.0):
    """配置的烹饪时长倍率作用后的总时长（原 HandsOnConfig.scaled：至少一刻，取整到整刻）。"""
    return roundToTick(recipeSeconds * times)


def batchOf(servingsLeft, mealCount, resultCount, maxStack, sameMeal=True):
    """能一起煮的份数：料够做几份，且成品堆叠放得下（PotLogic.batch）。sameMeal=False（锅里是别的菜）算 0。"""
    if not sameMeal or resultCount <= 0:
        return 0
    return max(0, min(servingsLeft, truncDiv(maxStack - mealCount, resultCount)))


def cookSecondsLeft(total, progress, speed):
    """徽章上显示的剩余整秒数，进位（原 PotLogic.refresh 的 COOK_LEFT：ceil(总刻*(1-进度)/速度/20)*20 刻）。"""
    return int(math.ceil(total * (1.0 - progress) / speed - EPS))


def stirStroke(clock, spoon, who, now, x, z, heated, batch, openStars, at=None):
    """厨师 who 在 now 搅了一下勺尖到 (x, z)（PotLogic 的 ACTION_STIR）。

    勺子正被别人握着就不算（返回 False）；否则锅算被搅过 STIR_WINDOW，勺尖交给评星。
    heated / batch：锅是否烧着、这一批有几份；锅不煮（没烧着、没有可煮的批）时搅了不攒星。
    """
    if not spoon.take(who, now):
        return False
    clock.stir(now)
    clock.skill.move(now, x, z, heated and batch > 0, openStars, at)
    return True


class PotClock(object):
    """一口锅的烹饪计时：谁在搅、料是谁放的、煮到哪了、奖励零头攒了多少。"""

    def __init__(self):
        self.skill = StirSkill()     # 这口锅的搅拌评星
        self.cookTime = 0.0          # 已煮的时间（配方秒）；到 total 出第一份
        self.pace = 0.0              # 上一步的速度倍率：批量速度、1（FD 原样）、0（还不知道）
        self.batch = 0               # 上一步按多少份算
        self.byHand = False          # 料是厨师在工位放的：等勺子
        self.stirredUntil = NEVER
        self.attendedAt = NEVER      # 厨师最后一次在工位的时刻
        self.bonusCarried = 0.0      # 前几批没凑够整份的奖励零头
        self.grade = 0               # 上一批出锅时的整星数
        self.bonus = 0               # 上一批多送的份数
        self.setsSaved = 0           # 上一批省下、该还给厨师的料套数
        self.savedAt = NEVER
        self._fed = -1               # 上一步锅里有几件料（-1：还没看过）
        self._handFed = False

    def stir(self, now):
        self.stirredUntil = now + STIR_WINDOW

    def isStirred(self, now):
        return now < self.stirredUntil - EPS

    def attend(self, now):
        """有厨师此刻在工位（工位每刻调一次）。"""
        self.attendedAt = now

    def attended(self, now):
        return now - self.attendedAt <= AWAY + EPS

    def here(self, now):
        return now - self.attendedAt <= HERE + EPS

    def feedByHand(self):
        """厨师在工位往锅里放了料：到锅下一步之前进来的料算手放的。"""
        self._handFed = True

    def watchFood(self, count):
        """锅每步调一次，count 是锅里料的总件数：多了就看是手放的还是自动进来的。"""
        if self._fed >= 0 and count > self._fed:
            self.byHand = self._handFed
        self._handFed = False
        self._fed = count

    def reloaded(self):
        """从存档读回之后调：读回来的料早就在锅里了，只有此后进来的才说明谁在喂。"""
        self._fed = -1

    def farmersDelightsWay(self, now, stirringRequired=True, inMenu=False):
        """这一步该按 FD 原样自己煮吗：没被搅，且（料不是手放的 / 厨师已走开 / 不要求搅拌 / 在锅自己的菜单里操作）。"""
        return not self.isStirred(now) and (
            not self.byHand or not self.attended(now) or not stirringRequired or inMenu)

    def keepTimeAt(self, pace, total):
        """速度倍率变了（料加减了，或在 FD 原样和被搅之间切换）：已煮的真实时间不变，按新速度折算进度。"""
        if self.pace > 0.0 and abs(pace - self.pace) > 1.0e-9 and total > 0.0:
            self.cookTime = min(total - TICK, self.cookTime * pace / self.pace)
        self.pace = pace

    def advance(self, now, dt, total, batch, stirringRequired=True, inMenu=False):
        """锅在煮的这一步（加热着、配方有效）推进 dt 秒。返回 WAITING / FD_WAY / STIRRED。"""
        if self.farmersDelightsWay(now, stirringRequired, inMenu):
            self.keepTimeAt(1.0, total)
            self.batch = 0
            self.cookTime += dt
            return FD_WAY
        speed = batchSpeed(batch)
        self.keepTimeAt(speed, total)
        self.batch = batch
        if not self.isStirred(now):
            return WAITING
        self.cookTime += dt * speed
        return STIRRED

    def finished(self, total):
        return self.cookTime >= total - EPS

    def progress(self, total, batch=1):
        """表盘上的进度 0..1；没有可煮的批（batch 为 0）或总时长为 0 时是 0。"""
        return clamp(self.cookTime / total, 0.0, 1.0) if batch > 0 and total > 0.0 else 0.0

    def serve(self, now, mealCount, resultCount, maxStack, grade=None):
        """被搅着的一批做出了第一份：结算整批（PotCooking.serveTheBatch）。返回 PotBonus.ServePlan。

        mealCount 是第一份出来之后锅里成品的件数；grade 缺省取此刻评星的整星数。
        """
        if grade is None:
            grade = self.skill.grade(now)
        plan = servePlan(self.batch, mealCount, resultCount, maxStack, grade, self.bonusCarried, self.here(now))
        self.grade = grade
        self.bonus = plan.bonus
        self.setsSaved = plan.saved
        self.savedAt = now
        self.bonusCarried = plan.carried
        self.cookTime = 0.0
        self.batch = 0
        return plan

    def takeSaved(self, now):
        """省下的料套数，只给结算时还在工位的那位，且只给一次。"""
        taken = self.setsSaved if now - self.savedAt <= HERE + EPS else 0
        self.setsSaved = 0
        return taken

    def dump(self):
        """随锅存档的两项：料是不是手放的、奖励零头。返回普通 dict。"""
        return {"byHand": self.byHand, "bonus": self.bonusCarried}

    def restore(self, byHand=False, bonus=0.0):
        """从存档读回。收的是取出来的标量，不是 blockEntityData 本身（引擎对象没有 .get()，
        调用方用 blockEntityData["k"] or 默认值 取）；零头坏了（NaN、负数、不止一份）就夹回合法范围。"""
        value = float(bonus or 0.0)
        self.byHand = bool(byHand)
        self.bonusCarried = clamp(value, 0.0, CARRY_CAP) if isFinite(value) else 0.0
        self.reloaded()
