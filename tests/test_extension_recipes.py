# -*- coding: utf-8 -*-
# runner: both
"""门面上的配方接口 ext.recipes（Api/ExtensionApi/Recipes.py、RecipeBuilder.py、RecipeTables.py、RecipeIds.py，Shared/Rules/RecipeJson.py）。

- JSON 就是 JE 农夫乐事的写法：JE 的标签名换成 common: 名，格式不对说哪里不对；Builder 写出来的是同一份 JSON、走同一条路；
- 厨锅：带标签格的配方登记进表（Id、Slots、Recipe 快照），别的模组的料配得上（假引擎口），按 ID 查得到 JE 写法、原样交回去就是覆盖（下标不变），
  删了打墓碑、查不到也配不上，再登记就回来；
- ID：写法不对、legacy:、新加的 farmersdelight: 都不收，覆盖主包已有的可以；旧接口追加的配方有派生的 legacy: ID（同一成品加 _2），能查能删；
- 砧板、营火：进 CuttingBoardDict / CuttingTagDict / CanCookedFoodDict（刀表是那个列表本身），原料被别的 ID 占着时拒绝、用它的 ID 才能覆盖，删了是真删；
- 客户端：登记类的返回 server_only，查询、matchCooking 照常；onRecipesChanged / syncToClients：交进来的同步函数被调，处理函数出错只打一次、不耽误别的。
"""
from __future__ import print_function

import io
import json
import os
import sys

import fdtest

Facade = fdtest.load("Api.ExtensionApi.Facade")
Recipes = fdtest.load("Api.ExtensionApi.Recipes")
Tables = fdtest.load("Api.ExtensionApi.RecipeTables")
RecipeJson = fdtest.load("Shared.Rules.RecipeJson")
Legacy = fdtest.load("Api.LegacyModAttr")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Pot = fdtest.load("Shared.Data.CookingPotRecipes")
Cutting = fdtest.load("Shared.Data.Cutting")
Cooking = fdtest.load("Shared.Data.Cooking")
CookingPot = fdtest.load("Shared.Rules.CookingPot")
JE_COOKING = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "generated", "resources", "data", "farmersdelight", "recipes", "cooking")
SERVER, CLIENT = Facade.getExtensionApi("server").recipes, Facade.getExtensionApi("client").recipes


class Port(object):
    """假的引擎口：别的模组把 other:steak 登记进了 common:raw_beef。"""

    def ready(self):
        return True

    def itemsOf(self, tag):
        return ["minecraft:beef", "arris:minced_beef", "other:steak"] if tag == "common:raw_beef" else []

    def tagsOf(self, name, aux=0):
        return ["common:raw_beef"] if name == "other:steak" else []

    def blocksOf(self, tag):
        return []

    def blockTagsOf(self, name):
        return []


class Sandbox(object):
    """进去时记下几张表和登记过的 ID，装上假引擎口；出来时原样放回（行对象就地放回内容）。"""

    def __enter__(self):
        self.rows = [(row, dict(row)) for row in Pot.CookingPotRecipeList]
        self.dicts = [(table, dict(table)) for table in (Cutting.CuttingBoardDict, Cutting.CuttingTagDict, Cooking.CanCookedFoodDict)]
        self.ids = (dict(Tables._ids["cutting"]), dict(Tables._ids["campfire_cooking"]), dict(Tables._keys["cutting"]), dict(Tables._keys["campfire_cooking"]))
        ItemTags.setPort("server", Port())
        return self

    def __exit__(self, *exc):
        ItemTags.setPort("server", None)
        Pot.CookingPotRecipeList[:] = [row for row, _ in self.rows]
        for row, fields in self.rows:
            row.clear()
            row.update(fields)
        for table, saved in self.dicts:
            table.clear()
            table.update(saved)
        for store, saved in zip((Tables._ids["cutting"], Tables._ids["campfire_cooking"], Tables._keys["cutting"], Tables._keys["campfire_cooking"]), self.ids):
            store.clear()
            store.update(saved)
        CookingPot.rebuildIndex()
        Recipes._handlers[:] = []
        Recipes._services.clear()
        return False


def _stew():
    return (SERVER.createBuilder("mymod:cooking/steak_stew", "farmersdelight:cooking").ingredient("#common:raw_beef").ingredient("arris:onion", ("minecraft:dye", 4))
            .output("mymod:steak_stew", 2).container("minecraft:bowl").cookingTime(100).experience(0.5).text("Steak stew"))


