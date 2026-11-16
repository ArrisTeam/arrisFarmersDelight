# -*- coding: utf-8 -*-
"""StrawRules - 刀具收割杂草 / 成熟麦子 / 成熟稻穗额外掉稻草（双端，纯规则）

JE 用全局战利品修改器 straw_from_*（条件 match_tool 属于 straw_harvesters 标签 = 刀）：
草丛 20%、高草丛 20%、沙地灌木 30%，成熟的小麦和成熟的稻穗 100%。不用刀就没有。
表在 Shared/Data/Farming.py 的 STRAW_SOURCES：方块名 → (概率 %, 要求的 aux 或 None)。
"""


def strawChance(table, blockName, aux):
    """这个方块被刀收割时掉稻草的概率（百分数）；不是来源或还没熟返回 0。"""
    entry = table.get(blockName)
    if entry is None:
        return 0
    percent, requiredAux = entry
    if requiredAux is not None and aux != requiredAux:
        return 0
    return percent
