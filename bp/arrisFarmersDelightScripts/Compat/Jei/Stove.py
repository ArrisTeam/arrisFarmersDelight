# -*- coding: utf-8 -*-
from .Registry import GetJeiApiModule, SetHoverText
from ...Shared.Data.Cooking import CanCookedFoodDict
from ...Shared.Rules.GrillStation import RECIPE_SECONDS  # 一件要多久（JE：煎锅 6 秒、炉灶按营火配方 30 秒）

def RegisterStoveRecipes():
    registry = GetJeiApiModule()
    recipeTag = "stove"
    if not registry:
        return
    registry.registerRecipeType(
        recipeTag,
        ("arris:stove", 0),
        "炉灶",
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
        self.recipeControl.GetChildByPath("/bg/timer").asLabel().SetText("%d 秒" % RECIPE_SECONDS)
        outputItem = self.recipeData["output"]
        inputItem = self.recipeData["input"]
        inputRender = self.recipeControl.GetChildByPath("/bg/jeiInputItemRender/item_cell/item/item_renderer")
        SetHoverText(self.recipeControl, "/bg/jeiInputItemRender", inputItem)
        inputRender.asItemRenderer().SetUiItem(inputItem, 0)
        outputRender = self.recipeControl.GetChildByPath("/bg/jeiOutputItemRender/item_cell/item/item_renderer")
        SetHoverText(self.recipeControl, "/bg/jeiOutputItemRender", outputItem)
        outputRender.asItemRenderer().SetUiItem(outputItem, 0)
