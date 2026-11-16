# -*- coding: utf-8 -*-
# runner: both
"""刀的额外掉落与洋葱掉落（Shared/Data/MobLoot.py、Shared/Rules/MobLoot.py）。

期望值抄自 JE 的战利品修饰器 data/farmersdelight/loot_modifiers/scavenging_*.json、add_onion_to_*.json：
牛 / 哞菇 / 马 / 驴 / 骡 / 羊驼 / 行商羊驼多 1 皮革，鸡 1 羽毛，兔 1 兔皮，蜘蛛 / 洞穴蜘蛛 1 线，潜影贝 1 潜影壳；
猪 50% + 抢夺每级 10% 掉火腿（着火掉烟熏火腿），疣猪兽必掉；僵尸 / 尸壳 / 僵尸村民 / 掠夺者 / 唤魔者 / 卫道士被玩家杀死
2% + 抢夺每级 1% 掉洋葱。
"""
from __future__ import print_function

import fdtest

Data = fdtest.load("Shared.Data.MobLoot")
Rules = fdtest.load("Shared.Rules.MobLoot")

ALWAYS = lambda percent: True   # noqa: E731
NEVER = lambda percent: False   # noqa: E731


def _recorder():
    seen = []

    def roll(percent):
        seen.append(percent)
        return False
    return roll, seen


def testKnifeAddsExactlyTheJeExtraDrops():
    expected = {
        "minecraft:cow": "minecraft:leather", "minecraft:mooshroom": "minecraft:leather",
        "minecraft:horse": "minecraft:leather", "minecraft:donkey": "minecraft:leather",
        "minecraft:mule": "minecraft:leather", "minecraft:llama": "minecraft:leather",
        "minecraft:trader_llama": "minecraft:leather",
        "minecraft:chicken": "minecraft:feather", "minecraft:rabbit": "minecraft:rabbit_hide",
        "minecraft:spider": "minecraft:string", "minecraft:cave_spider": "minecraft:string",
        "minecraft:shulker": "minecraft:shulker_shell",
    }
    assert sorted(Data.KNIFE_EXTRA_DROPS) == sorted(expected)
    for entity, item in expected.items():
        assert Rules.knifeDrops(entity, False, 0, NEVER) == [(item, 1)], entity


def testKnifeDoesNotDoubleCowOrChickenDrops():
    # 旧版把牛和鸡的全部掉落翻倍，JE 只额外给一个皮革 / 羽毛；规则层不再碰原有掉落，也不对这两种生物掉火腿
    assert Rules.knifeDrops("minecraft:cow", False, 3, ALWAYS) == [("minecraft:leather", 1)]
    assert Rules.knifeDrops("minecraft:chicken", True, 3, ALWAYS) == [("minecraft:feather", 1)]


def testPigHamIsHalfPlusTenPerLooting():
    roll, seen = _recorder()
    for looting in (0, 1, 2, 3):
        Rules.knifeDrops("minecraft:pig", False, looting, roll)
    assert seen == [50, 60, 70, 80]
    assert Rules.knifeDrops("minecraft:pig", False, 0, ALWAYS) == [("arris:ham", 1)]
    assert Rules.knifeDrops("minecraft:pig", False, 0, NEVER) == []


def testBurningPigAndHoglinDropSmokedHam():
    assert Rules.knifeDrops("minecraft:pig", True, 0, ALWAYS) == [("arris:smoked_ham", 1)]
    assert Rules.knifeDrops("minecraft:pig", True, 0, NEVER) == []
    assert Rules.knifeDrops("minecraft:hoglin", True, 0, NEVER) == [("arris:smoked_ham", 1)]


def testHoglinAlwaysDropsHamAndNeverRolls():
    roll, seen = _recorder()
    assert Rules.knifeDrops("minecraft:hoglin", False, 3, roll) == [("arris:ham", 1)]
    assert seen == []


def testHamChanceIsCappedAtOneHundredPercent():
    roll, seen = _recorder()
    Rules.knifeDrops("minecraft:pig", False, 9, roll)
    assert seen == [100]
    assert Rules.chanceWithLooting(2, 1, -5) == 2     # 负数抢夺当 0


def testOnionDropIsTwoPercentPlusOnePerLooting():
    roll, seen = _recorder()
    for looting in (0, 1, 3):
        Rules.onionDrops("minecraft:zombie", looting, roll)
    assert seen == [2, 3, 5]
    assert Rules.onionDrops("minecraft:zombie", 0, ALWAYS) == [("arris:onion", 1)]
    assert Rules.onionDrops("minecraft:zombie", 0, NEVER) == []


def testOnionMobs():
    expected = ["minecraft:zombie", "minecraft:husk", "minecraft:zombie_villager", "minecraft:zombie_villager_v2",
                "minecraft:pillager", "minecraft:evocation_illager", "minecraft:vindicator"]
    assert sorted(Data.ONION_MOBS) == sorted(expected)
    for mob in expected:
        assert Rules.onionDrops(mob, 0, ALWAYS) == [("arris:onion", 1)], mob
    for other in ("minecraft:drowned", "minecraft:zombie_pigman", "minecraft:villager_v2", "minecraft:cow"):
        assert Rules.onionDrops(other, 3, ALWAYS) == [], other


def testEnchantLevelReadsEngineLists():
    assert Rules.enchantLevel(None, Rules.LOOTING) == 0
    assert Rules.enchantLevel({"newItemName": "arris:iron_knife"}, Rules.LOOTING) == 0
    assert Rules.enchantLevel({"enchantData": []}, Rules.LOOTING) == 0
    assert Rules.enchantLevel({"enchantData": [(9, 4), (14, 2)]}, Rules.LOOTING) == 2
    assert Rules.enchantLevel({"enchantData": [[16, 1]]}, Rules.SILK_TOUCH) == 1


def testLootEntriesAreEngineItemDicts():
    assert Rules.lootEntries([("arris:ham", 1), ("minecraft:leather", 2)]) == [
        {"newItemName": "arris:ham", "newAuxValue": 0, "count": 1},
        {"newItemName": "minecraft:leather", "newAuxValue": 0, "count": 2}]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
