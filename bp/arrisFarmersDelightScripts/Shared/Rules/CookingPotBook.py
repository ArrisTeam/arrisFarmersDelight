# -*- coding: utf-8 -*-
"""CookingPotBook - 厨锅食谱书的规则：格号、搜索、选中食谱的展示内容、按配方补食材的计划（双端，纯规则）

厨锅容器是 netease:block_container 的 8 个格子：0-5 食材，6 容器（碗、玻璃瓶……），7 成品。
食谱表是 Shared/Data/CookingPotRecipes.CookingPotRecipeList，下游模组会在运行时往里追加，所以这里每次现读、不缓存。
"""
from ..Data.CookingPotRecipes import CookingPotRecipeList

INPUT_SLOTS = 6
VESSEL_SLOT = 6
RESULT_SLOT = 7
POT_SLOTS = 8
# 食谱书详情的展示格：与厨锅格同序，0-5 食材，6 容器，7 成品
BOOK_CELLS = 8
# 搜索词最多几个字
SEARCH_LIMIT = 16

try:
    _TEXT = unicode  # noqa: F821 - py2
except NameError:
    _TEXT = str


def _chars(value):
    """比较用的文字：py2 的 utf-8 字节串解成 unicode（不然和 unicode 的食谱名比较会抛异常），不是文字的当空。"""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return value if isinstance(value, _TEXT) else u""


def visibleRecipes(search):
    """搜索词过滤后的食谱：表里的下标，保持表的顺序。搜索词为空是全部；按食谱名包含判断，不分大小写。"""
    word = _chars(search).lower()
    return [index for index, recipe in enumerate(CookingPotRecipeList)
            if not word or word in _chars(recipe.get("text")).lower()]


def recipeAt(index):
    """表里第 index 条食谱；越界为 None。"""
    return CookingPotRecipeList[index] if 0 <= index < len(CookingPotRecipeList) else None


def pickedRecipe(search, picked):
    """（搜索词，在过滤后的列表里选中的序号）-> 食谱字典；没选中或越界为 None。"""
    shown = visibleRecipes(search)
    return recipeAt(shown[picked]) if 0 <= picked < len(shown) else None


def variantCount(recipe):
    """食谱有几个变体（可替换的配方）。"""
    return max(1, len(recipe["Recipe"]))


def variantOf(recipe, variant):
    """食谱的第 variant 个变体（超出个数时取模）：[(物品名, aux), ...]。"""
    rows = recipe["Recipe"]
    return list(rows[variant % len(rows)]) if rows else []


def vesselNames():
    """现有食谱用到的容器物品名（碗、玻璃瓶……）；下游追加的食谱也算。"""
    return frozenset(recipe["Vessel"][0] for recipe in CookingPotRecipeList if recipe.get("Vessel"))


def _stack(item, count=1):
    return {"newItemName": item[0], "newAuxValue": item[1], "count": count}


def listRows(indices):
    """食谱列表每行显示的物品：成品，一份。"""
    return [_stack(recipeAt(index)["CookResult"]) for index in indices]


def bookCells(recipe, variant):
    """食谱书详情的展示格 {格号: 物品堆}：食材（选中的变体）、容器（没有就空着）、成品。"""
    cells = dict((index, _stack(item)) for index, item in enumerate(variantOf(recipe, variant)[:INPUT_SLOTS]))
    if recipe.get("Vessel"):
        cells[VESSEL_SLOT] = _stack(recipe["Vessel"])
    cells[RESULT_SLOT] = _stack(recipe["CookResult"])
    return cells


def keyOf(stack):
    """物品堆 -> (物品名, aux)，空为 None。配方按这两样认食材，附加数据不看。"""
    if not stack or stack.get("count", 0) <= 0:
        return None
    return (stack.get("newItemName"), int(stack.get("newAuxValue") or 0))


def planFill(variant, slotKeys):
    """
    把配方变体的食材补进厨锅 6 个食材格的计划：返回 (放进空格的, 给已有的格子再加一个的) 或 None（空格不够）。
    - 一个食材占一个格子（锅按"每个非空格算一件食材"匹配，同一格叠几个都只算一件，所以同种食材要几件就占几格）；
    - 格子里已经放着配方要的食材时，那一格不再另占空格，只在放得下时再加一个（反复点就是备多份料）；
    - 两个列表的元素都是 (格号, (物品名, aux))；放进空格的是必须成功的，加一个的有就加、没有或放不下就算了。
    variant 是 [(物品名, aux), ...]，slotKeys 是 6 个食材格现有东西的 keyOf（空格为 None）。
    """
    need = [tuple(item) for item in variant]
    topUps = []
    for index, key in enumerate(slotKeys):
        if key is not None and key in need:
            need.remove(key)
            topUps.append((index, key))
    empty = [index for index, key in enumerate(slotKeys) if key is None]
    if len(need) > len(empty):
        return None
    return list(zip(empty, need)), topUps
