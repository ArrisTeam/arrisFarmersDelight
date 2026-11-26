# -*- coding: utf-8 -*-
"""recipejson - 开发工具共用：读行为包的合成配方 JSON，按 JE 的规则算一份配方的剩余物（py -3，给 gen_dishes / gen_crafts 用）

剩余物表就是游戏里用的 bp/.../Shared/Data/Remainders.py（纯数据，按路径加载）；JE 的面团配方（DoughRecipe）把水桶原样留下。
原料写标签（{"tag": X}）的格子读成 "#X"；membersOf 按词表 Shared/Data/Tags.py 的静态成员展开（原版标签 minecraft:egg 也在词表里，
别的原版标签用 VANILLA 里抄的成员），expand 把一份配方按格展开成全部具体的写法（砧板摆盘、测试用）。
"""
import glob
import importlib.util
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, "bp", "recipes")
SCRIPTS = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts")
DOUGH, WATER = "arris:wheat_dough", "minecraft:water_bucket"


def _remainders():
    spec = importlib.util.spec_from_file_location("Remainders", os.path.join(SCRIPTS, "Shared", "Data", "Remainders.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Remainders = _remainders()


def _tags():
    spec = importlib.util.spec_from_file_location("Tags", os.path.join(SCRIPTS, "Shared", "Data", "Tags.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Tags = _tags()
# 配方里用到、词表里没有的原版标签：成员照基岩版 3.10 原版的（minecraft:planks 是 11 种木板）
VANILLA = {
    "minecraft:planks": tuple("minecraft:%s_planks" % wood for wood in (
        "oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo", "crimson", "warped")),
}


def membersOf(option):
    """一格的选项 -> 能放的具体物品名：物品名就是它自己；"#标签" 是词表（或 VANILLA）里的静态成员，认不出的标签抛 KeyError。"""
    if not option.startswith("#"):
        return (option,)
    tag = option[1:]
    for table in (Tags.ITEM_TAGS, Tags.VANILLA_TAGS, VANILLA):
        if tag in table:
            return tuple(table[tag])
    raise KeyError("配方里的标签 %s 词表里没有（Shared/Data/Tags.py）" % tag)


def _item(entry):
    if isinstance(entry, dict) and entry.get("tag"):
        return ("#" + entry["tag"], 0)
    if isinstance(entry, dict):
        return (entry.get("item"), int(entry.get("data", 0) or 0))
    return (entry, 0)


def _gridOf(pattern, keys):
    """有序配方摆进 3×3（靠左上角，行优先）：一格一个物品名 / "#标签"，空格是 None。"""
    grid = []
    for row in range(3):
        line = pattern[row] if row < len(pattern) else ""
        for column in range(3):
            char = line[column] if column < len(line) else " "
            grid.append(_item(keys[char])[0] if char != " " and char in keys else None)
    return grid


def read(path):
    """一个配方文件 -> dict(kind, identifier, result, count, ingredients [(物品名, aux)，一格一个], extras [(物品名, aux, 个数)]
    有序配方 result 数组第二项起；无序的没有), grid（摆进 3×3 的样子：有序照 pattern 靠左上角，无序从第一格起依次摆；None 空格）, source)；
    不是合成配方返回 None。写标签的格子是 "#标签"。"""
    data = json.load(io.open(path, encoding="utf-8-sig"))
    for kind in ("minecraft:recipe_shapeless", "minecraft:recipe_shaped"):
        recipe = data.get(kind)
        if not recipe:
            continue
        results = recipe.get("result")
        results = results if isinstance(results, list) else [results]
        first = results[0]
        shaped = kind.endswith("shaped")
        if shaped:
            keys = recipe.get("key", {})
            ingredients = [_item(keys[char]) for row in recipe.get("pattern", []) for char in row if char in keys]
            grid = _gridOf(recipe.get("pattern", []), keys)
        else:
            ingredients = []
            for entry in recipe.get("ingredients", []):
                amount = int(entry.get("count", 1) or 1) if isinstance(entry, dict) else 1
                ingredients.extend([_item(entry)] * amount)
            grid = ([name for name, _aux in ingredients] + [None] * 9)[:9]
        extras = [(extra.get("item"), int(extra.get("data", 0) or 0), int(extra.get("count", 1) or 1))
                  for extra in results[1:] if shaped and isinstance(extra, dict) and extra.get("item")]
        return {"kind": "shaped" if shaped else "shapeless", "identifier": recipe["description"]["identifier"],
                "result": first.get("item") if isinstance(first, dict) else first,
                "count": int(first.get("count", 1) or 1) if isinstance(first, dict) else 1,
                "ingredients": ingredients, "extras": extras, "grid": grid, "source": os.path.basename(path)}
    return None


def recipes():
    """行为包里全部合成配方（按文件名排序）。"""
    found = []
    for path in sorted(glob.glob(os.path.join(RECIPES, "**", "*.json"), recursive=True)):
        recipe = read(path)
        if recipe is not None:
            found.append(recipe)
    return found


def returnsOf(result, names):
    """JE 里这份配方每格原料剩下什么：{原料名: 剩余物名}（面团配方的水桶剩它自己）。"""
    returns = {}
    for name in names:
        if result == DOUGH and name == WATER:
            returns[name] = WATER
        elif Remainders.craftRemainderOf(name):
            returns[name] = Remainders.craftRemainderOf(name)
    return returns


def keepsOf(result, options):
    """这份配方做完原样留下的格子选项（JE 的面团配方 DoughRecipe：水桶）：排好序、去重。"""
    if result != DOUGH:
        return ()
    return tuple(sorted(set(option for option in options if WATER in membersOf(option))))


def mayLeave(result, options):
    """这份配方做完可能还东西：某一格的某个成员带合成剩余物，或者有原样留下的格子。"""
    return bool(keepsOf(result, options)) or any(Remainders.craftRemainderOf(member) for option in options for member in membersOf(option))


def expand(recipe):
    """一份配方按格展开成全部具体的写法 [[(物品名, aux), ...], ...]：标签格换成词表里的每个成员（格子的先后不变，前面的格变得慢）；
    多重集合相同的写法只留第一种。"""
    ways = [[]]
    for name, aux in recipe["ingredients"]:
        ways = [way + [(member, aux)] for way in ways for member in membersOf(name)]
    unique, seen = [], set()
    for way in ways:
        key = tuple(sorted(way))
        if key not in seen:
            seen.add(key)
            unique.append(way)
    return unique


def remaindersOf(result, names):
    """JE 里做一份剩下的东西：[(剩余物名, 个数)]，按名字排序。"""
    returns = returnsOf(result, names)
    counts = {}
    for name in names:
        if name in returns:
            counts[returns[name]] = counts.get(returns[name], 0) + 1
    return sorted(counts.items())


def write(path, text, check):
    """生成文件：check 时只比较（不一致返回 1），否则内容变了才写。"""
    current = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if check:
        return 0 if current == text else 1
    if current != text:
        io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return 0
