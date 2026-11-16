# -*- coding: utf-8 -*-
"""StationBooks - 四个站点旁的食谱书页：厨锅、砧板（摆盘 + 切）、煎锅、炉灶（双端，纯规则）

对应 Hands-On Delight 的 PotBook / BoardBook / SkilletBook / StoveBook。页的写法见场景交互 · 前置的 Shared/Book.py：
{"key", "item"（成品）, "ways"（写法：[[这一格能放的 (物品名, aux), ...], ...]）, "foot"（脚注物品）, "note", "kind"（标签）}。
- 厨锅：一道菜一页，键是配方表下标；脚注是盛菜的容器和时钟，注明一份在站点里几秒（JE 的 CookTime x 配置倍率 / 1.5，HoD 的 PotBook）；能从背包放料；
- 砧板：摆盘的菜按成品一页（键 "d:成品名"，写法底座在前），能切的东西按食材一页（键 "c:名字:aux"，第二格是能用的工具，
  脚注是其余产物）；标签：全部 / 摆盘 / 刀切 / 别的工具；摆盘的菜能从背包放料，切的只看；
- 煎锅、炉灶：能煎 / 烤的一件一页，注明两面一共几秒（只煎一面的蛋按一面）；只看。
"""
from ..Data.Cooking import CanCookedFoodDict
from ..Data.CookingPotRecipes import CookingPotRecipeList
from ..Data.Cutting import CuttingBoardDict
from . import CookingPot, CuttingStation, DishStation, GrillStation, PanStation
from .HandsOn import PotCooking

CLOCK = "minecraft:clock"
DISH_PREFIX = "d:"
CUT_PREFIX = "c:"

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2：客户端发来的键可能是 unicode
except NameError:
    _TEXT = (str,)


def stack(name, aux=0, count=1):
    return {"newItemName": name, "newAuxValue": int(aux), "count": int(count)}


def _seconds(value):
    return "%d 秒" % int(round(value))


def _pair(value):
    return isinstance(value, (tuple, list)) and len(value) == 2


# ---------------------------------------------------------------- 放料（服务端按背包挑写法、凑份数；规则同前置包的 Shared/Book.py）

def needOf(kinds):
    """一份要的料：[(物品名, aux), ...] -> {(物品名, aux): 件数}。"""
    need = {}
    for kind in kinds:
        need[kind] = need.get(kind, 0) + 1
    return need


