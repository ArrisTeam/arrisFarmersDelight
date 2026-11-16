# -*- coding: utf-8 -*-
"""PotPieceTraits - 煮进汤里的配料切成碎料时算哪一类：谷物、意面、肉（双端，纯数据）

照 Hands-On Delight 的 CookedPieces.cut 用到的几样换成本包的物品名：
- GRAINS：标签 handson_delight:grains（农夫乐事的米和米饭、forge:grain 的小麦、forge:seeds 的各种种子）——切成三小粒；
- PASTA：标签 forge:pasta（生意面）——两条丝；
- MEAT：食物属性里 isMeat 的（原版的生熟肉和腐肉，农夫乐事 FoodValues 里带 meat() 的那些）——一大块加一小块。
- STRAINED：标签 handson_delight:strained（骨头）——煮完拣出来，汤里不留碎料。
蛋（标签 handson_delight:cracked）在 PotSunk.CRACKED。其余的看颜色：绿的是叶子加丝，别的是币加小块（Shared/Rules/PotPiecesLook.py）。
鱼不算肉（JE 的鳕鱼、鲑鱼没有 meat 标记），照 JE 切成币加小块。
"""

GRAINS = frozenset((
    "arris:rice",
    "arris:cooked_rice",
    "minecraft:wheat",
    "minecraft:wheat_seeds",
    "minecraft:beetroot_seeds",
    "minecraft:melon_seeds",
    "minecraft:pumpkin_seeds",
    "minecraft:torchflower_seeds",
    "minecraft:pitcher_pod",
    "arris:cabbage_seeds",
    "arris:tomato_seeds",
))

PASTA = frozenset((
    "arris:raw_pasta",
))

MEAT = frozenset((
    "minecraft:beef",
    "minecraft:cooked_beef",
    "minecraft:chicken",
    "minecraft:cooked_chicken",
    "minecraft:mutton",
    "minecraft:cooked_mutton",
    "minecraft:porkchop",
    "minecraft:cooked_porkchop",
    "minecraft:rabbit",
    "minecraft:cooked_rabbit",
    "minecraft:rotten_flesh",
    "arris:minced_beef",
    "arris:beef_patty",
    "arris:chicken_cuts",
    "arris:cooked_chicken_cuts",
    "arris:bacon",
    "arris:cooked_bacon",
    "arris:mutton_chops",
    "arris:cooked_mutton_chops",
    "arris:ham",
    "arris:smoked_ham",
    "arris:dog_food",
))

STRAINED = frozenset((
    "minecraft:bone",
))
