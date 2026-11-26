# -*- coding: utf-8 -*-
# runner: both
"""经典厨锅界面的搜索（Shared/Rules/PotSearch.py）：照 arrisJei 拆条件、一道菜逐件比，显示名、标签用假的口。

主会话钉的三条：中文词"牛炖"搜得到牛肉炖（中文词按显示名模糊）；"牛肉"不会配上一道分别有"牛"和"肉"两件东西的菜（逐件比，哪一档比法都一样）；
"bee"不会模糊配上物品 ID 里只是散着 b、e 的东西（字母的词、物品 ID 只认子串；ALL 那一档才会）。另外：条件的拆法和前缀（@ # & /，% 当普通文本）、
几个条件可以由不同的物品满足、显示名问不到时只比物品 ID、不搜盛菜的容器、墓碑和形状不对的行不在里面、py2 的字节串和 unicode 混着来不出警告、
记着的结果什么时候作废（表、标签的代数、显示名的版本、比法）、格号和行号的对照。
"""
from __future__ import print_function

import ast
import io
import os
import warnings

import fdtest

Search = fdtest.load("Shared.Rules.PotSearch")
Names = fdtest.load("Shared.Rules.ItemNames")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
Pot = fdtest.load("Shared.Data.CookingPotRecipes")
CookingPot = fdtest.load("Shared.Rules.CookingPot")
TEXT, MOD, TAG, ID = Search.TEXT, Search.MOD, Search.TAG, Search.ID


def _row(result, ways, text=None, **extra):
    """一道夹具菜（旧写法）：text 不给是"没写"（记成品的物品 ID）。"""
    found = {"Recipe": [[(name, 0) for name in way] for way in ways], "CookResult": (result, 0), "PushItem": [],
             "text": result if text is None else text}
    found.update(extra)
    return found


STEW = _row("test:stew", [["test:cow"]])                                    # 成品的显示名"牛肉炖"，没写 text
SPLIT = _row("test:split", [["test:cow", "test:meat"]])                     # "牛"和"肉"在两件东西上（黄牛、瘦肉）
COMBO = _row("test:combo", [["arris:tomato", "minecraft:beef"]])            # 番茄 + 生牛肉
BERRY = _row("test:berry_tree", [["test:twig"]])                            # 物品 ID 里散着 b、e，没有 bee；没有显示名
PICKLE = _row("test:pickles", [["test:cucumber"]], Vessel=("test:jar", 0))  # 盛菜的容器"坛子"
GHOST = _row("test:ghost", [["test:wisp"]], Disabled=True)                  # 删掉了（墓碑）
SALAD = {"Slots": [["#common:tomato"], ["test:leaf"]], "Recipe": [], "CookResult": ("test:salad", 0), "PushItem": [], "text": "test:salad"}
WRITTEN = _row("test:soup", [["test:water"]], text=u"写着名字的汤")
BROKEN = {"text": "没有成品", "Recipe": [[("test:x", 0)]]}
FIXTURES = (STEW, SPLIT, COMBO, BERRY, PICKLE, GHOST, SALAD, WRITTEN, BROKEN)
NAMES = {("test:stew", 0): u"牛肉炖", ("test:cow", 0): u"黄牛", ("test:meat", 0): u"瘦肉", ("test:split", 0): u"杂烩",
         ("test:jar", 0): u"坛子", ("test:ghost", 0): u"幽灵菜", ("minecraft:beef", 0): u"生牛肉", ("arris:tomato", 0): u"番茄",
         ("test:pickles", 0): u"酸黄瓜", ("test:salad", 0): u"沙拉"}


class NamePort(object):
    """假的显示名口：按 (物品名, aux) 查表，记下问了几次。"""

    def __init__(self, names):
        self.names, self.asked = dict(names), []

    def __call__(self, name, aux):
        self.asked.append((name, aux))
        answer = self.names.get((name, aux))
        if isinstance(answer, Exception):
            raise answer
        return answer


class TagPort(object):
    """假的标签口：test:cow 带 test:bovine。"""

    def ready(self):
        return True

    def itemsOf(self, tag):
        return ["test:cow"] if tag == "test:bovine" else []

    def tagsOf(self, name, aux=0):
        return ["test:bovine"] if name == "test:cow" else []

    def blocksOf(self, tag):
        return []

    def blockTagsOf(self, name):
        return []


class Rows(object):
    """with Rows(显示名表)：表尾加上夹具、装上显示名的口（None 不装）；出来时都拿掉、忘掉记着的。"""

    def __init__(self, names=NAMES):
        self.port = NamePort(names) if names is not None else None

    def __enter__(self):
        self.start = len(Pot.CookingPotRecipeList)
        Pot.CookingPotRecipeList.extend(FIXTURES)
        CookingPot.rebuildIndex()
        Names.setPort(None)
        Names.forget()
        if self.port is not None:
            Names.setPort(self.port)
        Search.forget()
        return self.port

    def __exit__(self, *exc):
        del Pot.CookingPotRecipeList[self.start:]
        CookingPot.rebuildIndex()
        ItemTags.setPort("server", None)
        Names.setPort(None)
        Names.forget()
        Search.forget()
        return False


