# -*- coding: utf-8 -*-
"""
格子区的几何（界面单位），纯逻辑。格子：经典版 18、携带版 28。

滚动视图里的格子按视口宽度排：列数按视口宽度算（不超过控件数），网格在视口里水平居中（列数固定的格子区不按宽度算，
见 Std/Client/Widgets.py 的 ScrollArea）。按行回收的窗口在 Std/Windowed/Client.py。
布局特有的几何（例如面板随格数长高）在使用方的界面扩展里（Client/Layouts.ScreenExtension）。
"""
from __future__ import division   # 尺寸可能是整数，比例一律按实数算（py2 下 / 默认是整除）

import math

CLASSIC_SLOT = 18
POCKET_SLOT = 28


def gridColumns(width, slot, maxColumns):
    """视口宽 width 放得下几列（至少一列，至多 maxColumns 列）。"""
    return max(1, min(maxColumns, int((width + 0.01) // slot)))


def gridLeft(width, columns, slot):
    """网格在视口里水平居中时的左边距。"""
    return max(0.0, (width - columns * slot) / 2.0)


def contentRows(count, columns):
    return int(math.ceil(count / float(columns))) if count > 0 and columns > 0 else 0

