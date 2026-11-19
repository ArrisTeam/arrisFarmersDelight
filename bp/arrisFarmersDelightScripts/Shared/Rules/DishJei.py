# -*- coding: utf-8 -*-
"""DishJei - 砧板摆盘的菜在 JEI 里怎么列、哪些工作台配方该藏（双端，纯规则）

对应 Hands-On Delight：compat/jei/HandsOnJeiPlugin.java（登记"砧板摆盘"分类、把这些菜的工作台配方藏起来）、compat/AssemblyLayout.java
（一条配方画成什么样：打底的那一样躺在板上，别的层三个一排放在格子里，箭头，成品）。JE 的一条摆盘配方每个位置是一组能互换的物品（Ingredient）；
我们的 Shared/Data/Dishes.py 一种写法一行（烤串的 13 种熟肉是 13 行，各来自一份配方文件），所以这里把"同一个成品、出一样多、一样多配料、只差一个位置"的
几行并回一条，那个位置轮着显示（烤串并成 1 条；蛋糕的三格奶各换各的，只并得了一格，是 3 条）。底座是哪一个照 DishStation 的规矩（HandsOn/Assembly.baseOf）。
藏工作台配方：拦的是"配方"不是"成品"（Compat/Diegesis/DishCrafts 同一个判断）——引擎给的一条工作台配方，每格的可选物品里能挑出一组正好是某道摆盘菜的配料，
才是被拦的那条；同一成品的别的配方（切片拼回整个派）照常显示。
"""
from ..Data.Dishes import DishList
from .HandsOn import Assembly

COLUMNS = 3                 # AssemblyLayout.COLUMNS：别的层三个一排
MOST_LAYERS = 8             # 除了底座最多还有几层（一道菜至多 9 样）


def _key(item):
    return (item[0], int(item[1]))


def _merged(rows):
    """一组写法（同一个成品、一样多的配料）并成尽量少的几条：挑一个位置，别的位置都一样的几行并成一条、这个位置轮着显示。
    只并一个位置，所以每条里轮到的每一种搭配都是真有的写法（几个位置各换各的话，会凑出表里没有的搭配）。返回 [每个位置的可选物品]。"""
    best = None
    for position in range(len(rows[0])):
        clusters, order = {}, []
        for row in rows:
            rest = tuple(row[:position] + row[position + 1:])
            if rest not in clusters:
                clusters[rest] = []
                order.append(rest)
            if row[position] not in clusters[rest]:
                clusters[rest].append(row[position])
        if best is None or len(order) < len(best[1]):
            best = (position, order, clusters)
    position, order, clusters = best
    found = []
    for rest in order:
        slots = [[item] for item in rest]
        slots.insert(position, clusters[rest])
        found.append(slots)
    return found


def recipes(dishList=None):
    """全部摆盘配方：[{"result": (物品名, aux), "count": 一份出几个, "base": 底座那个位置的可选物品 [(物品名, aux), ...],
    "layers": [别的每个位置的可选物品, ...]（照配方里的次序）}]。同一个成品、出一样多、一样多配料的几行，只差一个位置的并成一条（_merged）。"""
    groups, order = {}, []
    for entry in (DishList if dishList is None else dishList):
        ingredients = [_key(item) for item in entry.get("ingredients") or ()]
        if not ingredients:
            continue
        key = (_key(entry["result"]), int(entry.get("count") or 1), len(ingredients))
        if key not in groups:
            groups[key] = []
            order.append(key)
        if ingredients not in groups[key]:
            groups[key].append(ingredients)
    found = []
    for key in order:
        for slots in _merged(groups[key]):
            base = Assembly.baseOf([slot[0][0] for slot in slots])[0]
            found.append({"result": key[0], "count": key[1], "base": slots[base],
                          "layers": [slot for index, slot in enumerate(slots) if index != base]})
    return found


def layerPlace(index, count, height, size):
    """第 index 层（共 count 层）的格子左上角离配方区顶上多远、在第几列：三个一排，几排在高 height 的区域里上下居中（AssemblyLayout.layerX / layerY）。
    返回 (列, y)。"""
    rows = (count + COLUMNS - 1) // COLUMNS
    return index % COLUMNS, (height - rows * size) // 2 + index // COLUMNS * size


def itemsOf(recipe):
    """这条配方里出现的全部物品（查"这件东西能用来做什么"时按它登记）：底座和各层的每个可选物品，不重复。"""
    seen = []
    for slot in [recipe["base"]] + list(recipe["layers"]):
        for item in slot:
            if item not in seen:
                seen.append(item)
    return seen


# ---------------------------------------------------------------- 工作台配方

def _choices(entry):
    """引擎的配料一格 {"item": 名字或名字列表, ...} -> 可选的物品名。"""
    item = entry.get("item") if isinstance(entry, dict) else None
    if isinstance(item, (list, tuple)):
        return [name for name in item if name]
    return [item] if item else []


def craftSlots(recipe):
    """引擎给的一条工作台配方 -> (成品名, [每格可选的物品名, ...])；认不出形状返回 (None, [])。
    有序：{"pattern": [行, ...], "key": {字符: 配料}, "result": [...]}，空格不算；无序：{"ingredients": [配料（带 count 的展开成几格）], "result": [...]}。"""
    if not isinstance(recipe, dict):
        return None, []
    results = recipe.get("result") or ()
    first = results[0] if isinstance(results, (list, tuple)) and results else results
    name = first.get("item") if isinstance(first, dict) else None
    slots = []
    if recipe.get("pattern"):
        keys = recipe.get("key") or {}
        for row in recipe["pattern"]:
            for char in row:
                if char != " " and char in keys:
                    slots.append(_choices(keys[char]))
    elif recipe.get("ingredients"):
        for entry in recipe["ingredients"]:
            count = int(entry.get("count") or 1) if isinstance(entry, dict) else 1
            slots.extend([_choices(entry)] * count)
    else:
        return None, []
    return name, slots


def _fits(names, slots):
    """names（一道菜的配料名）能不能一格一个地摆进 slots（每格的可选物品名）：回溯着配，至多 9 格。"""
    if len(names) != len(slots):
        return False
    if not names:
        return True
    first, rest = names[0], names[1:]
    for index, slot in enumerate(slots):
        if first in slot and _fits(rest, slots[:index] + slots[index + 1:]):
            return True
    return False


def isDishCraft(recipe, dishList=None):
    """引擎给的这条工作台配方是不是被拦掉、改在砧板上摆的那条：成品是某道摆盘菜，而且每格的可选物品里能挑出一组正好是它的配料。"""
    name, slots = craftSlots(recipe)
    if not name or not slots:
        return False
    for entry in (DishList if dishList is None else dishList):
        if entry["result"][0] == name and _fits([item[0] for item in entry.get("ingredients") or ()], slots):
            return True
    return False
