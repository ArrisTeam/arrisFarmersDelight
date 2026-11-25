# -*- coding: utf-8 -*-
# runner: both
"""py2 里引擎给的整数可能是 long（Shared/Rules/TableWire.INT_TYPES / isInt 就是为它设的）：厨锅配方的 aux、格子里的 (物品名, aux) 选项、
书页的键、配方 JSON 的数、登记口的 aux 都要认 long，bool 不算。旧的索引按 (名字, aux) 元组查表，long 和 int 相等、哈希一样，本来就收；
逐格配对之后有几处写成了 isinstance(x, int)，py2 的 long 会让一行被当成坏行悄悄跳过。py3 里 LONG 就是 int，这些断言照样跑一遍。
"""
from __future__ import print_function

import fdtest

LONG = type(2 ** 64)        # py2：long；py3：int
Pot = fdtest.load("Shared.Data.CookingPotRecipes")
CookingPot = fdtest.load("Shared.Rules.CookingPot")
Table = fdtest.load("Shared.Rules.PotRecipeTable")
PotSlots = fdtest.load("Shared.Rules.PotSlots")
Books = fdtest.load("Shared.Rules.StationBooks")
Book = fdtest.load("Shared.Rules.CookingPotBook")
RecipeJson = fdtest.load("Shared.Rules.RecipeJson")
Farming = fdtest.load("Shared.Data.Farming")
SERVER = fdtest.load("Api.ExtensionApi.Facade").getExtensionApi("server")


def _item(name, aux=0):
    return {"newItemName": name, "newAuxValue": aux, "count": 1}


def testAPotRecipeWithLongAuxIsStillARecipe():
    ways = {"Recipe": [[("test:long_a", LONG(0)), ("minecraft:blue_dye", LONG(4))]], "CookResult": ("test:long_dish", LONG(0)),
            "PushItem": [], "text": "x"}
    slots = {"Id": "test:cooking/long_slots", "Slots": [[("test:long_b", LONG(2))], ["test:long_c"]], "Recipe": [],
             "CookResult": ("test:long_slots", LONG(0)), "PushItem": [], "text": "y"}
    Pot.CookingPotRecipeList.extend([ways, slots])
    CookingPot.rebuildIndex()
    try:
        assert Table.isPair(("x:y", LONG(3))) and not Table.isPair(("x:y", True)) and not Table.isPair(("x:y", 1.0))
        assert CookingPot.isLive(ways) and CookingPot.isLive(slots) and PotSlots.slotsProblem(slots["Slots"]) is None
        assert CookingPot.matchRecipe([_item("test:long_a"), _item("minecraft:blue_dye", LONG(4))])[0]["newItemName"] == "test:long_dish"
        assert CookingPot.matchRecipe([_item("test:long_b", 2), _item("test:long_c")])[0]["newItemName"] == "test:long_slots"
        assert Books.potRecipe(LONG(len(Pot.CookingPotRecipeList) - 1)) is slots and Books.potRecipe(True) is None
        assert Book._pair(("x:y", LONG(1))) and not Book._pair(("x:y", True))
    finally:
        del Pot.CookingPotRecipeList[-2:]
        CookingPot.rebuildIndex()


def testJsonNumbersAndTheRegistryAuxMayBeLong():
    spec, problem = RecipeJson.parse({"type": "farmersdelight:cooking", "ingredients": [{"item": "a:b", "data": LONG(3)}],
                                      "result": {"item": "a:c", "count": LONG(2)}, "cookingtime": LONG(200), "experience": LONG(1)})
    assert problem is None and spec["slots"] == [[("a:b", 3)]] and spec["count"] == 2 and spec["cookingTime"] == 200, (spec, problem)
    saved = dict(Farming.ComposterItemDict)
    try:
        assert SERVER.registerCompostable("mymod:leaf", LONG(30), LONG(1))["ok"] and Farming.ComposterItemDict[("mymod:leaf", 1)] == 30
        assert SERVER.registerCompostable("mymod:leaf", 30, True)["error"] == "invalid_name", "bool 不算整数"
    finally:
        Farming.ComposterItemDict.clear()
        Farming.ComposterItemDict.update(saved)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
