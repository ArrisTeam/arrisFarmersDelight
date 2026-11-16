# -*- coding: utf-8 -*-
"""Ticks - 方块实体 tick 的节拍与概率（双端，纯规则）

方块实体 tick 每个游戏刻都来一次，煎锅 / 炉灶 / 厨锅只需要每隔一段时间处理一次。节拍用真实时间（调用方传
time.time()），不用世界时间：世界时间会被 /time set 改、被 doDaylightCycle false 冻住——旧版按世界时间错峰，
冻住时大部分位置永远轮不到（不煎不煮），个别位置每刻都处理（20 倍速）。
"""
import random


def posHash(pos):
    """整数坐标哈希：给不同位置的同种方块错开相位。"""
    x, y, z = int(pos[0]), int(pos[1]), int(pos[2])
    return (x * 73856093 ^ y * 19349663 ^ z * 83492791) & 0x7FFFFFFF


class Pacer(object):
    """每个 key（一般是 (维度, 坐标)）每 period 秒放行一次；第一次见到时按坐标错开相位，不放行。
    落后超过一个周期（服务器卡顿、区块卸载后重新加载）只补一次，不连发。"""

    def __init__(self, period):
        self.period = float(period)
        self._next = {}

    def due(self, key, now):
        nextTime = self._next.get(key)
        if nextTime is None:
            phase = (posHash(key[-1]) % 1000) / 1000.0 * self.period
            self._next[key] = now + phase
            return False
        if now < nextTime:
            return False
        self._next[key] = nextTime + self.period if now - nextTime < self.period else now + self.period
        return True

    def forget(self, key):
        """方块没了：丢掉它的节拍。"""
        self._next.pop(key, None)

    def __len__(self):
        return len(self._next)


def probability(percent):
    """以 percent% 的概率返回 True。"""
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    return random.randint(1, 100) <= percent