def at(row):
    """夹具在表里的行号（按对象找：夹具之间可能相等）。"""
    return next(index for index, found in enumerate(Pot.CookingPotRecipeList) if found is row)


def _beefStew():
    return next(index for index, row in enumerate(Pot.CookingPotRecipeList) if row.get("Id") == "farmersdelight:cooking/beef_stew")


def testTheQueryIsSplitIntoConditionsLikeArrisJei():
    assert Search.parse(u"  番茄   牛肉 ") == ((TEXT, u"番茄"), (TEXT, u"牛肉"))
    assert Search.parse("@Arris #Tomato &Cook /Stew %food") == ((MOD, u"arris"), (TAG, u"tomato"), (ID, u"cook"), (ID, u"stew"), (TEXT, u"%food"))
    assert Search.parse("@ # & / ") == () and Search.parse(None) == () and Search.parse("") == ()
    assert Search.parse(u"牛肉".encode("utf-8")) == ((TEXT, u"牛肉"),), "py2 的字节串解成 unicode"


def testTheThreeNailsOfTheLead():
    with Rows():
        assert at(STEW) in Search.rows(u"牛炖") and _beefStew() in Search.rows(u"牛炖"), "中文词按显示名（标题）模糊：牛炖 配得上牛肉炖"
        for fuzzy in (Search.SUBSTRING, Search.CJK, Search.ALL):
            assert not Search.matches(SPLIT, u"牛肉", fuzzy), "逐件比：牛、肉分在两件东西上，配不上（%s）" % fuzzy
        assert Search.matches(SPLIT, u"牛 肉"), "两个条件各由一件满足：配得上"
        assert at(BERRY) not in Search.rows("bee") and not Search.matches(BERRY, "bee"), "字母的词只认子串：不散着配物品 ID"
        assert Search.matches(BERRY, "bee", Search.ALL), "ALL 那一档（arrisJei 打开模糊时）才配得上"
        assert Search.matches(BERRY, "berry") and Search.matches(BERRY, u"TEST:BERRY"), "子串照常，不分大小写"
        assert not Search.matches(STEW, u"牛炖", Search.SUBSTRING), "只认子串那一档：牛炖 配不上"
        assert Search.matches(STEW, u"牛肉炖", Search.SUBSTRING)


def testCjkFuzzinessOnlyLooksAtTheDisplayName():
    with Rows({("test:stew", 0): u"汤", ("test:cow", 0): u"牛"}):
        assert not Search.matches(STEW, u"st汤"), "含中文的词每个字都要在显示名里：s、t 只在物品 ID 里不算"
        assert Search.matches(STEW, u"st汤", Search.ALL), "ALL 拿显示名加物品 ID 一起比"
        assert Search.matches(STEW, u"汤")


def testEachConditionMayBeMetByADifferentItem():
    with Rows():
        assert Search.matches(COMBO, u"番茄 牛肉") and Search.matches(COMBO, u"番茄 生牛")
        assert not Search.matches(STEW, u"番茄 牛肉"), "番茄这一条谁都不满足"
        assert at(COMBO) in Search.rows(u"番茄 牛肉") and at(STEW) not in Search.rows(u"番茄 牛肉")


def testPrefixes():
    with Rows():
        assert Search.matches(STEW, "@test") and Search.matches(COMBO, "@minecraft") and not Search.matches(STEW, "@minecraft")
        assert not Search.matches(STEW, "@tst"), "前缀条件只认子串"
        assert Search.matches(SALAD, "#tomato") and Search.matches(SALAD, "#common:tom"), "格子里写的标签名"
        assert Search.matches(COMBO, "#tomato"), "食材自己带的标签（番茄在 common:tomato 里）"
        assert not Search.matches(STEW, "#bovine")
        ItemTags.setPort("server", TagPort())
        assert Search.matches(STEW, "#bovine") and Search.matches(SPLIT, "#bovine"), "别的模组给黄牛挂的标签"
        assert Search.matches(BERRY, "&berry") and Search.matches(BERRY, "/berry_tree") and Search.matches(STEW, "&test:cow")
        assert not Search.matches(STEW, u"%黄牛") and not Search.matches(STEW, u"%"), "% 照 arrisJei 关掉的前缀：整个词当普通文本"
        assert Search.matches(STEW, u"@test 黄牛 #bovine"), "几种条件一起"


def testTheVesselIsNotSearched():
    with Rows():
        assert not Search.matches(PICKLE, u"坛子") and not Search.matches(PICKLE, "&jar") and not Search.matches(PICKLE, "jar")
        assert Search.matches(PICKLE, u"酸黄瓜") and Search.matches(PICKLE, "cucumber")


