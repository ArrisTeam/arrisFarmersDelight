# -*- coding: utf-8 -*-
# runner: both
"""砧板站点摆盘的三个 HoD 游戏内测试的离线版（gametest/BoardTests.java：aPieGoesIntoItsCrust、aFeastIsLaidFromTheBook、everyDishIsLaidByHand）：
九层的派一次做两个、九样东西的盛宴从背包里一次放好、菜谱表里每一道菜都能一层层手放做成。
站点逻辑和前置包的 Manager 是真的，引擎是 potfake 的假引擎（boardkit 装好）。
"""
from __future__ import print_function

import dgtest
import boardkit as K
from boardkit import fake

Dishes = K.potfake.load("Shared.Rules.DishStation")
HONEY_HAM = "arris:honey_glazed_ham_block_stage0"


def _place(manager, name, count, slot=3, aux=0):
    """背包放好、点托盘拿到光标栈上、点板放上去；返回 place 动作被不被接受。"""
    K.carry(manager, slot, name, count, aux=aux)
    return K.do(manager, "a", K.custom("place"))


def _names(events):
    return [name for name, _data in events]


def testAPieOfNineLayersGoesIntoItsCrustTwoAtATime():
    """JE aPieGoesIntoItsCrust：派皮先放（两张），其余八样各两份按任意顺序放；整个派是方块，躺在板上。"""
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "arris:pie_crust", 2)
    order = ("minecraft:apple", "minecraft:sugar", "minecraft:wheat", "minecraft:apple", "minecraft:wheat", "minecraft:sugar", "minecraft:apple", "minecraft:wheat")
    for name in order:
        assert K.layers(data) and K.board(data) is None, "派皮之后一直是层，凑齐前不做成"
        assert _place(manager, name, 2)
    assert K.layers(data) == [] and K.board(data) == ("arris:apple_pie_item", 2), "九层、两个苹果派"
    assert K.count("minecraft:apple") == 0 and K.count("arris:pie_crust") == 0, "料都用掉了"
    assert _names(K.effects()).count("assembled") == 1


def testAFeastIsLaidFromTheBookInOneGo():
    """JE aFeastIsLaidFromTheBook：盛宴要九样东西，书一次从背包里全放好；盛宴躺在板上，用完的料没了，蜂蜜瓶换回空瓶。"""
    manager, data = K.setup()
    K.opened(manager)
    fake.give("a", 0, "minecraft:sweet_berries", 4)
    fake.give("a", 1, "minecraft:honey_bottle", 1)
    fake.give("a", 2, "arris:smoked_ham", 1)
    fake.give("a", 3, "arris:cooked_rice", 2)
    fake.give("a", 4, "minecraft:bowl", 1)
    assert K.do(manager, "a", K.custom("bookFill", key="d:" + HONEY_HAM, sets=1))
    assert K.board(data) == (HONEY_HAM, 1) and K.layers(data) == [], "蜜汁火腿盛宴躺在板上"
    assert K.count("minecraft:sweet_berries") == 0 and K.count("minecraft:honey_bottle") == 0 and K.count("arris:smoked_ham") == 0, "料全用了"
    assert K.count("minecraft:glass_bottle") == 1, "蜂蜜的瓶子还回来"
    assert K.count("minecraft:bowl") == 2, "米饭的两只碗也还回来（做一份剩下的容器）"
    events = dict(K.effects())
    assert events["assembled"]["block"] is True and len(events["assembled"]["layers"]) == 9, "九层一起融掉，成品是整块的"


def testDoughFromWaterKeepsItsBucketOfWaterAndTheCookGetsItBack():
    """JE doughKeepsItsWater（站点层）：五个小麦、一桶水做成五个面团（一桶水揉完整叠小麦），水桶原样回到背包（和工作台一样，不换成空桶）。"""
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:wheat", 5)
    assert K.layers(data) == [("minecraft:wheat", 5)] and K.board(data) is None
    assert _place(manager, "minecraft:water_bucket", 1, slot=4)
    assert K.board(data) == ("arris:wheat_dough", 5) and K.layers(data) == [], "五个小麦出五个面团"
    assert K.count("minecraft:water_bucket") == 1 and K.count("minecraft:bucket") == 0, "水桶还是满的，回到了背包"
    assert K.count("minecraft:wheat") == 0


