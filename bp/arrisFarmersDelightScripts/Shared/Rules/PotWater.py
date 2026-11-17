# -*- coding: utf-8 -*-
"""PotWater - 厨锅里清水的颜色：锅所在位置周围各列群系的水色取平均（双端，纯逻辑）

对应 Hands-On Delight 的 client/PotBehavior.colour（1048-1049）：没放料也不是怪物锅时水是
`WATER_ALPHA << 24 | BiomeColors.getAverageWaterColor(level, pos) & 0xFFFFFF`，后面再按料色和倒进去的液体色往汤色混（PotLiquidColor.brothTarget）。
getAverageWaterColor 是原版的"群系混合"（ClientLevel.calculateBlockTint）：取 pos 同一高度、以它为中心 (2r+1) x (2r+1) 列各自群系的水色，
逐通道整数平均（向下取整）；r 是视频设置里的"生物群系混合"，缺省 2（5 x 5）。
基岩版的水色表是 Shared/Data/BiomeWater.py（tools/gen_biome_water.py 按原版资源包生成，引擎画世界里的水用的就是它）：
锅里的水和旁边池塘的水同色，平原是 #44AFF5、不是 JE 的 #3F76E4；表里没有的群系（别的模组加的）用 DEFAULT_BIOME_WATER
（引擎对没写水色的群系用的缺省色，也是 #44AFF5）。

本模块不碰引擎：群系名由调用方给（biomeAt(x, y, z) -> 群系名或 None；客户端是 CreateBiome(levelId).GetBiomeName，在 Compat/Diegesis/PotBiome.py）。
只取锅所在区块里的列：客户端对没加载的区块回的是 ocean 而不是 None，锅在区块边上、邻居区块还没来时，那几列会把水色往海的颜色拽。
"""
from ..Data.BiomeWater import BiomeWater
from .HandsOn.PotLiquid import DEFAULT_BIOME_WATER, mixColors

BLEND_RADIUS = 2          # "生物群系混合"选项的缺省值：以锅为中心 5 x 5 列（Options.biomeBlendRadius）
NAMESPACE = "minecraft:"
CHUNK_SHIFT = 4           # 区块边长 16：方块坐标右移 4 位是区块坐标（负数向下取整，和引擎一致）


def waterOf(biome):
    """群系名 -> 它的水色 0xRRGGBB。名字带不带 minecraft: 都行；表里没有的（别的模组的群系）是缺省色 DEFAULT_BIOME_WATER。"""
    name = biome[len(NAMESPACE):] if biome.startswith(NAMESPACE) else biome
    return BiomeWater.get(name, DEFAULT_BIOME_WATER)


def columns(pos, radius=BLEND_RADIUS):
    """要查群系的那些列：以 pos 为中心、同一高度的 (2r+1) x (2r+1) 里落在 pos 所在区块的，[(x, y, z)]；pos 自己那一列一定在。"""
    x, y, z = pos
    chunk = (x >> CHUNK_SHIFT, z >> CHUNK_SHIFT)
    found = []
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            if ((x + dx) >> CHUNK_SHIFT, (z + dz) >> CHUNK_SHIFT) == chunk:
                found.append((x + dx, y, z + dz))
    return found


def waterAt(biomeAt, pos, radius=BLEND_RADIUS):
    """pos 处的水色 0xRRGGBB：columns 里各列群系的水色逐通道取平均（向下取整，和 JE 的整数除法一样）。

    biomeAt(x, y, z) 答不上来（回 None）的列不算；一列都没答上来返回 None，调用方照旧用缺省色。
    """
    colors = []
    for x, y, z in columns(pos, radius):
        biome = biomeAt(x, y, z)
        if biome:
            colors.append(waterOf(biome))
    return mixColors(colors) if colors else None
