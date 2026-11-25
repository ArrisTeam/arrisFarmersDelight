# -*- coding: utf-8 -*-
# runner: both
"""没写 text 的厨锅配方：经典界面显示成品的显示名，搜索也按它（Shared/Rules/ItemNames.py、CookingPotBook.titleOf / _found）。

JE 的配方 JSON 没有 text：别的模组照 RECIPE-JSON.md 搬来的配方，表里 text 记的是成品的物品 ID（"没写"的记号）。显示名要界面用到时
才问引擎（ready 广播那一刻服务端对自定义物品只给语言键，2026-11-26 实机），这里用假的口：
- 标题是口给的名字；口给 None、语言键（item.xxx.name / tile.xxx.name）、空、不是文字、抛异常时是物品 ID；没装口时也是物品 ID；
- 按显示名搜得到；先要不到、后来要到了，同一个搜索词的答案跟着变（真去问了、没要到时不记那次的结果，隔 RETRY_EVERY 次再问引擎）；
  永远要不到的名字不让搜索的记忆失效（隔着没问的不算 misses：第二次起记住，食谱格给同一个字典）；
- 农夫乐事自带的 28 行（都写了 text）标题一个字不变、不问口；py2 里口给 utf-8 字节串，搜索词是 unicode 也比得上。
"""
from __future__ import print_function

import fdtest

Book = fdtest.load("Shared.Rules.CookingPotBook")
Names = fdtest.load("Shared.Rules.ItemNames")
Pot = fdtest.load("Shared.Data.CookingPotRecipes")
CookingPot = fdtest.load("Shared.Rules.CookingPot")
INGOT = ("minecraft:iron_ingot", 0)
ROW = {"Id": "test:cooking/ingot", "Slots": [["minecraft:stick"]], "Recipe": [[("minecraft:stick", 0)]], "CookResult": INGOT,
       "PushItem": [], "text": "minecraft:iron_ingot"}


class Port(object):
    """假的口：按 (物品名, aux) 查表，记下问了几次。"""

    def __init__(self, names):
        self.names, self.asked = dict(names), []

    def __call__(self, name, aux):
        self.asked.append((name, aux))
        answer = self.names.get((name, aux))
        if isinstance(answer, Exception):
            raise answer
        return answer


class Rows(object):
    """with Rows(口)：表尾临时加 ROW、装上口；出来时拿掉、卸下、忘掉记着的名字和搜索。"""

    def __init__(self, port):
        self.port = port

    def __enter__(self):
        Pot.CookingPotRecipeList.append(ROW)
        CookingPot.rebuildIndex()
        Names.forget()
        Book._memo.clear()
        Book.setNamePort(self.port)
        return len(Pot.CookingPotRecipeList) - 1

    def __exit__(self, *exc):
        Pot.CookingPotRecipeList.remove(ROW)
        CookingPot.rebuildIndex()
        Book.setNamePort(None)
        Names.forget()
        Book._memo.clear()
        return False


def testARecipeWithoutTextShowsTheResultsDisplayNameAndIsFoundByIt():
    with Rows(Port({INGOT: "铁锭"})) as index:
        assert Book.titleOf(ROW) == "铁锭"
        assert index in Book.visibleRecipes(u"铁锭") and index in Book.visibleRecipes("铁") and index not in Book.visibleRecipes(u"金锭")
        assert index in Book.visibleRecipes(""), "空的搜索词是全部"


def testNoUsableNameFallsBackToTheItemId():
    for answer in (None, "item.fdprobe:tomato.name", "tile.arris:stove.name", "", 3, RuntimeError("engine")):
        with Rows(Port({INGOT: answer})):
            assert Book.titleOf(ROW) == "minecraft:iron_ingot", answer
    with Rows(None):
        assert Book.titleOf(ROW) == "minecraft:iron_ingot", "没装口"
    assert Names.isLangKey(u"item.x:y.name") and Names.isLangKey(b"tile.x.name") and not Names.isLangKey("铁锭")


def testANameThatArrivesLaterChangesTheSameSearch():
    port = Port({})
    with Rows(port) as index:
        assert index not in Book.visibleRecipes(u"铁锭") and Book.titleOf(ROW) == "minecraft:iron_ingot"
        port.names[INGOT] = "铁锭"
        seen = []
        for _turn in range(Names.RETRY_EVERY + 2):
            Book.titleOf(ROW)                    # 选中的那道菜：界面每次刷新都要它的标题，隔一阵会再真问一次引擎
            seen.append(index in Book.visibleRecipes(u"铁锭"))
        assert seen[-1] and not all(seen), "隔一阵再问引擎，要到了就跟着变：%r" % seen
        asked = len(port.asked)
        assert index in Book.visibleRecipes(u"铁锭") and len(port.asked) == asked, "要到了就记住，不再问"


def testANameThatNeverComesDoesNotDefeatTheSearchMemo():
    """主会话读差异时指出的：隔着没问的也算 misses 时，表里只要有一条成品没有语言条目（引擎永远给 item.xxx.name）的配方，
    _found 就永远不记结果——经典界面每要一次食谱格（gridCells / shownCount / pickedRecipe，一次刷新好几回）都把整张表过滤一遍、
    重建格子字典。现在只有真去问了、没要到才算：第一次过滤不记，第二次起记住；后来要到了名字，签名变了、搜索重算。
    空的搜索词不比名字（不问口），所以这里用一个比得上物品 ID 的搜索词。"""
    port = Port({INGOT: "item.minecraft:iron_ingot.name"})
    with Rows(port) as index:
        assert [Book.gridCells("") for _turn in range(3)] and port.asked == [], "空的搜索词不问口"
        cells, refreshes = [], 40
        for _turn in range(refreshes):           # 界面的一次刷新：食谱格、格数、选中的那道、它的标题
            cells.append(Book.gridCells("iron"))
            Book.shownCount("iron")
            Book.pickedRecipe("iron", 0)
            Book.titleOf(ROW)
        assert index in Book.visibleRecipes("iron"), "要不到名字时按物品 ID 搜"
        assert len(port.asked) <= 2 + refreshes // (Names.RETRY_EVERY + 1), "口只被真问了有限几次：%d" % len(port.asked)
        assert all(found is cells[1] for found in cells[1:]), "第 2 次起给的是同一个字典"
        port.names[INGOT] = "铁锭"
        for _turn in range(Names.RETRY_EVERY + 1):
            Book.titleOf(ROW)
        assert Book.titleOf(ROW) == "铁锭" and index in Book.visibleRecipes(u"铁锭"), "后来要到了名字：签名变了、按显示名搜得到"
        assert index not in Book.visibleRecipes("iron"), "记着的那次搜索跟着重算"


def testTheBuiltInRowsKeepTheirTitlesAndDoNotAsk():
    port = Port({})
    with Rows(port):
        for row in Pot.CookingPotRecipeList:
            if str(row.get("Id", "")).startswith("farmersdelight:"):
                assert Book.titleOf(row) == row["text"], row["Id"]
        assert port.asked == [], "写了 text 的不问口"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
