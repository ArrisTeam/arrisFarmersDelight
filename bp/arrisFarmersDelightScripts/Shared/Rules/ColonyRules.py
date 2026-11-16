# -*- coding: utf-8 -*-
"""ColonyRules - 蘑菇菌落：Bedrock 的 8 个 arris:growth 对应 JE 的 4 个年龄（双端，纯规则）

JE 的 MushroomColonyBlock 有 4 个年龄（0-3，贴图 stage0-3），只在沃土上长：每次随机刻 25%（random.nextInt(4) == 0）；
年龄 0-3 掉 2/3/4/5 个蘑菇，剪刀剪满龄的掉菌落本身（loot_tables/blocks/*_mushroom_colony.json）。
Bedrock 方块的 arris:growth 有 0-7，贴图、掉落（netease_blocks/*_mushroom_colony.json 里每个 growth 一个排列）是：
    growth 0-1  单个蘑菇的贴图（刚放下的，JE 没有）   掉 1 个蘑菇   arris_*_mushroom_colony_sprout
    growth 2-3  colony_stage0   JE 年龄 0   掉 2 个   colony0
    growth 4-5  colony_stage1   JE 年龄 1   掉 3 个   colony1
    growth 6    colony_stage2   JE 年龄 2   掉 4 个   colony2
    growth 7    colony_stage3   JE 年龄 3   掉 5 个（剪刀剪掉菌落本身）  colony3
外观是单个蘑菇的 growth 0-1 掉 1 个（和打掉一株蘑菇一样），生长上算年龄 0。每个年龄取一个"标准状态"
GROWTH_OF_AGE（正好是 JE 那 4 张贴图），自然生长与骨粉都在标准状态之间跳；growth 1、3、5 只在旧存档里出现，
growth 0-1 在第一次随机刻（脚下是沃土时）换成年龄 0 的外观。
"""
from .GrowthRates import COLONY_CHANCE, bedrockChance

COLONY_BLOCKS = ("arris:brown_mushroom_colony", "arris:red_mushroom_colony")
GROWTH_STATE = "arris:growth"
MAX_AGE = 3
AGE_OF_GROWTH = (0, 0, 0, 0, 1, 1, 2, 3)
GROWTH_OF_AGE = (2, 4, 6, 7)
SPROUT_GROWTH = (0, 1)
# 只有这些地面上的菌落才会长（tags/blocks/mushroom_colony_growable_on：只有沃土）
GROWABLE_ON = ("arris:rich_soil",)
# 放在沃土上的蘑菇在随机刻变成哪种菌落（RichSoilBlock.convertMushroomToColony）
MUSHROOM_TO_COLONY = {
    "minecraft:brown_mushroom": "arris:brown_mushroom_colony",
    "minecraft:red_mushroom": "arris:red_mushroom_colony",
}
# 战利品表要掉的蘑菇数（JE 年龄 0-3 → 2/3/4/5；外观是单个蘑菇的 growth 0-1 掉 1 个）。表在 JSON 里，这里给测试对照
MUSHROOMS_OF_AGE = (2, 3, 4, 5)
SPROUT_MUSHROOMS = 1


def ageOfGrowth(growth):
    """JE 年龄；不认识的 growth（比 7 大）按最老的算。"""
    if growth < 0:
        return 0
    if growth >= len(AGE_OF_GROWTH):
        return MAX_AGE
    return AGE_OF_GROWTH[growth]


def mushroomsOfGrowth(growth):
    return SPROUT_MUSHROOMS if growth in SPROUT_GROWTH else MUSHROOMS_OF_AGE[ageOfGrowth(growth)]


def tickGrowth(growth, rnd):
    """一次随机刻（脚下是沃土）后的 arris:growth；没有变化返回 None。"""
    age = ageOfGrowth(growth)
    settled = GROWTH_OF_AGE[age] if growth in SPROUT_GROWTH else growth
    if age < MAX_AGE and rnd.random() < bedrockChance(COLONY_CHANCE):
        return GROWTH_OF_AGE[age + 1]
    return settled if settled != growth else None


def boneMealGrowth(growth, rnd):
    """骨粉：(是不是合法目标, 新的 arris:growth)。MushroomColonyBlock：没长满才算，年龄 +1 或 +2。"""
    age = ageOfGrowth(growth)
    if age >= MAX_AGE:
        return False, None
    newAge = min(MAX_AGE, age + rnd.randint(1, 2))
    return True, GROWTH_OF_AGE[newAge]