def testTheJsonIsTheJavaFormatWithJavaTagNamesMapped():
    data = {"type": "farmersdelight:cooking", "ingredients": [{"tag": "forge:raw_beef"}, [{"item": "minecraft:carrot"}, {"tag": "forge:eggs"}]],
            "result": {"item": "mymod:stew", "count": 2}, "container": {"item": "minecraft:bowl"}, "cookingtime": 300}
    spec, problem = RecipeJson.parse(data)
    assert problem is None, problem
    assert spec["slots"] == [["#common:raw_beef"], [("minecraft:carrot", 0), "#minecraft:egg"]] and spec["count"] == 2
    assert spec["cookingTime"] == 300 and spec["experience"] == 0.0 and spec["container"] == ("minecraft:bowl", 0), "JE 没写经验就是 0"
    bad = [({"type": "x:y"}, "type"), (dict(data, ingredients=[]), "ingredients"), (dict(data, ingredients=[{"item": "carrot"}]), "ns:name"),
           (dict(data, ingredients=[{"item": "a:b"}] * 7), "ingredients"), (dict(data, result=None), "result"),
           ({"type": "farmersdelight:cutting", "ingredients": [{"item": "a:b"}], "result": [{"item": "a:c"}]}, "tool"),
           ({"type": "minecraft:campfire_cooking", "ingredient": {"tag": "forge:raw_beef"}, "result": "a:c"}, "营火烹饪只认物品"),
           ("not a dict", "JSON 对象")]
    for broken, word in bad:
        spec, problem = RecipeJson.parse(broken)
        assert spec is None and word in problem, (broken, problem)
    cut, problem = RecipeJson.parse({"type": "farmersdelight:cutting", "ingredients": [{"tag": "forge:dough"}], "result": [{"item": "a:noodle", "count": 2, "chance": 0.5}],
                                     "tool": [{"type": "farmersdelight:tool_action", "action": "knife_dig"}, {"tag": "forge:tools/knives"}]})
    assert problem is None and cut == {"type": "cutting", "input": "#common:dough", "tool": "knife", "results": [{"itemName": "a:noodle", "count": 2, "chance": 0.5}]}
    if os.path.isdir(JE_COOKING):
        with io.open(os.path.join(JE_COOKING, "beef_stew.json"), encoding="utf-8") as handle:
            spec, problem = RecipeJson.parse(json.load(handle))
        assert problem is None and spec["slots"] == [["#common:raw_beef"], ["#common:carrot"], ["#common:potato"]], (problem, spec)


def testAMissingContainerIsTheResultsCraftingRemainderLikeJava():
    """JE 的 CookingPotRecipe：没写 container 就取成品的合成剩余物（Shared/Data/Remainders.CRAFT 就是那个属性）。.refs 在场时 28 个 JE 文件
    逐个核：成品换成农夫乐事自己那一行的，推出来（或写明）的容器正好是那一行的 Vessel（24 个没写的推出碗 / 玻璃瓶 / 不要，4 个写明的照写）。"""
    base = {"type": "farmersdelight:cooking", "ingredients": [{"tag": "forge:raw_beef"}]}
    for result, vessel in (("arris:cookbeef_stew", ("minecraft:bowl", 0)), ("arris:hot_cocoa", ("minecraft:glass_bottle", 0)),
                           ("arris:dumplings", None), ("mymod:stew", None)):
        spec, problem = RecipeJson.parse(dict(base, result={"item": result}))
        assert problem is None and spec["container"] == vessel, (result, spec["container"])
    spec, _problem = RecipeJson.parse(dict(base, result={"item": "arris:cookbeef_stew"}, container={"item": "mymod:clay_bowl"}))
    assert spec["container"] == ("mymod:clay_bowl", 0), "写了就照写"
    if not os.path.isdir(JE_COOKING):
        return
    checked = 0
    for name in sorted(os.listdir(JE_COOKING)):
        with io.open(os.path.join(JE_COOKING, name), encoding="utf-8") as handle:
            data = json.load(handle)
        row = next(row for row in Pot.CookingPotRecipeList if row.get("Id") == "farmersdelight:cooking/" + name[:-len(".json")])
        spec, problem = RecipeJson.parse(dict(data, result={"item": row["CookResult"][0]}))
        assert problem is None and spec["container"] == (tuple(row["Vessel"]) if row.get("Vessel") else None), (name, spec["container"])
        checked += 1
    assert checked == 28, checked


