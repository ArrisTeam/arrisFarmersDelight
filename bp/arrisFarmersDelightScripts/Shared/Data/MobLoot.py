# -*- coding: utf-8 -*-
"""MobLoot - 刀杀死生物的额外掉落、洋葱从僵尸和灾厄村民身上掉（双端，纯数据）

照 JE 的战利品修饰器（data/farmersdelight/loot_modifiers/scavenging_*.json、add_onion_to_*.json）。
生物名是基岩版的实体标识（evoker 在基岩版叫 evocation_illager，僵尸村民有新旧两个标识）。
"""
# 手里拿着刀杀死下列生物，额外掉 (物品, 数量)，每次必掉
KNIFE_EXTRA_DROPS = {
    "minecraft:cow": ("minecraft:leather", 1),
    "minecraft:mooshroom": ("minecraft:leather", 1),
    "minecraft:horse": ("minecraft:leather", 1),
    "minecraft:donkey": ("minecraft:leather", 1),
    "minecraft:mule": ("minecraft:leather", 1),
    "minecraft:llama": ("minecraft:leather", 1),
    "minecraft:trader_llama": ("minecraft:leather", 1),
    "minecraft:chicken": ("minecraft:feather", 1),
    "minecraft:rabbit": ("minecraft:rabbit_hide", 1),
    "minecraft:spider": ("minecraft:string", 1),
    "minecraft:cave_spider": ("minecraft:string", 1),
    "minecraft:shulker": ("minecraft:shulker_shell", 1),
}

# 火腿：猪按概率掉（百分比：基础值，抢夺每级加几），疣猪兽必掉（None）；着火时掉烟熏火腿
HAM = "arris:ham"
SMOKED_HAM = "arris:smoked_ham"
KNIFE_HAM = {
    "minecraft:pig": (50, 10),
    "minecraft:hoglin": None,
}

# 洋葱：玩家杀死下列生物（用什么武器都行）有概率掉 1 个洋葱：基础 2%，抢夺每级 +1%
ONION = "arris:onion"
ONION_CHANCE = (2, 1)
ONION_MOBS = (
    "minecraft:zombie",
    "minecraft:husk",
    "minecraft:zombie_villager",
    "minecraft:zombie_villager_v2",
    "minecraft:pillager",
    "minecraft:evocation_illager",
    "minecraft:vindicator",
)

# 玩家射出的投射物杀死生物时，攻击者可能是投射物本身：认它的发射者
PROJECTILES = ("minecraft:arrow", "minecraft:thrown_trident")
