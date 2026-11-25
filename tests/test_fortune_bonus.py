# -*- coding: utf-8 -*-
# runner: both
"""时运多掉几个（Shared/Rules/FortuneBonus.py + Server/FortuneDrops.py）对照 JE 农夫乐事 1.3.4 方块战利品表里的 apply_bonus：
卷心菜种子、洋葱 binomial_with_bonus_count（extra 3、p 4/7：补多出来的"等级"次），番茄 uniform ×1，野生作物、沙地灌木 uniform ×2；
剪刀打野生作物不补，沙地灌木只在真掉了种子时补，创造模式不补。
"""
from __future__ import print_function

import io
import json
import os

import fdtest
import farmengine

LEVEL = farmengine.Level()
farmengine.install(LEVEL)
DROPPED = {}
farmengine._CompFactory.CreateItem = lambda self, levelId: type("Items", (), {
    "GetDroppedItem": staticmethod(lambda entityId, getUserData=False: DROPPED.get(entityId))})

Registry = fdtest.load("Server.EventRegistry")
FortuneDrops = fdtest.load("Server.FortuneDrops")
Fortune = fdtest.load("Shared.Rules.FortuneBonus")

JE_DIR = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "generated", "resources", "data", "farmersdelight", "loot_tables",
                      "blocks")
# JE 方块 -> 这边熟了的那个方块（作物只有熟的在 JE 的那一条里）
JE_BLOCKS = {"cabbages": "arris:cabbages_stage7", "onions": "arris:onions_stage3", "tomatoes": "arris:budding_tomatoes_stage6",
             "tomatoes_on_rope": "arris:tomatoes_vine_stage3", "sandy_shrub": "arris:sandy_shrub"}
JE_ITEMS = {"farmersdelight:cabbage_seeds": "arris:cabbage_seeds", "farmersdelight:onion": "arris:onion",
            "farmersdelight:tomato": "arris:tomato", "farmersdelight:tomato_seeds": "arris:tomato_seeds"}


class Rng(object):
    def __init__(self, randoms=(), ints=()):
        self.randoms, self.ints, self.asked = list(randoms), list(ints), []

    def random(self):
        return self.randoms.pop(0)

    def randint(self, low, high):
        self.asked.append((low, high))
        return self.ints.pop(0)


def testUniformBonusIsZeroToMultiplierTimesLevel():
    rng = Rng(ints=[5])
    assert Fortune.bonus("arris:wild_carrots", "minecraft:iron_hoe", None, 3, [], rng) == ("minecraft:carrot", 5)
    assert rng.asked == [(0, 6)]                                     # bonusMultiplier 2 × 时运 3
    rng = Rng(ints=[1])
    assert Fortune.bonus("arris:tomatoes_vine_stage3", None, None, 2, [], rng) == ("arris:tomato", 1)
    assert rng.asked == [(0, 2)]                                     # 番茄 bonusMultiplier 1
    assert Fortune.bonus("arris:wild_onions", None, None, 1, [], Rng(ints=[0])) is None      # 抽到 0：不多掉


def testBinomialBonusRollsOnlyTheExtraLevels():
    # JE 掷 等级 + 3 次，表里已经有 3 次：补的是"等级"次，每次 p = 0.5714286
    assert Fortune.bonus("arris:cabbages_stage7", None, None, 3, [], Rng(randoms=[0.1, 0.9, 0.5])) == ("arris:cabbage_seeds", 2)
    assert Fortune.bonus("arris:onions_stage3", None, None, 1, [], Rng(randoms=[0.6])) is None


def testNoFortuneShearsAndUnripeGetNothing():
    assert Fortune.bonus("arris:wild_carrots", None, None, 0, [], Rng()) is None
    assert Fortune.bonus("arris:wild_carrots", "minecraft:shears", None, 3, [], Rng(ints=[4])) is None      # 剪刀：掉的是它自己
    assert Fortune.bonus("arris:wild_carrots", "othermod:steel_shears", "shears", 3, [], Rng(ints=[4])) is None   # 别的模组的剪刀（itemType）
    assert Fortune.bonus("arris:cabbages_stage6", None, None, 3, [], Rng()) is None                         # 没熟
    assert Fortune.bonus("arris:sandy_shrub", None, None, 2, [], Rng(ints=[3])) is None                     # 12.5% 没中：没掉种子不补
    assert Fortune.bonus("arris:sandy_shrub", None, None, 2, ["minecraft:beetroot_seeds"], Rng(ints=[3])) == ("minecraft:beetroot_seeds", 3)


