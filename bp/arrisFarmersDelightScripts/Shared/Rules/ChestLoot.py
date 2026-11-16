# -*- coding: utf-8 -*-
"""ChestLoot - 战利品箱额外掉落的掷骰（双端，纯规则；随机源由调用方传入，离线可复现）"""
import random

from ..Data import ChestLoot as Data

_NAMESPACE_SEPARATOR = ":"


def tableKey(lootTablePath):
    """引擎事件给的战利品表路径 -> CHEST_LOOT 的键：
    "loot_tables/chests/village/village_plains_house.json" -> "chests/village/village_plains_house"。
    路径可能带包名前缀（"pack:loot_tables/..."）、反斜杠或大写，都先抹平。"""
    path = (lootTablePath or "").replace("\\", "/").lower().rsplit(_NAMESPACE_SEPARATOR, 1)[-1]
    if path.endswith(".json"):
        path = path[:-len(".json")]
    marker = "loot_tables/"
    if marker in path:
        path = path.split(marker, 1)[1]
    return path


def pickEntry(entries, rand):
    """按权重从条目里抽一个。"""
    total = sum(entry["weight"] for entry in entries)
    point = rand.randint(1, total)
    for entry in entries:
        point -= entry["weight"]
        if point <= 0:
            return entry
    return entries[-1]


def enchantments(kind, rand):
    """附魔方式 -> enchantData 列表 [(附魔编号, 等级)]。
    "random"：随机一种，等级在 1 到最高之间均匀取（JE enchant_randomly）；
    "levels"：1 到 3 种不同的附魔，等级偏高（对 JE enchant_with_levels 20-39 的近似：附魔台公式本身没搬）。"""
    pool = list(Data.KNIFE_ENCHANTS)
    wanted = 1
    if kind == "levels":
        wanted = 1 + (rand.random() < 0.5) + (rand.random() < 0.25)
    result = []
    for _ in range(wanted):
        enchantId, maxLevel = pool.pop(rand.randint(0, len(pool) - 1))
        low = 1 if kind == "random" else (maxLevel + 1) // 2
        result.append((enchantId, rand.randint(low, maxLevel)))
    return result


def rollPool(pool, rand):
    items = []
    for _ in range(rand.randint(pool["rolls"][0], pool["rolls"][1])):
        entry = pickEntry(pool["entries"], rand)
        if entry["item"] is None:
            continue
        count = entry["count"]
        itemDict = {"newItemName": entry["item"], "newAuxValue": 0,
                    "count": rand.randint(count[0], count[1]) if count else 1}
        if entry["enchant"]:
            itemDict["enchantData"] = enchantments(entry["enchant"], rand)
        items.append(itemDict)
    return items


def rollTable(key, rand=random):
    """键对应的追加表掷一次 -> 物品字典列表；这个键没有追加表返回 []。"""
    items = []
    for pool in Data.CHEST_LOOT.get(key, ()):
        items.extend(rollPool(pool, rand))
    return items
