# -*- coding: utf-8 -*-
"""jefood - 食物 / 小刀物品 JSON 对 JE 1.3.4 的参照表与读取小工具（不是测试本身，跑器只收 test_*.py）

参照表抄自 FarmersDelight 1.20.1 的 common/FoodValues.java 与 registry/ModItems.java（不依赖 .refs，离线可跑）。
"""
from __future__ import print_function, unicode_literals

import io
import json
import os

import fdtest

BEH = os.path.join(fdtest.ROOT, "bp", "netease_items_beh")
RES = os.path.join(fdtest.ROOT, "rp", "netease_items_res")
EFFECT_DIR = os.path.join(fdtest.ROOT, "bp", "netease_effects")

CONTAINERS = {"bowl": "minecraft:bowl", "bottle": "minecraft:glass_bottle", None: None}

# 物品短名: (营养, 饱和系数, 使用时长 tick, 容器, 可随时吃, 堆叠上限)
# 使用时长：JE 的快食 16、KelpRollItem 64、其余（含 DrinkableItem）32；容器：bowlFoodItem / 饮品 / 发光浆果布丁
FOODS = {
    "cabbage": (2, 0.4, 32, None, False, 64),
    "tomato": (1, 0.3, 32, None, False, 64),
    "onion": (2, 0.4, 32, None, False, 64),
    "apple_cider": (0, 0.0, 32, "bottle", True, 16),
    "fried_egg": (4, 0.4, 32, None, False, 64),
    "tomato_sauce": (4, 0.4, 32, "bowl", False, 64),
    "wheat_dough": (2, 0.3, 32, None, False, 64),
    "raw_pasta": (2, 0.3, 32, None, False, 64),
    "pie_crust": (2, 0.2, 32, None, False, 64),
    "pumpkin_slice": (3, 0.3, 32, None, False, 64),
    "cabbage_leaf": (1, 0.4, 16, None, False, 64),
    "minced_beef": (2, 0.3, 16, None, False, 64),
    "beef_patty": (4, 0.8, 16, None, False, 64),
    "chicken_cuts": (1, 0.3, 16, None, False, 64),
    "cooked_chicken_cuts": (3, 0.6, 16, None, False, 64),
    "bacon": (2, 0.3, 16, None, False, 64),
    "cooked_bacon": (4, 0.8, 16, None, False, 64),
    "cod_slice": (1, 0.1, 16, None, False, 64),
    "cooked_cod_slice": (3, 0.5, 16, None, False, 64),
    "salmon_slice": (1, 0.1, 16, None, False, 64),
    "cooked_salmon_slice": (3, 0.8, 16, None, False, 64),
    "mutton_chops": (1, 0.3, 16, None, False, 64),
    "cooked_mutton_chops": (3, 0.8, 16, None, False, 64),
    "ham": (5, 0.3, 32, None, False, 64),
    "smoked_ham": (10, 0.8, 32, None, False, 64),
    "melon_popsicle": (3, 0.2, 16, None, True, 64),
    "sweet_berry_cookie": (2, 0.1, 16, None, False, 64),
    "honey_cookie": (2, 0.1, 16, None, False, 64),
    "cake_slice": (2, 0.1, 16, None, False, 64),
    "apple_pie_slice": (3, 0.3, 16, None, False, 64),
    "sweet_berry_cheesecake_slice": (3, 0.3, 16, None, False, 64),
    "chocolate_pie_slice": (3, 0.3, 16, None, False, 64),
    "pumpkin_pie_slice": (3, 0.3, 16, None, False, 64),
    "fruit_salad": (6, 0.6, 32, "bowl", False, 16),
    "glow_berry_custard": (7, 0.6, 32, "bottle", True, 16),
    "mixed_salad": (6, 0.6, 32, "bowl", False, 16),
    "nether_salad": (5, 0.4, 32, "bowl", False, 16),
    "barbecue_stick": (8, 0.9, 32, None, False, 64),
    "egg_sandwich": (8, 0.8, 32, None, False, 64),
    "chicken_sandwich": (10, 0.8, 32, None, False, 64),
    "hamburger": (11, 0.8, 32, None, False, 64),
    "bacon_sandwich": (10, 0.8, 32, None, False, 64),
    "mutton_wrap": (10, 0.8, 32, None, False, 64),
    "dumplings": (8, 0.8, 32, None, False, 64),
    "stuffed_potato": (10, 0.7, 32, None, False, 64),
    "cabbage_rolls": (5, 0.5, 32, None, False, 64),
    "salmon_roll": (7, 0.6, 32, None, False, 64),
    "cod_roll": (7, 0.6, 32, None, False, 64),
    "kelp_roll": (12, 0.6, 64, None, False, 64),
    "kelp_roll_slice": (6, 0.5, 16, None, False, 64),
    "cooked_rice": (6, 0.4, 32, "bowl", False, 16),
    "bone_broth": (8, 0.7, 32, "bowl", False, 16),
    "cookbeef_stew": (12, 0.8, 32, "bowl", False, 16),
    "vegetable_soup": (12, 0.8, 32, "bowl", False, 16),
    "fish_stew": (12, 0.8, 32, "bowl", False, 16),
    "chicken_soup": (12, 0.8, 32, "bowl", False, 16),
    "fried_rice": (12, 0.8, 32, "bowl", False, 16),
    "onion_soup": (12, 0.8, 32, "bowl", False, 16),
    "pumpkin_soup": (14, 0.75, 32, "bowl", False, 16),
    "baked_cod_stew": (14, 0.75, 32, "bowl", False, 16),
    "noodle_soup": (14, 0.75, 32, "bowl", False, 16),
    "bacon_and_eggs": (10, 0.6, 32, "bowl", False, 16),
    "ratatouille": (10, 0.6, 32, "bowl", False, 16),
    "steak_and_potatoes": (12, 0.8, 32, "bowl", False, 16),
    "pasta_with_meatballs": (12, 0.8, 32, "bowl", False, 16),
    "pasta_with_mutton_chop": (12, 0.8, 32, "bowl", False, 16),
    "mushroom_rice": (12, 0.8, 32, "bowl", False, 16),
    "roasted_mutton_chops": (14, 0.75, 32, "bowl", False, 16),
    "vegetable_noodles": (14, 0.75, 32, "bowl", False, 16),
    "squid_ink_pasta": (14, 0.75, 32, "bowl", False, 16),
    "grilled_salmon": (14, 0.75, 32, "bowl", False, 16),
    "roast_chicken": (14, 0.75, 32, "bowl", False, 16),
    "stuffed_pumpkin": (14, 0.75, 32, "bowl", False, 16),
    "honey_glazed_ham": (14, 0.75, 32, "bowl", False, 16),
    "shepherds_pie": (14, 0.75, 32, "bowl", False, 16),
    "dog_food": (4, 0.2, 32, "bowl", False, 16),
}

