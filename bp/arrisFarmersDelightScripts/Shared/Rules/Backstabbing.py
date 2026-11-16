# -*- coding: utf-8 -*-
"""Backstabbing - 背刺魔咒的纯规则：物品上有几级、是不是从背后打的、伤害乘多少（双端）

照 JE 的 BackstabbingEnchantment：最高 3 级，稀有度 uncommon，附魔台最低等级 15 + (级 - 1) * 9（写在
netease_enchants/arris_backstabbing.json 的 cost 里）。玩家造成伤害时主手物品带这个魔咒、伤害来的位置在目标视线背后
（isLookingBehindTarget：来袭方向在水平面上的分量和目标视线的点积 < -0.5），伤害乘 级 * 0.2 + 1.2。
JE 的魔咒类别是"刀"；网易的自定义魔咒只能从固定的槽位里选，刀是 netease:weapon 的 sword 类型，所以写的是 sword
（原版的剑在附魔台上也可能出背刺；效果和 JE 一样只看主手物品上有没有这个魔咒）。
"""
import math

ENCHANT = "arris:backstabbing"
MAX_LEVEL = 3
BEHIND_DOT = -0.5


def levelOf(itemDict):
    """物品字典上背刺的等级（没有是 0）：自定义魔咒在 modEnchantData 里，[(魔咒名, 等级), ...]。"""
    for entry in (itemDict or {}).get("modEnchantData") or ():
        if len(entry) >= 2 and entry[0] == ENCHANT:
            return max(0, min(MAX_LEVEL, int(entry[1])))
    return 0


def lookOf(rot):
    """(俯仰角, 偏航角)（度）-> 视线的单位向量：偏航 0 朝南（+z），俯仰向下为正。"""
    pitch, yaw = math.radians(rot[0]), math.radians(rot[1])
    return (-math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))


def isBehind(look, targetPos, sourcePos):
    """伤害是不是从目标背后来的（JE 的 isLookingBehindTarget）：来袭方向归一化后去掉竖直分量，和视线的点积 < -0.5。"""
    dx, dy, dz = sourcePos[0] - targetPos[0], sourcePos[1] - targetPos[1], sourcePos[2] - targetPos[2]
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-4:
        return False
    return (dx / length) * look[0] + (dz / length) * look[2] < BEHIND_DOT


def damageOf(amount, level):
    """背刺后的伤害：乘 级 * 0.2 + 1.2（I 1.4 倍，II 1.6 倍，III 1.8 倍）。"""
    return amount * (level * 0.2 + 1.2)
