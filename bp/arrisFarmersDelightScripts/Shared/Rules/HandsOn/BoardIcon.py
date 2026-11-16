# -*- coding: utf-8 -*-
"""BoardIcon - 板上食物的图标：实心像素、主轴、虚线沿线画多长（双端）

移植自 Hands-On Delight 的 client/ItemVoxels.java：Icon.bounds / axis / solidSpan、Axis（26-243 行）。
HoD 把物品图标按像素切成体素；基岩版板上的东西是客户端掉落物，一整张图，切不开，所以只移植"图标哪里是实心、
它躺着的那条线在哪"。刀口线怎么落在上面见 BoardMarks.py。

坐标是场景像素，原点在食物（图标）中心：x 往操作者的左边长，z 往远处长（和站点坐标同向）。图标第 0 行在最上面（远端），
第 0 列在最左边（x 最大）。一件东西最长的那条边画 ITEM_SIZE 像素（图标 16 格，一格 0.625 像素）。
图标的实心像素由 Shared/Data/ItemMasks.py 给（tools/gen_item_masks.py 从贴图生成），表里没有的按整格实心算。
浮点用 Python 的双精度，HoD 是 float32，差在 1e-6 以内（拿原算法的 Java 对过）。
"""
import math

from ...Data.ItemMasks import ItemMasks

ITEM_SIZE = 10.0                 # BoardBehavior.ITEM_SIZE（62）：等着切的东西画多大，图标最长边的像素数
BLOCK_SCALE = 0.65               # :90 方块类的东西按物品画，这么大
BLOCK_SIZE = 8.0 * BLOCK_SCALE   # :91 它在板上占的边长
EPS = 1.0e-3
INFINITY = float("inf")


def normalized(angle):
    """Axis.normalized（224-233）：一条线转半圈还是它自己，折进 (-90, 90] 度。"""
    while angle > math.pi / 2.0:
        angle -= math.pi
    while angle <= -math.pi / 2.0:
        angle += math.pi
    return angle


class Axis(object):
    """食物躺着的那条线（ItemVoxels.Axis）：中心 (x, z)、指向远端的方向 (dirX, dirZ)、实心像素沿它从 start 到 end（start < 0 < end）、
    长宽比 elongation（圆的是 1）。"""

    __slots__ = ("x", "z", "dirX", "dirZ", "start", "end", "elongation")

    def __init__(self, x, z, dirX, dirZ, start, end, elongation):
        self.x, self.z, self.dirX, self.dirZ = x, z, dirX, dirZ
        self.start, self.end, self.elongation = start, end, elongation

    @staticmethod
    def square(half):
        """方块类的东西：边长 2 * half 的正方形，笔直朝远处。"""
        return Axis(0.0, 0.0, 0.0, 1.0, -half, half, 1.0)

    def at(self, spot):
        """离远端 spot（占全长的比例）的那一点 (x, z)。"""
        along = self.end - (self.end - self.start) * spot
        return (self.x + self.dirX * along, self.z + self.dirZ * along)

    def across(self):
        """垂直于食物长边的线的角度（弧度，离笔直横过去 x 方向多少，-90..90 度）。"""
        return normalized(math.atan2(self.dirX, -self.dirZ))

    def along(self):
        """食物长边自己的角度。"""
        return math.atan2(self.dirZ, self.dirX)


class Icon(object):
    """图标的实心像素（ItemVoxels.Icon 去掉颜色）。rows 每行一个整数，第 column 位为 1 就是实心。"""

    __slots__ = ("width", "height", "rows")

    def __init__(self, width, height, rows):
        self.width, self.height, self.rows = int(width), int(height), tuple(rows)

    @staticmethod
    def full(width=16, height=16):
        """整格实心（不知道图标长什么样时）。"""
        return Icon(width, height, [(1 << width) - 1] * height)

    def solid(self, column, row):
        return 0 <= column < self.width and 0 <= row < self.height and bool((self.rows[row] >> column) & 1)

    def bounds(self):
        """第一个和最后一个有实心像素的列和行：[左, 右, 上, 下]（Icon.bounds）；一个都没有时是 [宽, -1, 高, -1]。"""
        found = [self.width, -1, self.height, -1]
        for row in range(self.height):
            for column in range(self.width):
                if self.solid(column, row):
                    found = [min(found[0], column), max(found[1], column), min(found[2], row), max(found[3], row)]
        return found

    def pixel(self, size):
        """图标最长边画 size 像素时一格有多大。"""
        return size / float(max(self.width, self.height))

    def _middleX(self, column):
        return self.width / 2.0 - column - 0.5

    def _middleZ(self, row):
        return self.height / 2.0 - row - 0.5

    def axis(self, size=ITEM_SIZE):
        """Icon.axis（87-143）：穿过实心像素中心、顺着它们摊得最开的方向、指向远端的那条线。"""
        pixel = self.pixel(size)
        points = [(self._middleX(column), self._middleZ(row)) for row in range(self.height) for column in range(self.width)
                  if self.solid(column, row)]
        if not points:
            return Axis.square(size / 2.0)
        cx = sum(point[0] for point in points) / len(points)
        cz = sum(point[1] for point in points) / len(points)
        xx = sum((px - cx) * (px - cx) for px, _pz in points)
        zz = sum((pz - cz) * (pz - cz) for _px, pz in points)
        xz = sum((px - cx) * (pz - cz) for px, pz in points)
        angle = 0.5 * math.atan2(2.0 * xz, xx - zz)
        dirX, dirZ = math.cos(angle), math.sin(angle)
        if dirZ < -EPS or (abs(dirZ) <= EPS and dirX < 0.0):
            dirX, dirZ = -dirX, -dirZ                # 指向远端（图标上方）
        spread = math.sqrt(((xx - zz) / 2.0) ** 2 + xz * xz)
        big = (xx + zz) / 2.0 + spread
        small = max(1.0e-6, (xx + zz) / 2.0 - spread)
        alongs = [(px - cx) * dirX + (pz - cz) * dirZ for px, pz in points]
        return Axis(cx * pixel, cz * pixel, dirX, dirZ, (min(alongs) - 0.5) * pixel, (max(alongs) + 0.5) * pixel,
                    math.sqrt(big / small))

    def solidSpan(self, x, z, angle, size=ITEM_SIZE):
        """Icon.solidSpan（145-166）：线 (x + t cos, z + t sin) 上实心像素从哪到哪（t，像素）；碰不到返回 (inf, -inf)。
        照 HoD 每 1/4 格取一个点。"""
        pixel = self.pixel(size)
        step = pixel / 4.0
        alongX, alongZ = math.cos(angle), math.sin(angle)
        start, end = INFINITY, -INFINITY
        for index in range(int(2.0 * size / step + 1.0e-6) + 1):
            t = -size + index * step
            column = int(math.floor(self.width / 2.0 - (x + alongX * t) / pixel))
            row = int(math.floor(self.height / 2.0 - (z + alongZ * t) / pixel))
            if self.solid(column, row):
                start, end = min(start, t), max(end, t)
        return (start, end)


_icons = {}


def iconOf(name):
    """这件东西的实心图标：ItemMasks 里有就按它，没有（贴图读不到）按整格实心算。"""
    if name not in _icons:
        found = ItemMasks.get(name)
        _icons[name] = Icon(found[0], found[1], found[2]) if found is not None else Icon.full()
    return _icons[name]
