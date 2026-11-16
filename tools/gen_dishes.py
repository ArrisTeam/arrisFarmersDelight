# -*- coding: utf-8 -*-
"""gen_dishes - 从行为包的合成配方生成"砧板摆盘"的菜谱表 Shared/Data/Dishes.py（开发工具，py -3 运行）

哪些菜搬到砧板上照 Hands-On Delight 在 JE 上的规则（AssemblyRecipes 的说明）：FD 的合成配方里，原料不止一种、
成品是食物 / 用食物做的饮料 / 盛宴 / 派 / 蛋糕的，都改在砧板上摆；一种原料的（开箱、叶子压回卷心菜、切片拼回整个派）、
不是食物的（马饲料、派皮以外的材料）、牛奶倒进瓶子这类留在工作台。成品是不是食物按 JE 的 FD（基岩版这边的物品 JSON 和 JE
不全一致，比如这边牛奶瓶也能吃），所以成品名单写在下面的 DISH_RESULTS 里，配料从基岩版自己的配方读。
做一份剩下的东西照 JE 的合成剩余物算（tools/recipejson.py，表是 Shared/Data/Remainders.py）：extras 是换成了别的东西的
（奶桶剩空桶、奶瓶剩玻璃瓶、米饭剩碗），keeps 是原样留下的原料（面团配方的水桶）——HoD 的 Assembling.make 里它每轮都放回去，
不限做几份，做完整个还给厨师。
用法：py -3 tools/gen_dishes.py            生成 / 更新 Dishes.py
      py -3 tools/gen_dishes.py --check    只比较，不一致时退出码 1（tests/test_dish_station_rules.py 也会比）
"""
import os
import sys

import recipejson

OUT = os.path.join(recipejson.SCRIPTS, "Shared", "Data", "Dishes.py")

# JE 的 FD 里改在砧板上做的菜（基岩版的物品名）
DISH_RESULTS = (
    "arris:apple_pie_item", "arris:bacon_and_eggs", "arris:bacon_sandwich", "arris:barbecue_stick",
    "arris:chicken_sandwich", "arris:chocolate_pie_item", "arris:cod_roll", "arris:egg_sandwich", "arris:fruit_salad",
    "arris:gleaming_salad_block_stage0",
    "arris:grilled_salmon", "arris:hamburger", "arris:honey_cookie", "arris:honey_glazed_ham_block_stage0",
    "arris:kelp_roll", "arris:melon_juice", "arris:melon_popsicle", "arris:mixed_salad", "arris:mutton_wrap",
    "arris:nether_salad", "arris:pie_crust", "minecraft:pumpkin_pie", "arris:rice_roll_medley_block_stage0",
    "arris:roast_chicken_block_stage0",
    "arris:roasted_mutton_chops", "arris:salmon_roll", "arris:shepherds_pie_block_stage0", "arris:steak_and_potatoes",
    "arris:stuffed_potato", "arris:sweet_berry_cheesecake_item", "arris:sweet_berry_cookie", "arris:wheat_dough",
    "minecraft:cake",                  # JE 的 cake_from_milk_bottle（奶瓶 3、糖 2、蛋、小麦 3）：蛋糕是 CakeBlock 的方块物品，算菜
)


def dishes():
    found = []
    for recipe in recipejson.recipes():
        ingredients = recipe["ingredients"]
        if recipe["result"] not in DISH_RESULTS or len(set(ingredients)) < 2 or not 2 <= len(ingredients) <= 9:
            continue
        names = [name for name, _aux in ingredients]
        returns = recipejson.returnsOf(recipe["result"], names)
        keeps = sorted(name for name, left in returns.items() if left == name)
        extras = [(left, 0, count) for left, count in recipejson.remaindersOf(recipe["result"], names) if left not in keeps]
        found.append((recipe["result"], recipe["count"], ingredients, extras, keeps, recipe["source"]))
    return found


def render():
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""Dishes - 砧板上摆的菜：成品、一份出几个、配料（双端，纯数据，由 tools/gen_dishes.py 从合成配方生成，别手改）',
        "",
        "每道菜一行：result (物品名, aux)、count 一份出几个、ingredients 配料（一格一个，(物品名, aux)）、",
        "extras 做一份剩下的容器 (物品名, aux, 个数)（JE 的合成剩余物：奶桶剩空桶、奶瓶剩玻璃瓶、米饭剩碗），",
        "keeps 原样留下的配料名（面团配方的水桶：不限做几份，做完整个还给厨师），source 是生成它的配方文件。",
        "底座、收尾由 Shared/Rules/DishStation.py 按 Hands-On Delight 的规则（HandsOn/Assembly.baseOf）现算。",
        '"""',
        "DishList = [",
    ]
    for name, count, ingredients, extras, keeps, source in dishes():
        lines.append("    {\"result\": (%r, 0), \"count\": %d, \"ingredients\": [%s], \"extras\": [%s], \"keeps\": [%s], "
                     "\"source\": %r}," % (
                         str(name), count, ", ".join("(%r, %d)" % (str(n), a) for n, a in ingredients),
                         ", ".join("(%r, %d, %d)" % (str(n), a, c) for n, a, c in extras),
                         ", ".join("%r" % str(n) for n in keeps), str(source)))
    lines.append("]")
    return "\n".join(lines) + "\n"


def main(argv):
    return recipejson.write(OUT, render(), "--check" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
