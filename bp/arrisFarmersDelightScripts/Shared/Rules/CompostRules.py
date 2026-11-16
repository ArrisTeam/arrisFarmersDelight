# -*- coding: utf-8 -*-
"""CompostRules - 有机肥堆沤成沃土的概率（双端，纯规则）

JE 的 OrganicCompostBlock 有 composting 0-7 共 8 档，每次随机刻按下面的概率"前进一档"，第 8 次前进就变成沃土
（贴图 4 张，每两档一张）。Bedrock 的有机肥是 4 个方块（stage0-3），所以每个方块要 JE 的 2 次前进：
    chance = 0.02 × 周围 3×3×3（含自己）里堆肥催化剂的个数
           + 0.1（3×3×3 里有一格的上方天空光 > 12，露天）或 0.05（被盖住）
           + 0.1（3×3×3 里有水）
再按 GrowthRates 换成 Bedrock 的每刻概率。露天、旁边没有别的催化剂、没有水时一格有机肥自己算一个催化剂，
chance = 0.12，从放下到变成沃土大约 75 分钟；旁边有水是 0.22，约 41 分钟。
"""
from .GrowthRates import bedrockChance

COMPOST_STAGES = ("arris:organic_compost_stage0", "arris:organic_compost_stage1", "arris:organic_compost_stage2",
                  "arris:organic_compost_stage3")
RICH_SOIL = "arris:rich_soil"
ACTIVATOR_CHANCE = 0.02
OPEN_SKY_CHANCE = 0.1
COVERED_CHANCE = 0.05
WATER_CHANCE = 0.1
LEVELS_PER_BLOCK = 2            # JE 的 8 档 / Bedrock 的 4 个方块


def jeChance(activators, skyOpen, hasWater):
    """JE 一次随机刻有机肥前进一档的概率。"""
    chance = ACTIVATOR_CHANCE * activators
    chance += OPEN_SKY_CHANCE if skyOpen else COVERED_CHANCE
    if hasWater:
        chance += WATER_CHANCE
    return chance


def stageChance(activators, skyOpen, hasWater):
    """Bedrock 一次随机刻有机肥变成下一个方块的概率。"""
    return bedrockChance(min(1.0, jeChance(activators, skyOpen, hasWater)), LEVELS_PER_BLOCK)


def nextBlock(name):
    """下一个方块：stage3 之后是沃土；不是有机肥返回 None。"""
    if name not in COMPOST_STAGES:
        return None
    index = COMPOST_STAGES.index(name)
    return COMPOST_STAGES[index + 1] if index + 1 < len(COMPOST_STAGES) else RICH_SOIL

