# -*- coding: utf-8 -*-
"""PotPiecesPiece - 汤里浮着的一块碎料：常量、曲线、障碍表、颜色深浅（双端）

PotPieces 的零件，数值移植自 Diegesis 的 impl/client/fx/LiquidPieces.java 的常量和 Piece 构造、
Hands-On Delight 的 client/PotBehavior.java 150 / 157 / 1466-1476 行（障碍的半径和排法）。时间是秒，长度是汤节点的像素。
"""
import math

from .Mth import TWO_PI, lerp

MAX = 48                      # 最多同时浮这么多块
APPEAR_HALF_LIFE = 0.16       # 长出来 / 缩走的半衰期（秒）
GONE = 0.02                   # 缩到这么小就拿掉
REACH = 0.9                   # 离壁至少留 (1 - REACH) 的路
LIFT = 0.16                   # 浮在面上方这么高（像素）
GOLDEN_ANGLE = 2.3999631      # 金角：相邻两块转这么多，不扎堆
OUTWARD_STEP = 0.7548777      # 向外的步长（无理数，块数再多也均匀）
RISE_DEPTH = 2.2              # 从面下多深冒上来（像素）
RISE_TIME = 0.55              # 冒上来要多久（秒）
RISE_RING = 0.14              # 冒到面上敲出的涟漪有多强
PUSH_HALF_LIFE = 0.6          # 被挤开的块飘回自己的路的半衰期（秒）
CLEARANCE = 0.36              # 别的块离它至少这么远：它的大小的这个比例
SEPARATE_PASSES = 3           # 每帧挤几遍
OVERSHOOT = 2.6               # 冒上来的过冲
WAKE = 0.7                    # 块走过留下的尾迹的清晰度（0 不留）
WAKE_STEP = 0.4               # 走了这么远（像素）才留一个尾迹点
WAKE_FROM = 0.4               # 速度（像素 / 秒）超过它才有尾迹
WAKE_RANGE = 1.6              # 再快这么多尾迹才满
TUMBLE_FROM = 0.35            # 流速（弧度 / 秒）超过它实心的块才会翻身
TUMBLE_RATE = 0.3             # 流速 1 时每秒翻身的概率
TUMBLE_TIME = 0.6             # 翻一次要多久（秒）
TUMBLE_HOP = 0.45             # 翻身时跳多高（像素）
SPOON_RADIUS = 1.05           # 勺子在障碍表里的半径（PB 150）
ITEM_RADIUS = 1.15            # 整件的料的半径（PB 157）
POT_CENTER = 8.0


def approach(current, target, halfLife, dt):
    """Easing.approach：current 朝 target 指数地走，halfLife 秒走掉一半。"""
    if halfLife <= 0.0:
        return target
    return target + (current - target) * 0.5 ** (dt / halfLife)


def overshot(t):
    """冒上来的曲线：0..1 的 t -> 0 到 1，先冲过 1 再落回（1 + (OVERSHOOT + 1) * b ** 3 + OVERSHOOT * b ** 2，b = t - 1）。"""
    back = t - 1.0
    return 1.0 + (OVERSHOOT + 1.0) * back * back * back + OVERSHOOT * back * back


def obstaclesOf(spoon, items, center=POT_CENTER):
    """障碍表（x, z, 半径 逐个排开）：勺子穿过汤面处 spoon = (x, z) 和整件的料 items = [(x, z)]，都是离锅中心的像素（PB 1466-1476）。"""
    flat = [spoon[0] + center, spoon[1] + center, SPOON_RADIUS]
    for x, z in items:
        flat += [x + center, z + center, ITEM_RADIUS]
    return flat


def shaded(color, shade):
    """颜色各通道乘 shade（0.9..1，每块有自己的深浅）。"""
    return (int((color >> 16 & 0xFF) * shade + 0.5) << 16) | (int((color >> 8 & 0xFF) * shade + 0.5) << 8) | int((color & 0xFF) * shade + 0.5)


class Piece(object):
    """汤里浮着的一块。"""
    __slots__ = ("floater", "id", "reach", "wander", "shade", "mirrored", "angle", "yaw", "grown", "rise", "tumble", "over", "u", "v",
                 "wayX", "wayZ", "x", "z", "radius", "touching", "pushX", "pushZ", "wakeX", "wakeZ", "wakeClock", "rang", "leaving")

    def __init__(self, floater, index, rand):
        """index 是这是汤里长出来的第几块（不是现在第几块）：决定它在螺旋上的位置。随机数的次序同 Java。"""
        self.floater, self.id = floater, index
        self.reach = math.sqrt(0.06 + 0.94 * (index * OUTWARD_STEP % 1.0))
        self.wander = rand() * 2.0 - 1.0
        self.angle = index * GOLDEN_ANGLE
        self.yaw = rand() * TWO_PI if floater[3] else (rand() - 0.5) * 0.9
        self.shade = lerp(rand(), 0.9, 1.0)
        self.mirrored = rand() < 0.5
        self.grown = self.rise = self.tumble = 0.0
        self.u = self.v = self.wayX = self.wayZ = self.x = self.z = self.radius = 0.0
        self.pushX = self.pushZ = self.wakeX = self.wakeZ = self.wakeClock = 0.0
        self.over = self.touching = self.rang = self.leaving = False
