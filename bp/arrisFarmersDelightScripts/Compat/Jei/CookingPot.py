# -*- coding: utf-8 -*-
"""CookingPot - JEI 的"烹饪"分类：厨锅配方按成品、按用到的料登记，配方页上的配料一帧一帧轮换（客户端）

界面就绪时（JeiClient）登记一次：
- 按成品：每条配方（墓碑跳过，Shared/Rules/CookingPot.isLive）登在它的成品下；
- 按用途：配方用到的每一样（CookingPot.usesOf：格子的全部选项、标签格现在的成员、旧写法里的物品、盛菜的容器）都登这条配方；
  界面就绪时客户端的标签已经全了（前置包工程 .planning/kaleidoscope/R4 §6 第 7 项），别的模组进了标签的料也查得到；
- 配方页：配料按 CookingPot.framesOf 一帧一帧轮换（有格子的每格轮换自己的选项，和 JE 的 JEI 一样；格子不收的旧写法各占一帧）。
登记之后表又变了（下游晚到的配方、被移除的配方），JEI 里还是登记那一刻的样子（docs/ARCHITECTURE.md「联动契约与客户端的表」的限制）。
"""
from .Registry import GetJeiApiModule, SetHoverText
from ...Client import Texts
from ...Shared.Data.CookingPotRecipes import CookingPotRecipeList
from ...Shared.Rules import CookingPot as PotRules

TITLE = ("jei.farmersdelight.cooking", "烹饪")      # 分类名：JE 的键（英文 Cooking），客户端按玩家的语言查，语言文件里没有时用中文
RECIPE_TAG = "cooking_pot"
INPUTS = 6
INPUT_PATH = "/bg/stack_panel/input_panel/jeiInputItemRender%d"


def indexes():
    """({成品 (物品名, aux): [配方]}, {用到的 (物品名, aux): [配方]})：每张表里配方按配方表的先后、不重复。"""
    byResult, byInput = {}, {}
    for recipe in CookingPotRecipeList:
        if not PotRules.isLive(recipe) or not PotRules.framesOf(recipe):
            continue
        byResult.setdefault((recipe["CookResult"][0], recipe["CookResult"][1]), []).append(recipe)
        for kind in PotRules.usesOf(recipe):
            byInput.setdefault(kind, []).append(recipe)
    return byResult, byInput


def RegisterCookingPotRecipes():
    registry = GetJeiApiModule()
    if not registry:
        return
    registry.registerRecipeType(
        RECIPE_TAG,
        ("arris:cooking_pot", 0),
        Texts.of(*TITLE),
        CookingPotRecipe,
        "jei_farmers_delight.jeiCookingPotRecipe",
        65
    )
    byResult, byInput = indexes()
    for itemData in registry.getAllRegisteredItems():
        key = (itemData[0], itemData[1])
        if key in byResult:
            registry.setRecipeByResult(RECIPE_TAG, itemData, byResult[key])
        if key in byInput:
            registry.setRecipeByInput(RECIPE_TAG, itemData, byInput[key])


class CookingPotRecipe:
    def __init__(self, screenNode, recipeControl, recipeData, recipeIndex, itemData):
        self.screenNode = screenNode
        self.recipeControl = recipeControl
        self.recipeData = recipeData
        self.recipeIndex = recipeIndex
        self.itemData = itemData
        self.indexTurns = 0                          # 轮换到第几帧
        self.frames = PotRules.framesOf(recipeData)

    def _showInputs(self, frame):
        for index in range(INPUTS):
            path = INPUT_PATH % (index + 1)
            render = self.recipeControl.GetChildByPath(path + "/item_cell/item/item_renderer")
            if index >= len(frame):
                render.SetVisible(False)
                continue
            name, aux = frame[index]
            render.SetVisible(True)
            render.asItemRenderer().SetUiItem(name, aux)
            SetHoverText(self.recipeControl, path, name, aux)

    def OnCreate(self):
        """创建配方UI时调用"""
        if not self.frames:
            return
        self._showInputs(self.frames[0])
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
        if not self.frames:
            return
        self.indexTurns = (self.indexTurns + 1) % len(self.frames)
        self._showInputs(self.frames[self.indexTurns])
