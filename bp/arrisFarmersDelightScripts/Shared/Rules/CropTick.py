# -*- coding: utf-8 -*-
"""CropTick - 作物随机刻的生长规则：脚下耕地的公式、长一级的概率、稻苗长穗、番茄沿绳子往上爬（双端，纯规则）

world 是个只读接口（引擎里是 Server/FarmWorld.py，测试里是假世界）：
    nameAt(pos)      方块名（没加载按空气）
    moistureAt(pos)  原版耕地 minecraft:farmland 的湿润度 0-7
概率的来龙去脉见 GrowthRates、阶段表见 CropGrowth；randomTick 返回要做的修改（FarmEdits）。
"""
from . import FarmEdits
from .CropGrowth import FAMILIES, SOIL, splitStage, stageName, lastStage, isFamilyBlock
from .GrowthRates import growthSpeed, vanillaChance, bedrockChance, bedrockChanceOf, RICE_CHANCE

FARMLAND = "minecraft:farmland"
RICH_FARMLAND = "arris:rich_soil_farmland"
RICH_FARMLAND_MOIST = "arris:rich_soil_farmland_moist"
ROPE = "arris:rope"
RICE_PREFIX = "arris:rice_stage"
RICE_SUPPORTING = "arris:rice_supporting"
PANICLE_FIRST = "arris:rice_upper_crop_stage0"
VINE_PREFIX = "arris:tomatoes_vine_stage"
VINE_FIRST = VINE_PREFIX + "0"
# 地上那株往上最多挂 3 节藤：TomatoBlock.climbRopeAbove 的 vineHeight（这节藤下面连着几节藤再加 1，地上那株算 1）要 < 3 才再长
MAX_VINES = 3


def isRiceLower(name):
    return name == RICE_SUPPORTING or isFamilyBlock(name, RICE_PREFIX)


def isVine(name):
    return isFamilyBlock(name, VINE_PREFIX)


def _soilValue(world, mode, cell):
    name = world.nameAt(cell)
    if mode == "rice":
        # 稻穗只认脚下的稻苗（RicePaniclesBlock.mayPlaceOn），稻苗不算"肥沃"
        return 1.0 if isRiceLower(name) else 0.0
    if name == FARMLAND:
        return 3.0 if world.moistureAt(cell) > 0 else 1.0
    if name == RICH_FARMLAND_MOIST:
        return 3.0
    if name == RICH_FARMLAND:
        return 1.0
    return 0.0


def cropSpeed(world, prefix, pos):
    """CropBlock.getGrowthSpeed：pos 是作物的位置，读脚下 3×3 和四边四角有没有同种作物。"""
    spec = FAMILIES[prefix]
    mode = spec.get("speed", "farmland")
    rowStages = spec.get("rowStages")
    x, y, z = pos
    center = 0.0
    ring = []
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            value = _soilValue(world, mode, (x + dx, y - 1, z + dz))
            if dx == 0 and dz == 0:
                center = value
            else:
                ring.append(value)

    def same(dx, dz):
        return isFamilyBlock(world.nameAt((x + dx, y, z + dz)), prefix, rowStages)

    eastWest = same(-1, 0) or same(1, 0)
    northSouth = same(0, -1) or same(0, 1)
    diagonal = same(-1, -1) or same(1, -1) or same(1, 1) or same(-1, 1)
    return growthSpeed(center, ring, eastWest, northSouth, diagonal)


def _usesSoil(rate):
    return rate == SOIL or isinstance(rate, tuple)


def _jeRate(rate, vanilla):
    if rate == SOIL:
        return vanilla
    if isinstance(rate, tuple):
        return vanilla * rate[1]
    return rate


def growChance(world, prefix, stage, pos):
    """这一级方块每次随机刻（已经光照够了）长到下一级的概率，Bedrock 的；已经是最后一级返回 0。"""
    spec = FAMILIES[prefix]
    starts = spec["starts"]
    if stage + 1 >= len(starts):
        return 0.0
    rates = spec["rates"][starts[stage]:starts[stage + 1]]
    vanilla = None
    if any(_usesSoil(rate) for rate in rates):
        vanilla = vanillaChance(cropSpeed(world, prefix, pos))
    return bedrockChanceOf([_jeRate(rate, vanilla) for rate in rates])


def climbEdit(world, pos, isVineBlock):
    """TomatoBlock.climbRopeAbove：上面是绳子就在绳子位置长一节藤。pos 是地上那株（isVineBlock 假）或一节藤（真）。"""
    top = FarmEdits.above(pos)
    if world.nameAt(top) != ROPE:
        return None
    hanging = 0
    if isVineBlock:
        while isVine(world.nameAt(FarmEdits.below(pos, hanging + 1))):
            hanging += 1
    if hanging + 1 < MAX_VINES:
        return FarmEdits.block(top, VINE_FIRST)
    return None


def _riceHead(world, pos, rnd):
    """稻苗长到头以后每次随机刻有机会长出稻穗：上面是空气时下半变成 rice_supporting。"""
    if world.nameAt(FarmEdits.above(pos)) != FarmEdits.AIR:
        return []
    if rnd.random() >= bedrockChance(RICE_CHANCE):
        return []
    return [FarmEdits.block(pos, RICE_SUPPORTING), FarmEdits.block(FarmEdits.above(pos), PANICLE_FIRST)]


def randomTick(world, blockName, pos, light, rnd):
    """一次随机刻：返回要做的修改。不认识的方块、光照不够、已经长到头的什么都不做。"""
    prefix, stage = splitStage(blockName)
    if prefix is None:
        return []
    spec = FAMILIES[prefix]
    if light < spec["light"]:
        return []
    if spec["kind"] == "rice" and stage == lastStage(prefix):
        return _riceHead(world, pos, rnd)
    edits = []
    chance = growChance(world, prefix, stage, pos)
    if chance > 0 and rnd.random() < chance:
        edits.append(FarmEdits.block(pos, stageName(prefix, stage + 1)))
    climbFrom = spec.get("climbFrom")
    if climbFrom is not None and stage >= climbFrom:
        climb = climbEdit(world, pos, spec["kind"] == "tomatoVine")
        if climb is not None:
            edits.append(climb)
    return edits
