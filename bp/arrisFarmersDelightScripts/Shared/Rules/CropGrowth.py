# -*- coding: utf-8 -*-
"""CropGrowth - 作物的阶段表：每一级方块对应 JE 的哪几个年龄、怎么长（双端，纯规则）

作物的每个阶段是一个单独的方块，名字以阶段数字结尾（如 arris:cabbages_stage3）。
JE 的作物有 8 个年龄（0-7），Bedrock 这边有的每个年龄一个方块（卷心菜），有的几个年龄合成一个方块（洋葱 4 个）。
FAMILIES 把每一级方块覆盖的 JE 年龄记在 starts 里：第 s 级从年龄 starts[s] 起，到下一级的起点之前为止。
生长的时间、骨粉的增量都按 JE 的年龄算，再换回方块（见 GrowthRates、CropTick、BoneMealRules）。

rates[a] 是 JE 年龄 a → a+1 那次转变每次随机刻的概率（JE 的，没换算过）：
    浮点数    固定概率（稻苗、番茄）
    "soil"    CropBlock 公式，由脚下 3×3 的耕地算出（见 CropTick.cropSpeed）
    ("soil", f)  同上再乘 f（甜菜根、火把花苗）
"""
from .GrowthRates import CROP_LIGHT, RICE_LIGHT, RICE_CHANCE, TOMATO_CHANCE, SLOW_CROP_FACTOR

SOIL = "soil"
_FAST8 = (0, 1, 2, 3, 4, 5, 6, 7)
_EIGHT_IN_FOUR = (0, 2, 4, 7)          # 洋葱 / 胡萝卜 / 土豆：JE blockstate 里 8 个年龄合成 4 个模型
_SLOW_SOIL = (SOIL, SLOW_CROP_FACTOR)

# 方块名前缀（去掉末尾阶段数字）→ 怎么长。kind：crop 普通作物，tomatoBase 番茄地上的一株（budding 阶段接番茄阶段），
# tomatoVine 绳上的番茄，rice 稻苗，panicle 稻穗。bone：骨粉怎么算（BoneMealRules）。
FAMILIES = {
    "arris:cabbages_stage": {"starts": _FAST8, "kind": "crop", "bone": "age", "light": CROP_LIGHT,
                             "rates": (SOIL,) * 7},
    "arris:onions_stage": {"starts": _EIGHT_IN_FOUR, "kind": "crop", "bone": "age", "light": CROP_LIGHT,
                           "rates": (SOIL,) * 7},
    # 年龄轴把 JE 的 budding 年龄 0-3 接上番茄年龄 0-3：0-2 是 budding，3（成长到头的 budding）与 4 之间的转变
    # 合进第 2 级，所以第 3 级起是番茄 0-3 级。前 4 次转变走 CropBlock 公式，后 3 次是番茄的 1/6
    "arris:budding_tomatoes_stage": {"starts": (0, 1, 2, 4, 5, 6, 7), "kind": "tomatoBase", "bone": "tomatoBase",
                                     "light": CROP_LIGHT, "rates": (SOIL,) * 4 + (TOMATO_CHANCE,) * 3,
                                     "rowStages": (0, 1, 2), "climbFrom": 3},
    "arris:tomatoes_vine_stage": {"starts": (0, 1, 2, 3), "kind": "tomatoVine", "bone": "tomatoVine",
                                  "light": CROP_LIGHT, "rates": (TOMATO_CHANCE,) * 3, "climbFrom": 0},
    "arris:rich_soil_wheat": {"starts": _FAST8, "kind": "crop", "bone": "age", "light": CROP_LIGHT,
                              "rates": (SOIL,) * 7},
    "arris:rich_soil_beetroot": {"starts": (0, 1, 2, 3), "kind": "crop", "bone": "slowAge", "light": CROP_LIGHT,
                                 "rates": (_SLOW_SOIL,) * 3},
    "arris:rich_soil_carrots": {"starts": _EIGHT_IN_FOUR, "kind": "crop", "bone": "age", "light": CROP_LIGHT,
                                "rates": (SOIL,) * 7},
    "arris:rich_soil_potatoes": {"starts": _EIGHT_IN_FOUR, "kind": "crop", "bone": "age", "light": CROP_LIGHT,
                                 "rates": (SOIL,) * 7},
    # 火把花苗只有 2 个年龄，长到第 3 级就是开花的火把花
    "arris:rich_soil_torchflower": {"starts": (0, 1, 2), "kind": "crop", "bone": "oneAge", "light": CROP_LIGHT,
                                    "rates": (_SLOW_SOIL,) * 2},
    "arris:rice_stage": {"starts": (0, 1, 2, 3), "kind": "rice", "bone": "rice", "light": RICE_LIGHT,
                         "rates": (RICE_CHANCE,) * 3},
    "arris:rice_upper_crop_stage": {"starts": (0, 1, 2, 3), "kind": "panicle", "bone": "panicle", "light": CROP_LIGHT,
                                    "rates": (SOIL,) * 3, "speed": "rice"},
}

# 方块名前缀 → 最大阶段（历史接口：旧催熟表就是这张）
CROP_MAX_STAGE = dict((prefix, len(spec["starts"]) - 1) for prefix, spec in FAMILIES.items())


def splitStage(blockName):
    """"arris:onions_stage2" → ("arris:onions_stage", 2)；不是认识的作物返回 (None, None)。"""
    prefix, stageText = blockName[:-1], blockName[-1:]
    if prefix not in FAMILIES or not stageText.isdigit():
        return None, None
    stage = int(stageText)
    if stage > CROP_MAX_STAGE[prefix]:
        return None, None
    return prefix, stage


def stageName(prefix, stage):
    return prefix + str(stage)


def lastStage(prefix):
    return CROP_MAX_STAGE[prefix]


def maxAge(prefix):
    """JE 年龄轴上的最大年龄（最后一级的起点）。"""
    return FAMILIES[prefix]["starts"][-1]


def ageRange(prefix, stage):
    """第 stage 级方块覆盖的 JE 年龄，闭区间 (最小, 最大)；最后一级只有一个年龄。"""
    starts = FAMILIES[prefix]["starts"]
    first = starts[stage]
    if stage + 1 < len(starts):
        return first, starts[stage + 1] - 1
    return first, first


def stageOfAge(prefix, age):
    """JE 年龄 → 方块级数（超过最大年龄按最后一级）。"""
    starts = FAMILIES[prefix]["starts"]
    stage = 0
    for index, start in enumerate(starts):
        if age >= start:
            stage = index
    return stage


def isFamilyBlock(blockName, prefix, stages=None):
    """blockName 是不是 prefix 这一族的方块（stages 给了就限定在这几级）。"""
    found, stage = splitStage(blockName)
    return found == prefix and (stages is None or stage in stages)


def grownName(blockName, steps):
    """长 steps 级之后的方块名；不可催熟或已经成熟返回 None。（旧骨粉的写法，服务端接上新规则后删掉）"""
    prefix, stage = splitStage(blockName)
    if prefix is None or stage >= lastStage(prefix):
        return None
    return stageName(prefix, min(lastStage(prefix), stage + steps))