def testAStuffedPotatoGivesTheMilkBucketBackEmptyAndOnlyOneIsMadeBecauseABucketGoesDownOneAtATime():
    """JE milkGivesItsBucketBack（站点层）：三个烤土豆、三份馅（熟牛肉）、一桶奶：一桶奶只放得下一个，所以做一个酿馅土豆，空桶回到背包，剩下的土豆和馅也还回来。"""
    manager, data = K.setup()
    K.opened(manager)
    assert _place(manager, "minecraft:baked_potato", 3)
    assert _place(manager, "minecraft:cooked_beef", 3, slot=4)
    assert K.layers(data) == [("minecraft:baked_potato", 3), ("minecraft:cooked_beef", 3)]
    assert _place(manager, "minecraft:milk_bucket", 1, slot=5)
    assert K.layers(data) == [] and K.board(data) == ("arris:stuffed_potato", 1), "一个酿馅土豆"
    assert K.count("minecraft:bucket") == 1 and K.count("minecraft:milk_bucket") == 0, "空桶回来了"
    assert K.count("minecraft:baked_potato") == 2 and K.count("minecraft:cooked_beef") == 2, "剩下的也还回来"


def _cuttableBaseDish():
    """一道从"板上等着切的食物"打底的菜（FD 自己没有，下游有）：卷心菜打底、再放一根胡萝卜。"""
    return [{"ingredients": [("arris:cabbage", 0), ("minecraft:carrot", 0)], "result": ("x:cabbage_dish", 0)}]


def testABookPickLeavesTheFoodToBeCutUntilTheRestIsThereThenTheFoodBecomesTheDishesFirstLayer():
    """JE aBookPickLeavesTheFoodUntilTheRestIsThere：板上等着切的食物是这道菜的底座、背包里还凑不齐其余的料——食物留着等切（什么也不放）；
    料凑齐了，再点一下，食物成了这道菜的第一层，放完就做成（后半）。"""
    Dishes.rebuildIndex(_cuttableBaseDish())
    try:
        manager, data = K.setup()
        K.opened(manager)
        assert _place(manager, "arris:cabbage", 3)
        assert K.board(data) == ("arris:cabbage", 3) and K.layers(data) == [], "卷心菜躺着等切"
        assert not K.do(manager, "a", K.custom("bookFill", key="d:x:cabbage_dish", sets=1)), "背包里没有胡萝卜：什么也没放"
        assert K.board(data) == ("arris:cabbage", 3) and K.layers(data) == [] and K.count("minecraft:carrot") == 0, "食物留着，等着切"
        fake.give("a", 6, "minecraft:carrot", 5)
        assert K.do(manager, "a", K.custom("bookFill", key="d:x:cabbage_dish", sets=1))
        assert K.layers(data) == [] and K.board(data) == ("x:cabbage_dish", 3), "食物成了第一层，料齐了就做成：三份"
        assert K.count("arris:cabbage") == 0 and K.count("minecraft:carrot") == 2, "三个卷心菜、三根胡萝卜用掉了"
    finally:
        Dishes.rebuildIndex()


def _layersOf(dish):
    """JE BoardTests.layersOf：底座先放，其余的按配方顺序，和底座同名的排最后。"""
    first = dish["ingredients"][dish["base"]]
    order, same = [first], []
    for index, kind in enumerate(dish["ingredients"]):
        if index != dish["base"]:
            (same if kind == first else order).append(kind)
    return order + same


def _cutsFirst(manager, order):
    """第二层是能切第一层的工具（那道菜得从书里放，不能手放）：JE 里 Cutting.findWith(第一层, 第二层)。"""
    env = K.BoardLogic.BoardTools.envFor(manager.stations[(0, K.BOARD)].logic)
    first, second = ({"newItemName": kind[0], "newAuxValue": kind[1], "count": 1} for kind in order[:2])
    return env.cutsWith(first, second)


def testEveryDishIsLaidByHandLayerAfterLayer():
    """JE everyDishIsLaidByHand：菜谱表里每一道菜，把它的料一层一层放上去（放不下的料不放，凑成了还能长的点一下做成）都能做成，
    不会卡在半路、也不会把料吞掉；有别的菜可以用同一些层的，板上躺着的是某道菜就行。"""
    manager, data = K.setup()
    K.opened(manager)
    failed, laid = [], 0
    for dish in Dishes.dishes():
        order = _layersOf(dish)
        if len(order) < 2 or _cutsFirst(manager, order):
            continue
        K.advance(1.0)                      # 前置包每位玩家每秒最多 40 个动作（令牌桶）：一道菜用不完，连着放几十道要让它补
        while K.layers(data) or K.board(data):
            assert K.do(manager, "a", K.custom("take"))
        fake.world.players["a"]["inv"][:] = [None] * 36
        for kind in order:
            assert _place(manager, kind[0], 1, aux=kind[1])
        if K.layers(data):
            K.do(manager, "a", K.custom("assemble"))
        board = K.board(data)
        if K.layers(data) or board is None or not Dishes.isDishResult(board[0]):
            failed.append((dish["result"][0], K.layers(data), board))
        laid += 1
    assert not failed, "手放不成：%r" % (failed,)
    assert laid * 10 >= len(Dishes.dishes()) * 9, "要真的放过一批菜（菜谱表 33 个成品、86 条配方，几乎都能手放）：只放了 %d 条" % laid


if __name__ == "__main__":
    raise SystemExit(dgtest.run(globals()))
