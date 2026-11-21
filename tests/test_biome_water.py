# -*- coding: utf-8 -*-
# runner: py3
"""群系水色表（tools/gen_biome_water.py 按原版资源包生成的 Shared/Data/BiomeWater.py）：形状对、几个群系的值对、生成器读得对、和原版文件一致。

用到它的是 Shared/Rules/PotWater.py（厨锅里清水的颜色），那边的用例在 test_pot_water.py。
"""
from __future__ import print_function

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

import fdtest

Table = fdtest.load("Shared.Data.BiomeWater").BiomeWater
TOOLS = os.path.join(fdtest.ROOT, "tools")
TOOL = os.path.join(TOOLS, "gen_biome_water.py")
VANILLA = fdtest.vanilla()        # 本机版本号最高的原版资源包（tools/vanilla_pack.py，工具的缺省也是它）；没有游戏目录是 None


def tool():
    sys.dont_write_bytecode = True          # 导入生成器别在 tools/ 里留 .pyc
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import gen_biome_water
    return gen_biome_water


def fakePack(biomes, legacy=None):
    """临时的"原版资源包"：biomes 是 {群系 id: water_appearance 字典（或 None = 不写）}，legacy 是老格式文件的内容。返回目录，用完要 rmtree。"""
    root = tempfile.mkdtemp(prefix="fdbiomes")
    os.makedirs(os.path.join(root, "biomes"))
    for identifier, appearance in biomes.items():
        components = {"minecraft:fog_appearance": {"fog_identifier": "minecraft:fog_default"}}
        if appearance is not None:
            components["minecraft:water_appearance"] = appearance
        document = {"format_version": "1.21.120", "minecraft:client_biome": {"description": {"identifier": identifier}, "components": components}}
        name = identifier.split(":")[-1] + ".client_biome.json"
        with io.open(os.path.join(root, "biomes", name), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(document))
    if legacy is not None:
        with io.open(os.path.join(root, "biomes_client.json"), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(legacy))
    return root


def testEveryNameIsABareBiomeNameAndEveryColourAnRgbInteger():
    assert len(Table) >= 80, "原版 3.10 有 87 个群系的客户端定义"
    for name, color in Table.items():
        assert isinstance(name, str) and name == name.lower() and ":" not in name, "客户端 GetBiomeName 回的是不带命名空间的小写名：" + repr(name)
        assert isinstance(color, int) and 0 <= color <= 0xFFFFFF, (name, color)


def testTheBiomesTheOverworldIsMadeOfAreAllThere():
    for name in ("plains", "sunflower_plains", "forest", "birch_forest", "roofed_forest", "taiga", "cold_taiga", "mega_taiga", "desert",
                 "swampland", "mangrove_swamp", "jungle", "bamboo_jungle", "savanna", "mesa", "extreme_hills", "ice_plains", "mushroom_island",
                 "river", "frozen_river", "beach", "cold_beach", "stone_beach", "ocean", "deep_ocean", "cold_ocean", "frozen_ocean",
                 "lukewarm_ocean", "warm_ocean", "deep_warm_ocean", "meadow", "cherry_grove", "pale_garden",
                 "hell", "crimson_forest", "warped_forest", "soulsand_valley", "basalt_deltas", "the_end"):
        assert name in Table, name


def testSomeAnchorColoursAreWhatTheEngineDrawsTheWaterWith():
    # 原版 3.10 的 water_appearance：平原 #44AFF5（不是 JE 的 #3F76E4）、沼泽 #617B64（新格式；老文件写的是 #4c6559）、暖水海洋 #02B0E5、
    # 下界 #905957。游戏更新改了值就重新生成，再改这几行
    assert Table["plains"] == 0x44AFF5
    assert Table["swampland"] == Table["swampland_mutated"] == 0x617B64
    assert Table["warm_ocean"] == 0x02B0E5
    assert Table["hell"] == 0x905957
    assert len(set(Table.values())) > 40, "每个群系各有各的水色，不是一个常量"


def testTheToolReadsTheNewFormatFilesAndIgnoresTheOldFile():
    root = fakePack({"minecraft:plains": {"surface_color": "#44AFF5"}, "minecraft:swampland": {"surface_color": "#617b64", "surface_opacity": 0.65},
                     "minecraft:no_water": None, "mymod:lava_lands": {"surface_color": "#FF8000"}},
                    legacy={"biomes": {"default": {"water_surface_color": "#44AFF5"}, "minecraft:swampland": {"water_surface_color": "#4c6559"},
                                       "minecraft:desert": {"water_surface_color": "#32A598"}}})
    try:
        found = tool().waters(root)
    finally:
        shutil.rmtree(root)
    assert found == {"plains": 0x44AFF5, "swampland": 0x617B64, "mymod:lava_lands": 0xFF8000}, \
        "新格式的值；没写 water_appearance 的不进表；老文件不读（它的沼泽值和只在它里面的沙漠都不算）；别的命名空间的名字保留全名"


def testTheToolRefusesWhatItDoesNotUnderstand():
    for biomes, why in (({"minecraft:plains": {"surface_color": "#44AFF"}}, "五位的颜色"),
                        ({"minecraft:plains": {"surface_color": {"r": 0.2}}}, "不是字符串的颜色"),
                        ({}, "一份群系定义都没有")):
        root = fakePack(biomes)
        try:
            try:
                tool().waters(root)
            except SystemExit:
                continue
            raise AssertionError("应该报错：" + why)
        finally:
            shutil.rmtree(root)


def testTheRenderedTableIsSortedAndReadsBackToTheSameValues():
    text = tool().render({"b": 0x0000FF, "a": 0x44AFF5})
    assert text.index("'a': 0x44AFF5,") < text.index("'b': 0x0000FF,"), "按名字排序，生成出来的文件才稳定"
    assert text.startswith("# -*- coding: utf-8 -*-\n") and text.endswith("}\n")
    code = compile(text, "BiomeWater.py", "exec")
    scope = {}
    exec(code, scope)
    assert scope["BiomeWater"] == {"a": 0x44AFF5, "b": 0xFF}


def testTheTableMatchesTheVanillaPack():
    """拿本机最新的原版资源包比（工具不带 --vanilla 用的就是它）；本机没有游戏目录（别人的机器、只有本仓库的克隆）跳过。"""
    if VANILLA is None:
        print("跳过：本机没有原版资源包")
        return
    code = subprocess.call([sys.executable, "-B", TOOL, "--check"])
    assert code == 0, "原版资源包变了：py -3 tools/gen_biome_water.py 重新生成 Shared/Data/BiomeWater.py"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
