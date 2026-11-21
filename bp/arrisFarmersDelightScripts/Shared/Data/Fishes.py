# -*- coding: utf-8 -*-
"""Fishes - JE 的物品标签 minecraft:fishes（双端，纯数据）

照 JE 1.20.1 原版数据包的 data/minecraft/tags/items/fishes.json（client jar 里读的）：生熟鳕鱼、生熟鲑鱼、河豚、热带鱼，基岩版的物品名一样。
农夫乐事不往这个标签里加东西（它的鳕鱼片、鲑鱼片在 forge:raw_fishes / forge:cooked_fishes 里），鱼片也不是 meat()（FoodValues.COD_SLICE / SALMON_SLICE）。
用处：煎锅 / 炉灶上煎着的东西朝上那面的熟色，"肉和鱼"多带一点焦色（HoD 的 KitchenLooks.fryingTint：food.isMeat() || raw.is(ItemTags.FISHES)；
isMeat 的那一半是 Shared/Data/PotPieceTraits.MEAT，判断在 Shared/Rules/FryingTint.sears）。不属于对外联动契约。
"""
FISHES = frozenset((
    "minecraft:cod",
    "minecraft:cooked_cod",
    "minecraft:salmon",
    "minecraft:cooked_salmon",
    "minecraft:pufferfish",
    "minecraft:tropical_fish",
))
