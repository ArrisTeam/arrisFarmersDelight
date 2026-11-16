# -*- coding: utf-8 -*-
"""farmkit - 种植规则测试的公共小工具（不是测试本身，跑器只收 test_*.py）

FakeWorld   用字典摆方块的假世界，实现 CropTick / BoneMealRules / WildSpread 要的 nameAt / moistureAt / growthAt，
            并能把规则返回的修改（FarmEdits）落到字典里
ScriptRng   按剧本回答 random() / randint() 的随机数：测边界和每个分支，不靠碰运气
"""
from __future__ import print_function

import fdtest

FarmEdits = fdtest.load("Shared.Rules.FarmEdits")

AIR = "minecraft:air"


class FakeWorld(object):
    def __init__(self):
        self.blocks = {}
        self.moisture = {}
        self.growth = {}
        self.drops = []
        self.tops = {}

    def put(self, pos, name, moisture=None, growth=None):
        self.blocks[tuple(pos)] = name
        if moisture is not None:
            self.moisture[tuple(pos)] = moisture
        if growth is not None:
            self.growth[tuple(pos)] = growth
        return self

    def fill(self, name, low, high, moisture=None):
        for x in range(low[0], high[0] + 1):
            for y in range(low[1], high[1] + 1):
                for z in range(low[2], high[2] + 1):
                    self.put((x, y, z), name, moisture)
        return self

    def nameAt(self, pos):
        return self.blocks.get(tuple(pos), AIR)

    def moistureAt(self, pos):
        return self.moisture.get(tuple(pos), 0)

    def growthAt(self, pos):
        return self.growth.get(tuple(pos), 0)

    def apply(self, edits):
        for edit in edits:
            if edit[0] == FarmEdits.BLOCK:
                self.blocks[edit[1]] = edit[2]
            elif edit[0] == FarmEdits.STATES:
                self.growth[edit[1]] = edit[2].get("arris:growth", self.growth.get(edit[1], 0))
            elif edit[0] == FarmEdits.DROP:
                self.drops.append(edit[1:])
        return self


class ScriptRng(object):
    """random() 依次取 randoms 里的值（用完重复最后一个），randint(a, b) 依次取 ints 里的值（夹进 [a, b]）；
    ints 用完以后取 a（最小值）。"""

    def __init__(self, randoms=(0.0,), ints=()):
        self.randoms = list(randoms)
        self.ints = list(ints)
        self.calls = []

    def random(self):
        self.calls.append("random")
        if len(self.randoms) > 1:
            return self.randoms.pop(0)
        return self.randoms[0]

    def randint(self, low, high):
        self.calls.append(("randint", low, high))
        value = self.ints.pop(0) if self.ints else low
        return max(low, min(high, value))


def plot(world, center, name="minecraft:farmland", moisture=7, radius=1):
    """在 center 脚下（y - 1）铺一块 (2r+1)² 的耕地。"""
    x, y, z = center
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            world.put((x + dx, y - 1, z + dz), name, moisture if name == "minecraft:farmland" else None)
    return world
