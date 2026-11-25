# -*- coding: utf-8 -*-
# runner: both
"""没写 text 的厨锅配方：经典界面的标题显示成品的显示名，搜索框照旧按 text 搜（Shared/Rules/ItemNames.py、CookingPotBook.titleOf /
matchesSearch / _found）。

JE 的配方 JSON 没有 text：别的模组照 RECIPE-JSON.md 搬来的配方，表里 text 记的是成品的物品 ID（"没写"的记号）。显示名要界面用到时
才问引擎（ready 广播那一刻服务端对自定义物品只给语言键，2026-11-26 实机），这里用假的口：
- 标题是口给的名字；口给 None、语言键（item.xxx.name / tile.xxx.name）、空、不是文字、抛异常时是物品 ID；没装口时也是物品 ID；
  先要不到、后来要到了，隔 RETRY_EVERY 次再问引擎时标题跟着变；
- 搜索只按两端同步过来的 text 比（显示名是各端自己问引擎的，联机时两端可能不一样，按它过滤服务端认的格号会对不上）：
  没写 text 的按物品 ID 搜得到、按显示名搜不到；搜索从不问口；
- 装着几个口时挨个问，第一个给出名字的算数（单机时两端的口都在这一份模块里，各自只在自己那一端的线程里答得出），装的先后都一样；
- 农夫乐事自带的 28 行（都写了 text）标题一个字不变、不问口，按中文名照样搜得到；py2 里字节串和 unicode 的搜索词都比得上。
"""
from __future__ import print_function

import warnings

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


def testARecipeWithoutTextShowsTheResultsDisplayNameButIsSearchedByItsText():
    with Rows(Port({INGOT: "铁锭"})) as index:
        assert Book.titleOf(ROW) == "铁锭"
        assert index not in Book.visibleRecipes(u"铁锭") and index not in Book.visibleRecipes("铁"), "搜索不按显示名"
        assert index in Book.visibleRecipes("iron") and index in Book.visibleRecipes(u"MINECRAFT:IRON"), "没写 text 的按物品 ID 搜得到"
        assert index in Book.visibleRecipes(""), "空的搜索词是全部"


def testNoUsableNameFallsBackToTheItemId():
    for answer in (None, "item.fdprobe:tomato.name", "tile.arris:stove.name", "", 3, RuntimeError("engine")):
        with Rows(Port({INGOT: answer})):
            assert Book.titleOf(ROW) == "minecraft:iron_ingot", answer
    with Rows(None):
        assert Book.titleOf(ROW) == "minecraft:iron_ingot", "没装口"
    assert Names.isLangKey(u"item.x:y.name") and Names.isLangKey(b"tile.x.name") and not Names.isLangKey("铁锭")


def testANameThatArrivesLaterShowsUpInTheTitle():
    port = Port({})
    with Rows(port):
        assert Book.titleOf(ROW) == "minecraft:iron_ingot" and len(port.asked) == 1
        port.names[INGOT] = "铁锭"
        seen = [Book.titleOf(ROW) for _turn in range(Names.RETRY_EVERY + 1)]     # 选中的那道菜：界面每次刷新都要它的标题
        assert seen[-1] == "铁锭" and seen[0] == "minecraft:iron_ingot", "隔一阵再问引擎，要到了就跟着变：%r" % seen
        asked = len(port.asked)
        assert Book.titleOf(ROW) == "铁锭" and len(port.asked) == asked == 2, "隔着没问；要到了就记住，不再问"


