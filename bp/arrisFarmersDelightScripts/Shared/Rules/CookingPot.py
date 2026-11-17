# -*- coding: utf-8 -*-
"""CookingPot - 厨锅配方匹配与出料结算（双端，纯规则）

配方匹配：一锅里每个非空输入格算一件食材（同一格叠了多个也只算一件，与 Java 版一致）。
把各格的 (物品名, aux) 排序后作为键查索引，O(1)；CookingPotRecipeList 被修改后要调用 rebuildIndex()。
出锅一份：成品 CookCount 个（JE 的配方结果数量，饺子 2 个），吐出 PushItem 加上用掉的料剩下的空容器（JE 的
CookingPotBlockEntity：配料的合成剩余物，再加 INGREDIENT_REMAINDER_OVERRIDES，表在 Shared/Data/Remainders.py——
奶桶剩桶、奶瓶剩玻璃瓶、番茄酱剩碗……；配方的 PushItem 里已经写了的不重复给）。
另有几份给厨锅站点用的索引（Shared/Rules/PotStation.py、PotLayout.py）：每种写法各种料占几格（候选，带配方序号）、哪些物品是食材、
哪些物品是盛菜的容器、一份煮出来给多少经验（锅里记着煮了几份，盛出时一并给，见 Server/Helpers/PotContainer.py）。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList
from ..Data.Remainders import potRemainderOf

DEFAULT_COOK_SECONDS = 10.0  # JE 的厨锅配方缺省 200 刻
DEFAULT_EXPERIENCE = 1.0     # JE 的厨锅配方缺省经验
_recipeIndex = {}
_cookSeconds = {}            # 成品名 -> 一份煮多久（秒），按配方表顺序先到先得
_experience = {}             # 成品名 -> 盛出一个给多少经验（JE 按煮了几份给，一份出几个时平分到每个）
_partsIndex = {}             # frozenset(种类) -> [{种类: 占几格}, ...]（按配方表顺序）
_candidates = {}             # frozenset(种类) -> [(配方序号, {种类: 占几格}), ...]（按配方表顺序，一个写法一条）
_recipeOfKey = {}            # 查表键 -> 第一个有这种写法的配方序号（站点选菜时的"锅按现在的摆法读成哪道菜"）
_servingExperience = {}      # 成品名 -> 煮出一份给多少经验（JE 的 Experience，不除以一份出几个）
_ingredients = set()
_vessels = set()             # 盛菜用的容器的物品名（配方的 Vessel）


def pushItemsOf(variant, declared):
    """这种写法出锅一份吐出什么：配方写的 PushItem，再加上料剩下的空容器（PushItem 里已有的那件不重复）。"""
    pushed = list(declared or [])
    spare = list(pushed)
    for entry in variant:
        name = potRemainderOf(entry[0])
        if name is None:
            continue
        left = (name, 0)
        if left in spare:
            spare.remove(left)
        else:
            pushed.append(left)
    return pushed


def rebuildIndex():
    """重建配方索引。键冲突时保留先插入的那条，与旧实现"首个匹配获胜"一致。"""
    _recipeIndex.clear()
    _cookSeconds.clear()
    _experience.clear()
    _partsIndex.clear()
    _candidates.clear()
    _recipeOfKey.clear()
    _servingExperience.clear()
    _ingredients.clear()
    _vessels.clear()
    for index, recipeDict in enumerate(CookingPotRecipeList):
        cookResult = recipeDict["CookResult"]
        count = max(1, int(recipeDict.get("CookCount") or 1))
        _cookSeconds.setdefault(cookResult[0], float(recipeDict.get("CookTime") or DEFAULT_COOK_SECONDS))
        experience = DEFAULT_EXPERIENCE if recipeDict.get("Experience") is None else float(recipeDict["Experience"])
        _experience.setdefault(cookResult[0], experience / count)
        _servingExperience.setdefault(cookResult[0], experience)
        if recipeDict.get("Vessel"):
            _vessels.add(recipeDict["Vessel"][0])
        for variant in recipeDict["Recipe"]:
            key = tuple(sorted(variant))
            if key not in _recipeIndex:
                _recipeIndex[key] = (cookResult, pushItemsOf(variant, recipeDict.get("PushItem")), count)
            _recipeOfKey.setdefault(key, index)
            parts = {}
            for entry in variant:
                kind = (entry[0], entry[1])
                parts[kind] = parts.get(kind, 0) + 1
                _ingredients.add(kind)
            _partsIndex.setdefault(frozenset(parts), []).append(parts)
            _candidates.setdefault(frozenset(parts), []).append((index, parts))


def cookSecondsOf(resultName):
    """这道菜一份煮多久（秒）：配方表里的 CookTime，没写就是 10 秒（JE 的 200 刻）。"""
    return _cookSeconds.get(resultName, DEFAULT_COOK_SECONDS)


def experienceOf(resultName):
    """盛出一个这道菜给多少经验：配方表里一份的 Experience（没写就是 1，JE 的缺省）除以一份出几个。"""
    return _experience.get(resultName, DEFAULT_EXPERIENCE)


def servingExperienceOf(resultName):
    """煮出一份这道菜给多少经验（JE 的 Experience；盛出时按煮了几份算，见 experienceOrb）。"""
    return _servingExperience.get(resultName, DEFAULT_EXPERIENCE)


def experienceOrb(experience, count, roll):
    """盛出 count 个共给多少整数经验：整数部分照给，零头按概率进一（JE 的厨锅 / 熔炉同款）；roll 是 0..1 的随机数。"""
    total = max(0.0, float(experience) * count)
    whole = int(total)
    return whole + (1 if roll < total - whole else 0)


def partsFor(kinds):
    """种类集合正好是 kinds 的各个配方写法：[{种类: 占几格}, ...]。"""
    return _partsIndex.get(frozenset(kinds), ())


def candidatesFor(kinds):
    """种类集合正好是 kinds 的各个配方写法：[(配方序号, {种类: 占几格}), ...]，按配方表顺序（站点选菜用）。"""
    return _candidates.get(frozenset(kinds), ())


def isIngredient(kind):
    """(物品名, aux) 是不是某个配方的食材。"""
    return kind in _ingredients


def isVessel(itemName):
    """这个物品是不是某道菜盛菜用的容器（只比物品名，和锅自己装碗一致）。"""
    return itemName in _vessels


def vesselOf(resultName):
    """盛这道菜要的容器 (物品名, aux)，不要容器的菜返回 None。"""
    recipe = findRecipeByResult(resultName)
    return recipe.get("Vessel") if recipe else None


def lookupRecipe(inputKey):
    """inputKey 为 tuple(sorted([(name, aux), ...]))；返回 (成品 (name, aux), 余料列表) 或 None。"""
    hit = _recipeIndex.get(inputKey)
    return hit[:2] if hit else None


def inputKeyOf(itemDicts):
    """输入格物品列表（空格为 {} 或 None）→ 查表键；全空返回 None。"""
    entries = [(itemDict["newItemName"], itemDict["newAuxValue"]) for itemDict in itemDicts if itemDict]
    if not entries:
        return None
    return tuple(sorted(entries))


def matchRecipe(itemDicts):
    """返回 (成品 itemDict（count 是一份出几个）, 余料列表)；没有匹配的配方返回 (None, None)。"""
    key = inputKeyOf(itemDicts)
    hit = _recipeIndex.get(key) if key else None
    if not hit:
        return None, None
    cookResult, pushItemList, count = hit
    return {"newItemName": cookResult[0], "newAuxValue": cookResult[1], "count": count}, list(pushItemList)


def matchIndex(itemDicts):
    """格子里的料按现在的摆法被读成哪个配方（配方表里的序号）；读不成返回 None。"""
    key = inputKeyOf(itemDicts)
    return _recipeOfKey.get(key) if key else None


def resultNameOf(index):
    """配方表里第 index 条的成品名（锅记着的上一条配方的成品，见 PotRecipeMemory）。"""
    return CookingPotRecipeList[index]["CookResult"][0]


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
