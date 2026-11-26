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
    """{文件名: (种类 shaped / shapeless / furnace / transform, 配方体)}，一个文件只许一份配方。
    transform 是锻造台的 minecraft:recipe_smithing_transform（模板 + 底料 + 添加物 → 成品，成品是一个物品名的字符串）。"""
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
    return [(entry, 1) if not isinstance(entry, dict) else (entry["item"], entry.get("count", 1)) for entry in entries]


def nameOf(entry):
    """原料一格的写法 -> 物品名，写标签的是 "#标签名"。"""
    return ("#" + entry["tag"]) if "tag" in entry else entry["item"]


def cellsOf(kind, body):
    """一格一个原料（物品名或 "#标签"）：有序按 pattern 的先后（空格不算），无序按 ingredients 的先后、count 展开成几格。"""
    if kind == "shaped":
        return [nameOf(body["key"][char]) for char in "".join(body["pattern"]) if char != " "]
    if kind == "transform":
        return [body[key] for key in ("template", "base", "addition")]
    cells = []
    for entry in body["ingredients"]:
        cells += [nameOf(entry)] * entry.get("count", 1)
    return cells


def ingredientsOf(kind, body):
    """{物品名或 "#标签": 个数}：有序按 pattern 里每个键出现几次，无序把 count 加起来，锻造台是模板、底料、添加物各一。"""
    return collections.Counter(cellsOf(kind, body))


# 配方里用到、词表里没有的原版标签（基岩版 3.10 原版的成员）：和 tools/recipejson.VANILLA 一样
VANILLA = {"minecraft:planks": tuple("minecraft:%s_planks" % wood for wood in (
    "oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo", "crimson", "warped"))}


def membersOf(name):
    """一格 -> 能放的具体物品：物品就是它自己；"#标签" 是词表（Shared/Data/Tags）的静态成员。"""
    if not name.startswith("#"):
        return (name,)
    Tags = fdtest.load("Shared.Data.Tags")
    tag = name[1:]
    for table in (Tags.ITEM_TAGS, Tags.VANILLA_TAGS, VANILLA):
        if tag in table:
            return tuple(table[tag])
    raise KeyError("配方里的标签 %s 词表里没有" % tag)


def variantsOf(kind, body):
    """一份配方按格展开成全部具体的原料组合：[Counter({物品名: 个数})]，组合相同的只留一份（无序配方几格同一个标签时各选各的）。"""
    ways = [()]
    for cell in cellsOf(kind, body):
        ways = [way + (member,) for way in ways for member in membersOf(cell)]
    found, seen = [], set()
    for way in ways:
        key = tuple(sorted(way))
        if key not in seen:
            seen.add(key)
            found.append(collections.Counter(way))
    return found


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
