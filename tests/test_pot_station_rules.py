# -*- coding: utf-8 -*-
# runner: both
"""厨锅站点的纯规则（Shared/Rules/PotStation.py + Shared/Data/PotSunk.py）：站点声明、放料规则、托盘亮不亮、下锅就沉的料、
盛菜容器挑哪一格、份数、提示文字。选菜与摆料见 test_pot_layout.py。"""
from __future__ import print_function

import dgkit  # noqa: F401 - 先于内核的 import：它把 diegesisBp 放进 sys.path（站点声明要在前置包的 schema 上建一遍）
import fdtest
from arrisDiegesisScripts.Shared import Schema as KernelSchema

Rules = fdtest.load("Shared.Rules.PotStation")
PotCooking = fdtest.load("Shared.Rules.HandsOn.PotCooking")
CookingPot = fdtest.load("Shared.Rules.CookingPot")
PotSunk = fdtest.load("Shared.Data.PotSunk")

TOMATO = ("arris:tomato", 0)
ONION = ("arris:onion", 0)
BOWL = ("minecraft:bowl", 0)
BOTTLE = ("minecraft:glass_bottle", 0)


def _item(key, count=1):
    return {"newItemName": key[0], "newAuxValue": key[1], "count": count}


def _cells(*stacks):
    cells = [_item(key, count) for key, count in stacks]
    return cells + [None] * (Rules.INPUT_SLOTS - len(cells))


def testTheSchemaHasTheIngredientsTheServedSlotAndTheLockedControls():
    schema = Rules.buildSchema(KernelSchema)
    assert schema.groupNames == ["ingredients", "served"]
    assert [schema.groups[name].size for name in schema.groupNames] == [6, 1]
    assert all(not schema.groups[name].rules.returnOnClose for name in schema.groupNames), "两组都留在锅里，关站不退还"
    assert schema.controlNames == list(Rules.CONTROLS) == ["progress", "heated", "stirring", "spoon_x", "spoon_z", "stars"]
    assert all(schema.controls[name].isLocked for name in schema.controlNames), "只有服务端按锅的状态写"
    steps = dict((name, (schema.controls[name].minValue, schema.controls[name].maxValue, schema.controls[name].steps))
                 for name in schema.controlNames)
    assert steps["progress"] == (0.0, 1.0, 100) and steps["heated"] == (0.0, 1.0, 1) and steps["stirring"] == (0.0, 1.0, 1)
    assert steps["spoon_x"] == steps["spoon_z"] == (-1.0, 1.0, 64) and steps["stars"] == (0.0, 3.0, 60)
    assert schema.outputs == []


def testTheSchemaAcceptsEverythingButDishesIntoTheIngredientsAndNothingIntoServed():
    schema = Rules.buildSchema(KernelSchema)
    ingredients, served = schema.groups["ingredients"].rules, schema.groups["served"].rules
    assert ingredients.canAccept(_item(TOMATO)) and ingredients.canAccept(_item(("minecraft:dirt", 0)))
    assert not ingredients.canAccept(_item(BOWL)) and not ingredients.canAccept(_item(BOTTLE)), "盛菜的碗和瓶不下锅"
    assert not served.canAccept(_item(TOMATO)) and not served.canAccept(_item(BOWL))
    assert ingredients.maxStack == 64 and served.maxStack == 64


def testServingsAreTheSmallestFilledSlot():
    assert Rules.servingsLeft(_cells((TOMATO, 5), (ONION, 3))) == 3
    assert Rules.servingsLeft([None, {}, {"newItemName": "arris:tomato", "count": 0}]) == 0
    assert Rules.foodCount(_cells((TOMATO, 5), (ONION, 3))) == 8


