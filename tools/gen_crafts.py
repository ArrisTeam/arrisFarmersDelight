# -*- coding: utf-8 -*-
"""gen_crafts - 从行为包的无序合成配方生成"合成后补还的剩余物"表 Shared/Data/CraftReturns.py（开发工具，py -3 运行）

JE 里原料自带合成剩余物（奶桶剩空桶、奶瓶剩玻璃瓶、米饭剩碗……，表在 Shared/Data/Remainders.py），做完一份每格还一件。
基岩版有序配方把剩余物写进 result 数组，引擎照给；无序配方的 result 数组只出第一项，由服务端（Server/CraftReturns.py）
读格子对上这张表补还。只收做完可能还东西的无序配方（某一格的物品、或标签格按词表展开的某个成员带剩余物；面团的水桶原样留下）；
表里只记每格的选项（物品名或 "#标签"），还什么由服务端按格子里实际放的物品查 Remainders（Shared/Rules/Crafting）。
顺带生成游戏内自检用的 Server/Debug/CraftCases.py（不进发布包）：写了标签的工作台配方各摆成什么样、做一份 result 数组还给什么，
Server/Debug/McdkCraftTest 按它把每份配方在工作台界面里真做一遍。
用法：py -3 tools/gen_crafts.py            生成 / 更新 CraftReturns.py 和 CraftCases.py
      py -3 tools/gen_crafts.py --check    只比较，不一致时退出码 1（tests/test_recipe_rules.py 也会比）
"""
import os
import sys

import recipejson

OUT = os.path.join(recipejson.SCRIPTS, "Shared", "Data", "CraftReturns.py")
CASES = os.path.join(recipejson.SCRIPTS, "Server", "Debug", "CraftCases.py")


def entries():
    """{成品: [(各格的选项, 一份几个, 原样留下的选项, 配方文件)]}：只收做完可能还东西的无序配方。"""
    table = {}
    for recipe in recipejson.recipes():
        if recipe["kind"] != "shapeless":
            continue
        slots = [name for name, _aux in recipe["ingredients"]]
        if recipejson.mayLeave(recipe["result"], slots):
            table.setdefault(recipe["result"], []).append((slots, recipe["count"], recipejson.keepsOf(recipe["result"], slots),
                                                           recipe["source"]))
    return table


def _strings(names):
    return repr(tuple(str(name) for name in names))


def render():
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""CraftReturns - 无序合成配方做完一份补还的剩余物（双端，纯数据，由 tools/gen_crafts.py 从合成配方生成，别手改）',
        "",
        "成品 -> 做它的各条无序配方（只收做完可能还东西的）：slots 每格的选项（物品名，或 \"#标签\"，照配方里的先后，一格一个）、",
        "count 一份出几个、keeps 原样留下的选项（JE 面团配方的水桶）、source 是生成它的配方文件。",
        "还什么不写在表里：服务端 Server/CraftReturns.py 取结果时读格子，Shared/Rules/Crafting 按标签认出是哪条，再按格子里实际放的物品",
        "查 Shared/Data/Remainders.py（JE 的合成剩余物，每份每格还一件）。有序配方的剩余物写在 result 数组里，引擎自己给。",
        '"""',
        "CraftReturns = {",
    ]
    table = entries()
    for result in sorted(table):
        lines.append("    %r: [" % str(result))
        for slots, count, keeps, source in table[result]:
            lines.append("        {\"slots\": %s, \"count\": %d, \"keeps\": %s, \"source\": %r}," % (
                _strings(slots), count, _strings(keeps), str(source)))
        lines.append("    ],")
    lines.append("}")
    return "\n".join(lines) + "\n"


def caseRecipes():
    """写了标签的工作台配方（有序、无序）：source、kind、result (成品, 个数)、grid（3×3 一格一个）、extras（result 数组第二项起）、keeps。"""
    found = []
    for recipe in recipejson.recipes():
        slots = [name for name, _aux in recipe["ingredients"]]
        if any(name.startswith("#") for name in slots):
            found.append({"source": recipe["source"], "kind": recipe["kind"], "result": (recipe["result"], recipe["count"]),
                          "grid": tuple(recipe["grid"]), "extras": tuple((name, count) for name, _aux, count in recipe["extras"]),
                          "keeps": recipejson.keepsOf(recipe["result"], slots)})
    return found


def renderCases():
    rows = caseRecipes()
    tags = sorted(set(cell[1:] for row in rows for cell in row["grid"] if cell and cell.startswith("#")))
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""CraftCases - 写了标签的工作台配方（服务端自检用，纯数据，由 tools/gen_crafts.py 从 bp/recipes 生成，别手改；不进发布包）',
        "",
        "RECIPES 每份配方一行：source 配方文件、kind（shaped / shapeless）、result (成品, 一份几个)、grid 摆进 3×3 的样子（行优先；有序照 pattern",
        "靠左上角，无序从第一格起依次摆；物品名或 \"#标签\"，None 空格）、extras 有序配方 result 数组第二项起还的 (物品名, 个数)、keeps 原样留下的格子。",
        "MEMBERS 是这些标签在词表（Shared/Data/Tags.py）里的静态成员：引擎答不出成员时 Server/Debug/McdkCraftTest 用它。",
        '"""',
        "RECIPES = [",
    ]
    for row in rows:
        lines.append("    {\"source\": %r, \"kind\": %r, \"result\": %r, \"grid\": %r," % (
            str(row["source"]), str(row["kind"]), (str(row["result"][0]), row["result"][1]), row["grid"]))
        lines.append("     \"extras\": %r, \"keeps\": %r}," % (row["extras"], row["keeps"]))
    lines.append("]")
    lines.append("MEMBERS = {")
    for tag in tags:
        lines.append("    %r: %r," % (str(tag), tuple(str(name) for name in recipejson.membersOf("#" + tag))))
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv):
    check = "--check" in argv
    stale = [recipejson.write(path, text, check) for path, text in ((OUT, render()), (CASES, renderCases()))]
    return 1 if any(stale) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
