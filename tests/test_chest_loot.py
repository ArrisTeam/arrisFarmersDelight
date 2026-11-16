# -*- coding: utf-8 -*-
# runner: both
"""战利品箱里追加的农夫乐事物品（Shared/Data/ChestLoot.py、Shared/Rules/ChestLoot.py、Server/ChestLoot.py）。

JE 的 FDChestLoot 给 14 张原版箱子表各追加一张表（add_loot_table 修饰器）。基岩版没有战利品修饰器，也不能只加一个池
（同路径文件整份替换原版），所以在箱子第一次被打开时由脚本追加；这里守住：表名对得上基岩版原版的文件、
每张表的池数 / 次数 / 数量 / 权重照 JE、追加时原版掷出的物品原样保留。
（表名是不是基岩版原版真有的文件，在 tests/test_vanilla_overrides.py 里对本机原版行为包查。）
"""
from __future__ import print_function

import glob
import io
import json
import os
import random

import fakeengine
import fdtest

world = fakeengine.install()
Data = fdtest.load("Shared.Data.ChestLoot")
Rules = fdtest.load("Shared.Rules.ChestLoot")
Registry = fdtest.load("Server.EventRegistry")
ChestLoot = fdtest.load("Server.ChestLoot")

# JE FDChestLoot 的 14 张表对应的基岩版原版战利品表（JE 的 shipwreck_supply 在基岩版叫 shipwrecksupply）
BEDROCK_TABLES = [
    "chests/abandoned_mineshaft", "chests/bastion_hoglin_stable", "chests/bastion_treasure",
    "chests/end_city_treasure", "chests/pillager_outpost", "chests/ruined_portal", "chests/shipwrecksupply",
    "chests/simple_dungeon", "chests/village/village_butcher", "chests/village/village_desert_house",
    "chests/village/village_plains_house", "chests/village/village_savanna_house", "chests/village/village_snowy_house",
    "chests/village/village_taiga_house"]


class Scripted(object):
    """按顺序吐出预设整数的随机源，用来逐步检查抽取的算法。"""

    def __init__(self, ints, floats=()):
        self.ints, self.floats = list(ints), list(floats)

    def randint(self, low, high):
        value = self.ints.pop(0)
        assert low <= value <= high, (low, value, high)
        return value

    def random(self):
        return self.floats.pop(0)


# ---- 表名 ----

def testTableKeyAcceptsEveryPathSpelling():
    expected = "chests/village/village_plains_house"
    for path in ("loot_tables/chests/village/village_plains_house.json", "chests/village/village_plains_house",
                 "loot_tables\\chests\\village\\village_plains_house.json", "pack:loot_tables/chests/village/village_plains_house.json",
                 "Loot_Tables/Chests/Village/Village_Plains_House.JSON"):
        assert Rules.tableKey(path) == expected, path
    assert Rules.tableKey(None) == "" and Rules.tableKey("") == ""


def testTheFourteenJeTablesAreCovered():
    assert sorted(Data.CHEST_LOOT) == sorted(BEDROCK_TABLES)


def testEveryItemExists():
    names = set()
    for folder in ("netease_items_beh", "netease_blocks"):
        for path in glob.glob(os.path.join(fdtest.BP, folder, "*.json")):
            with io.open(path, encoding="utf-8") as f:
                data = json.load(f)
            names.add((data.get("minecraft:item") or data["minecraft:block"])["description"]["identifier"])
    used = set(entry["item"] for pools in Data.CHEST_LOOT.values() for pool in pools for entry in pool["entries"]
               if entry["item"])
    assert used - names == set(), sorted(used - names)


# ---- 抽取算法 ----

def testPickEntryFollowsTheWeights():
    entries = [{"weight": 1, "item": "a"}, {"weight": 2, "item": "b"}, {"weight": 3, "item": "c"}]
    picked = [Rules.pickEntry(entries, Scripted([point]))["item"] for point in range(1, 7)]
    assert picked == ["a", "b", "b", "c", "c", "c"]


def testRollPoolRollsTheRightNumberOfTimesWithCounts():
    pool = Data._pool((2, 3), Data._item("arris:rope", (2, 12)), Data._empty(2))
    # 掷 3 次：先取次数 3；第 1 次点数 1 落在绳子（权重 1），数量取 7；第 2、3 次点数 3、2 落在空条目（权重 2）
    rand = Scripted([3, 1, 7, 3, 2])
    items = Rules.rollPool(pool, rand)
    assert items == [{"newItemName": "arris:rope", "newAuxValue": 0, "count": 7}]
    assert rand.ints == [], "每一步取的随机数都用上了，没有多取也没有少取"


def testEmptyEntriesProduceNothing():
    pool = Data._pool((1, 1), Data._empty(5))
    assert Rules.rollPool(pool, Scripted([1, 3])) == []


def testRandomEnchantIsOneKindAtAnyLevel():
    rand = random.Random(7)
    seen = set()
    for _ in range(400):
        result = Rules.enchantments("random", rand)
        assert len(result) == 1
        enchantId, level = result[0]
        maxLevel = dict(Data.KNIFE_ENCHANTS)[enchantId]
        assert 1 <= level <= maxLevel
        seen.add(enchantId)
    assert seen == set(dict(Data.KNIFE_ENCHANTS))


def testLevelsEnchantIsOneToThreeDistinctHighLevels():
    rand = random.Random(11)
    counts = set()
    for _ in range(400):
        result = Rules.enchantments("levels", rand)
        ids = [enchantId for enchantId, level in result]
        assert 1 <= len(result) <= 3 and len(set(ids)) == len(ids)
        counts.add(len(result))
        for enchantId, level in result:
            maxLevel = dict(Data.KNIFE_ENCHANTS)[enchantId]
            assert (maxLevel + 1) // 2 <= level <= maxLevel
    assert counts == {1, 2, 3}


