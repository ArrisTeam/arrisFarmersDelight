# -*- coding: utf-8 -*-
"""LegacyModAttr - 对外联动契约 v1（双端可导入；服务端在加载时挂到 ModAttr("arris")）

linkage.md 公开的三个函数，按"变量名字符串"读写配置表：
    ArrisFarmersDelightInterface(target, element)   向列表 / 字典追加
    ArrisFarmersDelightObtain(target)               取回配置对象本身（活引用）
    AddCookingPotRecipe(name, recipe)               给已有厨锅配方追加一个变体（ModAttr 键为 ArrisAddCookingPotRecipe）
旧实现直接查 modConfig 的 globals()；数据表拆进 Shared/Data 后改为这里的显式白名单。
白名单里的就是 Shared/Data 的同一批容器对象（身份不变），签名、返回值、
"容器为空返回 False"、"未知名字抛 KeyError" 等行为逐字保留，由 tests/test_legacy_modattr_contract.py 锁住。
"""
from ..Shared.Data import Blocks, Cooking, CookingPotRecipes, Cutting, Effects, Farming, Food, GuideBook, Mobs
from ..Shared.Rules import CookingPot as CookingPotRules

# 每个厨锅配方变体最多 6 个食材（厨锅只有 6 个输入格）
MAX_RECIPE_INGREDIENTS = 6

# 变量名 → 配置对象。下游实测用到前 7 个；其余是旧 modConfig 里同样可以按名字访问的表
_TARGETS = {
    "CookingPotRecipeList": CookingPotRecipes.CookingPotRecipeList,
    "CuttingBoardDict": Cutting.CuttingBoardDict,
    "CanCookedFoodDict": Cooking.CanCookedFoodDict,
    "ComposterItemDict": Farming.ComposterItemDict,
    "StoveList": Cooking.StoveList,
    "CanProvideHeatBlockList": Cooking.CanProvideHeatBlockList,
    "knifeList": Cutting.knifeList,
    "axeList": Cutting.axeList,
    "itemChangeBlockDict": Food.itemChangeBlockDict,
    "shapedRecipeContainerDict": Food.shapedRecipeContainerDict,
    "pieList": Food.pieList,
    "platePackagedFoodDict": Food.platePackagedFoodDict,
    "canClimbList": Blocks.canClimbList,
    "cabinetList": Blocks.cabinetList,
    "WildCropDict": Farming.WildCropDict,
    "cropsDict": Farming.cropsDict,
    "negativeEffect": Effects.negativeEffect,
    "horseComponentsDict": Mobs.horseComponentsDict,
    "wolfComponentsDict": Mobs.wolfComponentsDict,
    "uiGuideBookPath": GuideBook.uiGuideBookPath,
    "uiGuideBookScreen": GuideBook.uiGuideBookScreen,
}


def _recipeTooLarge(recipeDict):
    for variant in recipeDict["Recipe"]:
        if len(variant) > MAX_RECIPE_INGREDIENTS:
            return True
    return False


def ArrisFarmersDelightInterface(target, element=None):
    """
    向配置字典或列表内添加元素
    :param target: 需要调用的变量名称 (str)
    :param element: 需要添加进去的元素(如果目标是list,则支持str或list,如果目标是dict,则仅支持dict)
    :return 修改结果
    """
    if not target:
        return False
    container = _TARGETS[target]
    if not container:
        return False
    if target == "CookingPotRecipeList":
        # 旧实现只接受单条配方字典（传列表会在这里报错）；现在逐条校验，任一条超过 6 格整体拒绝
        recipes = element if isinstance(element, list) else [element]
        for recipeDict in recipes:
            if _recipeTooLarge(recipeDict):
                return False
    if isinstance(container, list):
        if isinstance(element, list):
            container.extend(element)
        else:
            container.append(element)
    elif isinstance(container, dict) and isinstance(element, dict):
        container.update(element)
    if target == "CookingPotRecipeList":
        CookingPotRules.rebuildIndex()
    return container


def ArrisFarmersDelightObtain(target):
    """
    获取配置字典或列表
    :param target: 需要获取的变量名称 (str)
    :return 结果
    """
    if not target:
        return False
    container = _TARGETS[target]
    if not container:
        return False
    return container


def AddCookingPotRecipe(name, recipe):
    """
    在厨锅原有的配方上，新增额外配方
    :param name: 对应食物id (str)
    :param recipe: 对应需要添加上去的配方 (list)
    :return 结果
    """
    if not name:
        return False
    if len(recipe) > MAX_RECIPE_INGREDIENTS:
        return False
    for recipeDict in CookingPotRecipes.CookingPotRecipeList:
        if recipeDict["CookResult"][0] == name:
            recipeDict["Recipe"].append(recipe)
            CookingPotRules.rebuildIndex()
            return recipeDict["Recipe"]
    return False
