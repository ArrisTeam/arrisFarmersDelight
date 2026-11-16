# -*- coding: utf-8 -*-
# runner: both
"""煎锅数值与数据对 JE 1.3.4：营火配方表（煎锅 / 炉灶 / 手持煎锅都读它）。

参照表抄自 JE 的 data：原版 campfire_cooking 配方和 FD 的 SmeltingRecipes.foodSmeltingRecipes，不依赖 .refs。
"""
from __future__ import print_function, unicode_literals

import fdtest

Cooking = fdtest.load("Shared.Data.Cooking")

# JE 的营火烹饪配方：原版 9 条 + FD 的 7 条（FD 的物品换成本模组的名字），时间一律 600 刻（30 秒）
JE_CAMPFIRE_RECIPES = {
    "minecraft:beef": "minecraft:cooked_beef",
    "minecraft:chicken": "minecraft:cooked_chicken",
    "minecraft:cod": "minecraft:cooked_cod",
    "minecraft:kelp": "minecraft:dried_kelp",
    "minecraft:mutton": "minecraft:cooked_mutton",
    "minecraft:porkchop": "minecraft:cooked_porkchop",
    "minecraft:potato": "minecraft:baked_potato",
    "minecraft:rabbit": "minecraft:cooked_rabbit",
    "minecraft:salmon": "minecraft:cooked_salmon",
    # FD：fried_egg / beef_patty / cooked_chicken_cuts / cooked_cod_slice / cooked_salmon_slice / cooked_bacon / cooked_mutton_chops
    "minecraft:egg": "arris:fried_egg",
    "arris:minced_beef": "arris:beef_patty",
    "arris:chicken_cuts": "arris:cooked_chicken_cuts",
    "arris:cod_slice": "arris:cooked_cod_slice",
    "arris:salmon_slice": "arris:cooked_salmon_slice",
    "arris:bacon": "arris:cooked_bacon",
    "arris:mutton_chops": "arris:cooked_mutton_chops",
}


def testCookableFoodIsExactlyTheJeCampfireRecipes():
    table = dict(Cooking.CanCookedFoodDict)
    missing = sorted(set(JE_CAMPFIRE_RECIPES) - set(table))
    extra = sorted(set(table) - set(JE_CAMPFIRE_RECIPES))
    assert not missing and not extra, "缺 %s，多 %s" % (missing, extra)
    assert table == JE_CAMPFIRE_RECIPES


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
