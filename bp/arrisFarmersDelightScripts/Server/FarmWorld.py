# -*- coding: utf-8 -*-
"""FarmWorld - 种植规则的世界接口与修改落地（服务端）

Shared/Rules 里的 CropTick / BoneMealRules / WildSpread 只通过 nameAt / moistureAt / growthAt 读世界，
返回 FarmEdits 修改列表；这里把读接到引擎，并把修改写进世界。一个实例对应一个维度。
"""
from .Helpers.Engine import compFactory, levelId, System
from ..Shared.Rules import FarmEdits

FARMLAND_MOISTURE = "moisturized_amount"
WATER = ("minecraft:water", "minecraft:flowing_water")


class FarmWorld(object):
    def __init__(self, dimensionId):
        self.dimensionId = dimensionId

    # ---- 读 ----

    def nameAt(self, pos):
        info = compFactory.CreateBlockInfo(levelId).GetBlockNew(tuple(pos), self.dimensionId)
        return info["name"] if info else FarmEdits.AIR

    def statesAt(self, pos):
        return compFactory.CreateBlockState(levelId).GetBlockStates(tuple(pos), self.dimensionId) or {}

    def moistureAt(self, pos):
        return self.statesAt(pos).get(FARMLAND_MOISTURE, 0)

    def growthAt(self, pos):
        return self.statesAt(pos).get("arris:growth", 0)

    def hasWaterAt(self, pos):
        liquid = compFactory.CreateBlockInfo(levelId).GetLiquidBlock(tuple(pos), self.dimensionId)
        return bool(liquid) and liquid["name"] in WATER

    def topHeightAt(self, x, z):
        """这一列最高的非空气方块的高度（区块没加载返回 None）。"""
        return compFactory.CreateBlockInfo(levelId).GetTopBlockHeight((x, z), self.dimensionId)

    def rainingAt(self, pos):
        """pos 头顶正在下雨：主世界在下雨，并且这一列在 pos 上方一格以内没有更高的方块挡着
        （JE 的 isRainingAt(pos.above())；不看群系，沙漠和雪原也算）。"""
        if self.dimensionId != 0 or not compFactory.CreateWeather(levelId).IsRaining():
            return False
        top = self.topHeightAt(pos[0], pos[2])
        return top is None or top <= pos[1] + 1

    # ---- 写 ----

    def apply(self, edits):
        """把 FarmEdits 的修改依次写进世界（换方块不通知邻居，和作物生长一贯的写法一致）。"""
        for edit in edits:
            kind, pos = edit[0], edit[1]
            if kind == FarmEdits.BLOCK:
                compFactory.CreateBlockInfo(levelId).SetBlockNew(pos, {"name": edit[2]}, 0, self.dimensionId, False, False)
            elif kind == FarmEdits.STATES:
                states = self.statesAt(pos)
                states.update(edit[2])
                compFactory.CreateBlockState(levelId).SetBlockStates(pos, states, self.dimensionId)
            elif kind == FarmEdits.DROP:
                dropPos = (pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5)
                System.CreateEngineItemEntity({"itemName": edit[2], "count": edit[3], "auxValue": 0}, self.dimensionId, dropPos)
