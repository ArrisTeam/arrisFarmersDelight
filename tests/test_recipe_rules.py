# -*- coding: utf-8 -*-
# runner: py3
"""合成配方 JSON（bp/recipes）的静态检查：引擎读法的坑 + 本包的约定。

引擎怎么读（Strata 知识库 kb/engine/bp/08_recipes/RECIPE_ENGINE.md §7，反汇编核实 + 实测）：
- 无序配方（recipe_shapeless）的 result 写成数组时只认第一个（日志 unsupported multiple output types for result list in
  shapeless），多出来的退还物直接丢掉；只有有序配方（recipe_shaped）会把数组里其余的东西合成时一起给（原版蛋糕退 3 个桶）。
  所以要还容器的无序配方只能走 Shared/Data/Food.py 的 shapedRecipeContainerDict（服务端 CraftItemOutputChangeServerEvent 发），
  有序配方把容器写进 result 数组；同一个成品上两条路不能叠（会还两遍），字典按成品名查、分不出是哪个配方做的。
- 本包 min_engine_version 新于 1.19.22：有序配方的 key、熔炉配方的 input 写 count 整份作废；熔炉配方的 input / output 写
  count / data 也不生效（de99ed7 修过一次）。
- pattern 超过 3x3 整份作废；key 里没用到的键无害，pattern 里没定义的字符当空格，容易写错，这里查严。
本包的约定：文件名 arris_<名>.json 对应标识符 arris:<名>；配方里用到的 arris: 物品 / 方块必须在包里有定义。
"""
from __future__ import print_function

import os
import re

import fdtest
from recipekit import RECIPES, loadRecipes, packIdentifiers, readText, resultsOf

Food = fdtest.load("Shared.Data.Food")

FURNACE_TAGS = ("furnace", "blast_furnace", "smoker", "campfire", "soul_campfire")
ARRIS_ID = re.compile(r'"(arris:[a-z0-9_]+)"')


def testFileNamesAndIdentifiersMatch():
    seen = {}
    for name, (_kind, body) in loadRecipes().items():
        assert name.startswith("arris_"), name
        identifier = body["description"]["identifier"]
        assert identifier == "arris:" + name[len("arris_"):-len(".json")], "%s 的标识符是 %s" % (name, identifier)
        assert identifier not in seen, "%s 和 %s 标识符重复" % (name, seen.get(identifier))
        seen[identifier] = name


def testShapelessRecipesCannotReturnExtras():
    # 无序配方 result 数组里多出来的东西引擎不给：要还容器就走 shapedRecipeContainerDict，或者改成有序配方
    for name, (kind, body) in loadRecipes().items():
        if kind == "shapeless":
            assert len(resultsOf(body)) == 1, "%s 是无序配方，result 里第二项起会被引擎丢掉" % name


def testInputsCarryNoCountOrData():
    for name, (kind, body) in loadRecipes().items():
        if kind == "shaped":
            for char, entry in body["key"].items():
                assert "count" not in entry, "%s 的 key %s 写了 count，新引擎整份作废" % (name, char)
        if kind == "furnace":
            for side in ("input", "output"):
                assert set(body[side]) == {"item"}, "%s 的熔炉 %s 只许写 item" % (name, side)


def testShapedPatternsAndKeysAgree():
    for name, (kind, body) in loadRecipes().items():
        if kind != "shaped":
            continue
        pattern, key = body["pattern"], body["key"]
        assert 1 <= len(pattern) <= 3 and all(isinstance(row, str) and 1 <= len(row) <= 3 for row in pattern), name
        used = set("".join(pattern)) - {" "}
        assert used == set(key), "%s 的 pattern 用了 %s，key 定义了 %s" % (name, sorted(used), sorted(key))


def testFurnaceTagsAreFurnaces():
    for name, (kind, body) in loadRecipes().items():
        if kind == "furnace":
            assert body["tags"] and set(body["tags"]) <= set(FURNACE_TAGS), "%s: %s" % (name, body["tags"])
            # JE 的 campfire_cooking 营火和灵魂营火都能用，原版 Bedrock 的食物配方也是 campfire + soul_campfire 一起写
            assert ("campfire" in body["tags"]) == ("soul_campfire" in body["tags"]), "%s: %s" % (name, body["tags"])


def testPackItemsExist():
    known = packIdentifiers()
    for name in sorted(os.listdir(RECIPES)):
        for item in set(ARRIS_ID.findall(readText(os.path.join(RECIPES, name)))):
            own = "arris:" + name[len("arris_"):-len(".json")]
            assert item in known or item == own, "%s 用到的 %s 包里没有定义" % (name, item)


def testContainerReturnsHaveOneSource():
    # 字典里的成品：每个配方一次出的个数 = perCraft（一次取 N 个按 N // perCraft 份还），result 数组里不再还容器
    makers = {}
    for name, (kind, body) in loadRecipes().items():
        if kind != "furnace":
            results = resultsOf(body)
            makers.setdefault(results[0][0], []).append((name, results))
    for item, container in Food.shapedRecipeContainerDict.items():
        assert makers.get(item), "%s 在 shapedRecipeContainerDict 里，却没有配方做它" % item
        for name, results in makers[item]:
            assert len(results) == 1, "%s 的 result 数组和字典都还了容器，会还两遍" % name
            assert results[0][1] == container.get("perCraft", 1), "%s 一次出 %d 个，perCraft 是 %s" % (
                name, results[0][1], container.get("perCraft", 1))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
