# -*- coding: utf-8 -*-
"""PanLayout - 煎锅里的食物摆成什么样：几块在上面、几块垫在下面、各在哪、多大、转多少度、熟到哪一档（双端）

移植自 Hands-On Delight 的 client/SkilletBehavior.java：常量 41-43、84 行，refresh 里数块数（228-233）、look（308-310）、height（341-344）、
size（352-354）、place（357-366）、yaw（368-370）；场景文件 scenes/skillet.json 里 piece / under / lift 节点（锅里的 pos [0, 1.01, 0]）。
位置是场景像素，原点在锅心（锅在场景里的 (8, 0, 8)），x 朝镜头右边、z 朝镜头（锅柄那一侧）；时间一律是秒。

一锅最多 16 件，画出来的上面最多 PIECES 块、下面再垫最多 PIECES 块（"一批 16 个只画 8 块"）。上面的块一熟，换成熟的样子的那一档
（look）只在 [0, 1) 里分 12 档、熟透是 100，-1 是还没画过：档变了才重画。
"""
import math

PIECES = 4               # 最多这么多块躺在上面，下面再垫同样多块（SkilletBehavior 41）
PILE = 0.6               # 垫了东西时，上面的块抬高这么多像素（43）
FLOOR = 1.05             # 锅底的高度（84）：油花、油星、蛋液落点都从它算
EDGE = 0.5               # 油在食物四周冒泡，离食物中心多远：边长的这么多倍（93）
NODE_Y = 1.01            # piece / under / lift 节点在锅里的高度（skillet.json）
BATCH = 16               # 一锅最多煎几件（SkilletCooking.BATCH）
LOOK_STEPS = 12          # 上面那一面的熟度分 12 档（308-310）
RAW_LOOK, DONE_LOOK = -1, 100
SEARED = 0xFFB8875C      # 生的那面煎着时最多染成这个色（45-46）；SEAR 是染多重。熟色用的是 KitchenLooks 里同值的那两个（FryingTint），这两个只留着对照
SEAR = 0.7


def counts(count):
    """锅里 count 件 -> (算多少件煎, 上面画几块, 下面垫几块)（228-233）。空锅是 (0, 0, 0)。"""
    if count <= 0:
        return 0, 0, 0
    batch = max(1, min(count, BATCH))
    return batch, min(batch, PIECES), min(max(0, batch - PIECES), PIECES)


def size(pieces):
    """一块画多大（像素，352-354）：一块 9，两块 7.5，再多 6.5。"""
    return 9.0 if pieces <= 1 else (7.5 if pieces == 2 else 6.5)


_THREE = ((2.8, 2.2), (-2.8, 2.0), (0.2, -2.8))
_FOUR = ((2.9, 2.9), (-2.9, 2.7), (2.7, -2.9), (-2.8, -2.8))


def place(index, count):
    """第 index 块在 count 块时躺在哪，离锅心 (x, z) 像素（357-366，"像手摆的那样撒开"）。
    还在落、在翻的那块碰上锅里变多了，下标夹到最后一个位置。"""
    index = max(0, min(index, min(count, PIECES) - 1))
    if count == 1:
        return (0.0, 0.0)
    if count == 2:
        return (2.6, 0.4) if index == 0 else (-2.6, -0.4)
    if count == 3:
        return _THREE[index]
    return _FOUR[index]


def yaw(index, under):
    """这块在锅里转了多少度（368-370）：按下标定死，每次画都一样；垫在下面的再转 35 度。"""
    return ((index * 7919) % 41 - 20) * 1.2 + (35.0 if under else 0.0)


def look(up):
    """上面那一面熟到哪一档（308-310）：没画过 -1，熟透 100，否则 floor(up * 12)。"""
    if up < 0.0:
        return RAW_LOOK
    return DONE_LOOK if up >= 1.0 else int(math.floor(up * LOOK_STEPS))


def height(under, unders, flat=True):
    """一块躺多高（341-344）：垫了东西时上面的抬 PILE；方块一类的东西没有图标、竖在中心上，再高 4（掉落物都是平躺的，flat 总是真）。"""
    lift = PILE if (not under and unders > 0) else 0.0
    return lift + (0.0 if flat else 4.0)

