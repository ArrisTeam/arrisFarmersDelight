# -*- coding: utf-8 -*-
"""StationBooks - 四个站点旁的食谱书页：厨锅、砧板（摆盘 + 切）、煎锅、炉灶（双端，纯规则）

对应 Hands-On Delight 的 PotBook / BoardBook / SkilletBook / StoveBook。页的写法见沉浸式交互前置的 Shared/Book.py：
{"key", "item"（成品）, "ways"（写法：[[这一格能放的 (物品名, aux), ...], ...]）, "foot"（脚注物品）, "note", "kind"（标签）}。
- 厨锅：一道菜一页，键是配方表下标；脚注是盛菜的容器和时钟，注明一份在站点里几秒（JE 的 CookTime x 配置倍率 / 1.5，HoD 的 PotBook）；能从背包放料；
- 砧板：摆盘的菜按成品一页（键 "d:成品名"，写法底座在前），能切的东西按食材一页（键 "c:名字:aux"，第二格是能用的工具，
  脚注是全部产物（产物不止一种才有，含主产物，BoardBook.java:55）；标签：全部 / 摆盘 / 刀切 / 别的工具；摆盘的菜能从背包放料，切的只看；
- 煎锅、炉灶：能煎 / 烤的一件一页（成品相同的几种蛋并成一页，cookGroups），注明两面一共几秒（SkilletBook 31 行 / StoveBook 36 行：2 * sideTicks，不看 one_sided——只煎一面的
  从下往上煎透，用的也是两面的时间）；只看。
三种时间都带着配置里的倍率（cooking_pot_time / skillet_time / stove_time，站点关了算 1.0），书上写的就是服务端此刻的时间（两端同一份配置表）。
"""
from ..Data import Tags
from ..Data.Cooking import CanCookedFoodDict
from ..Data.CookingPotRecipes import CookingPotRecipeList
from ..Data.Cutting import CuttingBoardDict, CuttingTagDict
from . import CookingPot, CuttingStation, DishStation, GrillStation, ItemTags, PanStation
from .HandsOn import PotCooking
from .HandsOn.Mth import roundInt

CLOCK = "minecraft:clock"
DISH_PREFIX = "d:"
CUT_PREFIX = "c:"

try:
    _TEXT = (str, unicode)  # noqa: F821 - py2：客户端发来的键可能是 unicode
except NameError:
    _TEXT = (str,)


def stack(name, aux=0, count=1):
    return {"newItemName": name, "newAuxValue": int(aux), "count": int(count)}


SECONDS_KEY = "handson_delight.book.seconds"       # 页脚"多少秒"在语言文件里的键（HoD 的）
_words = {"seconds": "%d 秒"}                       # 现在用的写法：客户端建书页前按玩家的语言换（wordSeconds），服务端用不着书页的字


def wordSeconds(wording):
    """页脚的"多少秒"换一种写法（带一个数字的占位）；填不上的（语言文件里写坏了）不换，返回换了没有。"""
    try:
        wording % 1
    except (TypeError, ValueError):
        return False
    _words["seconds"] = wording
    return True


def shownSeconds(value):
    """一段时长在页上写成几秒：Java 的 Math.round（半数进位），不是 Python 的 round（py3 里 2.5 是 2），得到整数。
    站点食谱书的页脚和 JEI 里煎锅 / 炉灶配方页上的秒数都由这里换成数，只有这一种换法：JEI 原来把 6.0 直接填进语言文件的句子，
    中文的 %d 写成 6，英文的 %s 却写成 6.0。"""
    return roundInt(value)


def _seconds(value):
    """页脚的秒数：shownSeconds 换出的整数，按现在用的那一句（wordSeconds）写。"""
    return _words["seconds"] % shownSeconds(value)


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
    """配料井怎么摆（RecipeBook.drawDish：一格是一组备选，每秒换一种）：有 Slots 的配方（农夫乐事自己的、新接口登记的）摆成一种写法、
    一格几个选项（标签换成它现在的成员），玩家一眼知道"任一生肉"都行；格子不收的旧写法（契约的 AddCookingPotRecipe 给它加的）各自再成一种。
    没有 Slots 的（旧接口追加的，只有写法）每种写法一种、一格一件。某格一个成员都没有的不画那一种。"""
    cells = CookingPot.optionsOf(recipe)
    ways = [[list(options) for options in cells]] if cells and all(cells) else []
    return ways + [[[(entry[0], entry[1])] for entry in variant] for variant in CookingPot.extraWays(recipe) if variant]


