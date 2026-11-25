# -*- coding: utf-8 -*-
"""Skillet - JEI 的煎锅分类（客户端）

JE 的 JEI 没有煎锅这一类，分类名是我们的键；配方页和炉灶的一样（CookPages：一组原料一页，三种蛋并成一页），秒数是煎锅的（JE 6 秒）。
"""
from . import CookPages
from .Registry import GetJeiApiModule
from ...Client import Texts
from ...Shared.Rules.PanStation import SKILLET_SECONDS  # 一件要多久（JE：煎锅 6 秒、炉灶按营火配方 30 秒）

TITLE = ("arris_fd.jei.skillet", "煎锅")      # 客户端按玩家的语言查，没有时用中文
SECONDS = CookPages.SECONDS                   # 配方页上的"多少秒"：和站点食谱书页脚同一个键


def RegisterSkilletRecipes():
    registry = GetJeiApiModule()
    recipeTag = "skillet"
    if not registry:
        return
    registry.registerRecipeType(
        recipeTag,
        ("arris:skillet", 0),
        Texts.of(*TITLE),
        SkilletRecipe,
        "jei_farmers_delight.jeiSkilletAndStoveRecipe",
        55
    )
    CookPages.register(registry, recipeTag)


class SkilletRecipe(CookPages.CookRecipe):
    def seconds(self):
        return SKILLET_SECONDS
