# -*- coding: utf-8 -*-
"""GrowthRates - 作物生长的概率：JE 的公式，以及换成 Bedrock 随机刻的那一步（双端，纯规则）

数据来自 JE（Forge 1.20.1，Farmer's Delight 1.3.4）：
- CropBlock.randomTick：光照够了以后，``random.nextInt((int)(25.0F / speed) + 1) == 0`` 才长一级；
  speed 是脚下 3×3 耕地的和（见 growthSpeed）。卷心菜、洋葱、小麦、胡萝卜、土豆、甜菜根和稻穗都走这个；
  甜菜根与火把花苗另外先过一道 ``nextInt(3) != 0``（即再乘 2/3）。
- 稻苗 RiceBlock：speed 固定 10，番茄 TomatoBlock / HangingTomatoBlock：speed 固定 5。
- 蘑菇菌落 25%，沃土每次随机刻 20% 催熟上方作物（Configuration.RICH_SOIL_BOOST_CHANCE 缺省 0.2）。

JE 的随机刻速度缺省是 3（每个 16×16×16 的区段每刻随机 3 个方块），Bedrock 缺省是 1。
同样的时间里 Bedrock 的方块只轮到 JE 的三分之一次随机刻，所以每次随机刻的概率要乘 3（封顶 1）。
这个换算只在 bedrockChance / bedrockChanceOf 里做，别处一律写 JE 的概率。
"""

JE_RANDOM_TICK_SPEED = 3.0
BEDROCK_RANDOM_TICK_SPEED = 1.0
TICK_RATIO = JE_RANDOM_TICK_SPEED / BEDROCK_RANDOM_TICK_SPEED

# 稻苗：chance = 10（RiceBlock.tick）；番茄：speed = 5（TomatoBlock.randomTick）
RICE_SPEED = 10.0
TOMATO_SPEED = 5.0
SLOW_CROP_FACTOR = 2.0 / 3.0          # 甜菜根、火把花苗：if (random.nextInt(3) != 0) super.randomTick(...)
COLONY_CHANCE = 0.25                  # MushroomColonyBlock.tick：random.nextInt(4) == 0
RICH_SOIL_BOOST_CHANCE = 0.2          # 沃土每次随机刻催熟上方作物的概率

# 光照下限（JE 的 getRawBrightness）：作物 9，稻苗 6
CROP_LIGHT = 9
RICE_LIGHT = 6


def vanillaChance(speed):
    """CropBlock.randomTick 里一次随机刻长一级的概率：1 / ((int)(25 / speed) + 1)。"""
    return 1.0 / (int(25.0 / speed) + 1)


RICE_CHANCE = vanillaChance(RICE_SPEED)        # 1/3
TOMATO_CHANCE = vanillaChance(TOMATO_SPEED)    # 1/6


def growthSpeed(centerSoil, ringSoil, rowEastWest, rowNorthSouth, diagonal):
    """CropBlock.getGrowthSpeed：脚下 3×3 每格给 0（不能种）/ 1（干耕地）/ 3（湿润耕地），周围 8 格再除以 4，
    加上基础的 1；同种作物东西和南北两个方向都挨着，或者斜着挨着，减半。

    centerSoil 是正下方那格，ringSoil 是另外 8 格；rowEastWest / rowNorthSouth / diagonal 是三个"挨着同种"的布尔。
    """
    speed = 1.0 + centerSoil
    for value in ringSoil:
        speed += value / 4.0
    if rowEastWest and rowNorthSouth:
        speed /= 2.0
    elif diagonal:
        speed /= 2.0
    return speed


def bedrockChanceOf(jeChances):
    """Bedrock 一级相当于 JE 的若干次转变（每次的概率不一定相同）时，每次随机刻长这一级的概率。

    JE 要等的随机刻数是各次 1/p 之和；Bedrock 的随机刻只有 JE 的 1/TICK_RATIO，所以等待的平均刻数
    是那个和除以 TICK_RATIO，概率取它的倒数，封顶 1（一次随机刻最多长一级）。
    """
    total = 0.0
    for chance in jeChances:
        if chance <= 0:
            return 0.0
        total += 1.0 / chance
    if total <= 0:
        return 0.0
    return min(1.0, TICK_RATIO / total)


def bedrockChance(jeChance, steps=1):
    """JE 一次转变的概率 → Bedrock 每次随机刻的概率；steps 是 Bedrock 这一级要 JE 连续转变几次
    （洋葱 8 个年龄只有 4 级方块，一级最多要 3 次）。"""
    return bedrockChanceOf([jeChance] * steps)
