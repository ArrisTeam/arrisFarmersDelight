# -*- coding: utf-8 -*-
# runner: py3
"""工作台配方哪一格写标签：对着 .refs 里 JE 1.3.4 的配方逐格复算（主会话 2026-11-26 定的：JE 写标签的格子这边也写标签）。

JE 写了标签的工作台配方 65 条，帆布告示牌 34 条没搬，剩 31 条；每条在这边是 ONES 里列的配方文件。逐格比：
- JE 的标签（#forge:...）换成词表里的名字（Shared/Data/Tags.JE_NAMES 反查；forge:eggs 是原版的 minecraft:egg，minecraft:planks 照写）；
- JE 写物品的写物品（farmersdelight: 换成 arris:，几样改过名的照 RENAME；原版的 minecraft:bricks 在基岩版叫 brick_block）。
有意不同的（docs/ARCHITECTURE.md「和 JE 的出入」）：
- forge:ingots/iron 照团队的写法写 minecraft:iron_ingot（机械动力的转换表也是这样，词表里没有铁锭）；
- 有序配方里会剩容器的格子写具体物品：奶（蛋糕、巧克力派、芝士蛋糕、派皮：奶桶 / 奶瓶每种摆法一份文件）、厨锅的水桶——容器走 result 数组，
  不给有序配方开脚本还容器的路；
- 烤串那一格 JE 是"熟牛 / 猪 / 鸡 / 羊 / 鱼 / 熟兔肉"任一：基岩版一格只能写一个标签，拆成 common:cooked_meat、common:cooked_fish 两份。
无序配方一格一个原料（不写 count：count 大于 1 的标签格里有堆叠不到的成员，引擎整份作废——Strata 引擎研究，3.9 反编译），
物品写在前、标签写在后（引擎的无序配方是贪心匹配，按原料书写顺序、不回溯，宽的写前面会吃掉窄的那格的东西）。
"""
from __future__ import print_function

import collections
import io
import json
import os

import fdtest
import recipekit

Tags = fdtest.load("Shared.Data.Tags")
JE_RECIPES = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "generated", "resources", "data", "farmersdelight", "recipes")
RENAME = {"farmersdelight:apple_pie": "arris:apple_pie_item", "farmersdelight:chocolate_pie": "arris:chocolate_pie_item",
          "farmersdelight:sweet_berry_cheesecake": "arris:sweet_berry_cheesecake_item", "farmersdelight:skillet": "arris:skillet_item",
          "minecraft:bricks": "minecraft:brick_block"}
for _feast in ("roast_chicken", "shepherds_pie", "gleaming_salad"):
    RENAME["farmersdelight:%s_block" % _feast] = "arris:%s_block_stage0" % _feast