# 食物吃下后的效果：物品短名 -> [(效果名, 秒, 等级, 概率)]；没列出的食物没有效果。
# FoodValues.java 的 tick 除以 20；发光（发光浆果布丁）基岩版没有，不抄。
NOURISHMENT = "arris:nourishment"
EFFECTS = {}


def _give(effects, *names):
    for name in names:
        EFFECTS[name] = effects


_give([("absorption", 60, 0, 1.0)], "apple_cider")
_give([(NOURISHMENT, 30, 0, 1.0)], "cooked_rice")
_give([(NOURISHMENT, 60, 0, 1.0)], "bone_broth", "bacon_and_eggs", "ratatouille")
_give([(NOURISHMENT, 180, 0, 1.0)], "onion_soup", "cookbeef_stew", "vegetable_soup", "fish_stew", "chicken_soup", "fried_rice",
      "steak_and_potatoes", "pasta_with_meatballs", "pasta_with_mutton_chop", "mushroom_rice", "grilled_salmon")
_give([(NOURISHMENT, 300, 0, 1.0)], "pumpkin_soup", "baked_cod_stew", "noodle_soup", "roasted_mutton_chops",
      "vegetable_noodles", "squid_ink_pasta", "roast_chicken", "stuffed_pumpkin", "honey_glazed_ham", "shepherds_pie")
_give([("hunger", 30, 0, 0.3)], "wheat_dough", "raw_pasta", "chicken_cuts")
_give([("nausea", 12, 0, 0.3)], "nether_salad")
_give([("regeneration", 5, 0, 1.0)], "fruit_salad", "mixed_salad")
_give([("speed", 20, 0, 1.0)], "cake_slice")
_give([("speed", 30, 0, 1.0)], "apple_pie_slice", "sweet_berry_cheesecake_slice", "chocolate_pie_slice", "pumpkin_pie_slice")

# 效果提示（netease:customtips）：蓝字 = 有益，红字 = 有害，名字用基岩版中文，等级 >= 1 带罗马数字，时长 mm:ss
ZH_NAMES = {"speed": "速度", "regeneration": "生命恢复", "absorption": "伤害吸收", "hunger": "饥饿", "nausea": "反胃",
            "arris:nourishment": "滋养", "arris:comfort": "舒适"}
HARMFUL = frozenset(("hunger", "nausea"))
ROMAN = ("", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ")
# 提示不是效果表生成的：喂食说明、清除说明
CUSTOM_TIPS = frozenset(("milk_bottle", "hot_cocoa", "melon_juice", "dog_food", "horse_feed"))

# 小刀：(耐久, 附魔能力, 防火)。耐久 = JE 材质档的 uses（燧石是 ModMaterials.FLINT，其余原版 Tiers），
# 附魔能力 = 材质档的 enchantmentValue；下界合金刀 ModItems 里是 fireResistant()
KNIVES = {
    "flint": (131, 5, False),
    "iron": (250, 14, False),
    "diamond": (1561, 10, False),
    "netherite": (2031, 15, True),
    "golden": (32, 22, False),
}

# JE 里不是 FoodProperties、靠 Item 子类结算效果的饮品（DrinkableItem：喝的动画、32 刻、随时能喝、还回玻璃瓶、堆叠 16）
DRINKS = ("milk_bottle", "hot_cocoa", "melon_juice")
# DrinkableItem（含 FoodProperties 的苹果酒、骨汤）：喝的动画
DRINKABLE = frozenset(("apple_cider", "bone_broth") + DRINKS)


def _read(path):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def beh(short):
    """行为包物品的 components。"""
    return _read(os.path.join(BEH, "arris_%s.json" % short))["minecraft:item"]["components"]


def description(short):
    """行为包物品的 description。"""
    return _read(os.path.join(BEH, "arris_%s.json" % short))["minecraft:item"]["description"]


def res(short):
    """资源包物品的 components。"""
    return _read(os.path.join(RES, "arris_%s.json" % short))["minecraft:item"]["components"]


def shortNames(directory):
    return sorted(name[len("arris_"):-len(".json")] for name in os.listdir(directory)
                  if name.startswith("arris_") and name.endswith(".json"))


def tooltipOf(effects):
    """按效果表生成 netease:customtips 的文字，一行一个效果：§9速度 (00:30)。"""
    lines = []
    for name, seconds, amplifier, _chance in effects:
        color = "§c" if name in HARMFUL else "§9"
        lines.append("%s%s%s (%02d:%02d)" % (color, ZH_NAMES[name], ROMAN[amplifier], seconds // 60, seconds % 60))
    return "\n".join(lines)