def testTheSearchNeverAsksThePort():
    """搜索框只按两端同步过来的 text 比（主会话定的：显示名是各端自己问引擎的，联机时两端可能不一样，按它过滤，服务端认的格号会对不上）。
    所以界面怎么刷新、搜什么词，口都只被标题（titleOf）问；同一个搜索词（表没变时）的食谱格从第一次起就是同一个字典。"""
    port = Port({INGOT: "item.minecraft:iron_ingot.name"})
    with Rows(port) as index:
        for word in ("", "iron", u"铁锭", "MINECRAFT"):
            cells = []
            for _turn in range(40):              # 界面的一次刷新：食谱格、格数、选中的那道
                cells.append(Book.gridCells(word))
                Book.shownCount(word)
                Book.pickedRecipe(word, 0)
            assert all(found is cells[0] for found in cells), word
        assert port.asked == [], "搜索不问口"
        assert (index in Book.visibleRecipes("iron")) and index not in Book.visibleRecipes(u"铁锭")
        Book.titleOf(ROW)
        assert len(port.asked) == 1, "问口的只有标题"
        sauce = next(row for row in Pot.CookingPotRecipeList if row.get("Id") == "farmersdelight:cooking/tomato_sauce")
        for word, expected in ((u"番茄酱", True), ("番茄", True), (u"TOMATO", False)):
            assert Book.matchesSearch(sauce, word) == expected, word              # 写了 text 的按 text 比，字节串 / unicode 都行
        assert Book.matchesSearch(ROW, b"iron") and Book.matchesSearch(ROW, None) and not Book.matchesSearch({}, "iron")


def testSeveralPortsAreAskedInTurn():
    """主会话实机查出来的（2026-11-26，单机）：两端共用这一份模块，以前只有一个口、后装的算数——装着的是客户端的口，可引擎的
    GetItemBasicInfo 只在自己那一端的线程里答得出（服务端线程里客户端的口给 None），探针包两条配方的标题还是物品 ID。
    现在能装几个口，真去问时挨个问，第一个给出名字的算数，装的先后都一样；同一个口不重复装；都要不到时照旧隔一阵再问。"""
    for order in ("silent first", "named first", "raising first"):
        silent = Port({INGOT: RuntimeError("wrong thread")}) if order == "raising first" else Port({})
        named = Port({INGOT: "铁锭"})
        with Rows(None):
            for port in ((named, silent) if order == "named first" else (silent, named)) + (silent,):
                Book.setNamePort(port)
            assert Book.titleOf(ROW) == "铁锭", order
            assert len(named.asked) == 1 and len(silent.asked) == (0 if order == "named first" else 1), "同一个口不重复装、问到就停"
    with Rows(None):
        first, second = Port({}), Port({INGOT: "item.minecraft:iron_ingot.name"})
        Book.setNamePort(first)
        Book.setNamePort(second)
        assert Book.titleOf(ROW) == "minecraft:iron_ingot" and len(first.asked) == len(second.asked) == 1
        for _turn in range(Names.RETRY_EVERY):
            Book.titleOf(ROW)
        assert len(first.asked) == len(second.asked) == 1, "要不到：隔着没问"
        second.names[INGOT] = "铁锭"
        assert Book.titleOf(ROW) == "铁锭" and len(first.asked) == len(second.asked) == 2, "隔一阵再挨个问一次"
        Names.removePort(second)
        Names.forget()
        assert Book.titleOf(ROW) == "minecraft:iron_ingot", "卸下一个口"


def testMixedStringKindsDoNotWarnUnderPython2():
    """主会话定的 B4（T 复核时 py2 复现的）：text 是非 ASCII 的字节串、成品名是 unicode（旧接口追加的行可能这样写）时，"text 是不是
    成品的物品 ID"那一比在 py2 里出 UnicodeWarning（答案是对的）；现在先换成同一种再比。py2 下把警告当错误跑，py3 下照样过。"""
    soup = ("mymod:soup", 0)
    rows = [{"CookResult": (u"mymod:soup", 0), "text": "浓汤"}, {"CookResult": ("mymod:soup", 0), "text": u"浓汤"},
            {"CookResult": (u"mymod:soup", 0), "text": "mymod:soup"}, {"CookResult": ["mymod:soup", 0], "text": u"mymod:soup"}]
    getattr(Book, "__warningregistry__", {}).clear()     # py2：同一处警告过一次之后 registry 会挡住后面的，"error" 也不抛
    with Rows(Port({soup: "汤"})):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            titles = [Book.titleOf(row) for row in rows]
    assert titles[0] == "浓汤" and titles[1] == u"浓汤" and titles[2] == "汤" and titles[3] == "汤", titles


def testTheBuiltInRowsKeepTheirTitlesAndDoNotAsk():
    port = Port({})
    with Rows(port):
        for row in Pot.CookingPotRecipeList:
            if str(row.get("Id", "")).startswith("farmersdelight:"):
                assert Book.titleOf(row) == row["text"], row["Id"]
        assert port.asked == [], "写了 text 的不问口"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
