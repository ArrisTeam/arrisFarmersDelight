# -*- coding: utf-8 -*-
from .Registry import GetJeiApiModule, SetHoverText
from ...Client import Texts
from ...Shared.Data.Cutting import CuttingBoardDict, CuttingTagDict
from ...Shared.Rules import ItemTags

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
    for inputs, data in records():
        record = {"recipe": {"output": data, "input": inputs[0], "inputs": inputs}}
        for inputItem in inputs:
            cuttingBoardRecipesByInputDict.setdefault(inputItem, []).append(record)
        for tool in data.get("tool", []):
            cuttingBoardRecipesByInputDict.setdefault((tool, 0), []).append(record)
        for outputItemData in data["itemList"]:
            outputItem = (outputItemData.get("itemName", ""), outputItemData.get("itemAux", 0))
            cuttingBoardRecipesByResultDict.setdefault(outputItem, []).append(record)
    for outputItem, recipeList in cuttingBoardRecipesByResultDict.items():
        registry.setRecipeByResult(recipeTag, outputItem, recipeList)
    for inputItem, recipeList in cuttingBoardRecipesByInputDict.items():
        registry.setRecipeByInput(recipeTag, inputItem, recipeList)

def records():
    """每条砧板配方一条记录 [(原料 [(物品名, aux)], 配方)]：精确的那些原料就是键；按标签的（CuttingTagDict）原料是标签现在的成员
    （单人游戏里登记时引擎口已经准备好；远端客户端没量过，没准备好时按静态词表，只是少列别的模组的成员），配方页上轮换着画，
    按其中任何一样查用途都查得到。一个成员都没有的标签配方不登。"""
    found = [([inputItem], data) for inputItem, data in CuttingBoardDict.items()]
    found += [([(name, 0) for name in ItemTags.itemsOf(tag)], data) for tag, data in sorted(CuttingTagDict.items())]
    return [(inputs, data) for inputs, data in found if inputs]


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
        inputs = self.recipeData["recipe"].get("inputs") or ()
        if len(inputs) > 1:                      # 按标签的配方：原料在标签的成员里轮换
            self.inputTurns = (getattr(self, "inputTurns", 0) + 1) % len(inputs)
            inputItem = inputs[self.inputTurns]
            path = "/bg/stack_panel/cutting_board_panel/cutting_board_bg/jeiInputFoodRender"
            self.recipeControl.GetChildByPath(path + "/item_cell/item/item_renderer").asItemRenderer().SetUiItem(inputItem[0], inputItem[1])
            SetHoverText(self.recipeControl, path, inputItem[0], inputItem[1])
        data = self.recipeData["recipe"]["output"]
        tool = data["tool"]
        if self.indexTurns >= len(tool):
            self.indexTurns = 0
        toolRender = self.recipeControl.GetChildByPath("/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer/item_cell/item/item_renderer")
        toolRender.asItemRenderer().SetUiItem(tool[self.indexTurns], 0)
        SetHoverText(self.recipeControl, "/bg/stack_panel/cutting_board_panel/jeiKnifeRenderer", tool[self.indexTurns], 0)