def testANameThatCannotBeAskedFallsBackToTheItemId():
    with Rows(names=None):
        assert not Search.matches(STEW, u"牛肉") and not Search.matches(STEW, u"黄牛")
        assert Search.matches(STEW, "stew") and Search.matches(STEW, "test:cow"), "物品 ID（成品、食材）照样比"
        assert Search.matches(WRITTEN, u"名字的汤"), "写了的 text 照样比"
    with Rows({("test:stew", 0): "item.test:stew.name", ("test:cow", 0): RuntimeError("wrong thread")}):
        assert not Search.matches(STEW, "item") and Search.matches(STEW, "stew"), "语言键、抛异常都当要不到"


def testRemovedAndBrokenRowsAreNeverShown():
    with Rows():
        everything = Search.rows("")
        assert at(GHOST) not in everything and not Search.matches(GHOST, "") and not Search.matches(GHOST, u"幽灵")
        assert BROKEN not in [Pot.CookingPotRecipeList[index] for index in everything] and not Search.matches(BROKEN, "")
        assert at(STEW) in everything and at(SALAD) in everything, "只有格子的配方照样列"
        assert everything == sorted(everything), "照表里的先后"


def testPython2StringKindsMixWithoutWarnings():
    soup = _row("test:broth", [["test:bone"]], text=u"骨头汤".encode("utf-8"))
    names = {("test:bone", 0): u"大棒骨".encode("utf-8"), ("test:stew", 0): u"牛肉炖"}
    getattr(Search, "__warningregistry__", {}).clear()
    with Rows(names):
        Pot.CookingPotRecipeList.append(soup)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            for query in (u"骨头", u"骨头".encode("utf-8"), u"棒骨", u"棒骨".encode("utf-8"), u"牛炖".encode("utf-8")):
                Search.forget()
                assert Search.rows(query), query
            assert Search.matches(soup, u"骨汤") and Search.matches(soup, u"大骨".encode("utf-8"))


def testRememberedResultsAndWhenTheyAreThrownAway():
    with Rows() as port:
        first = Search.cells("")
        assert Search.cells("") is first and Search.cells(u"  ") is first, "界面每画一格都来要：同一个词给同一个字典"
        shown = Search.rows("")
        shown.append(-1)
        assert -1 not in Search.rows(""), "给出去的行号是拷贝"
        extra = _row("test:late", [["test:late_seed"]], text=u"后来的菜")
        Pot.CookingPotRecipeList.append(extra)
        assert Search.cells("") is not first and at(extra) in Search.rows(u"后来"), "表变长了：重算"
        extra["text"] = u"改过的名字"
        CookingPot.rebuildIndex()
        assert at(extra) not in Search.rows(u"后来") and at(extra) in Search.rows(u"改过"), "就地改了一行、重建了索引：重算"
        assert Search.rows("#bovine") == []
        ItemTags.setPort("server", TagPort())
        assert at(STEW) in Search.rows("#bovine"), "标签的代数变了：重算"
        port.names[("test:twig", 0)] = None
        before = Search.rows(u"小树枝")
        assert at(BERRY) not in before
        port.names[("test:twig", 0)] = u"小树枝"
        for _turn in range(Names.RETRY_EVERY + 1):
            Names.nameOf("test:twig", 0)          # 界面别处（选中那道的标题）隔一阵再问，问到了
        assert at(BERRY) in Search.rows(u"小树枝"), "新问到名字（显示名的版本变了）：重算"
        try:
            Search.FUZZY = Search.SUBSTRING
            assert at(STEW) not in Search.rows(u"牛炖"), "比法换了：重算"
        finally:
            Search.FUZZY = Search.CJK
        assert at(STEW) in Search.rows(u"牛炖")


def testCellsAndRows():
    with Rows():
        word = u"牛"
        shown = Search.rows(word)
        cells = Search.cells(word)
        assert Search.count(word) == len(shown) == len(cells) > 1
        for cell, row in enumerate(shown):
            assert Search.rowAt(word, cell) == row
            assert cells[cell] == {"newItemName": Pot.CookingPotRecipeList[row]["CookResult"][0],
                                   "newAuxValue": Pot.CookingPotRecipeList[row]["CookResult"][1], "count": 1}
        for cell in (-1, len(shown), None, "0", 1.0):
            assert Search.rowAt(word, cell) is None, cell


def testTheOldNativeScreenUsesTheSameMatcherAndSkipsRemovedRows():
    """旧的原生界面（DOLOR_SCREEN = False 时的后备，Client/Ui/CookingPotProxy.py；带着引擎，离线导不了）：按源码看，过滤用的是
    PotSearch.matches、开屏时只列 CookingPotBook.isShown 的行（以前开屏列整张表、墓碑也在），不再自己比 text。"""
    path = os.path.join(fdtest.BP, fdtest.SCRIPTS, "Client", "Ui", "CookingPotProxy.py")
    with io.open(path, "rb") as handle:
        tree = ast.parse(handle.read())
    calls = set("%s.%s" % (node.func.value.id, node.func.attr) for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name))
    assert "PotSearch.matches" in calls and "CookingPotBook.isShown" in calls, sorted(calls)
    assert not [call for call in calls if call.endswith(".matchesSearch")], "旧的按 text 比已经拿掉"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
