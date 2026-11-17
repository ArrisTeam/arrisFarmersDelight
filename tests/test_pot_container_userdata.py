# -*- coding: utf-8 -*-
# runner: both
"""厨锅容器格带着 userData 读写（Server/Helpers/PotContainer.py + Shared/Rules/ItemUserData.py）：改过名、带自定义数据的料在站点里拿起来、
放回去、摆开、退回、煮掉一部分时数据跟着走（JE 的物品栈本来就带）；"空的 userData"和"没有 userData"是同一种；放不进站点载荷的 userData 不进状态。
引擎是 potfake.py 里的假的（和引擎一样：不要 userData 就不给，GetContainerItem 的 getUserData 缺省 False）。"""
from __future__ import print_function

import copy

import fdtest
import potkit as K
from potkit import POT, SAUCE, TOMATO, fake

Fits = fdtest.load("Shared.Rules.ItemUserData")
HandCooking = K.HandCooking
CARROT, ONION = "minecraft:carrot", "arris:onion"
NAMED = {"display": {"Name": "Grandma's"}, "RepairCost": {"__type__": 3, "__value__": 2}}
LORE = {"display": {"Lore": ["a", "b"]}}


def _cells():
    return fake.containers[(0, POT)]


def testReadingTheFoodSlotsAsksTheEngineForUserDataAndWritingKeepsIt():
    manager, data = K.setup()
    fake.setContainer(POT, 0, CARROT, 3, userData=NAMED)
    assert K.cells()[0]["userData"] == NAMED, "inputs 带 userData"
    laid = copy.deepcopy(K.cells())
    laid[0]["count"] = 5
    K.PotContainer.setInputs(0, POT, K.cells(), laid)
    assert fake.container(POT, 0) == {"newItemName": CARROT, "newAuxValue": 0, "count": 5, "userData": NAMED}, "改了个数写回去：数据还在"


def testAnItemWithoutDataIsWrittenBackWithoutTheEmptyKeyAsBefore():
    # 引擎读出来的没数据的物品 userData 是 None：写回去不带这个键，和 B7 之前写的一样（只有真有数据的才带）
    manager, data = K.setup()
    _cells()[0] = {"newItemName": TOMATO, "newAuxValue": 0, "count": 4, "userData": None}
    laid = copy.deepcopy(K.cells())
    laid[0]["count"] = 2
    K.PotContainer.setInputs(0, POT, K.cells(), laid)
    assert fake.container(POT, 0) == {"newItemName": TOMATO, "newAuxValue": 0, "count": 2}, fake.container(POT, 0)


def testAStackTheStationPutsBackAfterReadingItDoesNotCarryTheEmptyKeyEither():
    manager, data = K.setup()
    _cells()[0] = {"newItemName": TOMATO, "newAuxValue": 0, "count": 4, "userData": None}     # 引擎读出来的样子
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.slot(0))) and K.do(manager, "a", K.click(K.slot(1)))
    assert fake.container(POT, 1) == {"newItemName": TOMATO, "newAuxValue": 0, "count": 4}, fake.container(POT, 1)


def testWhatTheStationPicksUpFromASlotCarriesItsDataAndComesBackToTheInventoryWithIt():
    manager, data = K.setup()
    fake.setContainer(POT, 0, CARROT, 3, userData=NAMED)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.slot(0)))
    hand = manager.sessions["a"].hand
    assert hand["count"] == 3 and hand["userData"] == NAMED, "光标栈上是带名字的那叠"
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert fake.world.players["a"]["inv"][5]["userData"] == NAMED and fake.world.players["a"]["inv"][5]["count"] == 3, "放回背包：名字还在"
    assert fake.container(POT, 0) is None


def testAStackWithTheSameDataMergesIntoTheSlotAndAStackWithOtherDataDoesNot():
    manager, data = K.setup()
    fake.setContainer(POT, 0, CARROT, 3, userData=NAMED)
    fake.give("a", 4, CARROT, 2, userData=copy.deepcopy(NAMED))
    fake.give("a", 6, CARROT, 2, userData=LORE)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(4))) and K.do(manager, "a", K.click(K.slot(0)))
    assert fake.container(POT, 0)["count"] == 5 and fake.container(POT, 0)["userData"] == NAMED, "同一种（数据也一样）并成一叠，数据还在"
    assert manager.sessions["a"].hand is None
    assert K.do(manager, "a", K.click(K.inv(6))) and K.do(manager, "a", K.click(K.slot(0), button=1))
    assert fake.container(POT, 0)["count"] == 2 and fake.container(POT, 0)["userData"] == LORE, "数据不一样的不是同一种：不并，和格子里的换了手"
    hand = manager.sessions["a"].hand
    assert hand["count"] == 5 and hand["userData"] == NAMED, "手上换到的那叠名字还在，两叠的数据没有串"


