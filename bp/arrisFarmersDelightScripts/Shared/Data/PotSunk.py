# -*- coding: utf-8 -*-
"""PotSunk - 下锅不浮在汤面上的料：倒进去的液体、打进去的蛋、化在汤里的粉（双端，纯数据）

照 Hands-On Delight 的物品标签换成本包的物品名：data/handson_delight/tags/items 里的 poured（倒进去：装它的瓶、桶不进汤，
奶、水、蜂蜜、番茄酱、龙息、岩浆）、cracked（蛋：壳不进汤）、dissolves（化掉：糖、可可豆、墨囊、骨粉、荧石粉、烈焰粉、蜂蜜）。
这些东西空手点不到：它们在锅里没有浮着的那一块，只能用"取回"动作（take_back）按放进去的先后倒着一格一格拿回来；
浮着的料（胡萝卜、肉……）照常点它自己那一格。
JE 的标签里还有别的模组的物品（Delightful、末影、Youkai 的酱和奶油……），本包没有的不写。物品身份是 (物品名, aux)。
"""

POURED = (
    ("minecraft:milk_bucket", 0),
    ("minecraft:water_bucket", 0),
    ("minecraft:lava_bucket", 0),
    ("minecraft:honey_bottle", 0),
    ("minecraft:dragon_breath", 0),
    ("arris:milk_bottle", 0),
    ("arris:tomato_sauce", 0),
)

CRACKED = (
    ("minecraft:egg", 0),
)

DISSOLVES = (
    ("minecraft:sugar", 0),
    ("minecraft:cocoa_beans", 0),
    ("minecraft:ink_sac", 0),
    ("minecraft:glow_ink_sac", 0),
    ("minecraft:bone_meal", 0),
    ("minecraft:honey_bottle", 0),
    ("minecraft:glowstone_dust", 0),
    ("minecraft:blaze_powder", 0),
)

SUNK = frozenset(POURED + CRACKED + DISSOLVES)
