# -*- coding: utf-8 -*-
"""Remainders - 原料用掉以后剩下的容器（双端，纯数据）

照 JE：物品自带的合成剩余物（Item.getCraftingRemainingItem）。原版是奶桶 / 水桶 / 岩浆桶剩空桶、蜂蜜瓶 / 龙息剩玻璃瓶；
FD 1.20 的 ModItems 里碗装食物（bowlFoodItem）和番茄酱剩碗，饮料（drinkItem）和发光浆果蛋奶沙司剩玻璃瓶。
工作台合成（ResultSlot：剩余物放回原来那格，那格没空就进背包）、砧板摆盘（Hands-On Delight 的 Assembling）、
厨锅（CookingPotBlockEntity）都按它还。厨锅另有 INGREDIENT_REMAINDER_OVERRIDES：鱼桶 / 细雪桶剩空桶，
原版的炖菜和汤剩碗，药水、附魔之瓶剩玻璃瓶（POT_OVERRIDES）。物品名比较，不看 aux（药水的种类在 aux 里，都剩玻璃瓶）。
"""
_BUCKET, _BOWL, _BOTTLE = "minecraft:bucket", "minecraft:bowl", "minecraft:glass_bottle"

CRAFT = {
    "minecraft:milk_bucket": _BUCKET,
    "minecraft:water_bucket": _BUCKET,
    "minecraft:lava_bucket": _BUCKET,
    "minecraft:honey_bottle": _BOTTLE,
    "minecraft:dragon_breath": _BOTTLE,
    # FD 的饮料（drinkItem）
    "arris:milk_bottle": _BOTTLE,
    "arris:hot_cocoa": _BOTTLE,
    "arris:apple_cider": _BOTTLE,
    "arris:melon_juice": _BOTTLE,
    "arris:glow_berry_custard": _BOTTLE,
    # FD 的碗装食物（bowlFoodItem）和番茄酱；JE 的 beef_stew 在这边叫 cookbeef_stew
    "arris:tomato_sauce": _BOWL,
    "arris:cooked_rice": _BOWL,
    "arris:bone_broth": _BOWL,
    "arris:cookbeef_stew": _BOWL,
    "arris:chicken_soup": _BOWL,
    "arris:vegetable_soup": _BOWL,
    "arris:fish_stew": _BOWL,
    "arris:fried_rice": _BOWL,
    "arris:pumpkin_soup": _BOWL,
    "arris:baked_cod_stew": _BOWL,
    "arris:noodle_soup": _BOWL,
    "arris:onion_soup": _BOWL,
    "arris:bacon_and_eggs": _BOWL,
    "arris:pasta_with_meatballs": _BOWL,
    "arris:pasta_with_mutton_chop": _BOWL,
    "arris:mushroom_rice": _BOWL,
    "arris:roasted_mutton_chops": _BOWL,
    "arris:vegetable_noodles": _BOWL,
    "arris:steak_and_potatoes": _BOWL,
    "arris:ratatouille": _BOWL,
    "arris:squid_ink_pasta": _BOWL,
    "arris:grilled_salmon": _BOWL,
    "arris:fruit_salad": _BOWL,
    "arris:mixed_salad": _BOWL,
    "arris:nether_salad": _BOWL,
    "arris:roast_chicken": _BOWL,
    "arris:stuffed_pumpkin": _BOWL,
    "arris:honey_glazed_ham": _BOWL,
    "arris:shepherds_pie": _BOWL,
    "arris:dog_food": _BOWL,
}

# 厨锅额外认的（JE CookingPotBlockEntity.INGREDIENT_REMAINDER_OVERRIDES）
POT_OVERRIDES = {
    "minecraft:powder_snow_bucket": _BUCKET,
    "minecraft:axolotl_bucket": _BUCKET,
    "minecraft:cod_bucket": _BUCKET,
    "minecraft:pufferfish_bucket": _BUCKET,
    "minecraft:salmon_bucket": _BUCKET,
    "minecraft:tropical_fish_bucket": _BUCKET,
    "minecraft:suspicious_stew": _BOWL,
    "minecraft:mushroom_stew": _BOWL,
    "minecraft:rabbit_stew": _BOWL,
    "minecraft:beetroot_soup": _BOWL,
    "minecraft:potion": _BOTTLE,
    "minecraft:splash_potion": _BOTTLE,
    "minecraft:lingering_potion": _BOTTLE,
    "minecraft:experience_bottle": _BOTTLE,
}


def craftRemainderOf(itemName):
    """工作台 / 砧板用掉这件原料剩下什么（物品名），没有返回 None。"""
    return CRAFT.get(itemName)


def potRemainderOf(itemName):
    """厨锅用掉这件食材吐出什么（物品名），没有返回 None。"""
    return CRAFT.get(itemName) or POT_OVERRIDES.get(itemName)
