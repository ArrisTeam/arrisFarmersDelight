# -*- coding: utf-8 -*-
from .Registry import GetJeiApiModule, SetHoverText
from ...Client import Texts
from ...Shared.Data.Cutting import CuttingBoardDict

TITLE = ("jei.farmersdelight.cutting", "砧板")      # 分类名：JE 的键（英文 Cutting Board），客户端按玩家的语言查，语言文件里没有时用中文

def RegisterCuttingBoardRecipes():
    registry = GetJeiApiModule()
    recipeTag = "cutting_board"
    if not registry:
        return
    registry.registerRecipeType(
        recipeTag,
        ("arris:cutting_board", 0),
        Texts.of(*TITLE),
        CuttingBoardRecipe,
        "jei_farmers_delight.jeiCuttingBoardRecipe",
        45
    )

    cuttingBoardRecipesByResultDict = {}
    cuttingBoardRecipesByInputDict = {}
    for inputItem, data in CuttingBoardDict.items():
        registry.setRecipeByInput(recipeTag, inputItem, [{"recipe": {"output": data, "input": inputItem}}])
        for tool in data.get("tool", []):
            toolItem = (tool, 0)
            if toolItem in cuttingBoardRecipesByInputDict:
                cuttingBoardRecipesByInputDict[toolItem].append({"recipe": {"output": data, "input": inputItem}})
            else:
                cuttingBoardRecipesByInputDict[toolItem] = [{"recipe": {"output": data, "input": inputItem}}]

        for outputItemData in data["itemList"]:
            outputItem = (outputItemData.get("itemName", ""), outputItemData.get("itemAux", 0))
            if outputItem in cuttingBoardRecipesByResultDict:
                cuttingBoardRecipesByResultDict[outputItem].append({"recipe": {"output": data, "input": inputItem}})
            else:
                cuttingBoardRecipesByResultDict[outputItem] = [{"recipe": {"output": data, "input": inputItem}}]
    for outputItem, recipeList in cuttingBoardRecipesByResultDict.items():
        registry.setRecipeByResult(recipeTag, outputItem, recipeList)
    for inputItem, recipeList in cuttingBoardRecipesByInputDict.items():
        registry.setRecipeByInput(recipeTag, inputItem, recipeList)

class CuttingBoardRecipe:
    def __init__(self, screenNode, recipeControl, recipeData, recipeIndex, itemData):
        self.screenNode = screenNode
        self.recipeControl = recipeControl
        self.recipeData = recipeData
        self.recipeIndex = recipeIndex
        self.itemData = itemData
        self.indexTurns = 0  # 物品轮播索引

    def OnCreate(self):
        """创建配方UI时调用"""
        grid = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/grid")
        if not grid:
            return
        data = self.recipeData["recipe"]["output"]
        inputItem = self.recipeData["recipe"]["input"]
        grid.asGrid().SetGridDimension((len(data["itemList"]), 1))
        inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/cutting_board_panel/cutting_board_bg/jeiInputFoodRender/item_cell/item/item_renderer")
        inputRender.asItemRenderer().SetUiItem(inputItem[0], inputItem[1])
        SetHoverText(self.recipeControl, "/bg/stack_panel/cutting_board_panel/cutting_board_bg/jeiInputFoodRender", inputItem[0], inputItem[1])
        tool = data["tool"]
        toolRender = self.recipeControl.GetChildByPath("/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer/item_cell/item/item_renderer")
        toolRender.asItemRenderer().SetUiItem(tool[0], 0)
        SetHoverText(self.recipeControl, "/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer", tool[0], 0)
        for index in range(len(data["itemList"])):
            outputItemData = data["itemList"][index]
            count = outputItemData.get("count", 1)
            outputItemName = outputItemData["itemName"]
            outputItemRender = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/grid/jeiInputItemRender" + str(index + 1) + "/item_cell/item/item_renderer")
            if not outputItemRender:
                continue
            outputItemRender.asItemRenderer().SetUiItem(outputItemName, 0)
            SetHoverText(self.recipeControl, "/bg/stack_panel/output_panel/grid/jeiInputItemRender" + str(index + 1), outputItemName, 0)
            label = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/grid/jeiInputItemRender" + str(index + 1) + "/item_cell/item/stack_count_label")
            label.asLabel().SetText(str(count))
    
    def OnGridChanged(self, path):
        grid = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/grid")
        if not grid:
            return
        data = self.recipeData["recipe"]["output"]
        inputItem = self.recipeData["recipe"]["input"]
        grid.asGrid().SetGridDimension((len(data["itemList"]), 1))
        inputRender = self.recipeControl.GetChildByPath("/bg/stack_panel/cutting_board_panel/cutting_board_bg/jeiInputFoodRender/item_cell/item/item_renderer")
        inputRender.asItemRenderer().SetUiItem(inputItem[0], inputItem[1])
        SetHoverText(self.recipeControl, "/bg/stack_panel/cutting_board_panel/cutting_board_bg/jeiInputFoodRender", inputItem[0], inputItem[1])
        tool = data["tool"]
        toolRender = self.recipeControl.GetChildByPath("/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer/item_cell/item/item_renderer")
        toolRender.asItemRenderer().SetUiItem(tool[0], 0)
        SetHoverText(self.recipeControl, "/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer", tool[0], 0)
        for index in range(len(data["itemList"])):
            outputItemData = data["itemList"][index]
            count = outputItemData.get("count", 1)
            outputItemName = outputItemData["itemName"]
            outputItemRender = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/grid/jeiInputItemRender" + str(index + 1) + "/item_cell/item/item_renderer")
            if not outputItemRender:
                continue
            outputItemRender.asItemRenderer().SetUiItem(outputItemName, 0)
            SetHoverText(self.recipeControl, "/bg/stack_panel/output_panel/grid/jeiInputItemRender" + str(index + 1), outputItemName, 0)
            label = self.recipeControl.GetChildByPath("/bg/stack_panel/output_panel/grid/jeiInputItemRender" + str(index + 1) + "/item_cell/item/stack_count_label")
            label.asLabel().SetText(str(count))
    
    def OnInterval(self):
        self.indexTurns += 1
        data = self.recipeData["recipe"]["output"]
        tool = data["tool"]
        if self.indexTurns >= len(tool):
            self.indexTurns = 0
        toolRender = self.recipeControl.GetChildByPath("/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer/item_cell/item/item_renderer")
        toolRender.asItemRenderer().SetUiItem(tool[self.indexTurns], 0)
        SetHoverText(self.recipeControl, "/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer", tool[self.indexTurns], 0)
