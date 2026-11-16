# -*- coding: utf-8 -*-
"""recipejson - 开发工具共用：读行为包的合成配方 JSON，按 JE 的规则算一份配方的剩余物（py -3，给 gen_dishes / gen_crafts 用）

剩余物表就是游戏里用的 bp/.../Shared/Data/Remainders.py（纯数据，按路径加载）；JE 的面团配方（DoughRecipe）把水桶原样留下。
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


def _item(entry):
    if isinstance(entry, dict):
        return (entry.get("item") or entry.get("tag"), int(entry.get("data", 0) or 0))
    return (entry, 0)


def read(path):
    """一个配方文件 -> dict(kind, identifier, result, count, ingredients [(物品名, aux)，一格一个], extras [(物品名, aux, 个数)]
    有序配方 result 数组第二项起；无序的没有), source)；不是合成配方返回 None。"""
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
        else:
            ingredients = []
            for entry in recipe.get("ingredients", []):
                amount = int(entry.get("count", 1) or 1) if isinstance(entry, dict) else 1
                ingredients.extend([_item(entry)] * amount)
        extras = [(extra.get("item"), int(extra.get("data", 0) or 0), int(extra.get("count", 1) or 1))
                  for extra in results[1:] if shaped and isinstance(extra, dict) and extra.get("item")]
        return {"kind": "shaped" if shaped else "shapeless", "identifier": recipe["description"]["identifier"],
                "result": first.get("item") if isinstance(first, dict) else first,
                "count": int(first.get("count", 1) or 1) if isinstance(first, dict) else 1,
                "ingredients": ingredients, "extras": extras, "source": os.path.basename(path)}
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
