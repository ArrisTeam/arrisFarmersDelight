# -*- coding: utf-8 -*-
"""PanOil - 锅里的油膜：每块食物底下一摊琥珀色的油，煎的时候慢慢淌开，锅空了或凉了慢慢收干（双端）

移植自 Hands-On Delight 的 client/PanOil.java（常量 36-42 行，frame 51-54、paint 57-77）。JE 里它是挂在锅节点 oil 上的画笔：
每块食物一张贴图（block/oil_film）的方片，边长 = 那块的大小 * SPREAD * (0.55 + 0.45 * sqrt(amount)) 的一半，贴在锅底上方 1.03，
只转四分之一圈的整数倍（让像素对得上锅的格子）。这里只算数：每块一摊 {"x", "z", "half", "alpha", "turn"}，怎么画由客户端决定。
时间是秒，位置是锅里的像素（离锅心）。
"""
import math

from .Mth import clamp, roundInt

SPREAD = 1.3         # 油淌到比那块食物大这么多倍（PanOil 39）
GROW = 2.5           # 煎着的时候淌满要这么久（秒，41）
DRY = 1.5            # 锅空了或凉了收干要这么久（41）
SHIMMER = 0.12       # 热油的光一明一暗的幅度（43）
HEIGHT = 1.03        # 油膜贴在锅底上方这么高（skillet.json 里 oil 节点的 pos）


class Oil(object):
    def __init__(self):
        self.places = []
        self.size = 0.0
        self.amount = 0.0
        self.clock = 0.0

    def lay(self, places, size):
        """现在锅里的食物各在哪（离锅心的 (x, z)）、画多大。"""
        self.places = [tuple(at) for at in places]
        self.size = size

    def frame(self, dt, frying):
        """煎着就淌开，否则收干。"""
        self.clock += dt
        self.amount = clamp(self.amount + (dt / GROW if frying else -dt / DRY), 0.0, 1.0)

    def puddles(self):
        """此刻每块底下的油：[{"x", "z", "half", "alpha": 0..255, "turn": 第几个四分之一圈}]；没油时是空表。"""
        if self.amount <= 0.0 or not self.places:
            return []
        grown = math.sqrt(self.amount)
        out = []
        for index, (x, z) in enumerate(self.places):
            half = self.size * SPREAD * 0.5 * (0.55 + 0.45 * grown)
            shimmer = 1.0 - SHIMMER + SHIMMER * math.sin(self.clock * 2.6 + index * 1.9)
            out.append({"x": x, "z": z, "half": half, "alpha": int(clamp(roundInt(255.0 * self.amount * shimmer), 0, 255)), "turn": index % 4})
        return out
