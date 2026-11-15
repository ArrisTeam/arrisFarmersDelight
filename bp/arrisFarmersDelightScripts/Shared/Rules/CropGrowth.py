# -*- coding: utf-8 -*-
"""CropGrowth - 作物催熟的阶段表（双端，纯规则）

作物的每个阶段是一个单独的方块，名字以阶段数字结尾（如 arris:cabbages_stage3）。
骨粉一次长 2-3 级，湿润沃土耕地每次随机刻额外长 1 级，都不超过该作物的最大阶段。
"""

# 方块名前缀（去掉末尾阶段数字）→ 最大阶段
CROP_MAX_STAGE = {
    "arris:cabbages_stage": 7,
    "arris:budding_tomatoes_stage": 6,
    "arris:tomatoes_vine_stage": 3,
    "arris:onions_stage": 3,
    "arris:rich_soil_wheat": 7,
    "arris:rich_soil_beetroot": 3,
    "arris:rich_soil_carrots": 3,
    "arris:rich_soil_potatoes": 3,
    "arris:rice_stage": 3,
    "arris:rice_upper_crop_stage": 3,
    "arris:rich_soil_torchflower": 2,
}


def splitStage(blockName):
    """"arris:onions_stage2" → ("arris:onions_stage", 2)；不是可催熟作物返回 (None, None)。"""
    prefix, stageText = blockName[:-1], blockName[-1:]
    if prefix not in CROP_MAX_STAGE or not stageText.isdigit():
        return None, None
    return prefix, int(stageText)


def grownName(blockName, steps):
    """长 steps 级之后的方块名；不可催熟或已经成熟返回 None。"""
    prefix, stage = splitStage(blockName)
    if prefix is None:
        return None
    maxStage = CROP_MAX_STAGE[prefix]
    if stage >= maxStage:
        return None
    return prefix + str(min(maxStage, stage + steps))
