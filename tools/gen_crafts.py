# -*- coding: utf-8 -*-
"""gen_crafts - 从行为包的无序合成配方生成"合成后补还的剩余物"表 Shared/Data/CraftReturns.py（开发工具，py -3 运行）

JE 里原料自带合成剩余物（奶桶剩空桶、奶瓶剩玻璃瓶、米饭剩碗……，表在 Shared/Data/Remainders.py），做完一份每格还一件。
基岩版有序配方把剩余物写进 result 数组，引擎照给；无序配方的 result 数组只出第一项，由服务端（Server/CraftReturns.py）
读格子对上这张表补还。只收做完可能还东西的无序配方（某一格的物品、或标签格按词表展开的某个成员带剩余物；面团的水桶原样留下）；
表里只记每格的选项（物品名或 "#标签"），还什么由服务端按格子里实际放的物品查 Remainders（Shared/Rules/Crafting）。
用法：py -3 tools/gen_crafts.py            生成 / 更新 CraftReturns.py
      py -3 tools/gen_crafts.py --check    只比较，不一致时退出码 1（tests/test_craft_returns.py 也会比）
"""
import os
import sys

import recipejson

OUT = os.path.join(recipejson.SCRIPTS, "Shared", "Data", "CraftReturns.py")


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


def main(argv):
    return recipejson.write(OUT, render(), "--check" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
