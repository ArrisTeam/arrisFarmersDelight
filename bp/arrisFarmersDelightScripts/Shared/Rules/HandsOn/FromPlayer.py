# -*- coding: utf-8 -*-
"""FromPlayer - 玩家往站点里放的东西从哪飞来：屏幕底边（背包所在的地方）投到站点里一个水平面上的那一点（双端，纯计算）

移植自 Hands-On Delight：client/FromPlayer.java（9-38）。一次放进好几件时，它们不是从放料的那个点出发，而是从屏幕底边的
一排点出发：第 index 件（共 count 件）在屏幕宽的 0.5 + (index - (count - 1) / 2) * 0.05、高的 0.97 处，射线投到高度 height 的水平面上；
和屏幕正中投到同一个面上的点做差、只留水平的两个分量，就是这一件相对它落点的起点偏移。只有开着站点的那位玩家有"屏幕"，
旁观的人（没有起点）东西从正上方落下，偏移是零（Optional 为空时 offset 返回 new Vector3f()，28-30 行）。
厨锅那边（PotDriftArrive / PotView._starts）是同一套数：起点的屏幕位置一样，只是落点相对锅心。
射线和相机的换算在内核（前置包 Client/View.rayAt），这里只出屏幕上的位置和做差。
"""
BOTTOM = 0.97                # 起点离屏幕上沿多远（占屏高的比例）：贴着屏幕下沿，背包那里（FromPlayer.java:15）
SPREAD = 0.05                # 先后几件在屏宽上相隔多远（占屏宽的比例，17 行）
MIDDLE = (0.5, 0.5)          # 屏幕正中（offset 里拿来做差的那一点，29 行）


def startAt(index, count):
    """第 index 件（共 count 件）起点在屏幕上的位置，占屏宽、屏高的比例 (x, y)（point，36-38 行）。"""
    return (0.5 + (index - (count - 1) / 2.0) * SPREAD, BOTTOM)


def planeAt(ray, height):
    """射线 (ox, oy, oz, dx, dy, dz)（站点像素）和水平面 y = height 的交点 (x, height, z)；平行、朝上或在身后返回 None。"""
    ox, oy, oz, dx, dy, dz = ray
    if abs(dy) < 1.0e-9:
        return None
    t = (height - oy) / dy
    if t < 0.0:
        return None
    return (ox + dx * t, height, oz + dz * t)


def offsetOf(start, middle):
    """起点相对落点的水平偏移 (x, z)（offset，26-33 行）：start、middle 是同一个水平面上的两点 (x, y, z)，
    任何一个是 None（旁观的人、相机还没就位）就是 (0, 0)。"""
    if start is None or middle is None:
        return (0.0, 0.0)
    return (start[0] - middle[0], start[2] - middle[2])
