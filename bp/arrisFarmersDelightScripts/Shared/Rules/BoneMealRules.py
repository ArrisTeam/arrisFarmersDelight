# -*- coding: utf-8 -*-
"""BoneMealRules - 骨粉对本模组植物的效果，照 JE 的 BonemealableBlock 实现（双端，纯规则）

boneMeal(world, name, pos, rnd) → (valid, edits)
    valid  JE 的 isValidBonemealTarget：为真骨粉就用掉（isBonemealSuccess 没过也一样）；沃土的"催熟"同样走这里
    edits  要做的修改（FarmEdits），读的是修改前的世界
world 接口：nameAt(pos)、growthAt(pos)（蘑菇菌落的 arris:growth）；rnd 要有 randint / random。

作物的增量（CropBlock.getBonemealAgeIncrease 是 nextInt(2, 5)）按 JE 年龄算，再按 CropGrowth.FAMILIES 换回 Bedrock 的方块：
    卷心菜 / 洋葱 / 小麦 / 胡萝卜 / 土豆   +2~5 个年龄；甜菜根、稻穗  nextInt(2, 5) / 3；火把花苗  +1
    budding 番茄    年龄轴 0-7（budding 0-3 接番茄 0-3）+1~4；地上和绳上的番茄  nextInt(2, 5) / 2，长不下就催上面的藤
    稻苗            年龄 +1~4，超过 3 就催上面的稻穗，没有稻穗就长出来
"""
from . import FarmEdits
from .ColonyRules import COLONY_BLOCKS, GROWTH_STATE, boneMealGrowth
from .CropGrowth import FAMILIES, maxAge, ageRange, stageOfAge, stageName, lastStage, splitStage
from .CropTick import ROPE, VINE_PREFIX, climbEdit, isVine
from .WildSpread import WILD_CROPS, WILD_RICE, SANDY_SHRUB, wildBoneMeal

BASE_PREFIX = "arris:budding_tomatoes_stage"
BASE_FIRST_TOMATO_STAGE = 3          # budding_tomatoes_stage3 起是番茄年龄 0
TOMATO_MAX_AGE = 3
RICE_PREFIX = "arris:rice_stage"
RICE_SUPPORTING = "arris:rice_supporting"
PANICLE_PREFIX = "arris:rice_upper_crop_stage"
CLIMB_AFTER_GROWTH = 0.3             # TomatoBlock.performBonemeal：长了以后还有 30% 顺手往绳上爬


def _inc(kind, rnd):
    if kind == "slowAge" or kind == "panicle":
        return rnd.randint(2, 5) // 3
    if kind == "oneAge":
        return 1
    return rnd.randint(2, 5)


def _randomAge(prefix, stage, rnd):
    low, high = ageRange(prefix, stage)
    return rnd.randint(low, high) if high > low else low


def _ageCrop(prefix, stage, pos, kind, rnd):
    if stage >= lastStage(prefix):
        return False, []
    age = _randomAge(prefix, stage, rnd)
    newStage = stageOfAge(prefix, min(maxAge(prefix), age + _inc(kind, rnd)))
    return True, [FarmEdits.block(pos, stageName(prefix, newStage))]


# ---------------- 番茄 ----------------

def _tomatoAge(name):
    prefix, stage = splitStage(name)
    return stage if prefix == VINE_PREFIX else stage - BASE_FIRST_TOMATO_STAGE


def _tomatoName(onVine, age):
    return VINE_PREFIX + str(age) if onVine else BASE_PREFIX + str(BASE_FIRST_TOMATO_STAGE + age)


def isTomatoTarget(world, pos, name):
    """TomatoBlock.isValidBonemealTarget：没熟都行；熟了要上面两格以内有绳子或没熟的藤。"""
    if _tomatoAge(name) < TOMATO_MAX_AGE:
        return True
    for height in (1, 2):
        upName = world.nameAt(FarmEdits.above(pos, height))
        if upName == ROPE:
            return True
        if not isVine(upName):
            return False
        if _tomatoAge(upName) < TOMATO_MAX_AGE:
            return True
    return False


