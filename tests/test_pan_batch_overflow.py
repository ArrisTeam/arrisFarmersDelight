# -*- coding: utf-8 -*-
# runner: both
"""煎锅里比一批（16 件）多的一叠煎好时，成品给站点里的厨师（Server/HandFrying._finish / _handOut，Compat/Diegesis/PanLogic.onOpen 接上站点里的人）。

HoD SkilletCooking.finish：锅里比一批多（FD 右键放的一大叠又被颠过）的话，一批熟了之后剩下的生料留在锅里，这一批成品给站点里的厨师
（users 里最后颠锅的人还在就是他，否则第一位）：Inventory.add，放不下 drop；站点里没有人才像 FD 的煎锅那样跳出锅外。
data 里 TO_COOK 说的就是给了厨师还是跳出去了（客户端据此演抬起缩没还是抛出去）。
"""
from __future__ import print_function

import panfake as P

fake, HandFrying = P.fake, P.HandFrying
BEEF, COOKED = P.BEEF, P.COOKED


def _bigPan(data, cook="a"):
    """FD 右键放进来的一大叠（20 个生牛肉），cook 颠了一下锅：从此归他，按一批 16 个煎。"""
    data["cookingDict"] = {"newItemName": BEEF, "newAuxValue": 0, "count": 20}
    hand = HandFrying.handOf(0, P.PAN, data)
    fake.world.time += 1.0
    assert HandFrying.toss(hand, cook, fake.world.time, data["cookingDict"])
    return hand


def _fry(manager, hand):
    """贴锅那面煎熟、等翻、翻一下（最后颠锅的还是 hand.cook）、另一面煎熟：这一批好了。"""
    side = P.Rules.sideSeconds(16)
    P.run(manager, side + 0.5)
    assert hand.frying.waits(), "贴锅那面熟了，等着翻"
    fake.world.time += 0.5
    assert HandFrying.toss(hand, hand.cook, fake.world.time, fake.blockEntities[(0, P.PAN)]["cookingDict"])
    P.run(manager, side + 0.5)


def _fried():
    events = P.events("fried")
    assert len(events) == 1, events
    return events[0][1]


def testTheBatchGoesToTheCookAtTheStationAndTheRestStaysRawInThePan():
    manager, data = P.setup()
    P.opened(manager)
    hand = _bigPan(data)
    _fry(manager, hand)
    assert fake.count("a", COOKED) == 16 and fake.spawned == [], "一批 16 个熟牛肉进了厨师的背包，没有抛出来"
    assert P.inPan() == (BEEF, 4), "剩下的 4 个生的留在锅里"
    fried = _fried()
    assert fried["to_cook"] is True and fried["in_pan"] is False and fried["stack"]["count"] == 16, "客户端演抬起缩没，不是抛出去"
    assert hand.frying.byHand and hand.fried == 1, "剩下的接着按手放的煎"


def testWithNobodyAtTheStationTheBatchJumpsOutOfThePan():
    manager, data = P.setup()
    hand = _bigPan(data)
    _fry(manager, hand)
    assert [(item["newItemName"], item["count"], pos) for item, _dim, pos in fake.spawned] == [(COOKED, 16, (10.5, 64.3, 10.5))], \
        "没人在站点里：像 FD 的煎锅那样跳出锅外"
    assert fake.count("a", COOKED) == 0 and P.inPan() == (BEEF, 4)
    assert _fried()["to_cook"] is False


def testTheCookWhoTossedLastGetsItEvenWhenSomeoneElseCameFirst():
    manager, data = P.setup()
    assert manager.open("b", list(P.PAN))                    # b 先到
    P.opened(manager, "a")
    hand = _bigPan(data, cook="a")
    _fry(manager, hand)
    assert fake.count("a", COOKED) == 16 and fake.count("b", COOKED) == 0, "站点里的第一位是 b，可最后颠锅的是 a"


def testWhenTheCookHasLeftTheFirstOneAtTheStationGetsIt():
    manager, data = P.setup()
    assert manager.open("b", list(P.PAN))
    P.opened(manager, "a")
    hand = _bigPan(data, cook="a")
    manager.close("a")
    _fry(manager, hand)
    assert fake.count("b", COOKED) == 16 and fake.count("a", COOKED) == 0 and fake.spawned == []
    assert _fried()["to_cook"] is True


def testWhenTheInventoryIsFullTheBatchDropsAtTheCooksFeet():
    manager, data = P.setup()
    P.opened(manager)
    for slot in range(36):
        P.hold("a", slot, "minecraft:stone", 64)
    hand = _bigPan(data)
    _fry(manager, hand)
    assert [(item["newItemName"], item["count"], pos) for item, _dim, pos in fake.spawned] == [(COOKED, 16, (10.5, 64.0, 8.5))], \
        "放不下：掉在厨师脚下（Inventory.add 失败再 drop）"
    assert _fried()["to_cook"] is True, "站点里有人：还是算给了厨师"


def testABatchThatIsTheWholePanStillStaysInThePan():
    manager, data = P.setup()
    P.opened(manager)
    data["cookingDict"] = {"newItemName": BEEF, "newAuxValue": 0, "count": 16}
    hand = HandFrying.handOf(0, P.PAN, data)
    fake.world.time += 1.0
    assert HandFrying.toss(hand, "a", fake.world.time, data["cookingDict"])
    _fry(manager, hand)
    assert P.inPan() == (COOKED, 16) and fake.count("a", COOKED) == 0 and fake.spawned == []
    fried = _fried()
    assert fried["in_pan"] is True and fried["to_cook"] is False, "整锅都是这一批：留在锅里等人取"


if __name__ == "__main__":
    import fdtest
    raise SystemExit(fdtest.run(globals()))
