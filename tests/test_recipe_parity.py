# -*- coding: utf-8 -*-
# runner: py3
"""合成配方对照 JE（Farmer's Delight 1.20）的账：每个成品有哪几种做法、退还什么容器、有序配方摆成什么样。

依据 .refs/FarmersDelight/src/generated/resources/data（farmersdelight/recipes、forge/tags/items、ModItems 的 craftRemainder），
标签在 TAGS 里展开成基岩版的物品。三块：
1. 退还的容器：用 JE 物品自带的合成剩余物（牛奶桶 / 水桶 -> 空桶，牛奶瓶 / 蜂蜜瓶 -> 玻璃瓶，煮熟的米饭 -> 碗）推出每份配方该还什么，
   和配方实际还的（有序配方 result 数组的第二项起 + 无序配方按成品名查 shapedRecipeContainerDict）逐条对：新配方漏还、多还都会红。
   例外是面团：JE 的 DoughRecipe 把水桶原样留下，不是空桶。
2. 成品的做法（FAMILIES）：JE 一个配方里的标签展开后有几种原料组合，基岩版就要有几个配方，一个不多一个不少，个数也对。
3. 有序配方的摆法（LAYOUTS）：和 JE 的 pattern 形状一致（键换成别的字母不影响）；面团的水桶配方挨着的两格都认。
有意没做的（引擎限制：无序配方的 result 数组只认第一项，字典按成品名查、一份配方只能还一种容器一个）：
- 填馅马铃薯的牛奶桶做法（2 种）：这个成品的玻璃瓶走字典，桶的变体还不了；要做只能把四种全改成有序配方。
- 多格标签的混搭：巧克力派 / 蛋糕 / 芝士蛋糕的牛奶桶瓶混用、牧羊人派的熟羊肉熟羊排混用。有序配方摆法固定，混搭要把每种位置
  组合各写一份；水果沙拉是无序配方，浆果混搭已做。
- 蜂蜜火腿、牧羊人派在 JE 是无序配方，这里仍是有序配方（要还两只碗 + 瓶，或因变体还桶 / 瓶）。
"""
from __future__ import print_function

import collections
import itertools

import fdtest
import recipekit

Food = fdtest.load("Shared.Data.Food")

# JE 标签 -> 基岩版物品（FD 的换成 arris:）：forge:cooked_chicken / cooked_mutton / cooked_beef / cooked_fishes/salmon /
# salad_ingredients（= crops/cabbage）/ berries / vegetables / milk，另有配方里直接写的候选 hay（干草块或稻草块）
TAGS = {
    "cooked_chicken": ("minecraft:cooked_chicken", "arris:cooked_chicken_cuts"),
    "cooked_mutton": ("minecraft:cooked_mutton", "arris:cooked_mutton_chops"),
    "cooked_beef": ("minecraft:cooked_beef", "arris:beef_patty"),
    "cooked_salmon": ("minecraft:cooked_salmon", "arris:cooked_salmon_slice"),
    "cabbage": ("arris:cabbage", "arris:cabbage_leaf"),
    "berries": ("minecraft:sweet_berries", "minecraft:glow_berries"),
    "vegetables": ("minecraft:beetroot", "minecraft:carrot", "arris:onion", "minecraft:potato", "arris:tomato"),
    "milk": ("minecraft:milk_bucket", "arris:milk_bottle"),
    "hay": ("minecraft:hay_block", "arris:rice_bale"),
}
# JE 物品自带的合成剩余物（ModItems 的 craftRemainder 和原版物品）：用它当原料，合成后还回来
REMAINDER = {
    "minecraft:milk_bucket": "minecraft:bucket",
    "minecraft:water_bucket": "minecraft:bucket",
    "minecraft:honey_bottle": "minecraft:glass_bottle",
    "arris:milk_bottle": "minecraft:glass_bottle",
    "arris:cooked_rice": "minecraft:bowl",
}


def one(item, count=1):
    return ((item,), count, False)


def anyOf(tag, count=1, mixed=False):
    """标签里任选一种；count 份时默认全选同一种（有序配方摆法固定），mixed 时各选各的（无序配方）。"""
    return (TAGS[tag], count, mixed)


