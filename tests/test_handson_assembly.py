# -*- coding: utf-8 -*-
# runner: both
"""Assembly 摆盘规则测试。

对应 Hands-On Delight 的 BoardTests：aSaladStartsFromItsBowl、aBurgerIsBuiltFromTheBreadUp、sixteenBurgersAtOnce、
theTopLayerComesBack（层的前缀匹配）。原测试用 FD 的真实配方，这里用同形状的合成配方：汉堡 = 面包、肉饼、菜叶、番茄、洋葱；
大汉堡再多一块肉饼；下界沙拉 = 碗、绯红菌、诡异菌。
"""
from __future__ import print_function


import fdtest

A = fdtest.load("Shared.Rules.HandsOn.Assembly")


def only(*names):
    return frozenset(names)


def accepts(ingredient, layer):
    return layer in ingredient


BREAD, PATTY, LEAF, TOMATO, ONION = only("bread"), only("patty"), only("leaf"), only("tomato"), only("onion")
BURGER = {"ingredients": [BREAD, PATTY, LEAF, TOMATO, ONION], "base": 0}
BIG_BURGER = {"ingredients": [BREAD, PATTY, PATTY, LEAF, TOMATO, ONION], "base": 0}
SALAD = {"ingredients": [only("bowl"), only("crimson_fungus"), only("warped_fungus")], "base": 0}
# 底座不在第一位的配方：奶酪夹在两片面包里，但必须先放面包（base = 1）
SANDWICH = {"ingredients": [only("cheese"), only("toast")], "base": 1}


def testABurgerIsBuiltFromTheBreadUp():
    dishes = [BURGER, SALAD]
    assert not A.isBase(dishes, "tomato", accepts), "a tomato is no base"
    assert A.isBase(dishes, "bread", accepts) and A.isBase(dishes, "bowl", accepts)
    assert not A.fits(dishes, ["tomato"], accepts)
    assert A.fits(dishes, ["bread"], accepts)
    layers = ["bread", "patty", "leaf", "tomato"]
    assert A.fits(dishes, layers, accepts), "bread, patty, leaf and tomato"
    assert not A.fits(dishes, layers + ["carrot"], accepts), "a carrot belongs to no burger"
    assert A.complete(dishes, layers, accepts) is None, "without the onion it is no burger yet"
    assert A.complete(dishes, layers + ["onion"], accepts) is BURGER, "the last layer makes the burger"


def testABiggerBurgerStartsTheSameWay():
    layers = ["bread", "patty", "leaf", "tomato", "onion"]
    assert not A.canGrow([BURGER], layers, accepts), "nothing bigger starts this way: the last layer makes the burger at once"
    assert A.canGrow([BURGER, BIG_BURGER], layers, accepts), "a bigger burger starts this way: the burger waits for the cook's word"
    assert A.complete([BIG_BURGER, BURGER], layers, accepts) is BURGER
    assert A.fits([BIG_BURGER], layers, accepts)
    assert not A.canGrow([BIG_BURGER], layers + ["patty", "tomato"], accepts)


def testPatternsNeedEachLayerOnItsOwnIngredient():
    dishes = [BIG_BURGER]
    assert A.fits(dishes, ["bread", "patty", "patty"], accepts)
    assert not A.fits(dishes, ["bread", "patty", "patty", "patty"], accepts), "只有两个肉饼的配料"
    assert A.fits(dishes, ["bread", "tomato", "patty"], accepts), "除了第一层必须是底座，顺序不限"
    assert not A.fits(dishes, ["patty"], accepts), "第一层必须是底座"
    assert not A.fits(dishes, [], accepts)
    assert not A.fits(dishes, ["bread"] * 7, accepts), "层数不能超过配料数"