def setsOf(kinds, pool, most):
    """背包 pool（{(物品名, aux): 数}）里的料够凑几份（最多 most 份）。"""
    need = needOf(kinds)
    return max(0, min([int(most)] + [pool.get(kind, 0) // count for kind, count in need.items()])) if need else 0


def bestKinds(variants, pool):
    """几种写法里背包凑得出份数最多的那种（同样多取靠前的）：[(物品名, aux), ...]；一份都凑不出返回 None。"""
    best, bestSets = None, 0
    for variant in variants:
        kinds = [(entry[0], entry[1]) for entry in variant]
        sets = setsOf(kinds, pool, 1 << 16)
        if sets > bestSets:
            best, bestSets = kinds, sets
    return best


# ---------------------------------------------------------------- 厨锅

def _potWays(recipe):
    """配料井怎么摆（RecipeBook.drawDish：一格是一组备选，每秒换一种）：配方表里 _ways 展开的留着每格的选项，就摆成一种写法、
    一格几个选项，玩家一眼知道"任一生肉"都行；没有（下游模组追加的、只有展开后的写法）每种写法一种、一格一件。"""
    cells = getattr(recipe.get("Recipe"), "slots", ())
    if cells:
        return [[[(name, 0) for name in options] for options in cells]]
    return [[[(entry[0], entry[1])] for entry in variant] for variant in (recipe.get("Recipe") or ()) if variant]


def potPages():
    pages = []
    for index, recipe in enumerate(CookingPotRecipeList):
        result = recipe.get("CookResult") if isinstance(recipe, dict) else None
        ways = _potWays(recipe) if _pair(result) else []
        if not ways:
            continue
        vessel = recipe.get("Vessel")
        foot = ([stack(vessel[0], vessel[1])] if _pair(vessel) else []) + [stack(CLOCK)]
        pages.append({"key": index, "item": stack(result[0], result[1], recipe.get("CookCount") or 1), "ways": ways,
                      "foot": foot, "note": _seconds(PotCooking.bookSeconds(CookingPot.cookSecondsOf(result[0]))), "kind": None})
    return pages


def potRecipe(key):
    """键 -> 配方字典；不认识返回 None。"""
    if isinstance(key, int) and not isinstance(key, bool) and 0 <= key < len(CookingPotRecipeList):
        return CookingPotRecipeList[key]
    return None


def potCurrent(inputs, meal=None):
    """锅里的料正在做的那道菜的键；料做不成菜时是锅里已经煮好的那锅（meal）的菜（PotBook.current）；都没有返回 None。"""
    cooking, _pushed = CookingPot.matchRecipe([item for item in inputs or () if item])
    made = cooking or meal
    recipe = CookingPot.findRecipeByResult(made["newItemName"]) if made else None
    for index, candidate in enumerate(CookingPotRecipeList):
        if candidate is recipe:
            return index
    return None


# ---------------------------------------------------------------- 砧板

BOARD_TABS = [
    {"kind": None, "item": stack("minecraft:compass")},
    {"kind": "dishes", "item": stack("arris:hamburger")},
    {"kind": "knife", "item": stack("arris:iron_knife")},
    {"kind": "tools", "item": stack("minecraft:iron_axe")},
]


def dishWay(dish):
    """一道摆盘菜的写法：底座在前，其余照配方顺序，一格一件。"""
    ingredients = list(dish["ingredients"])
    base = ingredients.pop(dish["base"]) if 0 <= dish["base"] < len(ingredients) else None
    return [[kind] for kind in ([base] if base is not None else []) + ingredients]


def boardPages():
    pages, byResult = [], {}
    for dish in DishStation.dishes():
        name, aux = dish["result"]
        page = byResult.get(name)
        if page is None:
            page = {"key": DISH_PREFIX + name, "item": stack(name, aux, dish["count"]), "ways": [], "foot": [], "note": "",
                    "kind": "dishes"}
            byResult[name] = page
            pages.append(page)
        page["ways"].append(dishWay(dish))
    for (name, aux), recipe in sorted(CuttingBoardDict.items()):
        outputs = [stack(entry["itemName"], entry.get("auxValue", 0), entry.get("count", 1)) for entry in recipe["itemList"]]
        tools = [(tool, 0) for tool in recipe.get("tool") or ()]
        if not outputs or not tools:
            continue
        pages.append({"key": "%s%s:%d" % (CUT_PREFIX, name, aux), "item": outputs[0], "ways": [[[(name, aux)], tools]],
                      "foot": outputs[1:], "note": "", "kind": "knife" if CuttingStation.isKnifeRecipe(recipe) else "tools"})
    return pages


def dishOf(key):
    """键 "d:成品名" -> 这道菜的各种写法（DishStation.dishes 的条目）；不是摆盘的键返回 []。"""
    if not isinstance(key, _TEXT) or not key.startswith(DISH_PREFIX):
        return []
    return [dish for dish in DishStation.dishes() if dish["result"][0] == key[len(DISH_PREFIX):]]


def boardCurrent(layers, item):
    """砧板现在在做的：层朝着的那道菜，否则板上能切的那件；都没有返回 None。"""
    kinds = [(layer["newItemName"], layer.get("newAuxValue") or 0) for layer in layers or () if layer and layer.get("newItemName")]
    target = DishStation.targetOf(kinds) if kinds else None
    if target is not None:
        return DISH_PREFIX + target["result"][0]
    if item and item.get("newItemName") and (item["newItemName"], item.get("newAuxValue") or 0) in CuttingBoardDict:
        return "%s%s:%d" % (CUT_PREFIX, item["newItemName"], item.get("newAuxValue") or 0)
    return None


# ---------------------------------------------------------------- 煎锅、炉灶

def _cookPages(sideSeconds):
    pages = []
    for raw in sorted(CanCookedFoodDict):
        sides = 1 if PanStation.isOneSided(raw) else 2
        pages.append({"key": raw, "item": stack(CanCookedFoodDict[raw]), "ways": [[[(raw, 0)]]], "foot": [stack(CLOCK)],
                      "note": _seconds(sides * sideSeconds), "kind": None})
    return pages


def panPages():
    """煎锅的书：每道都是两面的时间（SkilletBook：2 * sideTicks；蛋不翻面、从下往上煎透，用的也是两面的时间）。"""
    return [dict(page, note=_seconds(2 * PanStation.sideSeconds(1))) for page in _cookPages(PanStation.sideSeconds(1))]


def grillPages():
    return [page for page in _cookPages(GrillStation.sideSeconds()) if GrillStation.canGrill(page["key"])]


def cookCurrent(items):
    """煎锅 / 炉灶上第一件还生着的东西的键；没有返回 None。"""
    for item in items or ():
        name = item.get("newItemName") if item else None
        if name in CanCookedFoodDict:
            return name
    return None
