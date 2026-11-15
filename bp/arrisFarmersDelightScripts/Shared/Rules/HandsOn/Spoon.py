# -*- coding: utf-8 -*-
"""Spoon - 一把勺子一只手（双端）

移植自 Hands-On Delight 的 station/PotLogic.java：isStirring / onOpen / ACTION_STIR 里的勺子归属判断。

同一口锅同一时刻只有一个人能搅：有人正在搅时，别的厨师的动作不算；勺子停下 SPOON_FREE 秒后才能换人。
握着勺子的人也是这锅的"厨师"：评星看他做过这道菜多少份（见 PotBonus.openStars）。who 是调用方给的任意可比较的标识（玩家 id）。
"""
from .Mth import EPS, NEVER

SPOON_FREE = 0.5         # 原 SPOON_FREE = 10 刻：勺子停下这么久后，别的厨师才能接过去


class Spoon(object):
    def __init__(self):
        self.holder = None
        self.stirredAt = NEVER

    def isStirring(self, now):
        return now - self.stirredAt < SPOON_FREE - EPS

    def open(self, who, now):
        """who 打开了锅：没人在搅时，他成为这锅的厨师。"""
        if not self.isStirring(now):
            self.holder = who

    def take(self, who, now):
        """who 要搅一下。别人正握着勺子返回 False；否则勺子归 who，返回 True。"""
        if self.isStirring(now) and who != self.holder:
            return False
        self.stirredAt = now
        self.holder = who
        return True