def testAssignBacktracksWhenAGreedyChoiceWouldBlockALaterLayer():
    # 配料 1 接受 x 或 y，配料 2 只接受 x：层 [底座, x, y] 贪心会把 x 给配料 1，y 就没处放
    dish = {"ingredients": [only("base"), only("x", "y"), only("x")], "base": 0}
    assert A.assign(dish, ["base", "x", "y"], accepts) == [0, 2, 1]
    assert A.assign(dish, ["base", "y", "x"], accepts) == [0, 1, 2]
    assert A.assign(dish, ["base", "x", "x"], accepts) == [0, 1, 2]
    assert A.assign(dish, ["base", "y", "y"], accepts) is None


def testTheBaseIsTheOneThatGoesDownFirst():
    assert A.fits([SANDWICH], ["toast"], accepts)
    assert not A.fits([SANDWICH], ["cheese"], accepts), "cheese 不是底座"
    assert A.complete([SANDWICH], ["toast", "cheese"], accepts) is SANDWICH
    assert A.assign(SANDWICH, ["toast", "cheese"], accepts) == [1, 0]


def testASaladStartsFromItsBowl():
    assert not A.fits([SALAD], ["crimson_fungus"], accepts), "a fungus is no bowl"
    assert A.fits([SALAD], ["bowl", "crimson_fungus"], accepts)
    assert A.complete([SALAD], ["bowl", "crimson_fungus", "warped_fungus"], accepts) is SALAD


def testTheThinnestLayerSetsHowManyAreMade():
    # 3 个碗，5 个绯红菌（只有 3 个会摆上去：层数以最薄的为准），2 个诡异菌：做 2 份，退回 1 个碗 + 1 个绯红菌
    counts = [3, 3, 2]
    made = A.rounds(counts)
    assert made == 2, "two, as there were two warped"
    assert [count - made for count in counts] == [1, 1, 0], "a bowl and a fungus go back"
    assert A.rounds([20, 20, 20, 20, 20]) == A.BATCH == 16, "sixteen burgers from stacks of twenty"
    assert 20 - A.rounds([20, 20, 20, 20, 20]) == 4, "the onions over sixteen stay in the hand"
    assert A.rounds([20, 20], most=3) == 3, "工具耐久等外部限制通过 most 传入"
    assert A.rounds([]) == 0 and A.rounds([5, 0, 5]) == 0


def testBaseIsFoundByNameInTheDocumentedOrder():
    assert A.baseOf([only("minecraft:bowl"), only("minecraft:carrot")]) == (0, "bowl")
    assert A.baseOf([only("minecraft:carrot"), only("minecraft:bowl")]) == (1, "bowl")
    assert A.baseOf([only("farmersdelight:beef_patty"), only("minecraft:bread")]) == (1, "bread")
    assert A.baseOf([only("minecraft:rice"), only("minecraft:kelp")]) == (1, "kelp"), "kelp 排在 rice 前"
    assert A.baseOf([only("minecraft:rice"), only("farmersdelight:tortilla")]) == (1, "tortilla"), "a tortilla before rice"
    assert A.baseOf([only("farmersdelight:rice"), only("minecraft:carrot")]) == (0, "rice")
    assert A.baseOf([only("minecraft:carrot"), only("#forge:rods/wooden")]) == (1, "stick")
    assert A.baseOf([only("minecraft:blaze_rod")]) == (0, "stick")
    assert A.baseOf([only("minecraft:sugar"), only("minecraft:wheat")]) == (1, "wheat")
    assert A.baseOf([only("farmersdelight:wheat_dough")]) == (0, "wheat")
    assert A.baseOf([only("minecraft:flour")]) == (0, "wheat")
    assert A.baseOf([only("minecraft:glass_bottle"), only("minecraft:honey")]) == (0, "bottle")
    assert A.baseOf([only("minecraft:sugar"), only("minecraft:egg")]) == (0, A.BASE_FIRST), "都没有：第一个"
    assert A.baseOf([]) == (0, A.BASE_FIRST)