def testEmptyUserDataAndNoUserDataAreTheSameKind():
    # 内核的 sameItem：空的标签和没有标签算一样（引擎读出来的格子里 userData 是 None，脚本造的物品里没有这个键）
    for stored in ({"userData": None}, {"userData": {}}, {}):
        manager, data = K.setup()
        _cells()[0] = dict({"newItemName": ONION, "newAuxValue": 0, "count": 2}, **stored)
        fake.give("a", 4, ONION, 3)
        K.opened(manager)
        assert K.do(manager, "a", K.click(K.inv(4))) and K.do(manager, "a", K.click(K.slot(0)))
        assert fake.container(POT, 0)["count"] == 5 and manager.sessions["a"].hand is None, "并成一叠：%r" % (stored,)


def testLayingOutKeepsTheDataOnEveryHalf():
    manager, data = K.setup()
    fake.give("a", 3, TOMATO, 16, userData=NAMED)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.inv(3))) and K.do(manager, "a", K.click(K.slot(0)))
    manager.tick(0.05)
    assert K.shape(K.cells())[:3] == [(TOMATO, 8), (TOMATO, 8), None], "番茄酱的写法：摆成两格"
    assert [fake.container(POT, index)["userData"] for index in (0, 1)] == [NAMED, NAMED], "两格都带着名字"


def testTakeBackReturnsTheStackWithItsData():
    manager, data = K.setup()
    fake.setContainer(POT, 2, "minecraft:milk_bucket", 1, userData=NAMED)
    K.opened(manager)
    assert K.do(manager, "a", K.custom("take_back"))
    back = [item for item in fake.world.players["a"]["inv"] if item and item["newItemName"] == "minecraft:milk_bucket"]
    assert len(back) == 1 and back[0]["userData"] == NAMED, "取回的奶桶还是那只带名字的"


def testCookingPartOfAStackLeavesTheRestWithItsData():
    manager, data = K.setup()
    fake.setContainer(POT, 0, TOMATO, 3, userData=NAMED)
    fake.setContainer(POT, 1, TOMATO, 3, userData=NAMED)
    K.alone(7.0)
    assert K.preview()["count"] == 1 and [fake.container(POT, index)["count"] for index in (0, 1)] == [2, 2], "煮了一份"
    assert [fake.container(POT, index)["userData"] for index in (0, 1)] == [NAMED, NAMED], "剩下的料没被抹掉数据"


def testTheVesselThatIsLeftAfterAMealMovesOnKeepsItsData():
    manager, data = K.setup()
    fake.setContainer(POT, K.PotContainer.VESSEL_SLOT, K.BOWL, 3, userData=NAMED)
    K.setMeal(SAUCE, 1, data)
    K.potStep(fake.world.time)
    assert fake.container(POT, K.PotContainer.RESULT_SLOT)["count"] == 1
    assert fake.container(POT, K.PotContainer.VESSEL_SLOT)["count"] == 2 and fake.container(POT, K.PotContainer.VESSEL_SLOT)["userData"] == NAMED


def _slotItems(payload):
    return payload["state"]["slots"]["ingredients"]


def testUserDataThatCannotGoInTheStationPayloadIsLeftOutSoTheStationStillOpens():
    # 内核把格子里的物品原样编进状态（Wire.toWire：list 里同一类、嵌套不过深 ...），编不了会抛错；光标栈的它会兜底、格子里的不会
    bad = {"mixed": [1, "x"], "after": 1}
    manager, data = K.setup()
    fake.setContainer(POT, 0, CARROT, 3, userData=bad)
    fake.setContainer(POT, 1, ONION, 2, userData=LORE)
    payload = K.opened(manager)
    items = _slotItems(payload)
    assert "userData" not in items["0"] and items["0"]["count"] == 3, "放不进载荷的 userData 不带（和以前一样）"
    assert items["1"]["userData"] == LORE, "放得进的带着发给客户端"


BAD = {"mixed": [1, "x"], "after": 1}                       # 内核编不进载荷的 userData（和上一个用例同一份）


def _barredPot():
    """锅的 0 号格里是 3 个带着"站点载荷放不下的 userData"的胡萝卜（站点读它是没数据的样子），站点开着。"""
    manager, data = K.setup()
    fake.setContainer(POT, 0, CARROT, 3, userData=BAD)
    K.opened(manager)
    return manager


def _untouched(manager, hand=None, inventory=None):
    """0 号格还是原来那叠、数据一点没少；光标栈和背包也没多出东西。"""
    assert fake.container(POT, 0) == {"newItemName": CARROT, "newAuxValue": 0, "count": 3, "userData": BAD}, fake.container(POT, 0)
    assert K.PotContainer.inputs(0, POT)[0]["userData"] == BAD, "经典界面（引擎容器）读到的还是完整的"
    assert manager.sessions["a"].hand == hand
    if inventory is not None:
        assert fake.count("a", CARROT) == inventory


