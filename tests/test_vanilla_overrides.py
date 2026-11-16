# -*- coding: utf-8 -*-
# runner: py3
"""原版文件的覆盖版（tools/gen_vanilla_overrides.py 生成）：猫、农民交易、流浪商人交易；以及对本机原版行为包的其它核对。

引擎里附加包的同路径文件整份替换原版，所以这三份是"原版整份拷来 + 只在列表末尾追加本模组内容"。这里守两件事：
1. 追加的内容对（照 JE：猫被鳕鱼片 / 鲑鱼片吸引、驯服、繁殖、长大、治疗；农民收洋葱、番茄、卷心菜、稻米；
   流浪商人卖卷心菜种子、番茄种子、稻米、洋葱）、交易表合乎引擎的加载规则（TRADING.md §1）、用到的物品都存在；
2. 找得到本机的原版行为包时，重新生成一遍和提交的文件逐字比对：原版随游戏升级变了就失败，提醒重新生成
   （找不到原版目录就跳过这一条；FD_VANILLA_BP 环境变量可以指定目录）。
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

SLICES = ["arris:cod_slice", "arris:salmon_slice"]


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


# ---- 猫 ----

def testCatKeepsItsIdentityAndGainsTheSlicesWhereverItUsesFishAndSalmon():
    cat = _read("entities/cat.json")["minecraft:entity"]
    assert cat["description"]["identifier"] == "minecraft:cat"
    fishLists = []

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            if "fish" in node and "salmon" in node:
                fishLists.append(node)
            for value in node:
                walk(value)

    walk(cat)
    # 幼崽长大、成年繁殖、野猫驯服、野猫 / 驯服猫被吸引，共 5 张字符串列表
    assert len(fishLists) == 5, len(fishLists)
    for names in fishLists:
        assert names[-2:] == SLICES, names
    healable = cat["components"]["minecraft:healable"]["items"]
    assert [entry["item"] for entry in healable] == ["fish", "salmon"] + SLICES
    assert [entry["heal_amount"] for entry in healable[2:]] == [1, 1], "JE 按食物的营养值回血，鱼片都是 1"


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
    used.update(SLICES)
    missing = sorted(name for name in used if name not in items)
    assert not missing, "物品 JSON 里找不到: %s" % missing


# ---- 与本机原版逐字比对 ----

def testLivestockComponentsAreVanillaPlusOurItems():
    # Mobs.py 里追加的 tempt / beg 会整个盖掉原版同名组件：除了 items 多出本模组的物品，别的字段必须和原版一致
    vanilla = gen.find_vanilla()
    if vanilla is None:
        print("跳过：找不到本机原版行为包（FD_VANILLA_BP 可以指定）")
        return
    extras = {"arris:horse_feed", "arris:dog_food", "arris:cabbage", "arris:cabbage_leaf"}
    Mobs = fdtest.load("Shared.Data.Mobs")
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
    assert checked == 5, checked          # 马 / 驴 / 骡的 tempt、兔子的 tempt、狼的 beg


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
