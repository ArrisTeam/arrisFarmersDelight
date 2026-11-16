# -*- coding: utf-8 -*-
"""gen_crafts - 从行为包的无序合成配方生成"合成后补还的剩余物"表 Shared/Data/CraftReturns.py（开发工具，py -3 运行）

JE 里原料自带合成剩余物（奶桶剩空桶、奶瓶剩玻璃瓶、米饭剩碗……，表在 Shared/Data/Remainders.py），做完一份每格还一件。
基岩版有序配方把剩余物写进 result 数组，引擎照给；无序配方的 result 数组只出第一项，由服务端（Server/CraftReturns.py）
读格子对上这张表补还。只收用到了带剩余物原料的无序配方。
用法：py -3 tools/gen_crafts.py            生成 / 更新 CraftReturns.py
      py -3 tools/gen_crafts.py --check    只比较，不一致时退出码 1（tests/test_craft_returns.py 也会比）
"""
import os
import sys

import recipejson

OUT = os.path.join(recipejson.SCRIPTS, "Shared", "Data", "CraftReturns.py")


def entries():
    table = {}
    for recipe in recipejson.recipes():
        if recipe["kind"] != "shapeless":
            continue
        names = sorted(name for name, _aux in recipe["ingredients"])
        returns = recipejson.returnsOf(recipe["result"], names)
        if returns:
            table.setdefault(recipe["result"], []).append((names, recipe["count"], returns, recipe["source"]))
    return table


def render():
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""CraftReturns - 无序合成配方做完一份补还的剩余物（双端，纯数据，由 tools/gen_crafts.py 从合成配方生成，别手改）',
        "",
        "成品 -> 做它的各条无序配方：ingredients 原料名（排好序，一格一个）、count 一份出几个、returns {原料名: 剩余物名}",
        "（每份每格还一件，JE 的合成剩余物；面团配方的水桶剩它自己）、source 是生成它的配方文件。",
        "服务端 Server/CraftReturns.py 取结果时读格子对上这张表；有序配方的剩余物写在 result 数组里，引擎自己给。",
        '"""',
        "CraftReturns = {",
    ]
    table = entries()
    for result in sorted(table):
        lines.append("    %r: [" % str(result))
        for names, count, returns, source in table[result]:
            lines.append("        {\"ingredients\": (%s,), \"count\": %d, \"returns\": {%s}, \"source\": %r}," % (
                ", ".join("%r" % str(name) for name in names), count,
                ", ".join("%r: %r" % (str(name), str(left)) for name, left in sorted(returns.items())), str(source)))
        lines.append("    ],")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv):
    return recipejson.write(OUT, render(), "--check" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
