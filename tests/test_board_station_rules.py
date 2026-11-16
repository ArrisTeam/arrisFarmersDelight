# -*- coding: utf-8 -*-
# runner: both
"""砧板站点的纯规则（Shared/Rules/BoardStation.py）：站点声明、什么是工具、托盘里哪些亮、Shift 点托盘放不放、插着的工具。

对应 HoD 的 CuttingBoardStation.SCHEMA、Cutting.isTool / canStick、BoardBehavior.usable / onInventoryShiftClick。
"""
from __future__ import print_function

import dgkit  # noqa: F401 - 先于内核的 import：它把 diegesisBp 放进 sys.path（站点声明要在前置包的 schema 上建一遍）
import fdtest
from arrisDiegesisScripts.Shared import Schema as KernelSchema

Rules = fdtest.load("Shared.Rules.BoardStation")
Data = fdtest.load("Shared.Data.Cutting")


def _typeOf(item):
    name = item["newItemName"]
    for word, kind in (("pickaxe", "pickaxe"), ("axe", "axe"), ("shovel", "shovel"), ("hoe", "hoe"), ("knife", "sword"), ("sword", "sword")):
        if word in name:
            return kind
    return "food"


ENV = Rules.Env(lambda name: name in Data.knifeList or name == "othermod:jade_knife", _typeOf)


def _item(name, count=1):
    return {"newItemName": name, "newAuxValue": 0, "count": count}


def testTheSchemaHasABoardSlotAndNineLayersThatKeepAndAcceptNothing():
    schema = Rules.buildSchema(KernelSchema)
    assert schema.groupNames == ["board", "layers"] and schema.controlNames == [] and schema.outputs == []
    assert [schema.groups[name].size for name in schema.groupNames] == [1, 9]
    assert all(not schema.groups[name].rules.returnOnClose for name in schema.groupNames), "东西留在板里，关站不退还"
    assert schema.groups["layers"].rules.maxStack == 16 and schema.groups["board"].rules.maxStack == 64
    for name in schema.groupNames:
        assert not schema.groups[name].rules.canAccept(_item("arris:cabbage")), "什么也不收：放的走自定义动作"
    assert Rules.MOST_LAYERS == 9 and Rules.BATCH == 16 and Rules.BOARD_MAX == 64


def testWhatTheKnifeCutsAndWhatIsATool():
    assert ENV.cuttable(_item("arris:cabbage")) and ENV.cuttable(_item("minecraft:beef")) and not ENV.cuttable(_item("minecraft:bread"))
    assert not ENV.cuttable(None) and not ENV.cuttable(_item("arris:cabbage", 0))
    for name in ("arris:iron_knife", "minecraft:iron_axe", "minecraft:diamond_pickaxe", "minecraft:wooden_shovel", "minecraft:golden_hoe",
                 "minecraft:shears", "othermod:jade_knife"):
        assert ENV.isToolItem(_item(name)), name
    assert not ENV.isToolItem(_item("arris:cabbage")) and not ENV.isToolItem(_item("minecraft:bowl"))
    assert ENV.isToolItem(_item("othermod:obsidian_axe")), "物品类型是斧的也是（配方要的是斧类）"


def testKnivesAndAxesAreToolsButAStickIsNotATool():
    assert ENV.isTool(_item("arris:iron_knife"), None) and ENV.isTool(_item("arris:iron_knife"), _item("arris:cabbage"))
    assert ENV.isTool(_item("minecraft:iron_axe"), _item("minecraft:oak_log"))
    assert ENV.goesIntoADish(_item("minecraft:stick")) and not ENV.isToolItem(_item("minecraft:stick")), "棍子不是哪个配方的工具"


def testTheTrayShowsWhatIsCutWhatGoesIntoADishAndTheTools():
    for name in ("arris:cabbage", "minecraft:beef", "arris:ham", "minecraft:bread", "arris:tomato", "minecraft:bowl", "arris:beef_patty",
                 "arris:iron_knife", "minecraft:iron_axe", "minecraft:shears", "minecraft:stick"):
        assert ENV.usable(_item(name)), name
    for name in ("minecraft:dirt", "minecraft:diamond", "arris:wooden_basket_x"):
        assert not ENV.usable(_item(name)), name
    assert not ENV.usable(None)


def testShiftClickInTheTrayPlacesFoodButNeverATool():
    assert ENV.shiftPlaces(_item("arris:cabbage", 5), None) and ENV.shiftPlaces(_item("minecraft:bread", 2), None), "能切的、能做菜的"
    assert not ENV.shiftPlaces(_item("arris:iron_knife"), None) and not ENV.shiftPlaces(_item("minecraft:iron_axe"), _item("minecraft:oak_log"))
    assert not ENV.shiftPlaces(_item("minecraft:dirt"), None), "既不能切也不进菜：不放"
    assert not ENV.shiftPlaces(None, None)


def testOnlyPlainToolsAreStuckInAndEnchantedOnesAreNot():
    assert ENV.canStick(_item("arris:iron_knife")) and ENV.canStick(_item("minecraft:iron_sword")) and ENV.canStick(_item("minecraft:iron_axe"))
    assert ENV.canStick(_item("minecraft:shears")) and ENV.canStick(_item("othermod:jade_knife"))
    assert not ENV.canStick(_item("arris:cabbage")) and not ENV.canStick(_item("minecraft:bowl")) and not ENV.canStick(None)
    enchanted = _item("arris:iron_knife")
    enchanted["enchantData"] = [(9, 1)]
    assert not ENV.canStick(enchanted)
    named = _item("arris:iron_knife")
    named["userData"] = {"x": 1}
    assert not ENV.canStick(named)


def testWhatIsNoWorkInHandGivesWayToFood():
    assert ENV.isDone(_item("arris:hamburger", 2)) and ENV.isDone(_item("minecraft:cobblestone")) and ENV.isDone(_item("arris:iron_knife"))
    assert not ENV.isDone(_item("arris:cabbage")) and not ENV.isDone(None)
    assert ENV.isCarving(_item("arris:iron_knife")) and not ENV.isCarving(_item("arris:hamburger"))


def testTheDishAMadeBeforeIsNotCarving():
    assert not ENV.isCarving(_item("arris:hamburger")) and ENV.isDone(_item("arris:hamburger"))


def testAnAddonCanTeachTheBoardANewToolAndTheCacheFollows():
    saved = dict(Data.CuttingBoardDict)
    try:
        assert not ENV.isToolItem(_item("x:rolling_pin"))
        Data.CuttingBoardDict[("x:dough_ball", 0)] = {"itemList": [{"itemName": "x:sheet", "count": 1}], "tool": ["x:rolling_pin"]}
        assert ENV.isToolItem(_item("x:rolling_pin")) and ENV.usable(_item("x:rolling_pin")) and ENV.usable(_item("x:dough_ball"))
    finally:
        Data.CuttingBoardDict.clear()
        Data.CuttingBoardDict.update(saved)
    assert not ENV.isToolItem(_item("x:rolling_pin"))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
