# -*- coding: utf-8 -*-
"""PotBiome - 一口锅所在位置的水色：问客户端那一带是什么群系，交给 Shared/Rules/PotWater 算（客户端）

JE 的 PotBehavior.colour 每次重算汤色都取 BiomeColors.getAverageWaterColor(level, pos)。基岩版客户端的接口是
CreateBiome(levelId).GetBiomeName((x, y, z))（官方文档：获取客户端当前维度已加载区域某一位置所属的群系，回群系名、不带命名空间；
那一带没加载回 None），一列一次调用。
建场景时（PotScenes.ensure）问一次：水色挂在每口锅的场景上，没开站点的人看到的锅也对。之后不再问；区块卸载再加载时锅会重新建场景、再问一次。
"""
from ...Client.Engine import compFactory, levelId
from ...Shared.Rules import PotWater


def lookup(pos):
    """pos 处的水色 0xRRGGBB（周围 5 x 5 列的平均，见 PotWater）；一列都没问到返回 None。"""
    biome = compFactory.CreateBiome(levelId)
    return PotWater.waterAt(lambda x, y, z: biome.GetBiomeName((x, y, z)), pos)


def bind(scene):
    """给场景设上它所在位置的水色；问不到就不动，场景用缺省色（平原的蓝，PotScene.WATER）。"""
    water = lookup(scene.pos)
    if water is not None:
        scene.setWater(water)
