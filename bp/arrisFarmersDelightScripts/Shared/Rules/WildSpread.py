# -*- coding: utf-8 -*-
"""WildSpread - 野生作物、沙地灌木用骨粉往周围长（双端，纯规则）

野生作物照 WildCropBlock.performBonemeal：先数周围同种的，够 10 株就不长；再从自己旁边随机游走几步，
最后在一个"空气、脚下是允许的地面"的格子里种一株同样的。成功率 80%（isBonemealSuccess），不成功骨粉照样用掉。
野生稻米（WildRiceBlock）骨粉成功率 30%，成功了掉一个野生稻米物品。
沙地灌木照 SandyShrubBlock：在灌木上方撒一片 random_patch（32 次尝试，水平散布 2、竖直散布 3），
每次尝试挑到的格子是空气、脚下是沙子才种。
world 接口同 CropTick：nameAt(pos)。随机数 rnd 要有 randint / random（random.Random 即可）。
"""
from . import FarmEdits
from ..Data.Farming import WildCropDict

WILD_CROP_LIMIT = 10          # 周围（水平 ±4、竖直 ±1）同种野生作物到这个数就不再长
WILD_CROP_SUCCESS = 0.8
WILD_RICE_SUCCESS = 0.3
WILD_RICE = "arris:wild_rice"
SANDY_SHRUB = "arris:sandy_shrub"
SAND = ("minecraft:sand", "minecraft:red_sand")
SHRUB_TRIES = 32
SHRUB_XZ_SPREAD = 2
SHRUB_Y_SPREAD = 3
# 能用骨粉往外长的野生作物（不含野生稻米，它走另一条）
WILD_CROPS = ("arris:wild_beetroots", "arris:wild_cabbages", "arris:wild_carrots", "arris:wild_onions",
              "arris:wild_potatoes", "arris:wild_tomatoes")


def _walk(pos, rnd):
    """pos.offset(nextInt(3) - 1, nextInt(2) - nextInt(2), nextInt(3) - 1)"""
    dx = rnd.randint(0, 2) - 1
    dy = rnd.randint(0, 1) - rnd.randint(0, 1)
    dz = rnd.randint(0, 2) - 1
    return (pos[0] + dx, pos[1] + dy, pos[2] + dz)


def wildCropEdits(world, name, pos, rnd):
    """骨粉成功时野生作物往旁边长出一株的修改（可能一株都长不出来）。"""
    count = 0
    for dx in range(-4, 5):
        for dy in (-1, 0, 1):
            for dz in range(-4, 5):
                if world.nameAt((pos[0] + dx, pos[1] + dy, pos[2] + dz)) == name:
                    count += 1
                    if count >= WILD_CROP_LIMIT:
                        return []
    grounds = WildCropDict.get(name, ())

    def usable(cell):
        return world.nameAt(cell) == FarmEdits.AIR and world.nameAt(FarmEdits.below(cell)) in grounds

    origin = pos
    target = _walk(origin, rnd)
    for _ in range(4):
        if usable(target):
            origin = target
        target = _walk(origin, rnd)
    if usable(target):
        return [FarmEdits.block(target, name)]
    return []


def shrubEdits(world, pos, rnd):
    """沙地灌木骨粉：在上方撒一片灌木。"""
    center = FarmEdits.above(pos)
    placed = set()
    edits = []
    spreadX = SHRUB_XZ_SPREAD + 1
    spreadY = SHRUB_Y_SPREAD + 1
    for _ in range(SHRUB_TRIES):
        dx = rnd.randint(0, spreadX - 1) - rnd.randint(0, spreadX - 1)
        dy = rnd.randint(0, spreadY - 1) - rnd.randint(0, spreadY - 1)
        dz = rnd.randint(0, spreadX - 1) - rnd.randint(0, spreadX - 1)
        cell = (center[0] + dx, center[1] + dy, center[2] + dz)
        if cell in placed or world.nameAt(cell) != FarmEdits.AIR:
            continue
        if world.nameAt(FarmEdits.below(cell)) in SAND:
            placed.add(cell)
            edits.append(FarmEdits.block(cell, SANDY_SHRUB))
    return edits


def wildBoneMeal(world, name, pos, rnd):
    """野生作物 / 沙地灌木用骨粉 → (valid, edits)；都是合法目标（骨粉一定用掉），成功与否看各自的概率。"""
    if name == SANDY_SHRUB:
        return True, shrubEdits(world, pos, rnd)
    if name == WILD_RICE:
        if rnd.random() < WILD_RICE_SUCCESS:
            return True, [FarmEdits.drop(pos, WILD_RICE, 1)]
        return True, []
    if rnd.random() < WILD_CROP_SUCCESS:
        return True, wildCropEdits(world, name, pos, rnd)
    return True, []