def testACookingRecipeWithATagSlotWorksEverywhere():
    with Sandbox():
        builder = _stew()
        assert builder.toJson()["ingredients"] == [{"tag": "common:raw_beef"}, [{"item": "arris:onion"}, {"item": "minecraft:dye", "data": 4}]]
        assert builder.register() == {"ok": True, "error": None, "id": "mymod:cooking/steak_stew"}
        row = Pot.CookingPotRecipeList[-1]
        assert row["Slots"] == [["#common:raw_beef"], ["arris:onion", ("minecraft:dye", 4)]] and row["CookTime"] == 5.0 and row["Experience"] == 0.5
        assert row["Recipe"][:2] == [[("minecraft:beef", 0), ("arris:onion", 0)], [("minecraft:beef", 0), ("minecraft:dye", 4)]], "旧读者看的写法快照"
        matched = SERVER.matchCooking(["other:steak", ("minecraft:dye", 4)])
        assert matched["id"] == "mymod:cooking/steak_stew" and matched["result"]["count"] == 2 and matched["container"] == ("minecraft:bowl", 0)
        view = SERVER.getRecipeById("mymod:cooking/steak_stew")
        assert view["type"] == "farmersdelight:cooking" and view["cookingtime"] == 100 and view["text"] == "Steak stew"
        index = len(Pot.CookingPotRecipeList) - 1
        assert SERVER.registerFromJson(json.dumps(dict(view, cookingtime=40)))["ok"] and len(Pot.CookingPotRecipeList) == index + 1, "同 ID：就地覆盖"
        assert Pot.CookingPotRecipeList[index] is row and row["CookTime"] == 2.0
        assert SERVER.removeRecipe("mymod:cooking/steak_stew")["ok"] and row["Disabled"] is True
        assert SERVER.matchCooking(["other:steak", ("minecraft:dye", 4)]) is None and SERVER.getRecipeById("mymod:cooking/steak_stew") is None
        assert SERVER.removeRecipe("mymod:cooking/steak_stew")["error"] == "not_found"
        assert _stew().register()["ok"] and "Disabled" not in row and SERVER.matchCooking(["minecraft:beef", "arris:onion"])["id"] == "mymod:cooking/steak_stew"


def testIdRules():
    with Sandbox():
        stew = SERVER.getRecipeById("farmersdelight:cooking/beef_stew")
        assert stew["ingredients"] == [{"tag": "common:raw_beef"}, {"tag": "common:carrot"}, {"tag": "common:potato"}] and stew["cookingtime"] == 200
        for recipeId, error in (("bad id", "invalid_id"), ("nocolon", "invalid_id"), ("legacy:cooking/x", "reserved_namespace"),
                                ("farmersdelight:cooking/new_dish", "reserved_namespace")):
            assert SERVER.registerFromJson(stew, recipeId)["error"] == error, recipeId
        index = [row.get("Id") for row in Pot.CookingPotRecipeList].index("farmersdelight:cooking/beef_stew")
        assert SERVER.registerFromJson(dict(stew, result={"item": "mymod:better_stew"}))["ok"], "覆盖主包已有的可以"
        assert Pot.CookingPotRecipeList[index]["CookResult"] == ("mymod:better_stew", 0)
        assert SERVER.registerFromJson(dict(stew, type="farmersdelight:cutting"))["error"] in ("invalid_recipe", "type_mismatch")
        Legacy.ArrisFarmersDelightInterface("CookingPotRecipeList", [
            {"Recipe": [[("test:a", 0)]], "CookResult": ("test:soup", 0), "PushItem": [], "text": "1"},
            {"Recipe": [[("test:b", 0)]], "CookResult": ("test:soup", 0), "PushItem": [], "text": "2"}])
        ids = [recipe["id"] for recipe in SERVER.getRecipesOfType("cooking")]
        assert ids[-2:] == ["legacy:cooking/test/soup", "legacy:cooking/test/soup_2"] and "farmersdelight:cooking/apple_cider" in ids
        assert SERVER.removeRecipe("legacy:cooking/test/soup_2")["ok"] and SERVER.matchCooking(["test:b"]) is None
        assert SERVER.registerFromJson(stew, "legacy:cooking/test/soup")["error"] == "reserved_namespace", "派生的 ID 只读"


