# -*- coding: utf-8 -*-
"""RopeReel - 卷绳子：从被点的绳子往下找整根绳子最下面的一节（双端，纯规则）

JE RopeBlock.use（FD 1.3.4）：配置 enableRopeReeling（缺省开）、玩家潜行、手里是空的、能建造（abilities.mayBuild）时，
从被点的绳子往下数，一路都是绳子，**拆掉最下面那一节**（level.destroyBlock(pos, false)：不掉落），
同时给玩家背包放一根绳子（创造模式不给；背包放不下就什么都不做）。
"""

# 保险：一根绳子再长也不会超过世界高度
MAX_ROPES = 512


def lowestRope(pos, isRope, limit=MAX_ROPES):
    """pos 是被点的那节绳子；isRope(坐标) 说某一格是不是绳子。返回这根绳子最下面一节的坐标。"""
    x, y, z = pos
    low = y
    while limit > 0 and isRope((x, low - 1, z)):
        low -= 1
        limit -= 1
    return (x, low, z)
