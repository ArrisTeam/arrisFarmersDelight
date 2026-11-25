# -*- coding: utf-8 -*-
"""Stove - JEI 的炉灶分类（客户端）

JE 的 JEI 没有炉灶这一类，分类名是我们的键；配方页和煎锅的一样（CookPages：一组原料一页，三种蛋并成一页），秒数是炉灶的（JE 按营火配方 30 秒）。
"""
from . import CookPages
from .Registry import GetJeiApiModule
from ...Client import Texts
from ...Shared.Rules.GrillStation import RECIPE_SECONDS  # 一件要多久（JE：煎锅 6 秒、炉灶按营火配方 30 秒）

TITLE = ("arris_fd.jei.stove", "炉灶")      # 客户端按玩家的语言查，没有时用中文
SECONDS = CookPages.SECONDS                 # 配方页上的"多少秒"：和站点食谱书页脚同一个键


def RegisterStoveRecipes():
    registry = GetJeiApiModule()
    recipeTag = "stove"
    if not registry:
        return
    registry.registerRecipeType(
        recipeTag,
        ("arris:stove", 0),
        Texts.of(*TITLE),
        StoveRecipe,
        "jei_farmers_delight.jeiSkilletAndStoveRecipe",
        55
    )
    CookPages.register(registry, recipeTag)


class StoveRecipe(CookPages.CookRecipe):
    def seconds(self):
        return RECIPE_SECONDS
