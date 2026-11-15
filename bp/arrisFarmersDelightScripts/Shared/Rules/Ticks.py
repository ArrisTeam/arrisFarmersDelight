# -*- coding: utf-8 -*-
"""Ticks - 方块实体 tick 错峰与概率（双端，纯规则）"""
import random


def posHash(pos):
    """整数坐标哈希。用作 tick 错峰的盐，让不同位置的同种方块落在不同的 tick 上。"""
    x, y, z = int(pos[0]), int(pos[1]), int(pos[2])
    return (x * 73856093 ^ y * 19349663 ^ z * 83492791) & 0x7FFFFFFF


def isStaggeredTick(tickCount, pos, stride):
    """每 stride 个 tick 轮到这个位置一次（不同位置的相位不同）。"""
    return (tickCount + posHash(pos)) % stride == 0


def probability(percent):
    """以 percent% 的概率返回 True。"""
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    return random.randint(1, 100) <= percent
