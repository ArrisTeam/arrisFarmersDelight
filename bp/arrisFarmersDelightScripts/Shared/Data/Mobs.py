# -*- coding: utf-8 -*-
"""Mobs - 狗粮 / 马饲料的喂食规则，给原版狼、马类、兔子追加的实体组件（JSON 串）（双端，纯数据）

喂食（右键驯服的生物）照 JE 的 DogFoodItem / HorseFeedItem；吸引（tempt / beg）照 JE 的 CommonEvents.onAnimalsJoinWorld：
马、驴、骡被马饲料吸引，兔子被卷心菜和卷心菜叶吸引，狼向狗粮讨食。
追加的组件会整个盖掉原版同名组件，所以下面的 JSON 都是原版（3.10）的同名组件加上本模组的物品，原版没动的字段原样抄来。
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

# 下面几个"追加组件"表：键是组件名，值是组件的 JSON 串；horse / wolf 两张是对外联动契约的一部分（下游可以往里加）
horseComponentsDict = {
    "minecraft:behavior.tempt": _HORSE_TEMPT,
}

wolfComponentsDict = {
    "minecraft:behavior.beg": '{"priority": 9, "look_distance": 8, "look_time": [2, 4], "items": ["arris:dog_food", "bone", "porkchop", "cooked_porkchop", "chicken", "cooked_chicken", "beef", "cooked_beef", "rotten_flesh", "muttonraw", "muttoncooked", "rabbit", "cooked_rabbit"]}',
}

donkeyComponentsDict = {"minecraft:behavior.tempt": _HORSE_TEMPT}
muleComponentsDict = {"minecraft:behavior.tempt": _HORSE_TEMPT}

rabbitComponentsDict = {
    "minecraft:behavior.tempt": '{"priority": 3, "speed_multiplier": 1, "items": ["golden_carrot", "carrot", "dandelion", "arris:cabbage", "arris:cabbage_leaf"]}',
}

# 实体 -> 要追加的组件表（服务端在实体出现时逐个 AddActorComponent）
livestockComponents = {
    "minecraft:horse": horseComponentsDict,
    "minecraft:donkey": donkeyComponentsDict,
    "minecraft:mule": muleComponentsDict,
    "minecraft:wolf": wolfComponentsDict,
    "minecraft:rabbit": rabbitComponentsDict,
}