def potPages():
    pages = []
    for index, recipe in enumerate(CookingPotRecipeList):
        result = recipe.get("CookResult") if CookingPot.isLive(recipe) else None
        ways = _potWays(recipe) if _pair(result) else []
        if not ways:
            continue
        vessel = recipe.get("Vessel")
        foot = ([stack(vessel[0], vessel[1])] if _pair(vessel) else []) + [stack(CLOCK)]
        pages.append({"key": index, "item": stack(result[0], result[1], recipe.get("CookCount") or 1), "ways": ways,
                      "foot": foot, "note": _seconds(PotCooking.bookSeconds(CookingPot.cookSecondsOf(result[0]))), "kind": None})
    return pages


def potRecipe(key):
    """键 -> 配方字典；不认识、或那一行已经被移除（墓碑）返回 None。"""
    if isinstance(key, int) and not isinstance(key, bool) and 0 <= key < len(CookingPotRecipeList):
        recipe = CookingPotRecipeList[key]
        return recipe if CookingPot.isLive(recipe) else None
    return None


def potCurrent(inputs, meal=None):
    """锅里的料正在做的那道菜的键：锅读成的那条配方（同一成品有几条配方时不会指错）；料做不成菜时是锅里已经煮好的那锅（meal）
    的菜（PotBook.current）；都没有返回 None。"""
    found = CookingPot.matchIndex([item for item in inputs or () if item])
    if found is not None:
        return found
    recipe = CookingPot.findRecipeByResult(meal["newItemName"]) if meal else None
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
    cuts = [(_cutKey(key), [key], recipe) for key, recipe in sorted(CuttingBoardDict.items())]
    cuts += [(_cutKey(tag), [(name, 0) for name in ItemTags.itemsOf(tag)], recipe) for tag, recipe in sorted(CuttingTagDict.items())]
    for key, inputs, recipe in cuts:
        outputs = [stack(entry["itemName"], entry.get("auxValue", 0), entry.get("count", 1)) for entry in recipe["itemList"]]
        tools = [(tool, 0) for tool in recipe.get("tool") or ()]
        if not outputs or not tools or not inputs:
            continue
        pages.append({"key": key, "item": outputs[0], "ways": [[inputs, tools]], "foot": outputs if len(outputs) > 1 else [], "note": "",
                      "kind": "knife" if CuttingStation.isKnifeRecipe(recipe) else "tools"})
    return pages


def _cutKey(found):
    """切的那一页的键：精确的配方 "c:物品名:aux"，按标签的 "c:#标签名"（一格是标签的全部成员，轮换着画）。"""
    return "%s#%s" % (CUT_PREFIX, found) if not isinstance(found, tuple) else "%s%s:%d" % (CUT_PREFIX, found[0], found[1])


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
    found = CuttingStation.recipeKeyOf((item["newItemName"], item.get("newAuxValue") or 0)) if item and item.get("newItemName") else None
    return _cutKey(found) if found is not None else None


# ---------------------------------------------------------------- 煎锅、炉灶

def cookGroups():
    """营火配方（CanCookedFoodDict）怎么分页（站点的书、JEI 的煎锅 / 炉灶页共用）：成品相同、原料都在原版 minecraft:egg 标签里的并成一页
    （基岩版的三种蛋都煎成煎蛋：一页，原料那一格轮换），别的一件一页。[(原料名列表, 成品名)]：组里按标签成员的先后，组按第一件原料的名字排。"""
    eggs = list(ItemTags.itemsOf(Tags.EGG))
    groups = {}
    for raw in sorted(CanCookedFoodDict):
        result = CanCookedFoodDict[raw]
        groups.setdefault((result,) if raw in eggs else (result, raw), []).append(raw)
    found = []
    for key, raws in groups.items():
        raws.sort(key=lambda name: (eggs.index(name) if name in eggs else len(eggs), name))
        found.append((raws, key[0]))
    return sorted(found)


def _cookPages(sideSeconds):
    """一组原料一页（cookGroups），键是组里的第一件；每道都写两面一共几秒（2 * sideTicks）：不看 one_sided（只煎一面的从下往上煎透，用的也是两面的时间）。"""
    return [{"key": raws[0], "item": stack(result), "ways": [[[(raw, 0) for raw in raws]]], "foot": [stack(CLOCK)],
             "note": _seconds(2 * sideSeconds), "kind": None} for raws, result in cookGroups()]


def panPages():
    """煎锅的书（SkilletBook）：营火配方的每一件，蛋也在。"""
    return _cookPages(PanStation.sideSeconds(1))


def grillPages():
    """炉灶的书（StoveBook）：只列烤架收的（不收蛋，NOT_ON_GRILL）。"""
    return [page for page in _cookPages(GrillStation.sideSeconds()) if GrillStation.canGrill(page["key"])]


def cookCurrent(items):
    """煎锅 / 炉灶上第一件还生着的东西在哪一页（页的键：并成一页的几种蛋都翻到那一页）；没有返回 None。"""
    for item in items or ():
        name = item.get("newItemName") if item else None
        if name in CanCookedFoodDict:
            return next((raws[0] for raws, _result in cookGroups() if name in raws), name)
    return None
