# -*- coding: utf-8 -*-
# runner: both
"""砧板按标签认原料、剪刀按物品类型认（Shared/Data/Cutting.py 的 CuttingTagDict、Shared/Rules/CuttingStation.recipeOf）。

- 原料是标签的配方放在 CuttingTagDict（键是标签名，不带 #；契约表里不放假物品名）：JE 的 cutting/tag_dough（#forge:dough -> 生意面）还原在这里；
- 查配方：CuttingBoardDict 里精确的先（农夫乐事自己的面团照旧是那一条），查不到再按标签名的顺序看标签（别的模组登记进 common:dough 的面团，假引擎口）；
- 经典玩法、站点（BoardStation.Env）、食谱书（"c:#标签名" 那一页、现在这一页）、JEI 都认；契约的白名单里有它（同一个对象）、表同步登记了它；
- 剪刀的 6 条拆解配方带 item_type "shears"：别的模组的剪刀（引擎的 itemType 是 shears）也拆得了皮甲，动作照旧是剪。
"""
from __future__ import print_function

import sys
import types

import fdtest

Cutting = fdtest.load("Shared.Data.Cutting")
Tags = fdtest.load("Shared.Data.Tags")
Station = fdtest.load("Shared.Rules.CuttingStation")
Board = fdtest.load("Shared.Rules.BoardStation")
Books = fdtest.load("Shared.Rules.StationBooks")
Legacy = fdtest.load("Api.LegacyModAttr")
Tables = fdtest.load("Shared.Rules.SyncTables")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
HandsOnCutting = fdtest.load("Shared.Rules.HandsOn.Cutting")
OTHER_DOUGH, OUR_DOUGH = ("other:dough", 0), ("arris:wheat_dough", 0)


class Port(object):
    """假的引擎口：别的模组把 other:dough 登记进了 common:dough。"""

    def ready(self):
        return True

    def itemsOf(self, tag):
        return ["arris:wheat_dough", "other:dough"] if tag == Tags.DOUGH else []

    def tagsOf(self, name, aux=0):
        return [Tags.DOUGH] if name == "other:dough" else []

    def blocksOf(self, tag):
        return []

    def blockTagsOf(self, name):
        return []


class Ported(object):
    def __enter__(self):
        ItemTags.setPort("server", Port())

    def __exit__(self, *exc):
        ItemTags.setPort("server", None)
        return False


def _item(kind):
    return {"newItemName": kind[0], "newAuxValue": kind[1], "count": 1}


def _jei():
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    game = type("Game", (object,), {"GetChinese": staticmethod(lambda key: key)})
    engine.compFactory = type("Factory", (object,), {"CreateGame": staticmethod(lambda target: game())})()
    engine.levelId = "level"
    engine.clientApi = type("ClientApi", (object,), {"ImportModule": staticmethod(lambda path: None)})
    sys.modules[engine.__name__] = engine
    return fdtest.load("Compat.Jei.CuttingBoard")


def testTheJavaDoughRecipeIsATagRecipe():
    assert Cutting.CuttingTagDict == {Tags.DOUGH: {"itemList": [{"itemName": "arris:raw_pasta", "count": 1}], "tool": Cutting.knifeList}}
    assert Cutting.CuttingTagDict[Tags.DOUGH]["tool"] is Cutting.knifeList, "工具引用刀列表本身：下游加的刀也能切"
    assert all(not key.startswith("#") for key in Cutting.CuttingTagDict)
    assert all(isinstance(key, tuple) and not key[0].startswith("#") for key in Cutting.CuttingBoardDict), "契约表里不放假物品名"


def testExactRecipesComeFirstThenTags():
    assert Station.recipeOf(OUR_DOUGH) is Cutting.CuttingBoardDict[OUR_DOUGH] and Station.recipeKeyOf(OUR_DOUGH) == OUR_DOUGH
    assert Station.recipeOf(OTHER_DOUGH) is None, "没有引擎口：静态词表里 common:dough 只有农夫乐事的面团"
    with Ported():
        assert Station.recipeOf(OTHER_DOUGH) is Cutting.CuttingTagDict[Tags.DOUGH] and Station.recipeKeyOf(OTHER_DOUGH) == Tags.DOUGH
        assert Station.recipeOf(("other:dough", 3)) is Cutting.CuttingTagDict[Tags.DOUGH], "标签不看 aux"
        assert Station.recipeOf(OUR_DOUGH) is Cutting.CuttingBoardDict[OUR_DOUGH], "自己的面团照旧是精确的那一条"
        env = Board.Env(lambda name: name.endswith("knife"), lambda item: "")
        assert env.cuttable(_item(OTHER_DOUGH)) and env.cutsWith(_item(OTHER_DOUGH), _item(("arris:iron_knife", 0)))
        assert not env.cutsWith(_item(OTHER_DOUGH), _item(("minecraft:iron_axe", 0)))
        assert Books.boardCurrent([], _item(OTHER_DOUGH)) == "c:#" + Tags.DOUGH
        assert Books.boardCurrent([], _item(OUR_DOUGH)) == "c:arris:wheat_dough:0"
        page = next(page for page in Books.boardPages() if page["key"] == "c:#" + Tags.DOUGH)
        assert page["ways"][0][0] == [OUR_DOUGH, OTHER_DOUGH] and page["item"]["newItemName"] == "arris:raw_pasta" and page["kind"] == "knife"
    assert Station.recipeOf(None) is None and Station.recipeOf(("", 0)) is None


def testTheContractAndTheSyncKnowTheTable():
    assert Legacy.ArrisFarmersDelightObtain("CuttingTagDict") is Cutting.CuttingTagDict
    assert Tables.BY_NAME["CuttingTagDict"] == (Tables.MAP, Cutting.CuttingTagDict)
    entry = {"itemList": [{"itemName": "test:noodles", "count": 2}], "tool": Cutting.knifeList}
    try:
        assert Legacy.ArrisFarmersDelightInterface("CuttingTagDict", {"common:test_dough": entry}) is Cutting.CuttingTagDict
        assert Board._tools()[0] >= frozenset(Cutting.knifeList)
    finally:
        Cutting.CuttingTagDict.pop("common:test_dough", None)


def testShearsRecipesTakeAnyShears():
    recipes = [recipe for recipe in Cutting.CuttingBoardDict.values() if recipe["tool"] is Cutting.shearsList]
    assert len(recipes) == 6 and all(recipe["item_type"] == "shears" for recipe in recipes)
    leather = Cutting.CuttingBoardDict[("minecraft:leather_helmet", 0)]
    assert Station.fitsTool("other:shears", "shears", leather, lambda name: False)
    assert Station.fitsTool("minecraft:shears", "shears", leather, lambda name: False)
    assert not Station.fitsTool("other:knife", "sword", leather, lambda name: True), "刀拆不了皮甲（不是刀切的配方）"
    assert not Station.isKnifeRecipe(leather) and Station.strokeOf(leather) == HandsOnCutting.TOOL_SNIP
    assert "shears" in Board._tools()[1]


def testJeiListsTheTagRecipeUnderEveryMember():
    jei = _jei()
    with Ported():
        records = dict((tuple(inputs), recipe) for inputs, recipe in jei.records())
    assert records[(OUR_DOUGH, OTHER_DOUGH)] is Cutting.CuttingTagDict[Tags.DOUGH]
    assert records[(OUR_DOUGH,)] is Cutting.CuttingBoardDict[OUR_DOUGH]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
