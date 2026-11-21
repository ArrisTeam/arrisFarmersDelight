# -*- coding: utf-8 -*-
"""gen_biome_water - 按原版资源包算"各群系的水是什么颜色"，生成 Shared/Data/BiomeWater.py（开发工具，py -3 运行，只用标准库）

厨锅里没放料时是水，水色取所在位置的群系水色（HoD 的 PotBehavior.colour：BiomeColors.getAverageWaterColor）。基岩版引擎画世界里的水
用的就是每个群系客户端定义里的 minecraft:water_appearance.surface_color（原版资源包 biomes/<群系>.client_biome.json，一群系一份），
锅里的水因此和旁边池塘的水同色。
老格式 biomes_client.json 的 water_surface_color 不读：引擎先看新格式、新格式没写才轮到它，原版内置包又已经是每个群系一份新格式；
而且两边对不上（沼泽老文件 #4c6559、新文件 #617b64，21 个后来的群系老文件里根本没有）。
键是群系名，不带 minecraft: 命名空间（客户端 GetBiomeName 回的就是这样），值是 0xRRGGBB；没写 water_appearance 的群系不进表
（查表时取不到，Shared/Rules/PotWater 给缺省色）。
原版资源包的路径用 --vanilla 指定，缺省是本机游戏目录里版本号最高的那一份（vanilla_pack.newest；一份都没有就不生成）。
用法：py -3 tools/gen_biome_water.py [--vanilla <游戏的 resource_packs/vanilla 目录>] [--check]
"""
import glob
import io
import json
import os
import re
import sys

sys.dont_write_bytecode = True      # 别在 tools/ 里留 .pyc

import vanilla_pack

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "bp", "arrisFarmersDelightScripts", "Shared", "Data", "BiomeWater.py")
VANILLA_DEFAULT = vanilla_pack.newest()      # 不写死版本：游戏升级、旧目录删了也跟着最新的走
NAMESPACE = "minecraft:"
COLOR = re.compile(r"^#([0-9a-fA-F]{6})$")


def waters(vanilla):
    """原版资源包的 biomes/*.client_biome.json -> {群系名（去掉 minecraft:）: 0xRRGGBB}。

    找不到文件、颜色写法不认识、同一个群系有两份都直接报错：宁可生成失败，也别悄悄出一张错表。
    """
    pattern = os.path.join(vanilla, "biomes", "*.client_biome.json")
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise SystemExit("找不到群系的客户端定义：" + pattern)
    table = {}
    for path in paths:
        document = json.load(io.open(path, encoding="utf-8-sig"))["minecraft:client_biome"]
        identifier = document["description"]["identifier"]
        appearance = document.get("components", {}).get("minecraft:water_appearance")
        if not appearance or "surface_color" not in appearance:
            continue
        written = appearance["surface_color"]
        found = COLOR.match(written) if isinstance(written, str) else None
        if found is None:
            raise SystemExit("%s 的水色写法不认识：%r（只认 #RRGGBB）" % (path, written))
        name = identifier[len(NAMESPACE):] if identifier.startswith(NAMESPACE) else identifier
        if name in table:
            raise SystemExit("群系 %s 的定义有两份：%s" % (identifier, path))
        table[name] = int(found.group(1), 16)
    return table


def render(table):
    lines = [
        "# -*- coding: utf-8 -*-",
        '"""BiomeWater - 各群系的水是什么颜色（双端，纯数据，由 tools/gen_biome_water.py 按原版资源包生成，别手改）',
        "",
        "原版资源包每个群系的 minecraft:water_appearance.surface_color（biomes/<群系>.client_biome.json）：引擎画世界里的水用的就是它。",
        "键是群系名，不带命名空间（客户端 GetBiomeName 回的就是这样）；值 0xRRGGBB。厨锅里的清水怎么用它见 Shared/Rules/PotWater.py。",
        '"""',
        "BiomeWater = {",
    ]
    for name in sorted(table):
        lines.append("    %r: 0x%06X," % (str(name), table[name]))
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv):
    vanilla = argv[argv.index("--vanilla") + 1] if "--vanilla" in argv else VANILLA_DEFAULT
    if not vanilla:
        print("本机没有原版资源包（%s 下的任何版本里都没有）：不生成" % vanilla_pack.GAME)
        return 1
    text = render(waters(vanilla))
    current = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if "--check" in argv:
        return 0 if current == text else 1
    if current != text:
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