def testCuttingAndCampfireRecipes():
    with Sandbox():
        cut = SERVER.createBuilder("mymod:cutting/tofu", "cutting").ingredient("mymod:tofu").output("mymod:tofu_cube", 4).output("minecraft:bone_meal", 1, 0.5).tool("knife")
        assert cut.register()["ok"]
        entry = Cutting.CuttingBoardDict[("mymod:tofu", 0)]
        assert entry["tool"] is Cutting.knifeList and entry["itemList"] == [{"itemName": "mymod:tofu_cube", "count": 4}, {"itemName": "minecraft:bone_meal", "count": 1, "chance": 0.5}]
        tag = SERVER.createBuilder("mymod:cutting/any_log", "cutting").ingredient("#common:test_log").output("minecraft:stick", 2).tool("axe").register()
        assert tag["ok"] and Cutting.CuttingTagDict["common:test_log"]["item_type"] == "axe" and Cutting.CuttingTagDict["common:test_log"]["tool"] is Cutting.axeList
        taken = SERVER.createBuilder("mymod:cutting/cabbage", "cutting").ingredient("arris:cabbage").output("mymod:leaf").tool("knife").register()
        assert taken["error"] == "input_taken" and taken["by"] == "farmersdelight:cutting/arris/cabbage"
        assert SERVER.createBuilder("farmersdelight:cutting/arris/cabbage", "cutting").ingredient("arris:cabbage").output("mymod:leaf").tool("knife").register()["ok"]
        assert Cutting.CuttingBoardDict[("arris:cabbage", 0)]["itemList"] == [{"itemName": "mymod:leaf", "count": 1}]
        assert SERVER.getRecipeById("farmersdelight:cutting/tag_dough")["ingredients"] == [{"tag": "common:dough"}]
        assert SERVER.removeRecipe("mymod:cutting/tofu")["ok"] and ("mymod:tofu", 0) not in Cutting.CuttingBoardDict
        fry = SERVER.createBuilder("mymod:campfire_cooking/tofu", "minecraft:campfire_cooking").ingredient("mymod:tofu").output("mymod:fried_tofu").register()
        assert fry["ok"] and Cooking.CanCookedFoodDict["mymod:tofu"] == "mymod:fried_tofu"
        assert SERVER.getRecipeById("mymod:campfire_cooking/tofu") == {"id": "mymod:campfire_cooking/tofu", "type": "minecraft:campfire_cooking",
                                                                      "ingredient": {"item": "mymod:tofu"}, "result": "mymod:fried_tofu"}
        assert SERVER.createBuilder("mymod:campfire_cooking/beef", "campfire_cooking").ingredient("minecraft:beef").output("x:y").register()["error"] == "input_taken"
        assert SERVER.removeRecipe("mymod:campfire_cooking/tofu")["ok"] and "mymod:tofu" not in Cooking.CanCookedFoodDict
        assert SERVER.getRecipeById("farmersdelight:campfire_cooking/minecraft/beef")["result"] == Cooking.CanCookedFoodDict["minecraft:beef"]


def testTheClientSeesTheSameCuttingIdsWhileCampfireOnesAreDerived():
    """砧板登记用的 ID 写在条目里（随表同步）：客户端没有服务端那份登记记录，也按同一个 ID 查到；营火的值是物品名、放不下 ID，客户端查到的是派生的。"""
    with Sandbox():
        assert SERVER.createBuilder("mymod:cutting/tofu", "cutting").ingredient("mymod:tofu").output("mymod:tofu_cube", 4).tool("knife").register()["ok"]
        assert SERVER.createBuilder("mymod:campfire_cooking/tofu", "campfire_cooking").ingredient("mymod:tofu").output("mymod:fried_tofu").register()["ok"]
        assert Cutting.CuttingBoardDict[("mymod:tofu", 0)]["id"] == "mymod:cutting/tofu"
        for store in (Tables._ids["cutting"], Tables._ids["campfire_cooking"], Tables._keys["cutting"], Tables._keys["campfire_cooking"]):
            store.clear()                       # 客户端：只有表同步过来的表，没有服务端的登记记录
        assert CLIENT.getRecipeById("mymod:cutting/tofu")["result"] == [{"item": "mymod:tofu_cube", "count": 4}]
        assert "mymod:cutting/tofu" in [recipe["id"] for recipe in CLIENT.getRecipesOfType("cutting")]
        assert CLIENT.getRecipeById("mymod:campfire_cooking/tofu") is None
        assert CLIENT.getRecipeById("legacy:campfire_cooking/mymod/tofu")["result"] == "mymod:fried_tofu"
        Cutting.CuttingBoardDict[("mymod:tofu", 0)] = {"itemList": [{"itemName": "x:y", "count": 1}], "tool": Cutting.knifeList}
        assert SERVER.getRecipeById("mymod:cutting/tofu") is None and SERVER.getRecipeById("legacy:cutting/mymod/tofu"), \
            "旧接口把条目整个换掉了：那就是一条旧接口的配方"