def testBaseWordsMatchAnyChoiceOfAnIngredient():
    # 配料是候选列表时，任何一个候选的名字里有关键词就算
    assert A.baseOf([["minecraft:carrot"], ["minecraft:stick", "minecraft:blaze_rod"]]) == (1, "stick")
    assert A.baseOf([["minecraft:carrot", "minecraft:potato"], ["minecraft:oak_log"]]) == (0, A.BASE_FIRST)
    # 单个名字（字符串）也可以，关键词只在冒号后面的路径里找
    assert A.baseOf(["bowl_mod:carrot"]) == (0, A.BASE_FIRST), "命名空间里的 bowl 不算"
    assert A.baseOf(["minecraft:mushroom_stew", "minecraft:bowl"]) == (1, "bowl")


def testHowADishIsFinished():
    f = A.finishOf
    assert f("bowl", "x:salad", tossed=True) == A.FINISH_TOSS
    assert f("bowl", "x:plate", tossed=False) == A.FINISH_ARRANGE
    assert f("bread", "x:burger") == A.FINISH_SANDWICH
    assert f("bread", "x:chicken_wrap") == A.FINISH_ROLL and f("bread", "x:breakfast_burrito") == A.FINISH_ROLL
    assert f("bread", "x:anything", wrapped=True) == A.FINISH_ROLL
    assert f("stick", "x:kebab") == A.FINISH_SKEWER
    assert f("stick", "x:popsicle", frozen=True) == A.FINISH_FREEZE and f("stick", "x:icepop", hasIce=True) == A.FINISH_FREEZE
    assert f("rice", "x:nigiri") == A.FINISH_SHAPE and f("rice", "x:bibimbap", arranged=True) == A.FINISH_ARRANGE
    assert f("kelp", "x:roll") == A.FINISH_ROLL and f("tortilla", "x:taco") == A.FINISH_ROLL
    assert f("crust", "x:pie") == A.FINISH_PRESS and f("bottle", "x:juice") == A.FINISH_PRESS
    assert f("wheat", "x:bread_loaf") == A.FINISH_KNEAD
    assert f(A.BASE_FIRST, "x:thing") == A.FINISH_PRESS
    assert f("rice", "x:cake", isBlock=True) == A.FINISH_PRESS, "成品是方块（盛宴、蛋糕）：压"
    assert f("bread", "x:wheat_dough") == A.FINISH_KNEAD, "成品名以 dough 结尾：揉"
    assert f("bowl", "x:salad", hasTool=True, tossed=True) == A.FINISH_CHOP, "要刀的先算切"
    assert f("bowl", "x:feast", isBlock=True, tossed=True) == A.FINISH_TOSS, "碗优先于方块判断（原版顺序）"


def testASaladIsTossedOnlyIfItIsAllPlants():
    plants = [{"name": "minecraft:crimson_fungus"}, {"name": "minecraft:warped_fungus"}]
    assert A.isTossed(others=plants), "纯植物才拌"
    assert A.isTossed(tagged=True, others=[{"name": "x:beef", "meat": True}]), "打了拌标签就是拌"
    assert not A.isTossed(arranged=True, others=plants), "打了摆标签"
    assert not A.isTossed(isBlock=True, others=plants), "成品是方块：摆"
    assert not A.isTossed(others=plants + [{"name": "x:steak", "meat": True}])
    assert not A.isTossed(others=plants + [{"name": "x:cod", "fish": True}])
    assert not A.isTossed(others=plants + [{"name": "x:cracked_thing", "cracked": True}])
    assert not A.isTossed(others=plants + [{"name": "minecraft:egg"}]), "名字带 egg"
    assert not A.isTossed(others=plants + [{"name": "x:bacon_bits"}]), "名字带 bacon"
    assert A.isTossed(), "没有别的配料"


def testConstants():
    assert A.GRID == 3 and A.MOST_LAYERS == 9 == A.GRID * A.GRID and A.BATCH == 16


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
