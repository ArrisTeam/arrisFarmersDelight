# -*- coding: utf-8 -*-
# runner: both
"""锁住对外联动契约：ModAttr("arris") 上的三个函数（见 linkage.md）。

本机 AddOn/ 下 6 个下游包（Ends / Butcher / Fruits / Corn / Nether's Delight、Farmer's Respite）
在 LoadServerAddonScriptsAfter 里取这三个函数，按"变量名字符串"读写配置表：
    ArrisFarmersDelightInterface(target, element)  向列表 / 字典追加
    ArrisFarmersDelightObtain(target)              取回配置对象本身（活引用）
    ArrisAddCookingPotRecipe(name, recipe)         给已有厨锅配方追加一个变体
它们拿到的必须是同一批容器对象：下游会把 obtain("knifeList") 挂到自己的砧板配方 "tool" 上，
之后任何一方往 knifeList 里加刀都要对所有条目生效。重构移动数据表时，这个测试必须一直绿。
"""
from __future__ import print_function

import fdtest

# 契约函数所在模块（服务端在导入时把它们 SetAttr 到 ModAttr("arris")）
CONTRACT = fdtest.load("Api.LegacyModAttr")
POT_RULES = fdtest.load("Shared.Rules.CookingPot")
interface = CONTRACT.ArrisFarmersDelightInterface
obtain = CONTRACT.ArrisFarmersDelightObtain
addRecipe = CONTRACT.AddCookingPotRecipe

# 下游实测用到的 7 个变量名；linkage.md 还写了"其他变量详见 modConfig.py"，下面另列
USED_BY_DOWNSTREAM = ["CookingPotRecipeList", "CuttingBoardDict", "CanCookedFoodDict", "ComposterItemDict",
                      "StoveList", "CanProvideHeatBlockList", "knifeList"]
OTHER_PUBLIC = ["axeList", "itemChangeBlockDict", "shapedRecipeContainerDict", "pieList", "canClimbList",
                "cabinetList", "WildCropDict", "negativeEffect", "platePackagedFoodDict", "cropsDict",
                "horseComponentsDict", "wolfComponentsDict"]


def _recipe(result, variants, vessel=("minecraft:bowl", 0)):
    return {"Recipe": variants, "CookResult": result, "Vessel": vessel, "PushItem": [], "text": "test"}


def testAllNamesObtainable():
    for name in USED_BY_DOWNSTREAM + OTHER_PUBLIC:
        value = obtain(name)
        assert value, name
        assert obtain(name) is value, "obtain 每次必须返回同一个对象: %s" % name


def testObtainReturnsLiveKnifeList():
    knives = obtain("knifeList")
    board = obtain("CuttingBoardDict")
    beef = board[("minecraft:beef", 0)]
    assert beef["tool"] is knives, "砧板刀具条目必须引用同一个 knifeList 对象"
    knives.append("test:knife_a")
    try:
        assert "test:knife_a" in beef["tool"]
    finally:
        knives.remove("test:knife_a")


def testInterfaceAppendsStringToList():
    stoves = obtain("StoveList")
    before = len(stoves)
    result = interface("StoveList", "test:stove")
    try:
        assert result is stoves
        assert stoves[-1] == "test:stove" and len(stoves) == before + 1
    finally:
        stoves.remove("test:stove")


def testInterfaceExtendsListInPlace():
    heat = obtain("CanProvideHeatBlockList")
    before = list(heat)
    result = interface("CanProvideHeatBlockList", ["test:heat_a", "test:heat_b"])
    try:
        assert result is heat, "list + list 必须就地扩展，不能换成新列表"
        assert heat[-2:] == ["test:heat_a", "test:heat_b"]
    finally:
        del heat[len(before):]


def testInterfaceUpdatesDictInPlace():
    cookable = obtain("CanCookedFoodDict")
    result = interface("CanCookedFoodDict", {"test:raw": "test:cooked"})
    try:
        assert result is cookable and cookable["test:raw"] == "test:cooked"
    finally:
        del cookable["test:raw"]


def testInterfaceRejectsFalsyTargetAndUnknownName():
    assert interface(None) is False
    assert interface("") is False
    try:
        interface("NoSuchVariable", "x")
    except KeyError:
        pass
    else:
        raise AssertionError("未知变量名沿用旧行为：抛 KeyError")


def testCookingPotRecipeAppendAndIndex():
    recipes = obtain("CookingPotRecipeList")
    before = len(recipes)
    recipe = _recipe(("test:soup", 0), [[("test:a", 0), ("test:b", 0)]])
    result = interface("CookingPotRecipeList", recipe)
    try:
        assert result is recipes and recipes[-1] is recipe and len(recipes) == before + 1
        hit = POT_RULES.lookupRecipe(tuple(sorted([("test:b", 0), ("test:a", 0)])))
        assert hit is not None and hit[0] == ("test:soup", 0), "追加配方后必须重建索引"
    finally:
        recipes.remove(recipe)
        POT_RULES.rebuildIndex()


def testCookingPotRecipeRejectsMoreThanSixIngredients():
    recipes = obtain("CookingPotRecipeList")
    before = len(recipes)
    tooMany = _recipe(("test:big", 0), [[("test:x", 0)] * 7])
    assert interface("CookingPotRecipeList", tooMany) is False
    assert len(recipes) == before


def testAddCookingPotRecipeVariant():
    stew = None
    for recipeDict in obtain("CookingPotRecipeList"):
        if recipeDict["CookResult"][0] == "minecraft:mushroom_stew":
            stew = recipeDict
    assert stew is not None
    variant = [("test:mushroom", 0), ("test:mushroom", 0)]
    result = addRecipe("minecraft:mushroom_stew", variant)
    try:
        assert result is stew["Recipe"] and stew["Recipe"][-1] == variant
        hit = POT_RULES.lookupRecipe(tuple(sorted(variant)))
        assert hit is not None and hit[0] == ("minecraft:mushroom_stew", 0)
    finally:
        stew["Recipe"].remove(variant)
        POT_RULES.rebuildIndex()
    assert addRecipe("test:unknown_dish", variant) is False
    assert addRecipe("minecraft:mushroom_stew", [("test:x", 0)] * 7) is False
    assert addRecipe("", variant) is False


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
