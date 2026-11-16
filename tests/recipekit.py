# -*- coding: utf-8 -*-
"""recipekit - 合成配方测试的读取工具（不是测试本身，跑器只收 test_*.py）

读 bp/recipes 下的配方 JSON 和包里的物品 / 方块定义，给 test_recipe_rules.py、test_recipe_parity.py 共用。
"""
from __future__ import print_function

import collections
import io
import json
import os

import fdtest

RECIPES = os.path.join(fdtest.BP, "recipes")


def readText(path):
    with io.open(path, encoding="utf-8-sig") as f:
        return f.read()


def loadRecipes():
    """{文件名: (种类 shaped / shapeless / furnace, 配方体)}，一个文件只许一份配方。"""
    found = collections.OrderedDict()
    for name in sorted(os.listdir(RECIPES)):
        if not name.endswith(".json"):
            continue
        doc = json.loads(readText(os.path.join(RECIPES, name)))
        bodies = [(key, value) for key, value in doc.items() if key != "format_version"]
        assert len(bodies) == 1, "%s 里不是恰好一份配方" % name
        found[name] = (bodies[0][0].split("_")[-1], bodies[0][1])
    return found


def byIdentifier():
    """{标识符: (种类, 配方体)}。"""
    return dict((body["description"]["identifier"], (kind, body)) for kind, body in loadRecipes().values())


def resultsOf(body):
    """[(物品名, 个数), ...]，第一个进结果槽。"""
    result = body["result"]
    entries = result if isinstance(result, list) else [result]
    return [(entry["item"], entry.get("count", 1)) for entry in entries]


def ingredientsOf(kind, body):
    """{物品名: 个数}：有序按 pattern 里每个键出现几次，无序把 count 加起来。"""
    counts = collections.Counter()
    if kind == "shaped":
        for char in "".join(body["pattern"]):
            if char != " ":
                counts[body["key"][char]["item"]] += 1
    else:
        for entry in body["ingredients"]:
            counts[entry["item"]] += entry.get("count", 1)
    return counts


def packIdentifiers():
    """包里定义的物品和方块标识符（方块有子目录）。"""
    found = set()
    for folder in ("netease_items_beh", "netease_blocks"):
        for root, _dirs, files in os.walk(os.path.join(fdtest.BP, folder)):
            for name in files:
                if not name.endswith(".json"):
                    continue
                for value in json.loads(readText(os.path.join(root, name))).values():
                    if isinstance(value, dict) and "description" in value:
                        found.add(value["description"]["identifier"])
    return found
