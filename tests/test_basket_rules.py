# -*- coding: utf-8 -*-
# runner: both
"""篮子吸掉落物的规则（Shared/Rules/Basket.py）对照 JE 的 Basket / BasketBlockEntity（FD 1.3.4）。

期望值抄自 JE：
- Basket.COLLECTION_AREA_SHAPES：下 (0,-16,0)-(16,16,16)、上 (0,0,0)-(16,32,16)、北 (0,0,-16)-(16,16,16)、
  南 (0,0,0)-(16,16,32)、西 (-16,0,0)-(16,16,16)、东 (0,0,0)-(32,16,16)（Block.box，像素）；
- BasketBlockEntity.putStackInInventoryAllSlots / insertStack / canCombine：从 0 号格往后逐格试，空格整堆放进去，同种且没满的补满；
- isFull：每一格都有东西且数量正好是满堆；
- 吸进一整个掉落物之后 setTransferCooldown(8)，8 刻 = 0.4 秒。
"""
from __future__ import print_function

import fdtest

Basket = fdtest.load("Shared.Rules.Basket")

# JE 的 Block.box 像素值，按 get3DDataValue 的次序：下 上 北 南 西 东
JE_SHAPES = [
    (0, -16, 0, 16, 16, 16),
    (0, 0, 0, 16, 32, 16),
    (0, 0, -16, 16, 16, 16),
    (0, 0, 0, 16, 16, 32),
    (-16, 0, 0, 16, 16, 16),
    (0, 0, 0, 32, 16, 16),
]


def _stack(name, count, aux=0, **extra):
    stack = {"newItemName": name, "newAuxValue": aux, "count": count}
    stack.update(extra)
    return stack


def _maxStack(stack):
    return {"minecraft:egg": 16, "minecraft:diamond_sword": 1}.get(stack["newItemName"], 64)


def _empty():
    return [None] * Basket.SLOTS


# ---- 收集区 ----

def testCollectionAreasAreTheJavaShapes():
    for facing, pixels in enumerate(JE_SHAPES):
        low, high = Basket.AREAS[facing]
        assert tuple(low) + tuple(high) == tuple(value / 16.0 for value in pixels), facing
    assert (Basket.DOWN, Basket.UP, Basket.NORTH, Basket.SOUTH, Basket.WEST, Basket.EAST) == (0, 1, 2, 3, 4, 5)


def testUpwardAreaIsTheBasketBlockPlusTheBlockAbove():
    assert Basket.collectionBox((10, 64, 20), Basket.UP) == ((10, 64, 20), (11, 66, 21))
    assert Basket.collectionBox((10, 64, 20), Basket.DOWN) == ((10, 63, 20), (11, 65, 21))
    assert Basket.collectionBox((10, 64, 20), Basket.EAST) == ((10, 64, 20), (12, 65, 21))
    assert Basket.collectionBox((10, 64, 20), Basket.WEST) == ((9, 64, 20), (11, 65, 21))


def _inArea(footPos, basketPos=(10, 64, 10), facing=Basket.UP):
    return Basket.overlaps(Basket.itemBox(footPos), Basket.collectionBox(basketPos, facing))


def testItemsInTheBodyOrTheBlockAboveAreCollected():
    assert _inArea((10.5, 64.125, 10.5))            # 躺在篮子底板上
    assert _inArea((10.5, 65.2, 10.5))              # 在上面那一格里
    assert _inArea((10.5, 65.9, 10.5))              # 碰盒下沿还在收集区里
    assert not _inArea((10.5, 66.0, 10.5))          # 碰盒下沿正好贴着收集区上沿：不算（边贴边不相交）
    assert not _inArea((10.5, 63.7, 10.5))          # 碰盒上沿（63.95）没到篮子下沿
    assert _inArea((10.5, 63.8, 10.5))              # 上沿 64.05 进了篮子
    assert not _inArea((11.125, 64.5, 10.5))        # 碰盒正好贴着东边
    assert _inArea((11.1, 64.5, 10.5))              # 碰盒压进来一点


def testBasketCellsListTheBasketsAnItemCouldBeInside():
    assert Basket.basketCells((10.5, 64.125, 10.5)) == [(10, 64, 10), (10, 63, 10)]    # 篮子自己那一格排最前，下面一格的篮子够得着上面那格
    assert Basket.basketCells((10.5, 64.8, 10.5)) == [(10, 64, 10), (10, 63, 10), (10, 65, 10)]  # 碰盒顶上 0.05 探进了 65 那格
    assert Basket.basketCells((10.5, 66.0, 10.5)) == [(10, 66, 10), (10, 65, 10)]      # 脚底贴着 66：自己所在格 66 和 65 的篮子（收集到 67）
    cells = Basket.basketCells((10.95, 64.1, 10.5))                                      # 压着东边的格线：东邻也算
    assert (10, 64, 10) in cells and (11, 64, 10) in cells and (11, 63, 10) in cells
    assert cells[0] == (10, 64, 10)
    for facing in range(6):                                                              # 列出来的每一格都真的相交，没列的都不相交
        foot = (3.3, 20.6, -4.7)
        found = set(Basket.basketCells(foot, facing))
        for x in range(0, 6):
            for y in range(18, 23):
                for z in range(-7, -2):
                    assert _inArea(foot, (x, y, z), facing) == ((x, y, z) in found), (facing, x, y, z)


