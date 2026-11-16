# -*- coding: utf-8 -*-
"""StoveBurn - 踩在点燃的炉灶上被烫（双端，纯规则）

JE AbstractStoveBlock.burnEntitySteppingOnStove（FD 1.3.4），实体站在点燃的炉灶上每刻判一次：
炉灶点燃、实体碰撞盒碰到炉面上那块烤架区（GRILLING_AREA = Block.box(3, 0, 3, 13, 1, 13)，平移到炉灶上面一格）、
不在潜行（isSteppingCarefully）、不防火（fireImmune）、是生物（LivingEntity）、脚上没有冰霜行者，
才 hurt(STOVE_BURN, 1.0)：半颗心，之后靠无敌帧每 10 刻（0.5 秒）扎一下。
STOVE_BURN 不在 is_fire 标签里，所以抗火药水挡不住；护甲照常减伤（没有 bypasses_armor）。
"""
# 烤架区（相对炉灶上面一格的西北下角，单位格）：JE 的 Block.box(3, 0, 3, 13, 1, 13) 除以 16
GRILL_LOW = (3 / 16.0, 0.0, 3 / 16.0)
GRILL_HIGH = (13 / 16.0, 1 / 16.0, 13 / 16.0)
# 一次烫的伤害
DAMAGE = 1.0
# 冰霜行者的附魔号（ModAPI 的 EnchantType.FrostWalker）与鞋子的盔甲槽号（ArmorSlotType.FOOT）
FROST_WALKER = 25
FOOT_SLOT = 3


def grillBox(stovePos):
    """点燃的炉灶在 stovePos 时，烤架区的世界坐标盒子。"""
    x, y, z = stovePos
    return ((x + GRILL_LOW[0], y + 1 + GRILL_LOW[1], z + GRILL_LOW[2]), (x + GRILL_HIGH[0], y + 1 + GRILL_HIGH[1], z + GRILL_HIGH[2]))


def entityBox(footPos, width, height):
    half = width / 2.0
    return ((footPos[0] - half, footPos[1], footPos[2] - half), (footPos[0] + half, footPos[1] + height, footPos[2] + half))


def touchesGrill(stovePos, footPos, width, height):
    """实体的碰撞盒碰没碰到烤架区（边贴边不算，与 AABB.intersects 一致）。"""
    grill = grillBox(stovePos)
    box = entityBox(footPos, width, height)
    return all(box[0][i] < grill[1][i] and box[1][i] > grill[0][i] for i in range(3))


def hasFrostWalker(enchants):
    """鞋子的附魔表 [(附魔号, 等级), ...] 里有没有冰霜行者（等级 > 0）；没有附魔时引擎给 None。"""
    return any(kind == FROST_WALKER and level > 0 for kind, level in (enchants or ()))


def burns(touching, sneaking, living, frostWalker):
    """JE 的几条豁免合起来：都不豁免才烫。防火（fireImmune）由伤害类型 magma 交给引擎判（fire_immune 对 magma 无敌）。"""
    return bool(touching and living and not sneaking and not frostWalker)