def testFortuneLevelComesFromTheEnchantData():
    assert Fortune.fortuneLevel({"enchantData": [(17, 3), (18, 2)]}) == 2
    assert Fortune.fortuneLevel({"enchantData": []}) == 0 and Fortune.fortuneLevel(None) == 0


def _je():
    found = {}
    for name in sorted(os.listdir(JE_DIR)):
        with io.open(os.path.join(JE_DIR, name), encoding="utf-8") as handle:
            table = json.load(handle)

        def firstItem(node):
            if isinstance(node, dict):
                if node.get("type") == "minecraft:item":
                    return node.get("name")
                node = list(node.values())
            for value in node if isinstance(node, list) else ():
                found = firstItem(value)
                if found:
                    return found
            return None

        def walk(node, item=None):
            if isinstance(node, dict):
                item = node.get("name", item) if node.get("type") == "minecraft:item" else item
                if "entries" in node:                                # 番茄那两张把 apply_bonus 写在池子上，物品在池子的条目里
                    item = firstItem(node["entries"]) or item
                if node.get("function") == "minecraft:apply_bonus":
                    found[name[:-len(".json")]] = (item, node["formula"], node["parameters"])
                for value in node.values():
                    walk(value, item)
            elif isinstance(node, list):
                for value in node:
                    walk(value, item)
        walk(table)
    return found


def testTheTableIsJavasOwn():
    if not os.path.isdir(JE_DIR):
        print("跳过：没有 JE 的源码（.refs/FarmersDelight）")
        return
    je = _je()
    assert len(je) == len(Fortune.TABLE) == 11
    for name, (item, formula, parameters) in je.items():
        block = JE_BLOCKS.get(name, "arris:" + name)
        ours = Fortune.TABLE[block]
        assert ours[0] == JE_ITEMS.get(item, item), (name, item, ours)
        if formula == "minecraft:binomial_with_bonus_count":
            assert ours[1:3] == (Fortune.BINOMIAL, parameters["probability"]) and parameters["extra"] == 3, name
        else:
            assert formula == "minecraft:uniform_bonus_count" and ours[1:3] == (Fortune.UNIFORM, parameters["bonusMultiplier"]), name
        assert ours[3] == name.startswith(("wild_", "sandy_")), name      # JE 里有剪刀那一支的才看剪刀


# ---- 服务端 ----

def _destroy(name, hand, creative=False, drops=()):
    LEVEL.__init__()
    DROPPED.clear()
    if hand:
        LEVEL.hands["p1"] = hand
    if creative:
        LEVEL.creative.add("p1")
    ids = []
    for index, itemName in enumerate(drops):
        DROPPED["e%d" % index] = {"newItemName": itemName, "count": 1}
        ids.append("e%d" % index)
    args = {"fullName": name, "x": 1, "y": 64, "z": 2, "playerId": "p1", "dimensionId": 0, "dropEntityIds": ids, "auxData": 0}
    Registry.dispatch("DestroyBlockEvent", args, name)
    return [(entity[0]["itemName"], entity[0]["count"], entity[2]) for entity in LEVEL.entities]


def testTheServerDropsTheBonusAtTheBlock():
    FortuneDrops.random = Rng(ints=[4])
    hoe = {"newItemName": "minecraft:diamond_hoe", "count": 1, "enchantData": [(18, 3)]}
    assert _destroy("arris:wild_potatoes", hoe) == [("minecraft:potato", 4, (1.5, 64.5, 2.5))]
    FortuneDrops.random = Rng(ints=[4])
    assert _destroy("arris:wild_potatoes", hoe, creative=True) == []                    # 创造模式：没有掉落，也不补
    assert _destroy("arris:wild_potatoes", {"newItemName": "minecraft:diamond_hoe", "count": 1}) == []     # 没有时运
    assert _destroy("arris:wild_potatoes", None) == []                                   # 空手
    FortuneDrops.random = Rng(ints=[2])
    assert _destroy("arris:sandy_shrub", hoe, drops=["minecraft:beetroot_seeds"]) == [("minecraft:beetroot_seeds", 2, (1.5, 64.5, 2.5))]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