def testTheStationLeavesAStackWhoseDataCannotGoInThePayloadWhereItIs():
    # 站点读这一格时把放不进载荷的 userData 去掉（上一个用例）；拿起来、挪走再把没数据的写回去，格子里的数据就没了（B7 残留）。
    # 站点对这样的格子说不：它留在锅里原样不动，经典界面（引擎容器）和漏斗还能取
    manager = _barredPot()
    assert not K.do(manager, "a", K.click(K.slot(0))), "左键拿起：不行"
    assert not K.do(manager, "a", K.click(K.slot(0), button=1)), "右键拿一半：不行"
    assert not K.do(manager, "a", K.click(K.slot(0), kind="QUICK_MOVE")), "Shift 点：不行"
    _untouched(manager, inventory=0)


def testNothingIsMergedOrSwappedIntoSuchAStackEither():
    manager = _barredPot()
    fake.give("a", 4, CARROT, 2)
    fake.give("a", 5, ONION, 2)
    assert K.do(manager, "a", K.click(K.inv(4)))                         # 手上拿着 2 个没数据的胡萝卜
    carried = manager.sessions["a"].hand
    assert not K.do(manager, "a", K.click(K.slot(0))), "同一种要并进去：并完写回去的是没数据的，不行"
    assert not K.do(manager, "a", K.click(K.slot(0), button=1))
    assert K.do(manager, "a", K.click(K.inv(4)))                         # 放回去，换拿洋葱
    assert K.do(manager, "a", K.click(K.inv(5)))
    assert not K.do(manager, "a", K.click(K.slot(0))), "手上是别的东西：换手也不行（那叠会没数据地到手上）"
    _untouched(manager, hand=manager.sessions["a"].hand)
    assert carried["newItemName"] == CARROT and manager.sessions["a"].hand["newItemName"] == ONION


def testShiftClickingMoreOfTheSameFromTheInventoryGoesToAnotherSlot():
    manager = _barredPot()
    fake.give("a", 4, CARROT, 2)
    assert K.do(manager, "a", K.click(K.inv(4), kind="QUICK_MOVE"))
    assert fake.container(POT, 0)["count"] == 3 and fake.container(POT, 0)["userData"] == BAD, "那一格没并"
    assert fake.container(POT, 1)["count"] == 2 and fake.world.players["a"]["inv"][4] is None, "放进了下一个空格"


def testDoubleClickingAndDraggingLeaveSuchAStackAlone():
    manager = _barredPot()
    fake.give("a", 4, CARROT, 4)
    assert K.do(manager, "a", K.click(K.inv(4)))
    assert not K.do(manager, "a", K.click(K.slot(1), kind="PICKUP_ALL")), "双击聚拢：没有别的同种可收，那一格不收"
    assert manager.sessions["a"].hand["count"] == 4
    spread = {"type": "spread", "targets": [K.slot(0), K.slot(1)], "button": 0}
    assert K.do(manager, "a", spread), "拖着平分：不收的格子悄悄跳过，余下的格子照收"
    assert fake.container(POT, 0)["count"] == 3 and fake.container(POT, 0)["userData"] == BAD
    assert fake.container(POT, 1)["count"] == 4 and manager.sessions["a"].hand is None, "4 个全落在 1 号格"


def testAStackWhoseDataFitsIsStillPickedUpWithItsData():
    manager, data = K.setup()
    fake.setContainer(POT, 0, CARROT, 3, userData=NAMED)
    fake.setContainer(POT, 1, CARROT, 3, userData=BAD)
    K.opened(manager)
    assert K.do(manager, "a", K.click(K.slot(0)))
    assert manager.sessions["a"].hand["userData"] == NAMED and fake.container(POT, 0) is None, "放得进载荷的照旧：数据跟着走"


def testWhichUserDataFitsTheWire():
    assert Fits.fitsWire(None) and Fits.fitsWire({}) and Fits.fitsWire(NAMED) and Fits.fitsWire(LORE)
    assert Fits.fitsWire({"ench": [{"id": 9, "lvl": 2}, {"id": 1, "lvl": 1}], "x": 1.5, "t": True, "n": None, "mixedNumbers": [1, 2.5]})
    assert not Fits.fitsWire({"a": [1, "x"]}), "list 里不同类"
    assert not Fits.fitsWire({"a": [{"k": 1}, None]}), "dict 和 None 混着"
    assert not Fits.fitsWire({"a": float("nan")}) and not Fits.fitsWire({"a": float("inf")}), "不是有限的数"
    assert not Fits.fitsWire({1: "x"}), "键不是文本"
    assert not Fits.fitsWire({"a": object()}), "不认识的类型"
    deep = {}
    node = deep
    for _ in range(Fits.MAX_DEPTH):
        node["n"] = {}
        node = node["n"]
    assert not Fits.fitsWire(deep), "嵌套太深"
    assert not Fits.fitsWire({"items": [{"slot": i} for i in range(Fits.MAX_VALUES)]}), "太大（收纳袋、潜影盒那种）"
    assert Fits.fitsWire({"items": [{"slot": i} for i in range(50)]})


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