def _rollMany(key, trials, seed=5):
    rand = random.Random(seed)
    return [Rules.rollTable(key, rand) for _ in range(trials)]


def testVillagePlainsHouseIsOneToThreeStacksOfOnionsOrTomatoSeeds():
    for items in _rollMany("chests/village/village_plains_house", 300):
        assert 1 <= len(items) <= 3
        for itemDict in items:
            assert itemDict["newItemName"] in ("arris:onion", "arris:tomato_seeds") and 1 <= itemDict["count"] <= 3


def testBastionTreasureIsThreeQuartersEmpty():
    runs = _rollMany("chests/bastion_treasure", 4000)
    full = sum(1 for items in runs if items)
    assert abs(full / 4000.0 - 0.25) < 0.03, full
    knives = [items[0] for items in runs if items]
    assert all(knife["newItemName"] == "arris:diamond_knife" for knife in knives)
    enchanted = sum(1 for knife in knives if knife.get("enchantData"))
    assert abs(enchanted / float(len(knives)) - 0.5) < 0.06       # 两个条目一半带随机附魔


def testAbandonedMineshaftPoolsAndRanges():
    allowed = {"arris:cooking_pot", "arris:skillet_item", "arris:tomato_seeds", "arris:cabbage_seeds", "arris:rice", "arris:rope"}
    for items in _rollMany("chests/abandoned_mineshaft", 500):
        names = [itemDict["newItemName"] for itemDict in items]
        assert set(names) <= allowed
        assert names.count("arris:rope") <= 3                      # 绳子那个池固定 3 次
        assert sum(1 for name in names if name in ("arris:cooking_pot", "arris:skillet_item")) <= 1
        assert sum(1 for name in names if name.endswith("seeds") or name == "arris:rice") <= 4
        for itemDict in items:
            if itemDict["newItemName"] == "arris:rope":
                assert 2 <= itemDict["count"] <= 12
            elif itemDict["newItemName"].endswith("seeds") or itemDict["newItemName"] == "arris:rice":
                assert 2 <= itemDict["count"] <= 4


def testPillagerOutpostFavoursOnions():
    runs = _rollMany("chests/pillager_outpost", 6000)
    onions = crates = 0
    for items in runs:
        for itemDict in items:
            if itemDict["newItemName"] == "arris:onion":
                onions += 1
                assert 4 <= itemDict["count"] <= 12
            else:
                crates += 1
                assert itemDict["newItemName"] == "arris:onion_crate" and 1 <= itemDict["count"] <= 3
    assert abs(onions / float(crates) - 5 / 2.0) < 0.35, (onions, crates)       # 权重 5 : 2


def testButcherChestHasKnivesAndMeat():
    seen = set()
    for items in _rollMany("chests/village/village_butcher", 800):
        for itemDict in items:
            seen.add(itemDict["newItemName"])
            if itemDict["newItemName"] in ("arris:minced_beef", "arris:bacon", "arris:mutton_chops"):
                assert 2 <= itemDict["count"] <= 6
    assert seen == {"arris:flint_knife", "arris:iron_knife", "arris:ham", "arris:minced_beef", "arris:bacon", "arris:mutton_chops"}


def testUnknownTablesRollNothing():
    assert Rules.rollTable("chests/spawn_bonus_chest") == [] and Rules.rollTable("") == []


# ---- 服务端 ----

def _setUp():
    Registry.clearAll()
    Registry.registerHandler("OnContainerFillLoottableServerEvent", match=Data.CHEST_LOOT, keyOf=ChestLoot._tableKey)(
        ChestLoot.OnChestFilled)


def _fill(path, itemList):
    args = {"loottable": path, "playerId": "p1", "itemList": itemList, "dirty": False}
    Registry.dispatch("OnContainerFillLoottableServerEvent", args)
    return args


def testChestFillKeepsTheVanillaItemsAndAppendsOurs():
    _setUp()
    vanilla = [{"newItemName": "minecraft:bread", "newAuxValue": 0, "count": 3}, {"newItemName": "minecraft:coal", "count": 2}]
    original = [dict(item) for item in vanilla]
    original_roll = ChestLoot.rollTable
    ChestLoot.rollTable = lambda key: [{"newItemName": "arris:onion", "newAuxValue": 0, "count": 2}]
    try:
        args = _fill("loot_tables/chests/village/village_plains_house.json", vanilla)
    finally:
        ChestLoot.rollTable = original_roll
    assert args["dirty"] is True
    assert args["itemList"][:2] == original, "原版掷出的物品原样保留在最前面"
    assert args["itemList"][2:] == [{"newItemName": "arris:onion", "newAuxValue": 0, "count": 2}]


def testOtherChestsAreNotTouched():
    _setUp()
    for path in ("loot_tables/chests/spawn_bonus_chest.json", "loot_tables/chests/shipwrecktreasure.json", None, ""):
        args = _fill(path, [{"newItemName": "minecraft:bread", "count": 1}])
        assert args["dirty"] is False and len(args["itemList"]) == 1, path


def testAnEmptyRollDoesNotMarkTheListDirty():
    _setUp()
    original_roll = ChestLoot.rollTable
    ChestLoot.rollTable = lambda key: []
    try:
        args = _fill("loot_tables/chests/bastion_treasure.json", [])
    finally:
        ChestLoot.rollTable = original_roll
    assert args["dirty"] is False and args["itemList"] == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