BREAD, CARROT, ONION, TOMATO = one("minecraft:bread"), one("minecraft:carrot"), one("arris:onion"), one("arris:tomato")
BOWL, CRUST, RICE, CANVAS = one("minecraft:bowl"), one("arris:pie_crust"), one("arris:cooked_rice"), one("arris:canvas")
POTATO = one("minecraft:baked_potato")
# 成品 + 一次出几个 -> JE 里做它的各个配方的原料（有几个配方取并集）
FAMILIES = {
    ("arris:chicken_sandwich", 1): [[BREAD, CARROT, anyOf("cooked_chicken"), anyOf("cabbage")]],
    ("arris:mutton_wrap", 1): [[BREAD, ONION, anyOf("cooked_mutton"), anyOf("cabbage")]],
    ("arris:grilled_salmon", 1): [[BOWL, ONION, one("minecraft:sweet_berries"), anyOf("cooked_salmon"), anyOf("cabbage")]],
    ("arris:fruit_salad", 1): [[one("minecraft:apple"), one("minecraft:melon_slice", 2), anyOf("berries", 2, True),
                                one("arris:pumpkin_slice"), BOWL]],
    ("arris:kelp_roll", 1): [[one("arris:cooked_rice", 2), anyOf("vegetables"), one("minecraft:dried_kelp", 3)]],
    ("arris:stuffed_potato", 1): [[POTATO, anyOf("cooked_beef"), one("arris:milk_bottle")]],           # 只做瓶装牛奶
    ("arris:tomato_seeds", 1): [[(("arris:tomato", "arris:rotten_tomato"), 1, False)]],
    ("arris:pie_crust", 1): [[one("minecraft:wheat", 3), anyOf("milk")]],
    ("arris:chocolate_pie_item", 1): [[one("minecraft:cocoa_beans", 3), anyOf("milk", 3), one("minecraft:sugar", 2), CRUST],
                                      [one("arris:chocolate_pie_slice", 4)]],
    ("arris:apple_pie_item", 1): [[one("minecraft:wheat", 3), one("minecraft:apple", 3), one("minecraft:sugar", 2), CRUST],
                                  [one("arris:apple_pie_slice", 4)]],
    ("arris:sweet_berry_cheesecake_item", 1): [[one("minecraft:sweet_berries", 6), anyOf("milk", 2), CRUST],
                                               [one("arris:sweet_berry_cheesecake_slice", 4)]],
    ("arris:shepherds_pie_block_stage0", 1): [[one("minecraft:baked_potato", 2), anyOf("milk"), anyOf("cooked_mutton", 3),
                                               one("arris:onion", 2), BOWL]],
    ("arris:honey_glazed_ham_block_stage0", 1): [[one("minecraft:sweet_berries", 4), one("minecraft:honey_bottle"),
                                                  one("arris:smoked_ham"), one("arris:cooked_rice", 2), BOWL]],
    ("arris:horse_feed", 1): [[anyOf("hay"), one("minecraft:apple", 2), one("minecraft:golden_carrot")]],
    ("arris:cod_roll", 2): [[one("arris:cod_slice", 2), RICE]],
    ("arris:salmon_roll", 2): [[one("arris:salmon_slice", 2), RICE]],
    ("arris:roasted_mutton_chops", 1): [[one("arris:cooked_mutton_chops"), one("minecraft:beetroot"), BOWL, RICE, TOMATO]],
    ("arris:steak_and_potatoes", 1): [[POTATO, one("minecraft:cooked_beef"), BOWL, ONION, RICE]],
    ("arris:wheat_dough", 1): [[one("minecraft:wheat"), one("minecraft:water_bucket")]],               # DoughRecipe
    ("arris:wheat_dough", 3): [[one("minecraft:wheat", 3), one("minecraft:egg")]],
    ("arris:cooking_pot", 1): [[one("minecraft:brick", 2), one("minecraft:wooden_shovel"), one("minecraft:iron_ingot", 5),
                                one("minecraft:water_bucket")]],
    ("arris:tatami", 2): [[one("arris:canvas", 2), one("arris:straw", 2)]],
    ("arris:cabbage", 1): [[one("arris:cabbage_leaf", 2)]],
    ("arris:canvas", 1): [[one("arris:straw", 4)], [one("arris:canvas_rug", 2)]],
    ("arris:rope", 4): [[one("arris:straw", 2)], [one("arris:safety_net")]],
    ("minecraft:book", 1): [[one("minecraft:paper", 3), CANVAS]],
    ("minecraft:painting", 1): [[one("minecraft:stick", 8), CANVAS]],
    ("minecraft:scaffolding", 6): [[one("minecraft:bamboo", 6), CANVAS]],
    ("minecraft:lead", 1): [[one("arris:straw", 5)]],
    ("minecraft:packed_mud", 2): [[one("arris:straw"), one("minecraft:mud", 2)]],
    ("minecraft:paper", 1): [[one("arris:tree_bark", 3)]],
    ("minecraft:pumpkin_seeds", 1): [[one("arris:pumpkin_slice")]],
    ("minecraft:cake", 1): [[one("arris:cake_slice", 7)],
                            [one("arris:milk_bottle", 3), one("minecraft:sugar", 2), one("minecraft:egg"), one("minecraft:wheat", 3)]],
    ("minecraft:milk_bucket", 1): [[one("minecraft:bucket"), one("arris:milk_bottle", 4)]],
}
# JE 的 pattern（| 分行），键换成别的字母不影响，只比形状
LAYOUTS = [
    (("arris:pie_crust1", "arris:pie_crust2"), "wMw| w "),
    (("arris:chocolate_pie1", "arris:chocolate_pie2"), "ccc|mmm|xOx"),
    (("arris:sweet_berry_cheesecake1", "arris:sweet_berry_cheesecake2"), "sss|sss|mOm"),
    (("arris:apple_pie",), "###|aaa|xOx"),
    (("arris:cake_from_milk_bottle",), "mmm|ses|www"),
    (("arris:apple_pie_from_slices", "arris:chocolate_pie_from_slices", "arris:sweet_berry_cheesecake_from_slices"), "##|##"),
    (("arris:painting_from_canvas",), "sss|scs|sss"),
    (("arris:scaffolding_from_canvas",), "b#b|b b|b b"),
    (("arris:lead_from_straw",), "ss |ss |  s"),
    (("arris:tatami",), "cs|sc"),
    (("arris:cooking_pot",), "bSb|iWi|iii"),
    (("arris:kelp_roll", "arris:kelp_roll2", "arris:kelp_roll3", "arris:kelp_roll4", "arris:kelp_roll5"), "RXR|###"),
]


