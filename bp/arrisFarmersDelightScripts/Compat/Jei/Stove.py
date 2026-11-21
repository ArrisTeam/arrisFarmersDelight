# -*- coding: utf-8 -*-
from .Registry import GetJeiApiModule, SetHoverText
from ...Client import Texts
from ...Shared.Data.Cooking import CanCookedFoodDict
from ...Shared.Rules.GrillStation import RECIPE_SECONDS  # 一件要多久（JE：煎锅 6 秒、炉灶按营火配方 30 秒）
from ...Shared.Rules.StationBooks import shownSeconds

# 分类名（JE 的 JEI 没有炉灶这一类：我们的键），配方页的秒数和站点食谱书页脚的同一句（HoD 的键）；客户端按玩家的语言查，没有时用中文。
# 秒数和页脚一样先经 shownSeconds 换成整数再填：RECIPE_SECONDS 是 30.0，直接填英文的 %s 会写成 30.0 s
TITLE = ("arris_fd.jei.stove", "炉灶")
SECONDS = ("handson_delight.book.seconds", "%d 秒")

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

    items = registry.getAllRegisteredItems()
    for itemData in items:
        recipesByResultList = []
        for inputItem, outputItem in CanCookedFoodDict.items():
            if outputItem != itemData[0]:
                continue
            recipesByResultList.append({"input": inputItem, "output": outputItem})
        if recipesByResultList:
            registry.setRecipeByResult(recipeTag, itemData, recipesByResultList)
        recipesByInputList = []
        for inputItem, outputItem in CanCookedFoodDict.items():
            if inputItem != itemData[0]:
                continue
            recipesByInputList.append({"input": inputItem, "output": outputItem})
        if recipesByInputList:
            registry.setRecipeByInput(recipeTag, itemData, recipesByInputList)

class StoveRecipe:
    def __init__(self, screenNode, recipeControl, recipeData, recipeIndex, itemData):
        self.screenNode = screenNode
        self.recipeControl = recipeControl
        self.recipeData = recipeData
        self.recipeIndex = recipeIndex
        self.itemData = itemData
        self.indexTurns = 0  # 物品轮播索引

    def OnCreate(self):
        """创建配方UI时调用"""
        self.recipeControl.GetChildByPath("/bg/timer").asLabel().SetText(Texts.fill(SECONDS[0], SECONDS[1], shownSeconds(RECIPE_SECONDS)))
        outputItem = self.recipeData["output"]
        inputItem = self.recipeData["input"]
        inputRender = self.recipeControl.GetChildByPath("/bg/jeiInputItemRender/item_cell/item/item_renderer")
        SetHoverText(self.recipeControl, "/bg/jeiInputItemRender", inputItem)
        inputRender.asItemRenderer().SetUiItem(inputItem, 0)
        outputRender = self.recipeControl.GetChildByPath("/bg/jeiOutputItemRender/item_cell/item/item_renderer")
        SetHoverText(self.recipeControl, "/bg/jeiOutputItemRender", outputItem)
        outputRender.asItemRenderer().SetUiItem(outputItem, 0)
