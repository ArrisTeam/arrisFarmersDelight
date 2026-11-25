# -*- coding: utf-8 -*-
# runner: py3
"""每个方块的硬度、爆炸抗性对照 JE（ModBlocks，FD 1.3.4），外加炉灶的亮度和挖掘工具。

JE：strength(a) 把硬度和爆炸抗性都设成 a，strength(a, b) 分别设；没写 strength 的抄 copy 的原版方块（木桶 2.5、耕地 0.6、干草块 0.5、
白色羊毛 0.8、蛋糕 0.5、橡木木板 / 栅栏 2.0 / 3.0、砖块 2.0 / 6.0，草和作物、蘑菇一碰就碎）；盛宴是 feastProperties() 的 strength(0.5F)。
表写在这里；旁边有 JE 的源码（.refs/FarmersDelight）时，再从 ModBlocks.java 按上面的规则重新推一遍，和表对账。
基岩的方块：旧格式写 minecraft:destroy_time / explosion_resistance，新格式写 destructible_by_mining / destructible_by_explosion；
一碰就碎的作物、野生作物可以不写（缺省就是 0）。基岩版的 block_light_emission 是 0~1 的比例，引擎 ×15 取整。
"""
from __future__ import print_function

import io
import os
import re

import blockkit
import fdtest

JE_DIR = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "java", "vectorwing", "farmersdelight", "common")
CABINETS = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo", "crimson", "warped")
CRATES = ("carrot", "potato", "beetroot", "cabbage", "tomato", "onion")
WILD = ("sandy_shrub", "wild_cabbages", "wild_onions", "wild_tomatoes", "wild_carrots", "wild_potatoes", "wild_beetroots", "wild_rice")
PIES = ("apple_pie", "sweet_berry_cheesecake", "chocolate_pie", "pumpkin_pie")
FEASTS = ("roast_chicken_block", "stuffed_pumpkin_block", "honey_glazed_ham_block", "shepherds_pie_block", "gleaming_salad_block",
          "rice_roll_medley_block")

# JE 的注册名 -> (硬度, 爆炸抗性)
JE_STRENGTH = dict(
    [("stove", (2.0, 6.0)), ("cooking_pot", (0.5, 6.0)), ("skillet", (0.5, 6.0)), ("wooden_basket", (1.5, 1.5)),
     ("bamboo_basket", (1.5, 1.5)), ("cutting_board", (2.0, 2.0)), ("rice_bale", (0.5, 0.5)), ("rice_bag", (0.8, 0.8)),
     ("straw_bale", (0.5, 0.5)), ("rope", (0.2, 0.2)), ("safety_net", (0.2, 0.2)), ("rope_fence", (1.0, 1.0)),
     ("rope_fence_gate", (1.0, 1.0)), ("canvas_rug", (0.2, 0.2)), ("tatami", (0.8, 0.8)), ("full_tatami_mat", (0.3, 0.3)),
     ("half_tatami_mat", (0.3, 0.3)), ("brown_mushroom_colony", (0.0, 0.0)), ("red_mushroom_colony", (0.0, 0.0)),
     ("organic_compost", (1.2, 1.2)), ("rich_soil", (0.5, 0.5)), ("rich_soil_farmland", (0.6, 0.6)),
     ("cabbages", (0.0, 0.0)), ("onions", (0.0, 0.0)), ("budding_tomatoes", (0.0, 0.0)), ("tomatoes", (0.0, 0.0)),
     ("tomatoes_on_rope", (0.0, 0.0)), ("rice", (0.2, 0.2)), ("rice_panicles", (0.0, 0.0))]
    + [("%s_cabinet" % wood, (2.5, 2.5)) for wood in CABINETS] + [("%s_crate" % crop, (2.0, 3.0)) for crop in CRATES]
    + [(name, (0.0, 0.0)) for name in WILD] + [(name, (0.5, 0.5)) for name in PIES] + [(name, (0.5, 0.5)) for name in FEASTS])


def _stages(prefix, count, *extra):
    return ["arris:%s%d" % (prefix, stage) for stage in range(count)] + ["arris:" + name for name in extra]


