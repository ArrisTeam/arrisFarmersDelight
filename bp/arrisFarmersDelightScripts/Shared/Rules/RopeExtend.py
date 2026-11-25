# -*- coding: utf-8 -*-
"""RopeExtend - 拿着绳子点绳子：新的一节放在哪（双端，纯规则）

照 JE 的 RopeItem.updatePlacementContext（FD 1.3.4）。拿着绳子点方块时，"点到的格子"是：点到的方块能被顶替就是它自己
（绳子对手里的绳子算能被顶替：RopeBlock.canBeReplaced），否则是点到的面外侧那一格。这一格不是绳子：和这里无关，照常放。
是绳子：不潜行一律往下、潜行照点到的面，从它那个方向的下一格走起——
- 碰到不是绳子的一格：是水以外的液体（岩浆）不放；能被顶替（空气、水、草……）就放在这一格；别的（实心方块、没加载的格子）不放；
- 还是绳子：往下就接着走，往别的方向不放；
- 走到世界最下面还没找到，不放。
"""
from .Placement import placePositions
from .TatamiMat import isReplaceable

ROPE = "arris:rope"
DOWN = 0                                   # 引擎的面：0 下 1 上 2 北 3 南 4 西 5 东
LAVA = ("minecraft:lava", "minecraft:flowing_lava")
# 最低的维度（主世界）从 -64 起；下界、末地更高的那几格交给放方块失败（SetBlockNew 返回 False）
BOTTOM = -64


def startRope(clicked, face, nameAt):
    """拿着绳子点了 clicked 的 face 面：从哪一节绳子算起；点到的格子不是绳子（照常放）返回 None。
    nameAt(坐标) 查那一格的方块名（没加载的格子 None）。"""
    clickedName = nameAt(clicked)
    if clickedName == ROPE:
        return tuple(clicked)
    if isReplaceable(clickedName):
        return None                        # 点到的是草、水这些：JE 就放在它那一格，不看旁边
    beside = placePositions(*clicked)[face]
    return beside if nameAt(beside) == ROPE else None


def placeAt(start, face, sneaking, nameAt, bottom=BOTTOM):
    """从绳子 start 起，新的一节放在哪：坐标，或者 None（不放）。"""
    direction = face if sneaking else DOWN
    dx, dy, dz = placePositions(0, 0, 0)[direction]
    x, y, z = start
    while True:
        x, y, z = x + dx, y + dy, z + dz
        if y < bottom:
            return None
        name = nameAt((x, y, z))
        if name != ROPE:
            if name in LAVA:
                return None
            return (x, y, z) if isReplaceable(name) else None
        if direction != DOWN:
            return None
