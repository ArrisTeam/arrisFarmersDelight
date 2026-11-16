# -*- coding: utf-8 -*-
"""CookingPot - 厨锅配方匹配与出料结算（双端，纯规则）

配方匹配：一锅里每个非空输入格算一件食材（同一格叠了多个也只算一件，与 Java 版一致）。
把各格的 (物品名, aux) 排序后作为键查索引，O(1)；CookingPotRecipeList 被修改后要调用 rebuildIndex()。
另有两份给厨锅站点用的索引（Shared/Rules/PotStation.py）：每种写法各种料占几格、哪些物品是食材。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList

_recipeIndex = {}
_partsIndex = {}             # frozenset(种类) -> [{种类: 占几格}, ...]（按配方表顺序）
_ingredients = set()


def rebuildIndex():
    """重建配方索引。键冲突时保留先插入的那条，与旧实现"首个匹配获胜"一致。"""
    _recipeIndex.clear()
    _partsIndex.clear()
    _ingredients.clear()
    for recipeDict in CookingPotRecipeList:
        cookResult = recipeDict["CookResult"]
        pushItemList = recipeDict.get("PushItem", [])
        for variant in recipeDict["Recipe"]:
            key = tuple(sorted(variant))
            if key not in _recipeIndex:
                _recipeIndex[key] = (cookResult, pushItemList)
            parts = {}
            for entry in variant:
                kind = (entry[0], entry[1])
                parts[kind] = parts.get(kind, 0) + 1
                _ingredients.add(kind)
            _partsIndex.setdefault(frozenset(parts), []).append(parts)


def partsFor(kinds):
    """种类集合正好是 kinds 的各个配方写法：[{种类: 占几格}, ...]。"""
    return _partsIndex.get(frozenset(kinds), ())


def isIngredient(kind):
    """(物品名, aux) 是不是某个配方的食材。"""
    return kind in _ingredients


def lookupRecipe(inputKey):
    """inputKey 为 tuple(sorted([(name, aux), ...]))；返回 (成品 (name, aux), 余料列表) 或 None。"""
    return _recipeIndex.get(inputKey)


def inputKeyOf(itemDicts):
    """输入格物品列表（空格为 {} 或 None）→ 查表键；全空返回 None。"""
    entries = [(itemDict["newItemName"], itemDict["newAuxValue"]) for itemDict in itemDicts if itemDict]
    if not entries:
        return None
    return tuple(sorted(entries))


def matchRecipe(itemDicts):
    """返回 (成品 itemDict（count 恒为 1）, 余料列表)；没有匹配的配方返回 (None, None)。"""
    key = inputKeyOf(itemDicts)
    hit = _recipeIndex.get(key) if key else None
    if not hit:
        return None, None
    cookResult, pushItemList = hit
    return {"newItemName": cookResult[0], "newAuxValue": cookResult[1], "count": 1}, pushItemList


def findRecipeByResult(resultItemName):
    """按成品名找第一条配方（与旧实现"首个匹配获胜"一致）；没有返回 None。"""
    for recipeDict in CookingPotRecipeList:
        if recipeDict["CookResult"][0] == resultItemName:
            return recipeDict
    return None


def transferAmount(previewCount, resultCount, maxStackSize, vesselCount=None):
    """预览槽 → 产出槽这一次能转移多少份。

    不超过待出料数、产出槽剩余堆叠空间；成品需要容器时还不超过容器格里的容器数。
    """
    amount = min(previewCount, maxStackSize - resultCount)
    if vesselCount is not None:
        amount = min(amount, vesselCount)
    return max(0, amount)


rebuildIndex()
