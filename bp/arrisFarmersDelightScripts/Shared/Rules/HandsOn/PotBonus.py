# -*- coding: utf-8 -*-
"""PotBonus - 厨锅的星级奖励份数、开星门槛与出锅结算（双端）

移植自 Hands-On Delight 的 station/PotLogic.java（openStars / nextStar / bonusPercent / bonusRate / bonus）
与 station/PotCooking.java 的 serveTheBatch。

做过一道菜的份数越多，能开的星越多：第一次 1 星，做满 8 份开第 2 星，做满 32 份开第 3 星。
搅到 2 星每 4 份多送 1 份，搅到 3 星每 2 份多送 1 份；奖励向下取整，没凑够整份的部分带到下一批（carried），
所以一批大小不影响总奖励。
"""
from .Mth import clamp, floorInt, truncDiv

SECOND_STAR = 8          # 这道菜做过多少份开第 2 颗星
THIRD_STAR = 32          # 开第 3 颗星
CARRY_CAP = 0.999        # 带到下一批的零头最多这么多（不到一整份）
BONUS_EPS = 1.0e-4       # 防 0.49999 之类的浮点误差把整份吃掉


def openStars(made):
    """做过 made 份的菜能开几颗星。"""
    if made >= THIRD_STAR:
        return 3
    return 2 if made >= SECOND_STAR else 1


def nextStar(made):
    """离下一颗星有多远，0..1；星开满了是 1。"""
    if made >= THIRD_STAR:
        return 1.0
    if made >= SECOND_STAR:
        return float(made - SECOND_STAR) / (THIRD_STAR - SECOND_STAR)
    return float(made) / SECOND_STAR


def bonusPercent(stars):
    """搅到 stars 星时，每份多送的百分比。"""
    if stars >= 3:
        return 50
    return 25 if stars == 2 else 0


def bonusRate(stars):
    return bonusPercent(stars) / 100.0


def bonus(cooked, stars, carried):
    """cooked 份搅到 stars 星送几整份；carried 是前面几批没凑够整份的零头。"""
    return floorInt(cooked * bonusRate(stars) + carried + BONUS_EPS)


class ServePlan(object):
    """一批出锅的结算：用掉 cooked 套料，出 servings 套份量，多送 bonus 套，省下 saved 套还给厨师。"""

    def __init__(self, cooked, servings, saved, carried, extraItems):
        self.cooked = cooked
        self.servings = servings
        self.bonus = servings - cooked
        self.saved = saved
        self.carried = carried          # 新的零头
        self.extraItems = extraItems    # 锅"自己多生"的成品件数 = bonus * 每套出几件

    def __repr__(self):
        return "ServePlan(cooked=%d, servings=%d, bonus=%d, saved=%d, carried=%.3f)" % (
            self.cooked, self.servings, self.bonus, self.saved, self.carried)


def servePlan(batch, mealCount, resultCount, maxStack, grade, carried, here=True):
    """锅做完第一份后，剩下整批怎么结算（PotCooking.serveTheBatch）。

    batch       这一批按多少套料算（锅在上一步数的）
    mealCount   第一份出来之后，锅里成品已有多少件
    resultCount 一套料出几件成品
    maxStack    成品的最大堆叠
    grade       此刻整星数
    carried     之前攒的奖励零头
    here        厨师还在工位：省下的料才还给他，否则留在锅里接着煮
    """
    # 锅允许成品涨过堆叠上限：这一份之后就只剩它自己，所以至少 1 套
    room = max(1, truncDiv(maxStack - mealCount, resultCount) + 1)
    left = min(room, batch)
    # 用尽量少的料，凑满 room 容得下的最多份数；省下的料留在锅里
    cooked = 1
    servings = min(room, 1 + bonus(1, grade, carried))
    for size in range(2, left + 1):
        made = min(room, size + bonus(size, grade, carried))
        if made > servings:
            cooked, servings = size, made
    saved = max(0, left - cooked) if here else 0
    earned = carried + cooked * bonusRate(grade) - (servings - cooked)
    return ServePlan(cooked, servings, saved, clamp(earned, 0.0, CARRY_CAP), (servings - cooked) * resultCount)
