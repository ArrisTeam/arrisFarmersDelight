# -*- coding: utf-8 -*-
"""BoardAssembly - JEI 的"砧板摆盘"分类，和藏起被拦的工作台配方（客户端）

对应 Hands-On Delight：compat/jei/HandsOnJeiPlugin.java + AssemblyCategory.java。只在场景交互前置联动上、砧板站点开着时才登记（JeiClient 判）：
那时三明治这类菜改在砧板上摆、工作台上的合成被拦（Compat/Diegesis/DishCrafts），JEI 里要看得到它们在砧板上怎么摆，而且不该再看到那条做不出的工作台配方
（配置里的 remove_crafting_recipes 关了就不藏，和服务端拦不拦是同一个开关）。没装前置包时这个模块不会被调，JEI 照旧只有工作台配方。
画法照 AssemblyLayout：打底的那一样躺在板上（提示里多一行"先放在砧板上"），别的层三个一排放在格子里（几排上下居中），箭头，成品；
一个位置有几种可换的物品就轮着显示（JE 的 Ingredient）。界面定义：rp/ui/jei_farmers_delight.json 的 jeiBoardAssemblyRecipe；配方怎么并、哪条工作台配方该藏
在 Shared/Rules/DishJei.py。藏配方要 arrisJei 有 hideRecipes（能力标志 HIDE_RECIPES），老版本的 JEI 上只多出分类、工作台配方照旧显示。
"""
from .Registry import GetJeiApiModule, SetHoverText
from ...Client import Texts
from ...Shared.Rules import DishJei

TAG = "board_assembly"
ICON = ("arris:cutting_board", 0)
CONTROL = "jei_farmers_delight.jeiBoardAssemblyRecipe"
ROW_HEIGHT = 56                    # 一条配方在配方页里占多高（界面定义里的底板高 58）
AREA = "/bg/area"
HEIGHT, SLOT, LAYERS_X = 54, 18, 50          # AssemblyLayout：配方区高、格子边长、各层从哪一列起
TITLE = ("handson_delight.assembly", "砧板摆盘")
FIRST = ("handson_delight.assembly.first", "先放在砧板上")
HIDER = "arris_farmers_delight:board_dishes"
_done = {"registered": False}


def RegisterBoardAssemblyRecipes(hide):
    """登记分类和它的配方（只登记一次）；hide：把被拦的工作台配方藏起来。"""
    registry = GetJeiApiModule()
    if not registry or _done["registered"]:
        return
    _done["registered"] = True
    registry.registerRecipeType(TAG, ICON, Texts.of(*TITLE), BoardAssemblyRecipe, CONTROL, ROW_HEIGHT)
    byResult, byInput = {}, {}
    for recipe in DishJei.recipes():
        data = {"recipe": recipe}
        byResult.setdefault(recipe["result"], []).append(data)
        for item in DishJei.itemsOf(recipe):
            byInput.setdefault(item, []).append(data)
    for item, found in byResult.items():
        registry.setRecipeByResult(TAG, item, found)
    for item, found in byInput.items():
        registry.setRecipeByInput(TAG, item, found)
    if hide and getattr(registry, "HIDE_RECIPES", False):
        registry.hideRecipes(HIDER, "crafting_table", DishJei.isDishCraft)


class BoardAssemblyRecipe:
    def __init__(self, screenNode, recipeControl, recipeData, recipeIndex, itemData):
        self.screenNode = screenNode
        self.recipeControl = recipeControl
        self.recipeData = recipeData
        self.recipeIndex = recipeIndex
        self.itemData = itemData
        self.indexTurns = 0  # 物品轮播索引

    def _item(self, path, choices, extra=None):
        """这个位置现在轮到哪一样：画出来、配上悬浮文字。"""
        name, aux = choices[self.indexTurns % len(choices)]
        render = self.recipeControl.GetChildByPath(path + "/item_cell/item/item_renderer")
        if not render:
            return
        render.asItemRenderer().SetUiItem(name, aux)
        SetHoverText(self.recipeControl, path, name, aux, None, extra)

    def _draw(self, place):
        """place：把各层的格子摆到位、显隐设好（建的时候做一次，轮播时只换物品）。"""
        recipe = self.recipeData["recipe"]
        self._item(AREA + "/base", recipe["base"], Texts.of(*FIRST))
        layers = recipe["layers"]
        for index in range(DishJei.MOST_LAYERS):
            path = AREA + "/layer%d" % index
            if place:
                control = self.recipeControl.GetChildByPath(path)
                if not control:
                    continue
                control.SetVisible(index < len(layers))
                if index < len(layers):
                    column, top = DishJei.layerPlace(index, len(layers), HEIGHT, SLOT)
                    control.SetPosition((float(LAYERS_X + column * SLOT), float(top)))
            if index < len(layers):
                self._item(path, layers[index])
        if place:
            self._item(AREA + "/result", [recipe["result"]])
            label = self.recipeControl.GetChildByPath(AREA + "/result/item_cell/item/stack_count_label")
            if label:
                label.asLabel().SetText(str(recipe["count"]) if recipe["count"] > 1 else "")

    def OnCreate(self):
        """创建配方UI时调用"""
        self._draw(True)

    def OnInterval(self):
        """有几种可换物品的位置换下一种"""
        recipe = self.recipeData["recipe"]
        if any(len(slot) > 1 for slot in [recipe["base"]] + list(recipe["layers"])):
            self.indexTurns += 1
            self._draw(False)
