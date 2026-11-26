# -*- coding: utf-8 -*-
"""Mobs - 狗粮 / 马饲料的喂食规则，给原版狼、马类追加的实体组件（JSON 串），原版动物认农夫乐事的食物（双端，纯数据）

喂食（右键驯服的生物）照 JE 的 DogFoodItem / HorseFeedItem；吸引（tempt / beg）照 JE 的 CommonEvents.onAnimalsJoinWorld：
马、驴、骡被马饲料吸引，狼向狗粮和农夫乐事的十种肉讨食（JE 的狼对所有 isMeat 的食物讨食）。
追加的 tempt / beg 会整个盖掉原版同名组件，所以这几个 JSON 都是原版（3.10）的同名组件加上本模组的物品，原版没动的字段原样抄来
（horse / wolf 两张是对外联动契约，下游可以往里加，所以照旧是写死的 JSON 串）。

猫、鸡、猪、兔子、鹦鹉、狼认农夫乐事的食物（吸引、繁殖、喂小崽、驯服、治疗）是 ANIMAL_FOOD：不写死 JSON，
服务端读生效的实体定义、在定义里的列表末尾追加这些条目，按实体现在的组件组下发（Server/AnimalFood.py，规则 Shared/Rules/AnimalFood.py）。

喂食要靠 bribeable 这个"记号"组件：官方文档说"玩家右键实体"事件（PlayerInteractServerEvent）在玩家"可以与实体交互"时才来，
也就是目标对手里的物品有交互时；没有交互的话马饲料触发不了这个事件，狗粮（现在是能吃的）还会被玩家吃掉。bribeable 是原版
只有海豚用的"贿赂"组件，加在马和狼身上没有任何自带行为，只让引擎认为"这个物品能对它用"（按钮写"喂食"）；
真正的喂食由 Server/Livestock.py 在右键事件里处理并取消，所以引擎自己的"贿赂"从不执行。
"""
HORSE_FEED = "arris:horse_feed"
DOG_FOOD = "arris:dog_food"

# 喂食对哪些生物有效（JE 的 horse_feed_users / dog_food_users 实体标签），生物还得是驯服的
FEED_USERS = {
    HORSE_FEED: ("minecraft:horse", "minecraft:skeleton_horse", "minecraft:zombie_horse", "minecraft:donkey",
                 "minecraft:mule", "minecraft:llama"),
    DOG_FOOD: ("minecraft:wolf",),
}
# 喂食后的状态效果：(效果名, 秒, 等级 - 1)。JE 都是 6000 刻 = 300 秒
FEED_EFFECTS = {
    HORSE_FEED: (("speed", 300, 1), ("jump_boost", 300, 0)),
    DOG_FOOD: (("speed", 300, 0), ("strength", 300, 0), ("resistance", 300, 0)),
}
FEED_SOUNDS = {HORSE_FEED: "mob.horse.eat", DOG_FOOD: "random.eat"}
# 吃掉后还给玩家的容器（JE 的 craftRemainder），创造模式不给
FEED_RETURNS = {DOG_FOOD: "minecraft:bowl"}

_HORSE_TEMPT = '{"priority": 5, "speed_multiplier": 1.2, "items": ["arris:horse_feed", "golden_apple", "appleEnchanted", "golden_carrot"]}'


def _feedMarker(itemName):
    # 这个物品能对它用的记号；bribe_cooldown 为 0（右键事件里总是取消，引擎自己的"贿赂"从来不会执行）
    return '{"bribe_items": ["%s"], "bribe_cooldown": 0}' % itemName


# 下面几个"追加组件"表：键是组件名，值是组件的 JSON 串；horse / wolf 两张是对外联动契约的一部分（下游可以往里加）
horseComponentsDict = {
    "minecraft:behavior.tempt": _HORSE_TEMPT,
    "minecraft:bribeable": _feedMarker(HORSE_FEED),
}

wolfComponentsDict = {
    "minecraft:behavior.beg": '{"priority": 9, "look_distance": 8, "look_time": [2, 4], "items": ["arris:dog_food", "bone", "porkchop", "cooked_porkchop", "chicken", "cooked_chicken", "beef", "cooked_beef", "rotten_flesh", "muttonraw", "muttoncooked", "rabbit", "cooked_rabbit", "arris:minced_beef", "arris:beef_patty", "arris:chicken_cuts", "arris:cooked_chicken_cuts", "arris:bacon", "arris:cooked_bacon", "arris:mutton_chops", "arris:cooked_mutton_chops", "arris:ham", "arris:smoked_ham"]}',
    "minecraft:bribeable": _feedMarker(DOG_FOOD),
}

donkeyComponentsDict = {"minecraft:behavior.tempt": _HORSE_TEMPT, "minecraft:bribeable": _feedMarker(HORSE_FEED)}
muleComponentsDict = {"minecraft:behavior.tempt": _HORSE_TEMPT, "minecraft:bribeable": _feedMarker(HORSE_FEED)}
# 骷髅马、僵尸马、羊驼：只有喂食记号（JE 里它们吃马饲料的增益，但不被马饲料吸引）
skeletonHorseComponentsDict = {"minecraft:bribeable": _feedMarker(HORSE_FEED)}
zombieHorseComponentsDict = {"minecraft:bribeable": _feedMarker(HORSE_FEED)}
llamaComponentsDict = {"minecraft:bribeable": _feedMarker(HORSE_FEED)}

