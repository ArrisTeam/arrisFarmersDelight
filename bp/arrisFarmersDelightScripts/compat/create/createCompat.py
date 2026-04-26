# -*- coding: utf-8 -*-
"""
农夫乐事 x 机械动力 配方联动

包含：
- milling (石磨)  8 条：野生作物磨出种子/染料、稻穗磨出稻米+麦秸
- mixing  (搅拌) 3 条：卷心菜叶、派皮、番茄酱
- filling (灌注) 1 条：巧克力派

若 arrisCreate 副包未安装（ImportModule 失败）本模块静默 no-op
模组照常运行，不影响任何其它功能。
"""

from ...QuModLibs.Server import *

_REGISTERED = False


def _getRecipeApi():
    """延迟 import 机械动力 RecipeApi。若副包未装或未加载则返回 None。"""
    return serverApi.ImportModule("arrisCreateScripts.Api.ServerApi.RecipeApi")

def _registerMilling(api):
    """石磨配方 —— 对齐 recipes/integration/create/milling/*.json"""
    # 稻穗 -> 稻米 + 麦秸
    api.createBuilder("arris:milling/rice_panicle", "milling") \
        .ingredient("arris:rice_panicle") \
        .output("arris:rice", count=1) \
        .output("arris:straw", count=1) \
        .processingTime(50) \
        .register()

    # 野生甜菜 -> 甜菜种子 + 红色染料
    api.createBuilder("arris:milling/wild_beetroots", "milling") \
        .ingredient("arris:wild_beetroots") \
        .output("minecraft:beetroot_seeds", count=1) \
        .output("minecraft:red_dye", count=1) \
        .processingTime(50) \
        .register()

    # 野生卷心菜 -> 卷心菜种子 + 黄色染料
    api.createBuilder("arris:milling/wild_cabbages", "milling") \
        .ingredient("arris:wild_cabbages") \
        .output("arris:cabbage_seeds", count=1) \
        .output("minecraft:yellow_dye", count=1) \
        .processingTime(50) \
        .register()

    # 野生胡萝卜 -> 2 浅灰染料 + 10% 黄绿染料
    api.createBuilder("arris:milling/wild_carrots", "milling") \
        .ingredient("arris:wild_carrots") \
        .output("minecraft:light_gray_dye", count=2) \
        .outputWithChance("minecraft:lime_dye", 0.1, count=1) \
        .processingTime(50) \
        .register()

    # 野生洋葱 -> 品红染料 (+ 20% 三倍品红 + 10% 黄绿染料)
    api.createBuilder("arris:milling/wild_onions", "milling") \
        .ingredient("arris:wild_onions") \
        .output("minecraft:magenta_dye", count=1) \
        .outputWithChance("minecraft:magenta_dye", 0.2, count=3) \
        .outputWithChance("minecraft:lime_dye", 0.1, count=1) \
        .processingTime(50) \
        .register()

    # 野生马铃薯 -> 2 紫色染料 + 10% 黄绿染料
    api.createBuilder("arris:milling/wild_potatoes", "milling") \
        .ingredient("arris:wild_potatoes") \
        .output("minecraft:purple_dye", count=2) \
        .outputWithChance("minecraft:lime_dye", 0.1, count=1) \
        .processingTime(50) \
        .register()

    # 野生稻米 -> 稻米 + 50% 麦秸
    api.createBuilder("arris:milling/wild_rice", "milling") \
        .ingredient("arris:wild_rice") \
        .output("arris:rice", count=1) \
        .outputWithChance("arris:straw", 0.5, count=1) \
        .processingTime(50) \
        .register()

    # 野生番茄 -> 番茄种子 + 绿色染料
    api.createBuilder("arris:milling/wild_tomatoes", "milling") \
        .ingredient("arris:wild_tomatoes") \
        .output("arris:tomato_seeds", count=1) \
        .output("minecraft:green_dye", count=1) \
        .processingTime(50) \
        .register()


def _registerMixing(api):
    """搅拌配方 —— 对齐 recipes/integration/create/mixing/*.json"""
    # 卷心菜 -> 2 卷心菜叶（注意：Java 在此配方 type 是 mixing，输出切片；与砧板切法一致）
    api.createBuilder("arris:mixing/cabbage_slice_from_mixing", "mixing") \
        .ingredient("arris:cabbage") \
        .output("arris:cabbage_leaf", count=2) \
        .register()

    # 3 小麦粉 + 250mB 牛奶 -> 派皮
    api.createBuilder("arris:mixing/pie_crust_from_mixing", "mixing") \
        .ingredient("create:wheat_flour", count=3) \
        .fluidIngredient("create:milk", 250) \
        .output("arris:pie_crust", count=1) \
        .register()

    # 2 番茄 + 碗 -> 番茄酱
    api.createBuilder("arris:mixing/tomato_sauce_from_mixing", "mixing") \
        .ingredient("arris:tomato", count=2) \
        .ingredient("minecraft:bowl") \
        .output("arris:tomato_sauce", count=1) \
        .register()


def _registerFilling(api):
    """灌注配方 —— 对齐 recipes/integration/create/filling/*.json"""
    # 派皮 + 500mB 巧克力流体 -> 巧克力派（物品形态，可以放置为方块）
    api.createBuilder("arris:filling/chocolate_pie", "filling") \
        .ingredient("arris:pie_crust") \
        .fluidIngredient("create:chocolate", 500) \
        .output("arris:chocolate_pie_item", count=1) \
        .register()


def _registerAll():
    """一次性注册所有 FD × Create 联动配方。若 Create 副包缺失，静默 no-op。"""
    global _REGISTERED
    if _REGISTERED:
        return
    api = _getRecipeApi()
    if api is None:
        print("[arrisFarmersDelight] arrisCreate 未检测到，跳过 Create 联动配方注册")
        return
    _REGISTERED = True
    try:
        _registerMilling(api)
        _registerMixing(api)
        _registerFilling(api)
        print("[arrisFarmersDelight] Create 联动配方注册完成（milling 8 + mixing 3 + filling 1）")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[arrisFarmersDelight] Create 联动配方注册失败: {}".format(e))


@Listen("LoadServerAddonScriptsAfter")
def _onAllScriptsLoaded(args=None):
    """等 arrisCreate 的 BuiltinRecipes 全部跑完、RecipeApi 就绪后再注册。"""
    _registerAll()