TAG_NAMES = {"forge:eggs": "minecraft:egg", "minecraft:planks": "minecraft:planks"}
MILK, WATER = ("minecraft:milk_bucket", "arris:milk_bottle"), ("minecraft:water_bucket",)
# 有意写物品的 JE 标签：JE 标签 -> 这边可以写的物品（铁锭哪里都写物品；奶、水桶在有序配方里写物品，无序配方照写标签）
ITEMS_ALWAYS = {"forge:ingots/iron": ("minecraft:iron_ingot",)}
ITEMS_IN_SHAPED = {"forge:milk": MILK, "forge:buckets/water": WATER}
BARBECUE = ("#common:cooked_meat", "#common:cooked_fish")
# JE 的配方文件 -> 这边做同一件东西的配方文件
ONES = {
    "apple_pie.json": ["arris_apple_pie.json"], "bacon_and_eggs.json": ["arris_bacon_and_eggs.json"],
    "bacon_sandwich.json": ["arris_bacon_sandwich.json"],
    "barbecue_stick.json": ["arris_barbecue_stick.json", "arris_barbecue_stick_from_fish.json"],
    "cake_from_milk_bottle.json": ["arris_cake_from_milk_bottle.json"] + ["arris_cake_from_milk_bottle%d.json" % i for i in range(2, 6)],
    "chicken_sandwich.json": ["arris_chicken_sandwich.json"],
    "chocolate_pie.json": ["arris_chocolate_pie%d.json" % i for i in range(1, 7)],
    "cooking_pot.json": ["arris_cooking_pot.json"], "cutting_board.json": ["arris_cutting_board.json"],
    "egg_sandwich.json": ["arris_egg_sandwich.json"], "fruit_salad.json": ["arris_fruit_salad.json"],
    "gleaming_salad_block.json": ["arris_gleaming_salad_block.json"], "grilled_salmon.json": ["arris_grilled_salmon.json"],
    "hamburger.json": ["arris_hamburger.json"], "honey_cookie.json": ["arris_honey_cookie.json"],
    "iron_knife.json": ["arris_iron_knife.json"], "kelp_roll.json": ["arris_kelp_roll.json"],
    "mixed_salad.json": ["arris_mixed_salad.json"], "mutton_wrap.json": ["arris_mutton_wrap.json"],
    "pie_crust.json": ["arris_pie_crust1.json", "arris_pie_crust2.json"],
    "pumpkin_pie_from_pie_crust.json": ["arris_pumpkin_pie_from_pie_crust.json"], "roast_chicken_block.json": ["arris_roast_chicken.json"],
    "roasted_mutton_chops.json": ["arris_roasted_mutton_chops.json"], "shepherds_pie_block.json": ["arris_shepherds_pie_block.json"],
    "skillet.json": ["arris_skillet.json"], "steak_and_potatoes.json": ["arris_steak_and_potatoes.json"],
    "stove.json": ["arris_stove.json"], "stuffed_potato.json": ["arris_stuffed_potato.json"],
    "sweet_berry_cheesecake.json": ["arris_sweet_berry_cheesecake%d.json" % i for i in range(1, 4)],
    "sweet_berry_cookie.json": ["arris_sweet_berry_cookie.json"], "wheat_dough_from_egg.json": ["arris_wheat_dough_from_egg.json"],
}


def _alias():
    found = dict((name, tag) for tag, names in Tags.JE_NAMES.items() if tag in Tags.ITEM_TAGS or tag in Tags.VANILLA_TAGS for name in names)
    found.update(TAG_NAMES)
    return found


def _javaRecipes():
    """JE 写了标签的工作台配方（帆布告示牌除外）：{文件名: 配方}。"""
    found = {}
    for name in sorted(os.listdir(JE_RECIPES)):
        if not name.endswith(".json") or "canvas_sign" in name:
            continue
        with io.open(os.path.join(JE_RECIPES, name), encoding="utf-8") as handle:
            doc = json.load(handle)
        if doc.get("type") in ("minecraft:crafting_shaped", "minecraft:crafting_shapeless") and '"tag"' in json.dumps(doc):
            found[name] = doc
    return found


def _javaCells(doc):
    """JE 一格一个：[(物品名 / "#标签", ...)]（一格几个选项是 JE 的写法：烤串那一格）；有序按 pattern 的先后。"""
    def options(value):
        values = value if isinstance(value, list) else [value]
        return tuple(("#" + entry["tag"]) if "tag" in entry else entry["item"] for entry in values)
    if doc["type"] == "minecraft:crafting_shaped":
        return [options(doc["key"][char]) for char in "".join(doc["pattern"]) if char != " "]
    return [options(value) for value in doc["ingredients"]]


def _wanted(options, alias, shaped):
    """JE 一格 -> 这边这一格可以写的（一组）：标签换成词表的名字，有意写物品的那几种 JE 标签换成那几样物品。"""
    if len(options) > 1:
        return BARBECUE
    option = options[0]
    if not option.startswith("#"):
        return (RENAME.get(option, option.replace("farmersdelight:", "arris:")),)
    tag = option[1:]
    if tag in ITEMS_ALWAYS or (shaped and tag in ITEMS_IN_SHAPED):
        return ITEMS_ALWAYS.get(tag) or ITEMS_IN_SHAPED[tag]
    assert tag in alias, "JE 的 %s 词表里没有对应的名字" % tag
    return ("#" + alias[tag],)


