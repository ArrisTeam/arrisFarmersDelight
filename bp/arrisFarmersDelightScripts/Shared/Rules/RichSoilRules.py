# -*- coding: utf-8 -*-
"""RichSoilRules - 沃土耕地的湿度、沃土催熟的概率与范围（双端，纯规则）

JE 的 RichSoilFarmlandBlock.randomTick：附近有水或正下雨，湿度补满到 7；否则每次随机刻 -1。
湿度 7（"完全湿润"）的每次随机刻，沃土和沃土耕地以 20% 的概率给上方的植物催熟一次
（RichSoilBlock.tryBoostingPlantsAboveAndBelow，Configuration.RICH_SOIL_BOOST_CHANCE 缺省 0.2；
unaffected_by_rich_soil 标签里的不算）。Bedrock 的沃土耕地只分干（湿度 0）和湿（湿度 7）两个方块：
湿的一块断水以后要连着 7 次不湿的随机刻才干，换成 Bedrock 每刻的概率就是 dryChance。
"""
from .GrowthRates import RICH_SOIL_BOOST_CHANCE, bedrockChance

WATER_RADIUS = 4                  # 水平 ±4，竖直 0 ~ +1（RichSoilFarmlandBlock.isNearWater）
MOISTURE_STEPS = 7                # 湿度 7 → 0 要这么多次不湿的随机刻


def hydrationCells(pos):
    """耕地 pos 周围算"有水"的格子：水平 ±WATER_RADIUS、竖直 0 与 +1。"""
    x, y, z = pos
    for dx in range(-WATER_RADIUS, WATER_RADIUS + 1):
        for dz in range(-WATER_RADIUS, WATER_RADIUS + 1):
            for dy in (0, 1):
                yield (x + dx, y + dy, z + dz)


def boostChance():
    """Bedrock 每次随机刻沃土催熟上方作物的概率。"""
    return bedrockChance(RICH_SOIL_BOOST_CHANCE)


def dryChance():
    """湿润的沃土耕地在没有水的情况下，Bedrock 每次随机刻变干的概率。"""
    return bedrockChance(1.0, MOISTURE_STEPS)
