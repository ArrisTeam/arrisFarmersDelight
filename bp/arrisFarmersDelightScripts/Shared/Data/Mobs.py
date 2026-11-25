# -*- coding: utf-8 -*-
"""Mobs - 狗粮 / 马饲料的喂食规则，给原版狼、马类、兔子追加的实体组件（JSON 串）（双端，纯数据）

喂食（右键驯服的生物）照 JE 的 DogFoodItem / HorseFeedItem；吸引（tempt / beg）照 JE 的 CommonEvents.onAnimalsJoinWorld：
马、驴、骡被马饲料吸引，兔子被卷心菜和卷心菜叶吸引，狼向狗粮和农夫乐事的十种肉讨食（JE 的狼对所有 isMeat 的食物讨食）。
繁殖、喂小崽、治疗、驯服在成年 / 幼年 / 野生这些组件组里，加组件会被组的切换盖掉，所以那些改在覆盖原版实体文件里
（tools/gen_vanilla_overrides.py 生成 bp/entities/chicken、pig、rabbit、parrot、wolf.json）。
追加的 tempt / beg 会整个盖掉原版同名组件，所以 JSON 都是原版（3.10）的同名组件加上本模组的物品，原版没动的字段原样抄来。

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

rabbitComponentsDict = {
    "minecraft:behavior.tempt": '{"priority": 3, "speed_multiplier": 1, "items": ["golden_carrot", "carrot", "dandelion", "arris:cabbage", "arris:cabbage_leaf"]}',
}

# 实体 -> 要追加的组件表（服务端在实体出现时逐个 AddActorComponent）
livestockComponents = {
    "minecraft:horse": horseComponentsDict,
    "minecraft:donkey": donkeyComponentsDict,
    "minecraft:mule": muleComponentsDict,
    "minecraft:skeleton_horse": skeletonHorseComponentsDict,
    "minecraft:zombie_horse": zombieHorseComponentsDict,
    "minecraft:llama": llamaComponentsDict,
    "minecraft:wolf": wolfComponentsDict,
    "minecraft:rabbit": rabbitComponentsDict,
}
