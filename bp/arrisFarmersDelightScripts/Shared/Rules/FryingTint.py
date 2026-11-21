# -*- coding: utf-8 -*-
"""FryingTint - 煎锅 / 炉灶上煎着的一件朝上那面的熟色，和基岩版用来近似它的那一层粒子的颜色、不透明度（双端，纯计算）

JE（Hands-On Delight）：SkilletBehavior.drawPiece（327 行）/ StoveBehavior.draw（206 行）给整件 node.setTint(KitchenLooks.fryingTint(shown, cooked(shown),
shownUp, SEARED, SEAR))，Diegesis 的 TintedConsumer 把整件体素模型每个顶点的颜色乘上它（上下两面、四边一起）。朝上那面每 1/12 才重画一次（look），
熟了（up >= 1）换成熟的图、不染（白）；两面食材只有厨师没等贴锅那面熟透就翻过来时，朝上那面才是半熟。
- 生熟两张图的主色：JE 的 FoodColors.main（色相分 12 份取最大的一族再提亮，sampleMain），不是砧板碎屑、汤色那张 FoodColors.sample（按鲜艳度加权平均，
  Shared/Data/FoodColors）。本包的表是 Shared/Data/BrothColors.MainColors（tools/gen_broth_colors.py 按贴图生成，营火配方里的每件和它煎熟的样子都在）。
  JE 运行时从图标现算，下游模组经联动契约（CanCookedFoodDict）追加的东西这边没有贴图、表里没有：不染（tintOf 返回 None）。
- 肉和鱼（food.isMeat() || ItemTags.FISHES）的目标色再往焦色 SEARED 走 4 成：isMeat 是 Shared/Data/PotPieceTraits.MEAT，鱼是 Shared/Data/Fishes.FISHES。
- 蛋不归这里：打开的蛋是 Shared/Rules/EggLook 那几件预染色的显示物品（fryingTint 的 isCracked 一支），调用方别把蛋传进来。
基岩版的客户端掉落物染不了色：在这件朝上那面上叠一张同一图标的粒子，用普通的 alpha 混合近似"整件乘上 c"（overlay）；摆在哪在 TopOverlay。
"""
from ..Data.BrothColors import MainColors
from ..Data.Fishes import FISHES
from ..Data.PotPieceTraits import MEAT
from .HandsOn import KitchenLooks

WHITE = 0xFFFFFFFF


def sears(name):
    """JE 的 food.isMeat() || raw.is(ItemTags.FISHES)：这件煎着，朝上那面的目标色再带一点焦色。"""
    return name in MEAT or name in FISHES


def tintOf(rawName, cookedName, up, colors=MainColors):
    """朝上那面煎到 up 的一件整件乘上什么颜色（ARGB）：KitchenLooks.fryingTint(main(生的), main(熟的), 不是蛋, 是不是肉和鱼, up)。
    cookedName 是营火把它做成的东西（没有配方就是它自己）。熟了（up >= 1）是白：换成熟的图、不染；一点没煎（up <= 0，没画过的 -1 也是）
    fryingTint 从白往目标走 0，也是白，不用算（烤架上大多数件都是这样：还在烤贴灶那面）；生熟两张图有一张没有主色（下游追加的）返回 None：不染。"""
    if up >= 1.0 or up <= 0.0:
        return WHITE
    raw, cooked = colors.get(rawName), colors.get(cookedName)
    if raw is None or cooked is None:
        return None
    return KitchenLooks.fryingTint(raw, cooked, False, sears(rawName), up)


def overlay(tint):
    """整件乘上 tint（ARGB，只看 R、G、B）用叠在上面的一层近似：返回 (r, g, b, a)，都是 0..1；不用画（None、白）返回 None。
    叠上去的图标粒子画成颜色 q·图标、不透明度 a（particles_blend 是普通的 alpha 混合）：画出来 = (1 - a)·底下 + a·q·图标，
    底下是同一张图标、受差不多的光，要它等于 c·图标：(1 - a) + a·q = c，逐通道。q 得在 0..1 里，所以 a 至少是 1 - min(c)；取最小的那个
    （a 越小，粒子和掉落物受光、位置的偏差越不显）：a = 1 - min(c)，q = (c - min(c)) / a，最暗的通道 q = 0。
    c 是白时 a = 0，什么都不画：出现、收起时不会因为两者受光差一点闪一下，偏差只和染的深浅成正比。
    实机（2026-11-22）：生牛肉朝上 1/2，顶面被压到 (0.917, 0.938, 0.902)，c = (0.914, 0.933, 0.910)；鸡肉 11/12 压到 (0.878, 0.740, 0.583)，
    c = (0.874, 0.737, 0.577)——particles_blend 就是普通的 alpha 混合，叠出来就是 c。"""
    if tint is None:
        return None
    channels = [((tint >> shift) & 0xFF) / 255.0 for shift in (16, 8, 0)]
    low = min(channels)
    if low >= 1.0:
        return None
    alpha = 1.0 - low
    return tuple((value - low) / alpha for value in channels) + (alpha,)
