# -*- coding: utf-8 -*-
# runner: py3
"""合成配方 JSON（bp/recipes）的静态检查：引擎读法的坑 + 本包的约定。

引擎怎么读（Strata 知识库 kb/engine/bp/08_recipes/RECIPE_ENGINE.md §7，反汇编核实 + 实测）：
- 无序配方（recipe_shapeless）的 result 写成数组时只认第一个（日志 unsupported multiple output types for result list in
  shapeless），多出来的退还物直接丢掉；只有有序配方（recipe_shaped）会把数组里其余的东西合成时一起给（原版蛋糕退 3 个桶）。
  所以无序配方的剩余物由服务端补还（Server/CraftReturns.py 在 CraftItemOutputChangeServerEvent 里读合成格，对上
  tools/gen_crafts.py 生成的 Shared/Data/CraftReturns.py），有序配方把容器写进 result 数组；两条路不能叠（会还两遍）。
  Shared/Data/Food.py 的 shapedRecipeContainerDict 是给下游包按成品名登记的旧接口，本包留在里面的条目必须和生成的表一致。
- 本包 min_engine_version 新于 1.19.22：有序配方的 key、熔炉配方的 input 写 count 整份作废；熔炉配方的 input / output 写
  count / data 也不生效（de99ed7 修过一次）。
- pattern 超过 3x3 整份作废；key 里没用到的键无害，pattern 里没定义的字符当空格，容易写错，这里查严。
本包的约定：文件名 arris_<名>.json 对应标识符 arris:<名>；配方里用到的 arris: 物品 / 方块必须在包里有定义。
"""
from __future__ import print_function

import os
import re
import subprocess
import sys

import fdtest
from recipekit import RECIPES, loadRecipes, packIdentifiers, readText, resultsOf

Food = fdtest.load("Shared.Data.Food")
CraftReturns = fdtest.load("Shared.Data.CraftReturns").CraftReturns

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
    # 无序配方 result 数组里多出来的东西引擎不给：剩余物由服务端按 CraftReturns 表补还
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


def testTheReturnsTableIsUpToDateWithTheRecipes():
    tool = os.path.join(fdtest.ROOT, "tools", "gen_crafts.py")
    code = subprocess.call([sys.executable, tool, "--check"])
    assert code == 0, "合成配方改了：py -3 tools/gen_crafts.py 重新生成 Shared/Data/CraftReturns.py"


def testTheReturnsTableOnlyHoldsShapelessRecipes():
    recipes = loadRecipes()
    for result, entries in CraftReturns.items():
        for entry in entries:
            kind, body = recipes[entry["source"]]
            assert kind == "shapeless" and resultsOf(body) == [(result, entry["count"])], entry["source"]
            assert entry["returns"] and set(entry["returns"]) <= set(entry["ingredients"]), entry["source"]


def testLegacyContainerDictAgreesWithTheReturnsTable():
    # 留在旧字典里的本包成品：它的每条配方都是无序的、都只还这一种容器一个，一份的个数 = perCraft
    makers = {}
    for name, (kind, body) in loadRecipes().items():
        if kind != "furnace":
            makers.setdefault(resultsOf(body)[0][0], []).append((name, kind, resultsOf(body)))
    assert Food.shapedRecipeContainerDict, "表不能空：linkage 的 Interface / Obtain 对空容器返回 False"
    for item, container in Food.shapedRecipeContainerDict.items():
        assert makers.get(item), "%s 在 shapedRecipeContainerDict 里，却没有配方做它" % item
        for name, kind, results in makers[item]:
            assert kind == "shapeless" and len(results) == 1, "%s 不是只出一样东西的无序配方" % name
            assert results[0][1] == container.get("perCraft", 1), "%s 一次出 %d 个，perCraft 是 %s" % (
                name, results[0][1], container.get("perCraft", 1))
        entries = CraftReturns.get(item) or []
        assert sorted(entry["source"] for entry in entries) == sorted(name for name, _kind, _results in makers[item]), item
        for entry in entries:
            back = [entry["returns"][name] for name in entry["ingredients"] if name in entry["returns"]]
            assert back == [container["itemName"]], "%s 按 JE 还 %s，旧字典写的是 %s" % (entry["source"], back, container["itemName"])


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