# ---- 往 27 格里塞 ----

def testEmptyBasketTakesTheWholeStackIntoSlotZero():
    slots, changed, rest = Basket.insertAll(_empty(), _stack("arris:onion", 12), _maxStack)
    assert changed == [0] and rest is None
    assert slots[0] == _stack("arris:onion", 12) and slots[1:] == [None] * 26


def testSameKindTopsUpTheFirstPartialStackThenSpillsToTheNextEmptySlot():
    before = _empty()
    before[0] = _stack("arris:onion", 60)
    slots, changed, rest = Basket.insertAll(before, _stack("arris:onion", 10), _maxStack)
    assert [slots[0]["count"], slots[1]["count"]] == [64, 6] and changed == [0, 1] and rest is None
    assert before[0]["count"] == 60 and before[1] is None          # 传进来的格子表不被改


def testSlotOrderDecidesNotPartialFirst():
    # JE 是"哪一格先遇到用哪一格"：0 号格空着、5 号格有半堆同种，整堆进 0 号格
    before = _empty()
    before[5] = _stack("arris:onion", 30)
    slots, changed, rest = Basket.insertAll(before, _stack("arris:onion", 10), _maxStack)
    assert changed == [0] and rest is None
    assert slots[0]["count"] == 10 and slots[5]["count"] == 30


def testPartialStackBeforeTheFirstEmptySlotIsFilledFirst():
    before = _empty()
    before[0] = _stack("arris:rice", 1)
    before[1] = _stack("arris:onion", 30)
    before[3] = _stack("arris:onion", 63)
    slots, changed, rest = Basket.insertAll(before, _stack("arris:onion", 40), _maxStack)
    # 0 号别种；1 号补 34 到 64；2 号是空格，剩下 6 整个放进去；3 号没轮到
    assert changed == [1, 2] and rest is None
    assert slots[1]["count"] == 64 and slots[2] == _stack("arris:onion", 6) and slots[3]["count"] == 63


def testDifferentTagsAuxOrNamesDoNotMerge():
    plain = _stack("minecraft:potion", 1, 0)
    for other in (_stack("minecraft:potion", 1, 1), _stack("minecraft:potion", 1, 0, userData={"Potion": 1}),
                  _stack("minecraft:potion", 1, 0, enchantData=[(1, 1)]), _stack("minecraft:glass_bottle", 1, 0)):
        before = _empty()
        before[0] = other
        slots, changed, rest = Basket.insertAll(before, plain, _maxStack)
        assert changed == [1], other                # 没并进去，放进下一个空格
    before = _empty()
    before[0] = _stack("minecraft:potion", 1, 0, userData={})          # 没有数据和空数据是同一种
    assert Basket.insertAll(before, plain, _maxStack)[1] == [0]


def testSmallStackSizesAndFullBasketsLeaveARemainder():
    before = _empty()
    before[0] = _stack("minecraft:egg", 15)
    slots, changed, rest = Basket.insertAll(before, _stack("minecraft:egg", 5), _maxStack)
    assert slots[0]["count"] == 16 and slots[1]["count"] == 4 and rest is None
    full = [_stack("arris:onion", 64) for _ in range(Basket.SLOTS)]
    slots, changed, rest = Basket.insertAll(full, _stack("arris:onion", 3), _maxStack)
    assert changed == [] and rest == _stack("arris:onion", 3)
    almost = list(full)
    almost[26] = _stack("arris:onion", 62)
    slots, changed, rest = Basket.insertAll(almost, _stack("arris:onion", 3), _maxStack)
    assert changed == [26] and slots[26]["count"] == 64 and rest["count"] == 1


def testIsFullNeedsEverySlotFilledToTheStackLimit():
    full = [_stack("arris:onion", 64) for _ in range(Basket.SLOTS)]
    assert Basket.isFull(full, _maxStack)
    short = list(full)
    short[10] = _stack("arris:onion", 63)
    assert not Basket.isFull(short, _maxStack)
    hole = list(full)
    hole[26] = None
    assert not Basket.isFull(hole, _maxStack)
    eggs = [_stack("minecraft:egg", 16) for _ in range(Basket.SLOTS)]
    assert Basket.isFull(eggs, _maxStack)                       # 满堆按各物品自己的上限算
    over = list(full)
    over[0] = _stack("arris:onion", 65)
    assert not Basket.isFull(over, _maxStack)                   # JE 比的是 != 满堆


# ---- 冷却 ----

def testCooldownIsEightTicks():
    assert abs(Basket.COOLDOWN - 0.4) < 1e-9
    gate = Basket.Gate()
    key = (0, (1, 2, 3))
    assert gate.ready(key, 100.0)
    gate.captured(key, 100.0)
    assert not gate.ready(key, 100.39) and gate.ready(key, 100.4)
    assert gate.ready((0, (1, 2, 4)), 100.1)                    # 别的篮子不受影响


def testIdleBasketsRetryAfterAShortWhile():
    gate = Basket.Gate()
    key = (0, (1, 2, 3))
    gate.idle(key, 50.0)
    assert not gate.ready(key, 50.1) and gate.ready(key, 50.2)
    gate.captured(key, 60.0)
    assert len(gate) == 1
    gate.prune(60.3)
    assert len(gate) == 1                                        # 冷却还没完，留着
    gate.prune(60.5)
    assert len(gate) == 0


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
