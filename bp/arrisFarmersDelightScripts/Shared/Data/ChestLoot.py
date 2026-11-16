# -*- coding: utf-8 -*-
"""ChestLoot - 战利品箱里额外掷出的农夫乐事物品（双端，纯数据）

照 JE 的 FDChestLoot（data/farmersdelight/loot_tables/chests/fd_*.json）：JE 用战利品修饰器 add_loot_table，把下面这些表在原版箱子
的表之外再掷一次、掷出的东西加进箱子。这里的表名是基岩版原版战利品表的名字（去掉 loot_tables/ 和 .json；JE 的
shipwreck_supply 在基岩版叫 shipwrecksupply）。原版的表一个字不动，在箱子第一次被打开时由服务端追加（Server/ChestLoot.py）。

池：{"rolls": (最少, 最多), "entries": [...]}，每次抽一个条目，次数在区间里均匀取（含两端，同 JE 的 UniformGenerator）。
条目：{"item": 物品名或 None（空条目）, "weight": 权重, "count": (最少, 最多) 或 None（1 个）, "enchant": 附魔方式或 None}。
附魔方式："random" 是 JE 的 enchant_randomly（随机一种、随机等级），"levels" 是 enchant_with_levels 20 到 39 级（可出宝藏附魔，
一到三种）。JE 里这几件还带 set_damage（只剩 15% 到 80% 耐久），这里掉出来的是满耐久。
"""


def _item(name, count=None, weight=1, enchant=None):
    return {"item": name, "weight": weight, "count": count, "enchant": enchant}


def _empty(weight):
    return {"item": None, "weight": weight, "count": None, "enchant": None}


def _pool(rolls, *entries):
    return {"rolls": rolls, "entries": list(entries)}


# 菜刀的"随机适用附魔"：JE 里 FD 的刀是挖掘类工具，适用的是效率、精准采集、时运、耐久、经验修补、消失诅咒
# (基岩版的附魔编号, 最高等级)：15 效率、16 精准采集、18 时运、17 耐久、26 经验修补、28 消失诅咒
KNIFE_ENCHANTS = ((15, 5), (16, 1), (18, 3), (17, 3), (26, 1), (28, 1))

CHEST_LOOT = {
    "chests/abandoned_mineshaft": [
        _pool((1, 1), _item("arris:cooking_pot"), _item("arris:skillet_item"), _empty(6)),
        _pool((1, 4), _item("arris:tomato_seeds", (2, 4)), _item("arris:cabbage_seeds", (2, 4)),
              _item("arris:rice", (2, 4)), _empty(2)),
        _pool((3, 3), _item("arris:rope", (2, 12)), _empty(2)),
    ],
    "chests/bastion_hoglin_stable": [
        _pool((1, 1), _item("arris:diamond_knife", enchant="random"),
              _item("arris:golden_knife", weight=2, enchant="random"), _empty(2)),
        _pool((1, 2), _item("arris:ham", (2, 5), weight=4), _item("arris:smoked_ham", (2, 5), weight=2), _empty(2)),
    ],
    "chests/bastion_treasure": [
        _pool((1, 1), _item("arris:diamond_knife", enchant="random"), _item("arris:diamond_knife"), _empty(6)),
    ],
    "chests/end_city_treasure": [
        _pool((1, 1), _item("arris:diamond_knife", enchant="levels"), _item("arris:iron_knife", enchant="levels"),
              _empty(6)),
    ],
    "chests/pillager_outpost": [
        _pool((1, 2), _item("arris:onion", (4, 12), weight=5), _item("arris:onion_crate", (1, 3), weight=2), _empty(2)),
    ],
    "chests/ruined_portal": [
        _pool((1, 1), _item("arris:golden_knife", enchant="random"), _empty(3)),
    ],
    "chests/shipwrecksupply": [
        _pool((1, 2), _item("arris:tomato_seeds", (2, 4), weight=6), _item("arris:cabbage_seeds", (2, 4), weight=6),
              _item("arris:onion", (2, 4), weight=6), _item("arris:rice", (2, 4), weight=6)),
        _pool((1, 3), _item("arris:rope", (4, 12), weight=2), _empty(1)),
    ],
    "chests/simple_dungeon": [
        _pool((1, 4), _item("arris:tomato_seeds", (2, 4)), _item("arris:cabbage_seeds", (2, 4)), _empty(2)),
        _pool((3, 3), _item("arris:rope", (2, 12)), _empty(2)),
    ],
    "chests/village/village_butcher": [
        _pool((1, 1), _item("arris:flint_knife"), _item("arris:iron_knife"), _empty(1)),
        _pool((1, 2), _item("arris:ham"), _item("arris:minced_beef", (2, 6), weight=3),
              _item("arris:bacon", (2, 6), weight=3), _item("arris:mutton_chops", (2, 6), weight=3), _empty(1)),
    ],
    "chests/village/village_desert_house": [
        _pool((1, 3), _item("arris:tomato_seeds", (1, 3)), _item("arris:rice", (1, 3))),
    ],
    "chests/village/village_plains_house": [
        _pool((1, 3), _item("arris:onion", (1, 3)), _item("arris:tomato_seeds", (1, 3))),
    ],
    "chests/village/village_savanna_house": [
        _pool((1, 3), _item("arris:tomato_seeds", (1, 3)), _item("arris:cabbage_seeds", (1, 3))),
    ],
    "chests/village/village_snowy_house": [
        _pool((1, 3), _item("arris:onion", (1, 3)), _item("arris:cabbage_seeds", (1, 3))),
    ],
    "chests/village/village_taiga_house": [
        _pool((1, 3), _item("arris:cabbage_seeds", (1, 3)), _item("arris:rice", (1, 3))),
    ],
}