def expand(parts):
    """一个 JE 配方的原料 -> 所有可能的物品多重集合（frozenset((物品, 个数))）。"""
    options = []
    for choices, count, mixed in parts:
        if mixed:
            options.append([tuple(sorted(collections.Counter(c).items())) for c in itertools.combinations_with_replacement(choices, count)])
        else:
            options.append([((item, count),) for item in choices])
    found = set()
    for combo in itertools.product(*options):
        counts = collections.Counter()
        for picked in combo:
            for item, n in picked:
                counts[item] += n
        found.add(frozenset(counts.items()))
    return found


def canonical(rows):
    """pattern 的形状：每个键按第一次出现的先后换成序号，空格不变。"""
    names = {}
    return ["".join(" " if char == " " else str(names.setdefault(char, len(names))) for char in row) for row in rows]


def returnedContainers(body):
    """配方实际还的容器：有序配方 result 数组第二项起；无序配方按成品名查字典（一份配方还一个）。"""
    results = recipekit.resultsOf(body)
    back = collections.Counter()
    for item, count in results[1:]:
        back[item] += count
    container = Food.shapedRecipeContainerDict.get(results[0][0])
    if container:
        back[container["itemName"]] += 1
    return back


def expectedContainers(kind, body):
    """JE 说该还的容器：原料里自带剩余物的每件还一件；面团的水桶原样留下。"""
    ingredients = recipekit.ingredientsOf(kind, body)
    if recipekit.resultsOf(body)[0][0] == "arris:wheat_dough" and "minecraft:water_bucket" in ingredients:
        return collections.Counter({"minecraft:water_bucket": 1})
    back = collections.Counter()
    for item, count in ingredients.items():
        if item in REMAINDER:
            back[REMAINDER[item]] += count
    return back


def testContainersComeBackLikeJava():
    for name, (kind, body) in recipekit.loadRecipes().items():
        if kind != "furnace":
            assert returnedContainers(body) == expectedContainers(kind, body), "%s 退还 %s，JE 是 %s" % (
                name, dict(returnedContainers(body)), dict(expectedContainers(kind, body)))


def testEveryDishHasAllItsJavaVariants():
    made = collections.defaultdict(set)
    for kind, body in recipekit.loadRecipes().values():
        if kind != "furnace":
            item, count = recipekit.resultsOf(body)[0]
            made[(item, count)].add(frozenset(recipekit.ingredientsOf(kind, body).items()))
    for key, recipes in FAMILIES.items():
        expected = set()
        for parts in recipes:
            expected |= expand(parts)
        assert made[key] == expected, "%s ×%d 缺 %s，多出 %s" % (
            key[0], key[1], [dict(x) for x in expected - made[key]], [dict(x) for x in made[key] - expected])


def testShapedLayoutsFollowJava():
    byId = recipekit.byIdentifier()
    for identifiers, java in LAYOUTS:
        for identifier in identifiers:
            kind, body = byId[identifier]
            assert kind == "shaped", identifier
            assert canonical(body["pattern"]) == canonical(java.split("|")), "%s 的摆法 %s 和 JE 的 %s 不一样" % (
                identifier, body["pattern"], java)


def testDoughFromWaterTakesAnyTwoNeighbouringCells():
    # JE 的 DoughRecipe 一格小麦 + 一格水桶摆哪都行；有序配方只能把挨着的格子（上下左右、斜着）都写一遍（左右镜像自动算）
    accepted = set()
    for kind, body in recipekit.loadRecipes().values():
        if kind != "shaped" or recipekit.resultsOf(body)[0][0] != "arris:wheat_dough":
            continue
        assert body.get("assume_symmetry", True) is True
        cells = dict((char, (x, y)) for y, row in enumerate(body["pattern"]) for x, char in enumerate(row) if char != " ")
        wheat = [c for c, entry in body["key"].items() if entry["item"] == "minecraft:wheat"][0]
        bucket = [c for c, entry in body["key"].items() if entry["item"] == "minecraft:water_bucket"][0]
        dx, dy = cells[bucket][0] - cells[wheat][0], cells[bucket][1] - cells[wheat][1]
        accepted |= set([(dx, dy), (-dx, dy)])
    assert accepted == set((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)) - set([(0, 0)]), sorted(accepted)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
