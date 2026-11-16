# -*- coding: utf-8 -*-
"""gen_dishes - 从行为包的合成配方生成"砧板摆盘"的菜谱表 Shared/Data/Dishes.py（开发工具，py -3 运行）

哪些菜搬到砧板上照 Hands-On Delight 在 JE 上的规则（AssemblyRecipes 的说明）：FD 的合成配方里，原料不止一种、
成品是食物 / 用食物做的饮料 / 盛宴 / 派 / 蛋糕的，都改在砧板上摆；一种原料的（开箱、叶子压回卷心菜）、不是食物的
（马饲料、派皮以外的材料）、牛奶倒进瓶子这类留在工作台。成品是不是食物按 JE 的 FD（基岩版这边的物品 JSON 和 JE 不全一致，
比如这边牛奶瓶也能吃），所以成品名单写在下面的 DISH_RESULTS 里，配料从基岩版自己的配方读。
有序配方的结果数组从第二项起是退还的容器（基岩版无序配方只出第一项，所以无序的走 Food.shapedRecipeContainerDict），
生成到每道菜的 extras 里，砧板做成时按份数一起退还。成品若另有单一原料的工作台配方（切片拼回整个派），列进 KeepAtTable：
前置包在场时工作台照样能拿（合成事件里看不到原料，分不出是哪条配方）。
用法：py -3 tools/gen_dishes.py            生成 / 更新 Dishes.py
      py -3 tools/gen_dishes.py --check    只比较，不一致时退出码 1（tests/test_dishes_table.py 也会比）
"""
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, "bp", "recipes")
OUT = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts", "Shared", "Data", "Dishes.py")

# JE 的 FD 里改在砧板上做的菜（基岩版的物品名）
DISH_RESULTS = (
    "arris:apple_pie_item", "arris:bacon_and_eggs", "arris:bacon_sandwich", "arris:barbecue_stick",
    "arris:chicken_sandwich", "arris:chocolate_pie_item", "arris:cod_roll", "arris:egg_sandwich", "arris:fruit_salad",
    "arris:grilled_salmon", "arris:hamburger", "arris:honey_cookie", "arris:honey_glazed_ham_block_stage0",
    "arris:kelp_roll", "arris:melon_juice", "arris:melon_popsicle", "arris:mixed_salad", "arris:mutton_wrap",
    "arris:nether_salad", "arris:pie_crust", "arris:rice_roll_medley_block_stage0", "arris:roast_chicken_block_stage0",
    "arris:roasted_mutton_chops", "arris:salmon_roll", "arris:shepherds_pie_block_stage0", "arris:steak_and_potatoes",
    "arris:stuffed_potato", "arris:sweet_berry_cheesecake_item", "arris:sweet_berry_cookie", "arris:wheat_dough",
)


def _item(entry):
    if isinstance(entry, dict):
        return (entry.get("item") or entry.get("tag"), int(entry.get("data", 0) or 0))
    return (entry, 0)


def _read(path):
    data = json.load(io.open(path, encoding="utf-8-sig"))
    for kind in ("minecraft:recipe_shapeless", "minecraft:recipe_shaped"):
        recipe = data.get(kind)
        if not recipe:
            continue
        results = recipe.get("result")
        results = results if isinstance(results, list) else [results]
        result = results[0]
        name = result.get("item") if isinstance(result, dict) else result
        count = int(result.get("count", 1) or 1) if isinstance(result, dict) else 1
        extras = [] if kind.endswith("shapeless") else [
            (extra.get("item"), int(extra.get("data", 0) or 0), int(extra.get("count", 1) or 1))
            for extra in results[1:] if isinstance(extra, dict) and extra.get("item")]
        if kind.endswith("shapeless"):
            ingredients = []
            for entry in recipe.get("ingredients", []):
                amount = int(entry.get("count", 1) or 1) if isinstance(entry, dict) else 1
                ingredients.extend([_item(entry)] * amount)
        else:
            keys = recipe.get("key", {})
            ingredients = [_item(keys[char]) for row in recipe.get("pattern", []) for char in row if char in keys]
        return name, count, ingredients, extras
    return None


def keepAtTable():
    """DISH_RESULTS 里另有单一原料工作台配方的成品（切片拼回整个派）。"""
    keep = set()
    for path in glob.glob(os.path.join(RECIPES, "**", "*.json"), recursive=True):
        read = _read(path)
        if read is not None and read[0] in DISH_RESULTS and len(set(read[2])) < 2:
            keep.add(read[0])
    return sorted(keep)


def dishes():
    found = []
    for path in sorted(glob.glob(os.path.join(RECIPES, "**", "*.json"), recursive=True)):
        read = _read(path)
        if read is None or read[0] not in DISH_RESULTS:
            continue
        name, count, ingredients, extras = read
        if len(set(ingredients)) < 2 or not 2 <= len(ingredients) <= 9:
            continue
        found.append((name, count, ingredients, extras, os.path.basename(path)))
    return found


def render():
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""Dishes - 砧板上摆的菜：成品、一份出几个、配料（双端，纯数据，由 tools/gen_dishes.py 从合成配方生成，别手改）',
        "",
        "每道菜一行：result (物品名, aux)、count 一份出几个、ingredients 配料（一格一个，(物品名, aux)）、",
        "extras 做一份退还的容器 (物品名, aux, 个数)（有序配方结果数组的第二项起），source 是生成它的配方文件。",
        "KeepAtTable：另有单一原料工作台配方的成品（切片拼回整个派），前置包在场时工作台也不拦。",
        "底座、收尾由 Shared/Rules/DishStation.py 按 Hands-On Delight 的规则（HandsOn/Assembly.baseOf）现算。",
        '"""',
        "DishList = [",
    ]
    for name, count, ingredients, extras, source in dishes():
        lines.append("    {\"result\": (%r, 0), \"count\": %d, \"ingredients\": [%s], \"extras\": [%s], \"source\": %r}," % (
            str(name), count, ", ".join("(%r, %d)" % (str(n), a) for n, a in ingredients),
            ", ".join("(%r, %d, %d)" % (str(n), a, c) for n, a, c in extras), str(source)))
    lines.append("]")
    lines.append("KeepAtTable = [%s]" % ", ".join("%r" % str(name) for name in keepAtTable()))
    return "\n".join(lines) + "\n"


def main(argv):
    text = render()
    current = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if "--check" in argv:
        return 0 if current == text else 1
    if current != text:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