def _tomatoGrow(world, pos, name, rnd, edits):
    """TomatoBlock.performBonemeal（地上的和绳上的同一段逻辑）。"""
    onVine = isVine(name)
    newAge = _tomatoAge(name) + rnd.randint(2, 5) // 2
    if newAge <= TOMATO_MAX_AGE:
        edits.append(FarmEdits.block(pos, _tomatoName(onVine, newAge)))
        if rnd.random() < CLIMB_AFTER_GROWTH:
            _addClimb(world, pos, onVine, edits)
        return
    upPos = FarmEdits.above(pos)
    upName = world.nameAt(upPos)
    if upName == ROPE:
        _addClimb(world, pos, onVine, edits)
    elif isVine(upName) and isTomatoTarget(world, upPos, upName):
        _tomatoGrow(world, upPos, upName, rnd, edits)


def _addClimb(world, pos, onVine, edits):
    climb = climbEdit(world, pos, onVine)
    if climb is not None:
        edits.append(climb)


def _tomato(world, name, pos, rnd):
    prefix, stage = splitStage(name)
    if prefix == BASE_PREFIX and stage < BASE_FIRST_TOMATO_STAGE:
        # BuddingTomatoBlock：年龄轴 +1~4，超过 budding 的最大年龄就变成地上的番茄
        age = _randomAge(prefix, stage, rnd)
        newStage = stageOfAge(prefix, min(maxAge(prefix), age + rnd.randint(1, 4)))
        return True, [FarmEdits.block(pos, stageName(prefix, newStage))]
    if not isTomatoTarget(world, pos, name):
        return False, []
    edits = []
    _tomatoGrow(world, pos, name, rnd, edits)
    return True, edits


# ---------------- 稻米 ----------------

def _panicleRipe(name):
    prefix, stage = splitStage(name)
    return prefix == PANICLE_PREFIX and stage >= lastStage(prefix)


def _panicleEdits(name, pos, rnd):
    """RicePaniclesBlock（CropBlock）：+ nextInt(2, 5) / 3，也就是 0 或 1 个年龄。"""
    prefix, stage = splitStage(name)
    newStage = min(lastStage(prefix), stage + _inc("panicle", rnd))
    return [FarmEdits.block(pos, stageName(prefix, newStage))]


def _rice(world, name, pos, rnd):
    """RiceBlock：上面的稻穗已经熟了就不是合法目标；年龄 +1~4，超出的部分去催稻穗，还没有稻穗就长一个出来。"""
    upPos = FarmEdits.above(pos)
    upName = world.nameAt(upPos)
    hasPanicle = splitStage(upName)[0] == PANICLE_PREFIX
    if hasPanicle and _panicleRipe(upName):
        return False, []
    age = lastStage(RICE_PREFIX) if name == RICE_SUPPORTING else splitStage(name)[1]
    growth = min(age + rnd.randint(1, 4), 7)
    if growth <= lastStage(RICE_PREFIX):
        return True, [FarmEdits.block(pos, stageName(RICE_PREFIX, growth))]
    if hasPanicle:
        return True, _panicleEdits(upName, upPos, rnd)
    if upName == FarmEdits.AIR:
        remaining = growth - lastStage(RICE_PREFIX) - 1
        return True, [FarmEdits.block(pos, RICE_SUPPORTING), FarmEdits.block(upPos, stageName(PANICLE_PREFIX, remaining))]
    return True, []


# ---------------- 入口 ----------------

def boneMeal(world, name, pos, rnd):
    if name in COLONY_BLOCKS:
        valid, growth = boneMealGrowth(world.growthAt(pos), rnd)
        return valid, ([FarmEdits.states(pos, {GROWTH_STATE: growth})] if valid else [])
    if name in WILD_CROPS or name == WILD_RICE or name == SANDY_SHRUB:
        return wildBoneMeal(world, name, pos, rnd)
    if name == RICE_SUPPORTING:
        return _rice(world, name, pos, rnd)
    prefix, stage = splitStage(name)
    if prefix is None:
        return False, []
    kind = FAMILIES[prefix]["bone"]
    if kind == "tomatoBase" or kind == "tomatoVine":
        return _tomato(world, name, pos, rnd)
    if kind == "rice":
        return _rice(world, name, pos, rnd)
    if kind == "panicle":
        if _panicleRipe(name):
            return False, []
        return True, _panicleEdits(name, pos, rnd)
    return _ageCrop(prefix, stage, pos, kind, rnd)