def testTheLegacyAddSkipsRemovedDishes():
    """T 复核时复现的：旧接口的 AddCookingPotRecipe 往被删的菜（墓碑）里加写法，返回成功却永远不生效。现在跳过不是活配方的行，
    同成品后面有活的就加到它上面，没有活的返回 False（和原来"没有这道菜"一样）。"""
    with Sandbox():
        stew = next(row for row in Pot.CookingPotRecipeList if row.get("Id") == "farmersdelight:cooking/beef_stew")
        ways = list(stew["Recipe"])
        assert SERVER.removeRecipe("farmersdelight:cooking/beef_stew")["ok"]
        assert Legacy.AddCookingPotRecipe("arris:cookbeef_stew", [("minecraft:dirt", 0)]) is False and stew["Recipe"] == ways
        assert SERVER.createBuilder("mymod:cooking/beef_again", "cooking").ingredient("minecraft:cookie").output("arris:cookbeef_stew").register()["ok"]
        again = Pot.CookingPotRecipeList[-1]
        assert Legacy.AddCookingPotRecipe("arris:cookbeef_stew", [("minecraft:dirt", 0)]) is again["Recipe"] and again["Recipe"][-1] == [("minecraft:dirt", 0)]
        assert stew["Recipe"] == ways and CookingPot.matchRecipe([{"newItemName": "minecraft:dirt", "newAuxValue": 0, "count": 1}])[0]["newItemName"] \
            == "arris:cookbeef_stew"


def testTheClientReadsButDoesNotRegister():
    with Sandbox():
        assert _stew().register()["ok"]
        client = (CLIENT.createBuilder("mymod:cooking/x", "cooking").ingredient("minecraft:apple").output("mymod:x").register())
        assert client == {"ok": False, "error": "server_only", "id": "mymod:cooking/x"}
        assert CLIENT.removeRecipe("mymod:cooking/steak_stew")["error"] == "server_only" and CLIENT.syncToClients()["error"] == "server_only"
        assert CLIENT.onRecipesChanged(lambda event: None)["error"] == "server_only"
        assert CLIENT.getRecipeById("mymod:cooking/steak_stew")["id"] == "mymod:cooking/steak_stew" and CLIENT.matchCooking(["other:steak", "arris:onion"])


class _Capture(object):
    def __init__(self):
        self.parts, self.saved = [], None

    def write(self, text):
        self.parts.append(text if isinstance(text, str) else text.encode("utf-8"))

    def flush(self):
        pass

    def __enter__(self):
        self.saved = (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = self
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self.saved
        return False


def testSyncToClientsCallsTheSyncAndTheHandlers():
    with Sandbox():
        synced, seen = [], []
        Recipes.provide(syncNow=lambda: synced.append(1))

        def broken(event):
            raise KeyError("their handler")

        assert SERVER.onRecipesChanged(broken)["ok"] and SERVER.onRecipesChanged(lambda event: seen.append((event.types, event.recipeIds)))["ok"]
        assert SERVER.onRecipesChanged("nope")["error"] == "invalid_handler"
        with _Capture() as out:
            assert SERVER.syncToClients("farmersdelight:cooking", "mymod:cooking/x")["ok"]
            assert SERVER.syncToClients()["ok"]
        assert synced == [1, 1] and seen == [(["cooking"], ["mymod:cooking/x"]), (None, None)]
        assert "".join(out.parts).count("Traceback") == 1, "出错的处理函数只打一次调用栈"
        assert SERVER.syncToClients(["fishing"])["error"] == "invalid_recipe_types"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
