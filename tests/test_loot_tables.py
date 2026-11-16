# -*- coding: utf-8 -*-
# runner: both
"""方块战利品表对照 JE（bp/loot_tables + bp/netease_blocks 里每个方块的 minecraft:loot）。

JE 的对应文件在 data/farmersdelight/loot_tables/blocks/。这里只守住"改过的事实"：
- 蔬菜箱、米袋、稻米捆、稻草捆破坏后掉自己（原来掉 9 个内容物，拆箱靠合成表）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

BLOCKS_DIR = os.path.join(fdtest.BP, "netease_blocks")
TABLES_DIR = os.path.join(fdtest.BP, "loot_tables")

# JE：破坏后掉自己的方块
SELF_DROPPING = ("arris:beetroot_crate", "arris:cabbage_crate", "arris:carrot_crate", "arris:onion_crate",
                 "arris:potato_crate", "arris:tomato_crate", "arris:rice_bag", "arris:rice_bale", "arris:straw_bale")


def _readJson(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def blockTables():
    """{方块标识: 战利品表路径}，只含写了 minecraft:loot 的方块。"""
    result = {}
    for root, dirs, files in os.walk(BLOCKS_DIR):
        for name in files:
            if not name.endswith(".json"):
                continue
            data = _readJson(os.path.join(root, name))["minecraft:block"]
            table = data["components"].get("minecraft:loot")
            if table:
                result[data["description"]["identifier"]] = table["table"]
    return result


def tableDrops(tablePath):
    """战利品表的掉落：[(物品, 最少, 最多)]，每个池每个条目一行（这些表没有条件和权重分支）。"""
    data = _readJson(os.path.join(fdtest.BP, tablePath))
    drops = []
    for pool in data["pools"]:
        assert pool.get("rolls") == 1, tablePath
        for entry in pool["entries"]:
            assert entry["type"] == "item", tablePath
            low, high = 1, 1
            for function in entry.get("functions", []):
                if function["function"] == "set_count":
                    low, high = function["count"]["min"], function["count"]["max"]
            drops.append((entry["name"], low, high))
    return drops


def testEveryReferencedTableExistsAndParses():
    problems = []
    for block, table in sorted(blockTables().items()):
        path = os.path.join(fdtest.BP, table)
        if not os.path.isfile(path):
            problems.append("%s 的战利品表不存在: %s" % (block, table))
            continue
        _readJson(path)
    assert not problems, "\n".join(problems)


def testCratesBagsAndBalesDropThemselves():
    tables = blockTables()
    for block in SELF_DROPPING:
        assert block in tables, block
        assert tableDrops(tables[block]) == [(block, 1, 1)], "%s 应该只掉自己: %r" % (block, tableDrops(tables[block]))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
