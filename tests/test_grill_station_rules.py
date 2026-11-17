# -*- coding: utf-8 -*-
# runner: both
"""炉灶站点的纯规则（Shared/Rules/GrillStation.py）：站点的声明、什么能摆上去、烤位、一面多久、这一下右键开不开。
对应 Hands-On Delight 的 StoveStation（SCHEMA、opens）与 StoveCooking（canGrill、isDone）；gametest 的 anEggStaysOffTheGrill、
kitchenThingsOpenTheStove 在这里和 test_grill_station_logic.py 里。"""
from __future__ import print_function

import dgtest
import fdtest

Rules = fdtest.load("Shared.Rules.GrillStation")
Cooking = fdtest.load("Shared.Data.Cooking")
Schema = dgtest.load("Shared.Schema")           # 前置包的声明模块：站点的 schema 用它建（客户端经 ImportModule 拿同一个）


def _item(name="minecraft:beef", count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def testWhatOpensTheGrill():
    """StoveStation.opens：空手、能烤的、食物、刀和工具、碗和瓶开站；盖着东西、炉灶自己用得上的、别的东西不开。"""
    assert Rules.opens(None, "", False) and Rules.opens("minecraft:beef", "food", False)
    assert Rules.opens("minecraft:bread", "food", False) and Rules.opens("minecraft:carrot", "food", False), "食物都开，哪怕不能烤"
    assert Rules.opens("arris:iron_knife", "sword", False) and Rules.opens("minecraft:iron_axe", "axe", False)
    assert Rules.opens("minecraft:bowl", "", False) and Rules.opens("minecraft:glass_bottle", "", False)
    assert Rules.opens("minecraft:egg", "", False), "蛋有营火配方：开站，再被弹回手上（JE 的 opens 看 recipe 不看 NOT_ON_GRILL）"
    for held, kind in (("arris:cooking_pot", "block"), ("arris:skillet", "block"), ("minecraft:flint_and_steel", ""),
                       ("minecraft:fire_charge", ""), ("minecraft:iron_shovel", "shovel"), ("minecraft:water_bucket", "bucket"),
                       ("minecraft:stick", ""), ("minecraft:iron_sword", "sword")):
        assert not Rules.opens(held, kind, False), held
    assert not Rules.opens(None, "", True) and not Rules.opens("minecraft:beef", "food", True), "上面摆着锅：烤架是它的"


def testSixPlacesAndTheSameTableAsTheSkillet():
    assert Rules.PLACES == 6 and not hasattr(Rules, "slotCenter"), "烤位的位置在 StoveLayout（HoD 场景的像素）和 StoveFacing，不在站点规则里"
    assert Rules.canGrill("minecraft:beef") and Rules.grilledOf("minecraft:beef") == "minecraft:cooked_beef"
    assert "arris:stove" in Rules.STOVE_BLOCKS and "arris:stove_extinguish" in Rules.STOVE_BLOCKS, "点着的和熄着的炉灶都开站（HoD 的 opens 不看 LIT）"
    assert "minecraft:stone" not in Rules.STOVE_BLOCKS and "arris:stove_extinguish" not in Cooking.StoveList, "熄着的不进对外的 StoveList"
    Cooking.StoveList.append("addon:big_stove")
    try:
        assert "addon:big_stove" in Rules.STOVE_BLOCKS, "附属包追加的炉灶也开站：前置包拿着的容器每次按 StoveList 判"
    finally:
        Cooking.StoveList.remove("addon:big_stove")
    assert "addon:big_stove" not in Rules.STOVE_BLOCKS


def testAnEggRunsThroughTheBarsButTheFoodThatStaysIsGrilled():
    """anEggStaysOffTheGrill：站点的炉灶不收蛋（HoD 的 NOT_ON_GRILL），收别的能烤的；蛋仍然有营火配方（农夫乐事自己的右键能放）。"""
    assert not Rules.canGrill("minecraft:egg") and Rules.hasRecipe("minecraft:egg"), "蛋：有配方，但不收"
    for name in Cooking.CanCookedFoodDict:
        assert Rules.canGrill(name) == (name not in Rules.NOT_ON_GRILL), name
    assert not Rules.canGrill("minecraft:stick") and not Rules.canGrill(None) and not Rules.canGrill("")
    assert Rules.mayPlace(_item("minecraft:beef")) and not Rules.mayPlace(_item("minecraft:egg")) and not Rules.mayPlace(None)
    assert Rules.usable("minecraft:beef") and not Rules.usable("minecraft:egg") and not Rules.usable("minecraft:bread"), "托盘只列烤得了的"


def testAPieceIsDoneWhenThereIsNothingLeftToCook():
    assert Rules.isDone("minecraft:cooked_beef") and Rules.isDone("arris:cooked_bacon")
    assert not Rules.isDone("minecraft:beef") and not Rules.isDone("minecraft:egg") and not Rules.isDone(None)


def testTheSchemaHasOneGrillGroupOfSixKeptOneItemSlots():
    schema = Rules.buildSchema(Schema)
    group = schema.slotGroup(Rules.GROUP_GRILL)
    assert schema.groupNames == ["grill"] and group.size == 6 and group.rules.maxStack == 1
    assert not group.rules.returnOnClose, "关站不退：东西留在炉灶上继续烤"
    assert group.rules.canAccept(_item("minecraft:beef")) and not group.rules.canAccept(_item("minecraft:egg"))
    assert not group.rules.canAccept(_item("minecraft:stick"))
    assert schema.controlNames == [] and schema.outputs == []


def testASideIsAThirdOfTheStoveTime():
    assert abs(Rules.sideSeconds() - 10.0) < 1.0e-9, "30 / 1.5 / 2 = 10 秒（JE：营火 600 刻 / 1.5 / 2）"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
