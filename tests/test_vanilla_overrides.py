# -*- coding: utf-8 -*-
# runner: py3
"""原版文件的覆盖版（tools/gen_vanilla_overrides.py 生成）：农民交易、流浪商人交易；以及对本机原版行为包的其它核对。

引擎里附加包的同路径文件整份替换原版，所以这两份是"原版整份拷来 + 只在列表末尾追加本模组内容"。这里守两件事：
1. 追加的内容对（照 JE：农民收洋葱、番茄、卷心菜、稻米；流浪商人卖卷心菜种子、番茄种子、稻米、洋葱）、
   交易表合乎引擎的加载规则（TRADING.md §1）、用到的物品都存在；
2. 找得到本机的原版行为包时，重新生成一遍和提交的文件逐字比对：原版随游戏升级变了就失败，提醒重新生成
   （找不到原版目录就跳过这一条；FD_VANILLA_BP 环境变量可以指定目录）。
六种动物原来也是整文件覆盖，现在是运行时加组件（tests/test_animal_food.py），这里只查它们的物品都存在、实体文件不再覆盖。
"""
from __future__ import print_function

import glob
import io
import json
import os
import sys

import fdtest

sys.path.insert(0, os.path.join(fdtest.ROOT, "tools"))
import gen_vanilla_overrides as gen  # noqa: E402

Mobs = fdtest.load("Shared.Data.Mobs")


def _read(relPath):
    with io.open(os.path.join(fdtest.BP, *relPath.split("/")), encoding="utf-8") as f:
        return json.load(f)


def _items():
    names = set()
    for path in glob.glob(os.path.join(fdtest.BP, "netease_items_beh", "*.json")):
        with io.open(path, encoding="utf-8") as f:
            names.add(json.load(f)["minecraft:item"]["description"]["identifier"])
    return names


def _tradeItems(table):
    for tier in table["tiers"]:
        for group in tier["groups"]:
            for trade in group["trades"]:
                for entry in trade["wants"] + trade["gives"]:
                    yield entry["item"]


# ---- 动物不再整文件覆盖 ----

def testNoVanillaAnimalIsOverriddenAnyMore():
    # 六种动物改成运行时加组件（Server/AnimalFood.py）：包里不再带同路径的实体文件，免得盖掉原版的更新、和别的包的覆盖抢
    for entityType in sorted(Mobs.ANIMAL_FOOD):
        path = os.path.join(fdtest.BP, "entities", entityType.split(":")[1] + ".json")
        assert not os.path.exists(path), path
    for path in glob.glob(os.path.join(fdtest.BP, "entities", "*.json")):
        with io.open(path, encoding="utf-8-sig") as f:
            identifier = json.load(f)["minecraft:entity"]["description"]["identifier"]
        assert not identifier.startswith("minecraft:"), (path, identifier)
    assert sorted(gen.OUTPUTS) == ["trading/economy_trades/farmer_trades.json", "trading/economy_trades/wandering_trader_trades.json"]


# ---- 交易 ----

def _checkTradeTable(table):
    exp = [tier.get("total_exp_required", index) for index, tier in enumerate(table["tiers"])]     # 不写就是等级序号
    assert exp == sorted(exp) and len(set(exp)) == len(exp), exp
    for tier in table["tiers"]:
        for group in tier["groups"]:
            assert group["num_to_select"] <= len(group["trades"])
            for trade in group["trades"]:
                assert trade["wants"] and trade["gives"]
                assert trade.get("weight", 1) > 0
                assert trade.get("max_uses", 7) != 0


def testFarmerBuysTheJeCropsOnTheSameTerms():
    table = _read("trading/economy_trades/farmer_trades.json")
    _checkTradeTable(table)

    def buys(tier):
        return {trade["wants"][0]["item"]: (trade["wants"][0]["quantity"], trade["gives"][0], trade["max_uses"],
                                            trade["trader_exp"], trade["wants"][0]["price_multiplier"])
                for trade in table["tiers"][tier]["groups"][0]["trades"]}

    emerald = {"item": "minecraft:emerald", "quantity": 1}
    # JE VillagerEvents：新手农民 洋葱 26、番茄 26（16 次、2 经验），学徒 卷心菜 16、稻米 20（16 次、5 经验）
    assert buys(0)["arris:onion"] == (26, emerald, 16, 2, 0.05)
    assert buys(0)["arris:tomato"] == (26, emerald, 16, 2, 0.05)
    assert buys(1)["arris:cabbage"] == (16, emerald, 16, 5, 0.05)
    assert buys(1)["arris:rice"] == (20, emerald, 16, 5, 0.05)
    # 原版的收购交易还在
    assert {"minecraft:wheat", "minecraft:potato", "minecraft:beetroot", "minecraft:carrot"} <= set(buys(0))
    assert "minecraft:pumpkin" in buys(1)