# 实体 -> 要追加的组件表（服务端在实体出现时逐个 AddActorComponent）
livestockComponents = {
    "minecraft:horse": horseComponentsDict,
    "minecraft:donkey": donkeyComponentsDict,
    "minecraft:mule": muleComponentsDict,
    "minecraft:skeleton_horse": skeletonHorseComponentsDict,
    "minecraft:zombie_horse": zombieHorseComponentsDict,
    "minecraft:llama": llamaComponentsDict,
    "minecraft:wolf": wolfComponentsDict,
}

# ---- 原版动物认农夫乐事的食物（JE：CommonSetup 改 Chicken.FOOD_ITEMS、Pig.FOOD_ITEMS、Parrot.TAME_FOOD，Cat.TEMPT_INGREDIENT 加鱼片，
# RabbitsEatCabbageMixin 让卷心菜（标签 crops/cabbage：卷心菜、卷心菜叶）算兔子的食物，狼吃所有 isMeat 的食物）。
# JE 的 isFood 同时管吸引、繁殖、喂小崽：基岩的吸引是 behavior.tempt、繁殖在成年组的 breedable、喂小崽在幼年组的 ageable，都加。
CAT_SLICES = ("arris:cod_slice", "arris:salmon_slice")
CAT_SLICE_HEAL = 1                  # 猫吃一片鱼片回的血：JE 按食物的饱食度，两种鱼片都是 1（原版整条的鱼是 2）
CHICKEN_FOOD = ("arris:cabbage_seeds", "arris:tomato_seeds", "arris:rice")
PIG_FOOD = ("arris:cabbage", "arris:tomato")
RABBIT_FOOD = ("arris:cabbage", "arris:cabbage_leaf")
PARROT_FOOD = CHICKEN_FOOD
# 狼：JE FoodValues 里带 meat() 的 11 种去掉狗粮（狗粮对驯服的狼的右键由 Server/Livestock 接管，JE 的 DogFoodItem 也先于狼自己的喂食）。
# (物品, JE 的饱食度)；治疗量照基岩原版狼的写法 = 饱食度 × 2（原版生猪排饱食度 3、治疗 6，熟猪排 8、16）
WOLF_MEATS = (("arris:minced_beef", 2), ("arris:beef_patty", 4), ("arris:chicken_cuts", 1), ("arris:cooked_chicken_cuts", 3),
              ("arris:bacon", 2), ("arris:cooked_bacon", 4), ("arris:mutton_chops", 1), ("arris:cooked_mutton_chops", 3),
              ("arris:ham", 5), ("arris:smoked_ham", 10))
WOLF_FOOD = tuple(name for name, _food in WOLF_MEATS)


def _healing(pairs):
    return tuple({"item": name, "heal_amount": amount} for name, amount in pairs)


# 实体 -> ((组件, 列表字段, 追加的条目), ...)。组件在顶层还是哪个组件组里不写在这里：定义里凡是带这个组件的地方都追加
# （原版 3.10：猫的 tempt 在野生 / 驯服两组、tameable 在野生组、healable 在顶层；鸡、猪、兔子的 tempt 在顶层、ageable 在幼年组、
# breedable 在成年组；鹦鹉的 tameable 在野生组；狼的 breedable / ageable 在成年 / 幼年组、healable 在顶层）。
ANIMAL_FOOD = {
    "minecraft:cat": (
        ("minecraft:behavior.tempt", "items", CAT_SLICES),
        ("minecraft:tameable", "tame_items", CAT_SLICES),
        ("minecraft:breedable", "breed_items", CAT_SLICES),
        ("minecraft:ageable", "feed_items", CAT_SLICES),
        ("minecraft:healable", "items", _healing((name, CAT_SLICE_HEAL) for name in CAT_SLICES)),
    ),
    "minecraft:chicken": (
        ("minecraft:behavior.tempt", "items", CHICKEN_FOOD),
        ("minecraft:breedable", "breed_items", CHICKEN_FOOD),
        ("minecraft:ageable", "feed_items", CHICKEN_FOOD),
    ),
    "minecraft:pig": (
        ("minecraft:behavior.tempt", "items", PIG_FOOD),
        ("minecraft:breedable", "breed_items", PIG_FOOD),
        ("minecraft:ageable", "feed_items", PIG_FOOD),
    ),
    "minecraft:rabbit": (
        ("minecraft:behavior.tempt", "items", RABBIT_FOOD),
        ("minecraft:breedable", "breed_items", RABBIT_FOOD),
        ("minecraft:ageable", "feed_items", RABBIT_FOOD),
    ),
    "minecraft:parrot": (
        ("minecraft:tameable", "tame_items", PARROT_FOOD),
    ),
    "minecraft:wolf": (
        ("minecraft:breedable", "breed_items", WOLF_FOOD),
        ("minecraft:ageable", "feed_items", WOLF_FOOD),
        ("minecraft:healable", "items", _healing((name, food * 2) for name, food in WOLF_MEATS)),
    ),
}
