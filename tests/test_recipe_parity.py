# -*- coding: utf-8 -*-
# runner: py3
"""合成配方对照 JE（Farmer's Delight 1.20）的账：每个成品有哪几种做法、退还什么容器、有序配方摆成什么样。

依据 .refs/FarmersDelight/src/generated/resources/data（farmersdelight/recipes、forge/tags/items、ModItems 的 craftRemainder），
标签在 TAGS 里展开成基岩版的物品。四块：
1. 退还的容器：用 JE 物品自带的合成剩余物（牛奶桶 / 水桶 -> 空桶，牛奶瓶 / 蜂蜜瓶 -> 玻璃瓶，煮熟的米饭 -> 碗）推出每份配方该还什么，
   和配方实际还的逐条对：有序配方看 result 数组的第二项起（引擎给），无序配方看 tools/gen_crafts.py 生成的
   Shared/Data/CraftReturns.py（服务端读合成格补还）。新配方漏还、多还都会红。例外是面团：JE 的 DoughRecipe 把水桶原样留下。
2. 成品的做法（FAMILIES）：JE 一个配方里的标签展开后有几种原料组合，基岩版就要有几个配方，一个不多一个不少，个数也对；
   标签占好几格时各格可以混着放（奶桶奶瓶、熟羊肉熟羊排、浆果）。
3. 有序配方的摆法（LAYOUTS）：和 JE 的 pattern 形状一致（键换成别的字母不影响；奶桶奶瓶是 JE 的同一个标签，算同一个键）。
4. JE 的无序配方这边也是无序（SHAPELESS_IN_JAVA）：蜂蜜火腿、牧羊人派、牛奶瓶倒回桶、面团（JE 的 DoughRecipe 摆哪都行）……
蛋糕的三桶奶做法是原版自带的配方，本包只补带奶瓶的几种。
"""
from __future__ import print_function

import collections
import itertools

import fdtest
import recipekit