def testWanderingTraderSellsTheJeSeeds():
    table = _read("trading/economy_trades/wandering_trader_trades.json")
    _checkTradeTable(table)
    group = table["tiers"][0]["groups"][2]
    assert group["num_to_select"] == 5
    ours = [trade for trade in group["trades"] if trade["gives"][0]["item"].startswith("arris:")]
    assert [trade["gives"][0]["item"] for trade in ours] == [
        "arris:cabbage_seeds", "arris:tomato_seeds", "arris:rice", "arris:onion"]
    for trade in ours:
        assert trade["wants"] == [{"item": "minecraft:emerald", "quantity": 1}]
        assert trade["gives"][0]["quantity"] == 1 and trade["max_uses"] == 1     # JE：1 个绿宝石换 1 个，只能买 1 次


def testEveryModItemTheOverridesMentionExists():
    items = _items()
    used = set()
    for relPath in ("trading/economy_trades/farmer_trades.json", "trading/economy_trades/wandering_trader_trades.json"):
        used.update(name for name in _tradeItems(_read(relPath)) if name.startswith("arris:"))
    for patches in Mobs.ANIMAL_FOOD.values():
        for _component, _field, extra in patches:
            used.update(entry["item"] if isinstance(entry, dict) else entry for entry in extra)
    missing = sorted(name for name in used if name not in items)
    assert not missing, "物品 JSON 里找不到: %s" % missing


def testWolfBegsForTheSameMeatsItEats():
    import jefood
    for name, food in Mobs.WOLF_MEATS:
        assert jefood.FOODS[name.split(":")[1]][0] == food, name                # JE FoodValues 的饱食度（tests/jefood.py 抄的那份）
    beg = json.loads(Mobs.wolfComponentsDict["minecraft:behavior.beg"])["items"]
    assert beg[-10:] == list(Mobs.WOLF_FOOD) and "arris:dog_food" in beg


# ---- 与本机原版逐字比对 ----

def testLivestockComponentsAreVanillaPlusOurItems():
    # Mobs.py 里追加的 tempt / beg 会整个盖掉原版同名组件：除了 items 多出本模组的物品，别的字段必须和原版一致
    vanilla = gen.find_vanilla()
    if vanilla is None:
        print("跳过：找不到本机原版行为包（FD_VANILLA_BP 可以指定）")
        return
    extras = {"arris:horse_feed", "arris:dog_food"} | set(Mobs.WOLF_FOOD)
    checked = 0
    for entity, table in sorted(Mobs.livestockComponents.items()):
        with io.open(os.path.join(vanilla, "entities", entity.split(":")[1] + ".json"), encoding="utf-8-sig") as f:
            base = gen.load(f.read())["minecraft:entity"]["components"]
        for name in ("minecraft:behavior.tempt", "minecraft:behavior.beg"):
            if name not in table:
                continue
            ours, theirs = json.loads(table[name]), base[name]
            assert set(ours) == set(theirs), (entity, name, sorted(set(ours) ^ set(theirs)))
            for key in theirs:
                if key == "items":
                    assert set(theirs[key]) <= set(ours[key]) and set(ours[key]) - set(theirs[key]) <= extras, (entity, name)
                else:
                    assert ours[key] == theirs[key], (entity, name, key, ours[key], theirs[key])
            checked += 1
    assert checked == 4, checked          # 马 / 驴 / 骡的 tempt、狼的 beg（兔子的 tempt 改成了运行时读定义追加，tests/test_animal_food.py）


def testChestLootTableNamesAreRealVanillaFiles():
    # Server/ChestLoot.py 按这些名字认原版战利品箱（Shared/Data/ChestLoot.py 的键），名字错了不会有任何报错，只是永远追加不上
    vanilla = gen.find_vanilla()
    if vanilla is None:
        print("跳过：找不到本机原版行为包（FD_VANILLA_BP 可以指定）")
        return
    for key in sorted(fdtest.load("Shared.Data.ChestLoot").CHEST_LOOT):
        assert os.path.isfile(os.path.join(vanilla, "loot_tables", *(key + ".json").split("/"))), key


def testOverridesAreCurrentAgainstTheLocalVanillaPack():
    vanilla = gen.find_vanilla()
    if vanilla is None:
        print("跳过：找不到本机原版行为包（FD_VANILLA_BP 可以指定）")
        return
    for out, text in gen.generate(vanilla).items():
        with io.open(os.path.join(fdtest.BP, *out.split("/")), encoding="utf-8", newline="") as f:
            current = f.read().replace("\r\n", "\n")
        assert current == text, "%s 和原版（%s）不一致：py -3 tools/gen_vanilla_overrides.py 重新生成" % (out, vanilla)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
