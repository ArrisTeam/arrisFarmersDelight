# -*- coding: utf-8 -*-
"""MobLoot - 刀的额外掉落与洋葱掉落的结算（双端，纯规则）

概率照 JE 的 random_chance_with_looting：基础概率 + 武器抢夺等级 × 每级加成。
引擎相关的部分（谁杀的、手里拿的什么、有没有着火）由服务端模块取好再传进来。
"""
from ..Data import MobLoot as Data
from .Ticks import probability

# EnchantType.WeaponLoot / MiningSilkTouch（ModAPI 的附魔枚举值）
LOOTING = 14
SILK_TOUCH = 16


def enchantLevel(itemDict, enchantType):
    """物品字典里某个附魔的等级，没有返回 0。enchantData 是 [(附魔类型, 等级)]。"""
    for entry in (itemDict or {}).get("enchantData") or []:
        if entry[0] == enchantType:
            return int(entry[1])
    return 0


def chanceWithLooting(base, perLevel, looting):
    """百分比概率：基础 + 每级加成 × 抢夺等级，夹在 0 到 100 之间。"""
    return max(0, min(100, base + perLevel * max(0, looting)))


def knifeDrops(entityName, burning, looting, roll=probability):
    """手里拿着刀杀死 entityName 时额外掉落的 [(物品, 数量)]；roll(百分比) 决定一次概率是否成功。"""
    drops = []
    if entityName in Data.KNIFE_EXTRA_DROPS:
        drops.append(Data.KNIFE_EXTRA_DROPS[entityName])
    if entityName in Data.KNIFE_HAM:
        chance = Data.KNIFE_HAM[entityName]
        if chance is None or roll(chanceWithLooting(chance[0], chance[1], looting)):
            drops.append((Data.SMOKED_HAM if burning else Data.HAM, 1))
    return drops


def onionDrops(entityName, looting, roll=probability):
    """玩家杀死 entityName 时的洋葱掉落 [(物品, 数量)]。"""
    if entityName in Data.ONION_MOBS and roll(chanceWithLooting(Data.ONION_CHANCE[0], Data.ONION_CHANCE[1], looting)):
        return [(Data.ONION, 1)]
    return []


def lootEntries(drops):
    """[(物品, 数量)] 变成战利品事件 itemList 里的物品字典。"""
    return [{"newItemName": name, "newAuxValue": 0, "count": count} for name, count in drops]