# JE 的注册名 -> 基岩这边对应的方块（名字不一样、拆成几级的；没写的就是 arris:<同名>）
NETEASE = {
    "stove": ["arris:stove", "arris:stove_extinguish"], "bamboo_basket": ["arris:basket"],
    "rope_fence_gate": ["arris:rope_fence_gate", "arris:rope_fence_gate_open"],
    "full_tatami_mat": ["arris:tatami_full_mat", "arris:tatami_full_mat_head"], "half_tatami_mat": ["arris:tatami_half_mat"],
    "organic_compost": _stages("organic_compost_stage", 4), "rich_soil_farmland": ["arris:rich_soil_farmland", "arris:rich_soil_farmland_moist"],
    "cabbages": _stages("cabbages_stage", 8), "onions": _stages("onions_stage", 4), "budding_tomatoes": _stages("budding_tomatoes_stage", 3),
    "tomatoes": _stages("budding_tomatoes_stage", 7)[3:], "tomatoes_on_rope": _stages("tomatoes_vine_stage", 4),
    "rice": _stages("rice_stage", 4, "rice_supporting"), "rice_panicles": _stages("rice_upper_crop_stage", 4),
    "roast_chicken_block": _stages("roast_chicken_block_stage", 4, "roast_chicken_block_leftover"),
    "stuffed_pumpkin_block": _stages("stuffed_pumpkin_block_stage", 4),
    "honey_glazed_ham_block": _stages("honey_glazed_ham_block_stage", 4, "honey_glazed_ham_block_leftover"),
    "shepherds_pie_block": _stages("shepherds_pie_block_stage", 4, "shepherds_pie_block_leftover"),
    "gleaming_salad_block": _stages("gleaming_salad_block_stage", 4, "gleaming_salad_block_leftover"),
    "rice_roll_medley_block": _stages("rice_roll_medley_block_stage", 8, "rice_roll_medley_block_leftover"),
}
# copy 的原版方块（MC 1.20.1 的 Blocks）：(硬度, 爆炸抗性)
VANILLA = {"BRICKS": (2.0, 6.0), "OAK_PLANKS": (2.0, 3.0), "HAY_BLOCK": (0.5, 0.5), "WHITE_WOOL": (0.8, 0.8), "BROWN_CARPET": (0.1, 0.1),
           "WHITE_CARPET": (0.1, 0.1), "OAK_FENCE": (2.0, 3.0), "BARREL": (2.5, 2.5), "BROWN_MUSHROOM": (0.0, 0.0),
           "RED_MUSHROOM": (0.0, 0.0), "DIRT": (0.5, 0.5), "FARMLAND": (0.6, 0.6), "CAKE": (0.5, 0.5), "TALL_GRASS": (0.0, 0.0),
           "WHEAT": (0.0, 0.0)}


def _value(components, old, new, newKey):
    if old in components:
        return components[old]["value"]
    if new in components:
        return components[new][newKey]
    return None


def _strength(identifier):
    components = blockkit.components(identifier)
    return (_value(components, "minecraft:destroy_time", "minecraft:destructible_by_mining", "seconds_to_destroy"),
            _value(components, "minecraft:explosion_resistance", "minecraft:destructible_by_explosion", "explosion_resistance"))


def testEveryBlockHasJavasHardnessAndBlastResistance():
    wrong = []
    for name, (hardness, resistance) in sorted(JE_STRENGTH.items()):
        for identifier in NETEASE.get(name, ["arris:" + name]):
            found = _strength(identifier)
            # 一碰就碎的（JE 0 / 0）可以不写，缺省就是 0
            expected = (hardness, resistance)
            if found[0] is None and hardness == 0.0:
                found = (0.0, found[1])
            if found[1] is None and resistance == 0.0:
                found = (found[0], 0.0)
            if found != expected:
                wrong.append("%s（JE %s）：%r，应为 %r" % (identifier, name, found, expected))
    assert not wrong, "\n".join(wrong)


def _read(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def _javaStrength():
    """{JE 注册名: (硬度, 爆炸抗性)}：从 ModBlocks.java 按 strength / instabreak / feastProperties / copy 推出来（帆布告示牌没移植，跳过）。"""
    source = _read(os.path.join(JE_DIR, "registry", "ModBlocks.java"))
    found = {}
    for chunk in source.split("BLOCKS.register(")[1:]:
        chunk = chunk.split("public static")[0]
        name = re.match(r'\s*"(\w+)"', chunk).group(1)
        if name.endswith("_sign"):
            continue
        strength = re.findall(r"strength\(([\d.]+)F(?:,\s*([\d.]+)F)?\)", chunk)
        copied = re.search(r"copy\(Blocks\.(\w+)\)", chunk)
        if strength:
            hardness, resistance = strength[-1]
            found[name] = (float(hardness), float(resistance or hardness))
        elif "instabreak()" in chunk or "copy(ModBlocks.TOMATO_CROP" in chunk:
            found[name] = (0.0, 0.0)
        elif "feastProperties()" in chunk:
            found[name] = (0.5, 0.5)
        elif copied:
            found[name] = VANILLA[copied.group(1)]
        else:
            raise AssertionError("推不出 %s 的硬度：%s" % (name, chunk[:120]))
    return found


def testTheTableIsJavasOwn():
    if not os.path.isdir(JE_DIR):
        print("跳过：没有 JE 的源码（.refs/FarmersDelight）")
        return
    derived = _javaStrength()
    assert derived == JE_STRENGTH, sorted(set(derived.items()) ^ set(JE_STRENGTH.items()))


def testLitStoveGivesLightThirteenAndTheBurntOutOneNone():
    lit = blockkit.components("arris:stove")["minecraft:block_light_emission"]["emission"]
    assert int(lit * 15) == 13 and int(round(lit * 15)) == 13        # 取整、四舍五入都是 13
    assert blockkit.components("arris:stove_extinguish")["minecraft:block_light_emission"]["emission"] == 0


def testStoveNeedsAPickaxeToDropLikeBricks():
    for identifier in ("arris:stove", "arris:stove_extinguish"):
        tier = blockkit.components(identifier)["netease:tier"]
        assert tier["digger"] == "pickaxe" and tier["destroy_special"] is True


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
