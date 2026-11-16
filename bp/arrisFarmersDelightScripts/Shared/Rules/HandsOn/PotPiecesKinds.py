# -*- coding: utf-8 -*-
"""PotPiecesKinds - 一锅汤里浮着哪几种碎料、什么颜色、多大、有多少块（双端）

移植自 Hands-On Delight 的 client/CookedPieces.java（ingredients / cut / of）和 client/PotBehavior.java 的 pieces（1026-1040 行，数量）。
碎料不是"成品菜的样子"，而是这道菜的配方里的配料切碎煮熟了的样子：蛋是蛋白条加蛋黄块，米是三小粒，意面是两条丝，肉是大块加小块，
绿色的是叶子加丝，其余是币加小块；每两块食材之后再浮一滴油（比汤色亮 0.55）。

一块碎料叫 floater：元组 (kind, color, size, solid)——kind 是图案名（COIN / CHUNK / NUGGET / SHRED / LEAF / DROP，Diegesis 的
block/bits/ 里的几张灰度图，按 color 染色），color 是 0xRRGGBB，size 是画多宽（像素），solid 是不是有厚度的实心片（油滴是漂在面上的一层膜，False）。

食材怎么分类不在这里查表：调用方给 traitsOf(物品) -> 特征集合（"egg" 蛋、"grain" 谷物、"pasta" 意面、"meat" 肉里有哪些）和 colorOf(物品) -> 0xRRGGBB
（FoodColors.main，本包的表在 Shared/Data/BrothColors.py 的 MainColors）。
"""
from .PotColors import FAT_LIGHT, isGreen, lighter

COIN, CHUNK, NUGGET, SHRED, LEAF, DROP = "coin", "chunk", "nugget", "shred", "leaf", "drop"

BIG = 1.65                # 肉块、币的大小
SMALL = 1.2               # 小块
HERB = 1.3                # 叶子和丝
FAT = 0.75                # 油滴
EGG_WHITE = 0xF4F1E6
EGG_YOLK = 0xF2C230
GRAINS = 3                # 一件谷物切成这么多小粒
GRAIN = 0.75              # 粒的大小
PIECES_PER_DROP = 2       # 每这么多块食材之后浮一滴油
PIECES_BASE = 14          # 一锅汤里浮着的块数：PIECES_BASE + PIECES_PER_SERVING * 份数，最多 PIECES_MOST
PIECES_PER_SERVING = 5
PIECES_MOST = 32


def floater(kind, color, size, solid=True):
    """一块碎料。"""
    return (kind, color, size, solid)


def piecesCount(servings):
    """汤里该浮多少块：没有汤（0 份）是 0，否则 min(PIECES_MOST, PIECES_BASE + PIECES_PER_SERVING * servings)（PB 1030）。"""
    return 0 if servings <= 0 else min(PIECES_MOST, PIECES_BASE + PIECES_PER_SERVING * servings)


def ingredientsOf(inputs, hasRemainder, leavesNoPieces, cooked=None):
    """CookedPieces.ingredients：这道菜的配方里哪些东西会变成碎料，按配方里的先后、重复的只算一次。

    inputs：配方每格的第一个可选物品（Java 的 choices[0]）；hasRemainder(物品)：用掉会留下容器的（奶桶、奶瓶）不是食材；
    leavesNoPieces(物品)：倒进去的液体、溶掉的（糖、骨粉）、煮完拣出来的（骨头）不留碎料；
    cooked(物品)：进炉子烧出来的熟食（还是食物才换），没有就是原样。返回换成熟食之后的物品列表。
    """
    found = []
    for item in inputs:
        if hasRemainder(item) or leavesNoPieces(item):
            continue
        done = cooked(item) if cooked else item
        if done not in found:
            found.append(done)
    return found


def cut(color, traits):
    """CookedPieces.cut：一件煮熟的食材切成哪几块。color 是 FoodColors.main 给的颜色，traits 是它的特征集合。

    蛋最先判（白和黄是固定的颜色）；然后谷物、意面、肉；然后看颜色是不是绿的（isGreen）；其余是币加小块。
    """
    if "egg" in traits:
        return [floater(SHRED, EGG_WHITE, HERB), floater(NUGGET, EGG_YOLK, SMALL)]
    if "grain" in traits:
        return [floater(NUGGET, color, GRAIN) for _ in range(GRAINS)]
    if "pasta" in traits:
        return [floater(SHRED, color, HERB), floater(SHRED, color, HERB)]
    if "meat" in traits:
        return [floater(CHUNK, color, BIG), floater(NUGGET, color, SMALL)]
    if isGreen(color):
        return [floater(LEAF, color, HERB), floater(SHRED, color, HERB)]
    return [floater(COIN, color, BIG * 0.9), floater(NUGGET, color, SMALL)]


def cookedPieces(items, broth, traitsOf, colorOf):
    """CookedPieces.of：一道菜的全部碎料（floater 列表）。

    items 是 ingredientsOf 给的食材；broth 是汤色（0xRRGGBB，油滴按它提亮 FAT_LIGHT）。
    食材全切完之后，每 PIECES_PER_DROP 块食材后面插一滴油：第 i 滴插在下标 i * (PIECES_PER_DROP + 1) + PIECES_PER_DROP。
    """
    pieces = []
    for item in items:
        traits = traitsOf(item)
        pieces += cut(0 if "egg" in traits else colorOf(item), traits)
    fat = lighter(broth, FAT_LIGHT)
    for index in range(len(pieces) // PIECES_PER_DROP):
        pieces.insert(index * (PIECES_PER_DROP + 1) + PIECES_PER_DROP, floater(DROP, fat, FAT, False))
    return pieces
