# -*- coding: utf-8 -*-
"""FarmEdits - 种植规则算出来的"要改什么"（双端，纯规则）

CropTick / BoneMealRules 这些纯规则只读世界（world.nameAt 等）、返回修改列表，不碰引擎；
服务端的 Server/FarmWorld.py 把列表落到世界里。每条修改是一个元组：
    ("block", pos, 方块名)             换成这个方块（默认状态，不通知邻居）
    ("states", pos, {状态名: 值})      改方块状态（自定义方块的 arris:growth 之类）
    ("drop", pos, 物品名, 数量)        在方块处掉落物品
"""

BLOCK = "block"
STATES = "states"
DROP = "drop"

AIR = "minecraft:air"


def block(pos, name):
    return (BLOCK, tuple(pos), name)


def states(pos, mapping):
    return (STATES, tuple(pos), dict(mapping))


def drop(pos, itemName, count=1):
    return (DROP, tuple(pos), itemName, count)


def above(pos, height=1):
    return (pos[0], pos[1] + height, pos[2])


def below(pos, depth=1):
    return (pos[0], pos[1] - depth, pos[2])
