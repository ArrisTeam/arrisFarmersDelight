# -*- coding: utf-8 -*-
from .Registry import GetJeiApiModule, SetHoverText
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList

def RegisterCookingPotRecipes():
    registry = GetJeiApiModule()
    recipeTag = "cooking_pot"
    if not registry:
        return
    registry.registerRecipeType(
        recipeTag,
        ("arris:cooking_pot", 0),
        "厨锅",
        CookingPotRecipe,
        "jei_farmers_delight.jeiCookingPotRecipe",
        65
    )

    items = registry.getAllRegisteredItems()
    for itemData in items:
        recipesByResultList = []
        for recipe in CookingPotRecipeList:
            outputItem = recipe["CookResult"]
            if outputItem[0] != itemData[0] or outputItem[1] != itemData[1]:
                continue
            recipesByResultList.append(recipe)
        if recipesByResultList:
            registry.setRecipeByResult(recipeTag, itemData, recipesByResultList)
        recipesByInputList = []
        for recipe in CookingPotRecipeList:
            for inputData in recipe["Recipe"]:
                for inputItem in inputData:
                    if inputItem[0] != itemData[0] or inputItem[1] != itemData[1] or recipe in recipesByInputList:
                        continue
                    recipesByInputList.append(recipe)
            vessel = recipe.get("Vessel")
            if vessel and vessel[0] == itemData[0] and vessel[1] == itemData[1] and recipe not in recipesByInputList:
                recipesByInputList.append(recipe)
        if recipesByInputList:
            registry.setRecipeByInput(recipeTag, itemData, recipesByInputList)

class CookingPotRecipe:
    def __init__(self, screenNode, recipeControl, recipeData, recipeIndex, itemData):
        self.screenNode = screenNode
        self.recipeControl = recipeControl
        self.recipeData = recipeData
        self.recipeIndex = recipeIndex
        self.itemData = itemData
        self.indexTurns = 0  # 物品轮播索引

    def OnCreate(self):
        """创建配方UI时调用"""
        if not self.recipeData["Recipe"]:
            return
        inputNum = len(self.recipeData["Recipe"][0])
        for index in range(inputNum):
            inputItemData = self.recipeData["Recipe"][0][index]
            renderer = self.recipeControl.GetChildByPath("/bg/stack_panel/input_panel/jeiInputItemRender" + str(index + 1))
            inputRender = renderer.GetChildByPath("/item_cell/item/item_renderer")
            inputRender.SetVisible(True)
            inputRender.asItemRenderer().SetUiItem(inputItemData[0], inputItemData[1])
            SetHoverText(self.recipeControl, "/bg/stack_panel/input_panel/jeiInputItemRender" + str(index + 1), inputItemData[0], inputItemData[1])
        for index in range(inputNum, 6):
            inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/input_panel/jeiInputItemRender" + str(index + 1) + "/item_cell/item/item_renderer")
            inputRender.SetVisible(False)
        vessel = self.recipeData.get("Vessel")
        inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/jeiVesselItemRender/item_cell/item/item_renderer")
        if vessel:
            SetHoverText(self.recipeControl, "/bg/stack_panel/output_panel/jeiVesselItemRender", vessel[0], vessel[1])
            inputRender.asItemRenderer().SetUiItem(vessel[0], vessel[1])
        else:
            inputRender.SetVisible(False)
        cookResult = self.recipeData["CookResult"]
        inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/jeiOutputItemRender/item_cell/item/item_renderer")
        SetHoverText(self.recipeControl, "/bg/stack_panel/output_panel/jeiOutputItemRender", cookResult[0], cookResult[1])
        inputRender.asItemRenderer().SetUiItem(cookResult[0], cookResult[1])
    
    def OnInterval(self):
        self.indexTurns += 1
        if self.indexTurns >= len(self.recipeData["Recipe"]):
            self.indexTurns = 0
        index = self.indexTurns
        inputNum = len(self.recipeData["Recipe"][index])
        for i in range(inputNum):
            inputItemData = self.recipeData["Recipe"][index][i]
            inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/input_panel/jeiInputItemRender" + str(i + 1) + "/item_cell/item/item_renderer")
            inputRender.SetVisible(True)
            SetHoverText(self.recipeControl, "/bg/stack_panel/input_panel/jeiInputItemRender" + str(i + 1), inputItemData[0], inputItemData[1])

            inputRender.asItemRenderer().SetUiItem(inputItemData[0], inputItemData[1])
        for i in range(inputNum, 6):
            inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/input_panel/jeiInputItemRender" + str(i + 1) + "/item_cell/item/item_renderer")
            inputRender.SetVisible(False)