def testAnythingButAServingContainerGoesInAndWhatMakesNothingJustLies():
    assert Rules.mayPlace(_item(TOMATO)) and Rules.mayPlace(_item(("minecraft:dirt", 0))), "凑不成菜的东西也收"
    assert not Rules.mayPlace(_item(BOWL)) and not Rules.mayPlace(_item(BOTTLE)), "某道菜盛菜用的容器不收"
    assert not Rules.mayPlace({}) and not Rules.mayPlace(None) and not Rules.mayPlace(_item(TOMATO, 0))
    pumpkin = ("minecraft:pumpkin", 0)
    assert CookingPot.isVessel("minecraft:pumpkin") and not Rules.mayPlace(_item(pumpkin)), "填馅南瓜盛菜用南瓜"


def testTheTrayLightsIngredientsAndServingContainersOnly():
    assert Rules.usable(TOMATO) and Rules.usable(BOWL) and Rules.usable(BOTTLE)
    assert not Rules.usable(("minecraft:dirt", 0)) and not Rules.usable(None)
    assert Rules.isIngredient(TOMATO) and not Rules.isIngredient(BOWL), "碗是盛菜的，不是料"


def testWhatPouredCrackedOrDissolvedSinksAndWhatFloatsDoesNot():
    for key in (("minecraft:milk_bucket", 0), ("arris:milk_bottle", 0), ("minecraft:egg", 0), ("minecraft:sugar", 0),
                ("minecraft:cocoa_beans", 0), ("minecraft:honey_bottle", 0), ("arris:tomato_sauce", 0)):
        assert Rules.isSunk(key), key
    for key in (TOMATO, ONION, ("minecraft:carrot", 0), ("minecraft:beef", 0), BOWL):
        assert not Rules.isSunk(key), key
    cells = _cells((("minecraft:milk_bucket", 0), 1), (TOMATO, 3), (("minecraft:egg", 0), 2))
    assert Rules.sunkSlots(cells) == [0, 2]
    assert Rules.sunkSlots(_cells()) == []
    assert all(isinstance(kind, tuple) and len(kind) == 2 for kind in PotSunk.POURED + PotSunk.CRACKED + PotSunk.DISSOLVES)
    assert PotSunk.SUNK == frozenset(PotSunk.POURED + PotSunk.CRACKED + PotSunk.DISSOLVES)


def testEverySunkItemOfTheTagsThatTheRecipesUseIsKnownToTheTable():
    # 配方里用到的"倒进去 / 打进去 / 化掉"的料（奶、蛋、糖、可可豆、墨囊、骨粉、蜂蜜…）都在表里：不然它们会浮在汤面上
    used = set(key for recipe in CookingPot.CookingPotRecipeList for variant in recipe["Recipe"] for key in variant)
    for key in (("minecraft:milk_bucket", 0), ("arris:milk_bottle", 0), ("minecraft:egg", 0), ("minecraft:sugar", 0),
                ("minecraft:cocoa_beans", 0), ("minecraft:ink_sac", 0), ("minecraft:bone_meal", 0)):
        assert key in used and Rules.isSunk(key), key


def testTheContainerComesFromTheSelectedHotbarSlotFirstThenFromTheStartOfTheInventory():
    window = [None] * 36
    window[4] = _item(BOWL, 3)
    window[20] = _item(BOWL, 2)
    window[1] = _item(("minecraft:glass_bottle", 0), 5)
    assert Rules.containerSlot(window, 4, "minecraft:bowl") == 4
    assert Rules.containerSlot(window, 6, "minecraft:bowl") == 4, "选中的格子里不是碗：从头找"
    assert Rules.containerSlot(window, 1, "minecraft:bowl") == 4
    window[4] = None
    assert Rules.containerSlot(window, 4, "minecraft:bowl") == 20
    assert Rules.containerSlot(window, 20, "minecraft:bowl") == 20, "选中的槽号只认快捷栏（0-8），别的当没选"
    assert Rules.containerSlot(window, -1, "minecraft:glass_bottle") == 1
    assert Rules.containerSlot(window, 0, "minecraft:bucket") == -1
    window[20] = _item(BOWL, 0)
    assert Rules.containerSlot(window, 0, "minecraft:bowl") == -1, "数量是 0 的不算"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
