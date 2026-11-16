# -*- coding: utf-8 -*-
"""PotDriftExtras - 浮料的几个小帮手：平躺抖动角、成品的位置、碎料要绕开的东西（双端）

移植自 Hands-On Delight：SceneRenderer.renderSlotItem 的平躺抖动（Diegesis，814-820）、client/PotBehavior.java 的 drift 末尾
（1462-1478）。坐标是站点像素，角度是度。
"""
from .PotDrift import ITEM_LIFT, ITEM_RADIUS, MIDDLE, SPOON_RADIUS


def flatJitter(index):
    """第 index 格平躺的料绕竖轴额外转的角度，度：((index * 7919) % 25 - 12) * 0.7（再加 180 度、躺平 -90 度，由调用方的摆法决定）。"""
    return ((index * 7919) % 25 - 12) * 0.7


def servedAt(surfaceY):
    """成品（FD 的结果格里那份）浮在哪：液面中心 (x, y, z)，站点 px（PotBehavior.java:1478）。"""
    return (MIDDLE, surfaceY + ITEM_LIFT, MIDDLE)


def obstacleList(drift, present, out=None):
    """浮着的碎料要绕开的东西：[x, z, 半径, ...]，先是勺子再是每件整料，站点 px（PotBehavior.java:1462-1477，给 setFloatingObstacles）。"""
    out = [] if out is None else out
    del out[:]
    out.extend((drift.spoonX + MIDDLE, drift.spoonZ + MIDDLE, SPOON_RADIUS))
    for i in range(drift.slots):
        if present[i]:
            out.extend((drift.itemX[i] + MIDDLE, drift.itemZ[i] + MIDDLE, ITEM_RADIUS))
    return out