CraftReturns = fdtest.load("Shared.Data.CraftReturns").CraftReturns

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
    ("arris:stuffed_potato", 1): [[POTATO, anyOf("cooked_beef"), anyOf("milk")]],
    ("arris:tomato_seeds", 1): [[(("arris:tomato", "arris:rotten_tomato"), 1, False)]],
    ("arris:pie_crust", 1): [[one("minecraft:wheat", 3), anyOf("milk")]],
    ("arris:chocolate_pie_item", 1): [[one("minecraft:cocoa_beans", 3), anyOf("milk", 3, True), one("minecraft:sugar", 2), CRUST],
                                      [one("arris:chocolate_pie_slice", 4)]],
    ("arris:apple_pie_item", 1): [[one("minecraft:wheat", 3), one("minecraft:apple", 3), one("minecraft:sugar", 2), CRUST],
                                  [one("arris:apple_pie_slice", 4)]],
    ("arris:sweet_berry_cheesecake_item", 1): [[one("minecraft:sweet_berries", 6), anyOf("milk", 2, True), CRUST],
                                               [one("arris:sweet_berry_cheesecake_slice", 4)]],
    ("arris:shepherds_pie_block_stage0", 1): [[one("minecraft:baked_potato", 2), anyOf("milk"), anyOf("cooked_mutton", 3, True),
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
    # 南瓜派的成品是原版的 minecraft:pumpkin_pie（JE 的 FD 也是）：派皮做 2 个，4 片拼回 1 个
    ("minecraft:pumpkin_pie", 2): [[one("arris:pumpkin_slice", 4), one("minecraft:egg"), one("minecraft:sugar"), CRUST]],
    ("minecraft:pumpkin_pie", 1): [[one("arris:pumpkin_pie_slice", 4)]],
    ("minecraft:pumpkin_seeds", 1): [[one("arris:pumpkin_slice")]],
    # 蛋糕：三桶奶是原版自带的配方，本包补带奶瓶的三种组合
    ("minecraft:cake", 1): [[one("arris:cake_slice", 7)]] + [
        [one("minecraft:milk_bucket", 3 - bottles)] * (bottles < 3) + [one("arris:milk_bottle", bottles), one("minecraft:sugar", 2),
                                                                      one("minecraft:egg"), one("minecraft:wheat", 3)]
        for bottles in (1, 2, 3)],
    ("minecraft:milk_bucket", 1): [[one("minecraft:bucket"), one("arris:milk_bottle", 4)]],
}
# JE 的 pattern（| 分行），键换成别的字母不影响，只比形状
LAYOUTS = [
    (("arris:pie_crust1", "arris:pie_crust2"), "wMw| w "),
    (tuple("arris:chocolate_pie%d" % index for index in range(1, 7)), "ccc|mmm|xOx"),
    (tuple("arris:sweet_berry_cheesecake%d" % index for index in range(1, 4)), "sss|sss|mOm"),
    (("arris:apple_pie",), "###|aaa|xOx"),
    (("arris:cake_from_milk_bottle",) + tuple("arris:cake_from_milk_bottle%d" % index for index in range(2, 6)), "mmm|ses|www"),
    (("arris:apple_pie_from_slices", "arris:chocolate_pie_from_slices", "arris:sweet_berry_cheesecake_from_slices"), "##|##"),
    (("arris:painting_from_canvas",), "sss|scs|sss"),
    (("arris:scaffolding_from_canvas",), "b#b|b b|b b"),
    (("arris:lead_from_straw",), "ss |ss |  s"),
    (("arris:tatami",), "cs|sc"),
    (("arris:pumpkin_pie_from_pie_crust",), "cec|csc| O "),
    (("arris:pumpkin_pie_from_slices",), "##|##"),
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


# JE 的同一个标签在这边是几种物品：比摆法时算同一个键
SAME_KEY = {"minecraft:milk_bucket": "milk", "arris:milk_bottle": "milk"}
# JE 是无序配方的成品（这边也必须全是无序配方；同一成品在 JE 另有有序做法的不列）
SHAPELESS_IN_JAVA = ("arris:honey_glazed_ham_block_stage0", "arris:shepherds_pie_block_stage0", "arris:roast_chicken_block_stage0",
                     "arris:rice_roll_medley_block_stage0", "arris:stuffed_potato", "arris:wheat_dough", "minecraft:milk_bucket",
                     "arris:milk_bottle", "arris:honey_cookie", "arris:cod_roll", "arris:salmon_roll", "arris:roasted_mutton_chops",
                     "arris:steak_and_potatoes", "arris:fruit_salad", "arris:organic_compost_stage0")


def canonical(rows, key=None):
    """pattern 的形状：每个键按第一次出现的先后换成序号，空格不变；给了 key 时按键对应的物品算（同一 JE 标签的物品算一个键）。"""
    names = {}

    def of(char):
        item = key[char]["item"] if key else char
        return str(names.setdefault(SAME_KEY.get(item, item), len(names)))
    return ["".join(" " if char == " " else of(char) for char in row) for row in rows]


def returnedContainers(name, kind, body):
    """配方实际还的容器：有序配方是 result 数组第二项起（引擎给）；无序配方是生成的 CraftReturns 表里这份配方的那条（服务端补还）。"""
    results = recipekit.resultsOf(body)
    back = collections.Counter()
    if kind == "shaped":
        for item, count in results[1:]:
            back[item] += count
        return back
    for entry in CraftReturns.get(results[0][0], ()):
        if entry["source"] == name:
            assert entry["count"] == results[0][1], name
            for item in entry["ingredients"]:
                if item in entry["returns"]:
                    back[entry["returns"][item]] += 1
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
            assert returnedContainers(name, kind, body) == expectedContainers(kind, body), "%s 退还 %s，JE 是 %s" % (
                name, dict(returnedContainers(name, kind, body)), dict(expectedContainers(kind, body)))


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
            assert canonical(body["pattern"], body["key"]) == canonical(java.split("|")), "%s 的摆法 %s 和 JE 的 %s 不一样" % (
                identifier, body["pattern"], java)


def testJavasShapelessRecipesAreShapelessHere():
    kinds = collections.defaultdict(set)
    for name, (kind, body) in recipekit.loadRecipes().items():
        if kind != "furnace":
            kinds[recipekit.resultsOf(body)[0][0]].add((kind, name))
    for result in SHAPELESS_IN_JAVA:
        assert kinds[result], "%s 没有配方" % result
        shaped = sorted(name for kind, name in kinds[result] if kind != "shapeless")
        assert not shaped, "%s 在 JE 是无序配方，这边 %s 是有序的" % (result, shaped)


def testDoughFromWaterKeepsTheBucketLikeJava():
    # JE 的 DoughRecipe：一格小麦 + 一格水桶，摆哪都行（就是无序配方），水桶原样留下——表里它的剩余物是它自己
    water = [entry for entry in CraftReturns["arris:wheat_dough"] if "minecraft:water_bucket" in entry["ingredients"]]
    assert len(water) == 1 and water[0]["ingredients"] == ("minecraft:water_bucket", "minecraft:wheat")
    assert water[0]["count"] == 1 and water[0]["returns"] == {"minecraft:water_bucket": "minecraft:water_bucket"}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
