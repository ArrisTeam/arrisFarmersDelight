# -*- coding: utf-8 -*-
# runner: both
"""厨锅配方的格子（Slots）给读表的各处用上：标签格（别的模组的料，假引擎口）、只有格子没有写法的配方、墓碑。

- 经典界面（CookingPotBook）：详情的食材格一格一格轮换自己的选项、格子不收的旧写法另占一帧；"添加食材"按锅里和背包里有的料把格子具体化成写法；
  墓碑不在食谱格里；Shift 点击认标签格收的料是食材；
- 站点食谱书（StationBooks）：锅读成的那条配方就是现在这一页（同一成品两条配方时不指错）；墓碑没有页、书里放料按键查不到它；
- 站点书里放料（PotLayout.planFillFor）：标签格收的料也放得进去；
- JEI（Compat/Jei/CookingPot.indexes）：按用途查得到标签格的成员和容器，墓碑不登；
- 汤里漂的碎料（PotPiecesLook.dishSlots）：只有格子的配方取每格的第一个选项。
"""
from __future__ import print_function

import sys
import types

import fdtest

Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Rules = fdtest.load("Shared.Rules.CookingPot")
Book = fdtest.load("Shared.Rules.CookingPotBook")
Books = fdtest.load("Shared.Rules.StationBooks")
Layout = fdtest.load("Shared.Rules.PotLayout")
Look = fdtest.load("Shared.Rules.PotPiecesLook")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
TABLE = Recipes.CookingPotRecipeList
STEAK, BEEF, ONION, CARROT = ("other:steak", 0), ("minecraft:beef", 0), ("arris:onion", 0), ("minecraft:carrot", 0)


class _Engine(object):
    """Compat/Jei 只经 Client/Engine 碰引擎：GetChinese 原样还回键，没有 arrisJei。"""

    class _Game(object):
        @staticmethod
        def GetChinese(key):
            return key

    @staticmethod
    def CreateGame(target):
        return _Engine._Game()


def _jei():
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory, engine.levelId = _Engine(), "level"
    engine.clientApi = type("ClientApi", (object,), {"ImportModule": staticmethod(lambda path: None)})
    sys.modules[engine.__name__] = engine
    return fdtest.load("Compat.Jei.CookingPot")


Jei = _jei()


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


def _item(kind, count=1):
    return {"newItemName": kind[0], "newAuxValue": kind[1], "count": count}


STEW = {"Id": "test:cooking/steak_stew", "Slots": [["#common:raw_beef"], ["arris:onion"], ["arris:onion", "minecraft:carrot"]],
        "Recipe": [], "CookResult": ("test:steak_stew", 0), "Vessel": ("minecraft:bowl", 0), "PushItem": [], "text": "x"}
DEAD = {"Id": "test:cooking/dead", "Slots": [["minecraft:dirt"]], "Recipe": [[("minecraft:dirt", 0)]], "CookResult": ("test:dead", 0),
        "PushItem": [], "text": "y", "Disabled": True}


class Setup(object):
    """表尾加上 STEW、DEAD 两行，装上假引擎口；出来时都拿掉。"""

    def __enter__(self):
        TABLE.extend([STEW, DEAD])
        Rules.rebuildIndex()
        ItemTags.setPort("server", Port())
        return len(TABLE) - 2

    def __exit__(self, *exc):
        ItemTags.setPort("server", None)
        TABLE.remove(STEW)
        TABLE.remove(DEAD)
        Rules.rebuildIndex()
        return False


def testTheClassicScreenCyclesEachSlotAndFillsFromWhatIsAtHand():
    with Setup() as at:
        assert Book.recipeAt(at) is STEW and Book.recipeAt(at + 1) is None, "只有格子的配方在食谱格里，墓碑不在"
        assert at in Book.visibleRecipes("") and at + 1 not in Book.visibleRecipes("")
        assert Book.variantCount(STEW) == 3, "选项最多的那格（生牛肉：三样）有几个就轮几帧"
        assert [Book.variantOf(STEW, n) for n in range(4)] == [
            [BEEF, ONION, ONION], [("arris:minced_beef", 0), ONION, CARROT], [STEAK, ONION, ONION], [BEEF, ONION, ONION]]
        stock = [STEAK, None, CARROT]
        rows = Book.fillOrder(STEW, [ONION] + [None] * 5, stock)
        assert rows[0] == [STEAK, ONION, ONION] and [STEAK, ONION, CARROT] in rows, "按锅里和背包里有的料具体化；锅里已有的多的在前"
        assert Book.planFill(rows[0], [ONION] + [None] * 5) == ([(1, STEAK), (2, ONION)], [(0, ONION)])
        assert not Book.isPureVessel("other:steak") and Book.isAmbiguous("minecraft:bowl") is False


def testTheStationBookPointsAtTheRecipeThePotReads():
    twin = {"Recipe": [[("test:a", 0)]], "CookResult": ("arris:fried_rice", 0), "PushItem": [], "text": "z"}
    with Setup() as at:
        assert Books.potCurrent([_item(STEAK), _item(ONION), _item(CARROT)]) == at
        assert Books.potRecipe(at) is STEW and Books.potRecipe(at + 1) is None, "书里放料按键查：墓碑查不到"
        pages = dict((page["key"], page) for page in Books.potPages())
        assert at + 1 not in pages and pages[at]["ways"] == [[[BEEF, ("arris:minced_beef", 0), STEAK], [ONION], [ONION, CARROT]]]
        TABLE.append(twin)
        Rules.rebuildIndex()
        try:
            assert Books.potCurrent([_item(("test:a", 0))]) == len(TABLE) - 1, "同一成品的第二条配方：指它，不指第一条"
        finally:
            TABLE.remove(twin)
            Rules.rebuildIndex()


def testBookFillPutsTaggedFoodIn():
    with Setup():
        plan = Layout.planFillFor(STEW, {}, {STEAK: 3, ONION: 6}, 2, lambda kind: 64)
        assert plan == ({STEAK: 1, ONION: 2}, 2), plan
        assert Layout.planFillFor(STEW, {}, {ONION: 6}, 2, lambda kind: 64) is None, "没有生牛肉一类的料"


def testJeiFindsTheRecipeByEveryMemberAndTheVessel():
    with Setup():
        byResult, byInput = Jei.indexes()
        assert byResult[("test:steak_stew", 0)] == [STEW] and ("test:dead", 0) not in byResult
        for kind in (STEAK, BEEF, ONION, CARROT, ("minecraft:bowl", 0)):
            assert STEW in byInput[kind], kind
        assert DEAD not in byInput.get(("minecraft:dirt", 0), [])
        page = Jei.CookingPotRecipe(None, None, STEW, 0, ("test:steak_stew", 0))
        assert page.frames == Rules.framesOf(STEW) and len(page.frames) == 3


def testSoupPiecesOfASlotsOnlyRecipeUseTheFirstOptions():
    with Setup():
        assert Rules.framesOf(STEW)[0] == [BEEF, ONION, ONION]
        assert Look.dishSlots("test:steak_stew") != Look.EMPTY, "牛肉和洋葱会留下碎料"
        assert Look.dishSlots("test:dead") != Look.EMPTY, "删掉的菜（墓碑）：锅里已经煮好的那锅照墓碑那一行漂碎料，不抛"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