def testEveryJavaTagCellIsATagCellHere():
    if not os.path.isdir(JE_RECIPES):
        print("跳过：没有 JE 源码（.refs/FarmersDelight）")
        return
    alias, ours = _alias(), recipekit.loadRecipes()
    java = _javaRecipes()
    assert len(java) == 31 and sorted(java) == sorted(ONES), sorted(set(java) ^ set(ONES))
    tags = 0
    for javaName, doc in sorted(java.items()):
        wanted = [_wanted(options, alias, doc["type"].endswith("shaped")) for options in _javaCells(doc)]
        tags += sum(1 for options in wanted if options[0].startswith("#"))
        result = RENAME.get(doc["result"]["item"], doc["result"]["item"].replace("farmersdelight:", "arris:"))
        barbecue = set()
        for fileName in ONES[javaName]:
            kind, body = ours[fileName]
            assert recipekit.resultsOf(body)[0] == (result, doc["result"].get("count", 1)), fileName
            assert kind == ("shaped" if doc["type"].endswith("shaped") else "shapeless"), fileName
            cells = recipekit.cellsOf(kind, body)
            if kind == "shaped":
                assert len(body["pattern"]) == len(doc["pattern"]), fileName
                assert all(cell in options for cell, options in zip(cells, wanted)), (fileName, cells, wanted)
            else:
                _matches(fileName, cells, wanted, barbecue)
        if javaName == "barbecue_stick.json":
            assert barbecue == set(BARBECUE), barbecue
    assert tags >= 60, tags


def _matches(fileName, cells, wanted, barbecue):
    """无序配方：一格一个原料，物品在前、标签在后；每格对上 JE 的一格（烤串那一格两份文件各取一个标签）。"""
    assert len(cells) == len(wanted), (fileName, cells)
    tagged = [cell.startswith("#") for cell in cells]
    assert tagged == sorted(tagged), "%s：物品写在前、标签写在后（无序配方是贪心匹配）%s" % (fileName, cells)
    left = list(cells)
    for options in sorted(wanted, key=len):
        hit = [cell for cell in left if cell in options]
        assert hit, (fileName, options, cells)
        left.remove(hit[0])
        if options == BARBECUE:
            barbecue.add(hit[0])


def testShapelessTagCellsAreOneEach():
    """无序配方里写标签的原料不写 count（一格一个，要几格写几个）：count 大于 1 时标签里堆叠不到那么多的成员（奶桶、水桶）会让整份配方作废。"""
    for name, (kind, body) in recipekit.loadRecipes().items():
        if kind == "shapeless":
            for entry in body["ingredients"]:
                assert "tag" not in entry or entry.get("count", 1) == 1, name


def testShapedCellsThatLeaveSomethingAreItems():
    """有序配方的容器写在 result 数组里、和放进去的是什么无关：会剩东西的格子（奶、水桶……）不能写标签。"""
    remainders = fdtest.load("Shared.Data.Remainders")
    for name, (kind, body) in recipekit.loadRecipes().items():
        if kind == "shaped":
            for cell in set(recipekit.cellsOf(kind, body)):
                if cell.startswith("#"):
                    assert not [m for m in recipekit.membersOf(cell) if remainders.craftRemainderOf(m)], (name, cell)


def testTheEggRecipesTakeAllThreeEggs():
    """用户定的：三种蛋一视同仁。JE 写 #forge:eggs 的 4 条（这边 8 个文件）写原版标签 minecraft:egg。"""
    eggs = collections.Counter()
    for name, (kind, body) in recipekit.loadRecipes().items():
        if kind in ("shaped", "shapeless") and "#minecraft:egg" in recipekit.cellsOf(kind, body):
            eggs[recipekit.resultsOf(body)[0][0]] += 1
        assert kind not in ("shaped", "shapeless") or "minecraft:egg" not in recipekit.cellsOf(kind, body), name
    assert eggs == {"minecraft:cake": 5, "minecraft:pumpkin_pie": 1, "arris:roast_chicken_block_stage0": 1, "arris:wheat_dough": 1}, eggs


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
