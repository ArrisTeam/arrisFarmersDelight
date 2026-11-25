# -*- coding: utf-8 -*-
# runner: both
"""JEI 配方页上我们自己写的字按玩家的语言给（Compat/Jei：厨锅、砧板、煎锅、炉灶四个分类的名字，煎锅 / 炉灶配方页上的秒数；砧板摆盘那一类原来就是）。

分类名在客户端界面就绪、登记分类时经 Texts.of 按玩家的语言查，秒数在配方页建出来时经 Texts.fill 写；语言文件里没有时用代码里的中文。
JE 的 JEI 有的分类用它的键（jei.farmersdelight.cooking / cutting，英文照 JE 的 en_us）；煎锅、炉灶在 JE 归原版的营火一类，这里是我们的键 arris_fd.jei.*；
秒数和站点食谱书页脚是同一句，用 HoD 的键 handson_delight.book.seconds。
这里核对：Compat/Jei 里写死的中文（说明、注释除外）都是 (键, 中文) 的缺省或 Texts 调用的缺省，键两个语言文件里都有、中文和代码里的一样、占位的个数对得上；
登记分类时给的名字都经 Texts.of 查；再把真的四个模块装在假的 Client/Engine 上（GetChinese 按语言文件答，arrisJei 的注册表记下名字），
登记四类、建煎锅和炉灶的配方页，看中文、英文、语言文件里一句都没有时页上写出来的字——秒数要和站点食谱书的页脚一样是整数
（StationBooks.shownSeconds：煎锅 6.0、炉灶 30.0 秒原来直接填进英文的 %s，写成了 6.0 s / 30.0 s）。
"""
from __future__ import print_function

import ast
import io
import os
import re
import sys
import types

import fdtest

JEI = os.path.join(fdtest.BP, fdtest.SCRIPTS, "Compat", "Jei")
TEXTS = os.path.join(fdtest.ROOT, "rp", "texts")
CJK = re.compile(u"[一-鿿]")
KEY = re.compile(r"^[a-z_]+(\.[a-z_]+)+$")
PLACEHOLDER = re.compile(r"%[sd]")
# JE 农夫乐事 1.20 en_us.json 里 JEI 分类的名字
JE_ENGLISH = {"jei.farmersdelight.cooking": u"Cooking", "jei.farmersdelight.cutting": u"Cutting Board"}


def _u(text):
    return text.decode("utf-8") if isinstance(text, bytes) else text


def _lang(name):
    """语言文件：{键: 那一句}（## 开头的是注释）。"""
    found = {}
    with io.open(os.path.join(TEXTS, name), encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, text = line.partition("=")
                found[key] = text
    return found


def _const(node):
    """字符串常量节点的值（py2 是 Str，py3 是 Constant）；不是为 None。"""
    if type(node).__name__ == "Str":
        return node.s
    if type(node).__name__ == "Constant" and isinstance(node.value, (str, bytes)):
        return node.value
    return None


def _isTexts(call, name):
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr == name and isinstance(func.value, ast.Name) and func.value.id == "Texts"


def _modules():
    for name in sorted(os.listdir(JEI)):
        if name.endswith(".py"):
            with io.open(os.path.join(JEI, name), "rb") as handle:
                yield name, ast.parse(handle.read())


def _pairs(tree):
    """(键, 中文) 的写法：二元组常量，或 Texts.of / fill 的头两个参数。返回 [(键, 中文, 中文那个节点)]。"""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            key, text = _const(node.elts[0]), _const(node.elts[1])
        elif isinstance(node, ast.Call) and (_isTexts(node, "of") or _isTexts(node, "fill")) and len(node.args) >= 2:
            key, text = _const(node.args[0]), _const(node.args[1])
            node = ast.Tuple(elts=node.args[:2])
        else:
            continue
        if key is not None and text is not None and KEY.match(_u(key)):
            found.append((_u(key), _u(text), node.elts[1]))
    return found


def testEveryChineseWordOnTheJeiPagesComesWithAKeyBothLanguageFilesHave():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    keys = set()
    for name, tree in _modules():
        docstrings = set(id(node.body[0].value) for node in ast.walk(tree) if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
                         and node.body and isinstance(node.body[0], ast.Expr) and _const(node.body[0].value) is not None)
        pairs = _pairs(tree)
        covered = set(id(node) for _, _, node in pairs)
        loose = [_u(_const(node)) for node in ast.walk(tree) if id(node) not in docstrings and id(node) not in covered
                 and _const(node) is not None and CJK.search(_u(_const(node)))]
        assert not loose, "%s 里还有写死的中文：%r" % (name, loose)
        for key, text, _ in pairs:
            assert key in chinese and key in english, "%s：两个语言文件里都要有 %s" % (name, key)
            assert chinese[key] == text, "%s：中文的语言文件和代码里的那句一样：%s" % (name, key)
            assert len(PLACEHOLDER.findall(english[key])) == len(PLACEHOLDER.findall(text)), "%s：占位的个数对得上：%s" % (name, key)
            keys.add(key)
    assert set(JE_ENGLISH) | set(["arris_fd.jei.skillet", "arris_fd.jei.stove", "handson_delight.book.seconds"]) <= keys, sorted(keys)
    for key, text in JE_ENGLISH.items():
        assert english[key] == text, "英文照 JE：%s" % key


def testEveryCategoryNameIsLookedUpWhenItIsRegistered():
    registered = []
    for name, tree in _modules():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "registerRecipeType":
                title = node.args[2]
                assert isinstance(title, ast.Call) and _isTexts(title, "of"), "%s:%d 分类名要经 Texts.of 查" % (name, node.lineno)
                registered.append(name)
    assert sorted(registered) == ["BoardAssembly.py", "CookingPot.py", "CuttingBoard.py", "Skillet.py", "Stove.py"], registered


# ---------------------------------------------------------------- 真的四个模块，假的引擎：页上写出来的字

lang, titles, written = {}, {}, {}


class _Control(object):
    """配方页上的一个控件：记下写进去的字。"""

    def __init__(self, path):
        self.path = path

    def asLabel(self):
        return self

    def asItemRenderer(self):
        return self

    def SetText(self, text):
        written[self.path] = text

    def SetUiItem(self, *args):
        written[self.path] = args
        return True


class _Page(object):
    """一张配方页：悬停文本的控件不给（SetHoverText 当场返回），别的都给。"""

    @staticmethod
    def GetChildByPath(path):
        return None if path.endswith("/hover_text") else _Control(path)


class _Registry(object):
    """arrisJei 的注册表：记下登记的分类名，配方一概收下。"""

    @staticmethod
    def registerRecipeType(tag, icon, title, *rest):
        titles[tag] = title

    @staticmethod
    def getAllRegisteredItems():
        return []

    @staticmethod
    def setRecipeByResult(*args):
        return None

    @staticmethod
    def setRecipeByInput(*args):
        return None


def _install():
    """JEI 的模块只经 Client/Engine 碰引擎：GetChinese 照 lang 答（unicode，和引擎一样；没有的键原样还回去），ImportModule 给出假的 arrisJei。"""
    class _Game(object):
        @staticmethod
        def GetChinese(key):
            return lang.get(_u(key), key)

    class _Factory(object):
        @staticmethod
        def CreateGame(target):
            return _Game()

    jei = types.ModuleType("arrisJeiScripts.api.jei")
    jei.JeiRecipeRegistry = type("JeiRecipeRegistry", (object,), {"getInstance": staticmethod(_Registry)})
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory, engine.levelId = _Factory(), "level"
    engine.clientApi = type("ClientApi", (object,), {"ImportModule": staticmethod(lambda path: jei)})
    sys.modules[engine.__name__] = engine
    return dict((name, fdtest.load("Compat.Jei." + name)) for name in ("CookingPot", "CuttingBoard", "Skillet", "Stove"))


MODULES = _install()
Books = fdtest.load("Shared.Rules.StationBooks")
REGISTER = (("CookingPot", "RegisterCookingPotRecipes"), ("CuttingBoard", "RegisterCuttingBoardRecipes"),
            ("Skillet", "RegisterSkilletRecipes"), ("Stove", "RegisterStoveRecipes"))
PAGES = (("Skillet", "SkilletRecipe"), ("Stove", "StoveRecipe"))
SHOWN = {
    "zh_CN": ({"cooking_pot": u"烹饪", "cutting_board": u"砧板", "skillet": u"煎锅", "stove": u"炉灶"}, {"Skillet": u"6 秒", "Stove": u"30 秒"}),
    "en_US": ({"cooking_pot": u"Cooking", "cutting_board": u"Cutting Board", "skillet": u"Skillet", "stove": u"Stove"}, {"Skillet": u"6 s", "Stove": u"30 s"}),
}


def _render(language):
    """按 language 的语言文件（None：一句都查不到）登记四类、建煎锅和炉灶的配方页：({分类: 名字}, {模块: 页上的秒数})。"""
    lang.clear()
    if language:
        lang.update(_lang(language + ".lang"))
    titles.clear()
    for module, register in REGISTER:
        getattr(MODULES[module], register)()
    seconds = {}
    for module, page in PAGES:
        written.clear()
        getattr(MODULES[module], page)(None, _Page(), {"input": "minecraft:beef", "output": "minecraft:cooked_beef"}, 0, ("minecraft:beef", 0)).OnCreate()
        assert isinstance(written["/bg/timer"], str), "py2 里是 utf-8 的字节串（标签的接口只收 str）"
        seconds[module] = _u(written["/bg/timer"])
    assert all(isinstance(title, str) for title in titles.values())
    return dict((tag, _u(title)) for tag, title in titles.items()), seconds


def testTheJeiPagesSayTheirWordsInThePlayersLanguageWithWholeSeconds():
    for language, shown in sorted(SHOWN.items()):
        assert _render(language) == shown, (language, _render(language))
    assert _render(None) == SHOWN["zh_CN"], "语言文件里一句都没有：分类名和秒数都是代码里的中文"


def testThePagesAndTheBookFooterTurnSecondsIntoTheSameNumber():
    for module, constant in (("Skillet", "SKILLET_SECONDS"), ("Stove", "RECIPE_SECONDS")):
        seconds = getattr(MODULES[module], constant)
        number = Books.shownSeconds(seconds)
        assert isinstance(number, int) and number == int(seconds), (module, seconds, number)
        assert _render(None)[1][module] == u"%d 秒" % number and _render("en_US")[1][module] == u"%d s" % number
        assert MODULES[module].SECONDS[0] == Books.SECONDS_KEY, "和页脚同一个键"
    assert Books.shownSeconds(2.5) == 3 and Books.shownSeconds(2.4) == 2, "Java 的 Math.round：半数进位"
    assert Books._seconds(2.5) == "3 秒", "页脚也经 shownSeconds"
    for module, constant in (("Skillet", "SKILLET_SECONDS"), ("Stove", "RECIPE_SECONDS")):
        kept = getattr(MODULES[module], constant)
        setattr(MODULES[module], constant, 2.5)
        try:
            assert _render(None)[1][module] == u"3 秒" and _render("en_US")[1][module] == u"3 s", "配方页也是半数进位（不是截掉小数）：经的是 shownSeconds"
        finally:
            setattr(MODULES[module], constant, kept)


def testTheThreeEggsShareOneSkilletAndStovePage():
    """JEI 的煎锅 / 炉灶页和站点的书一样分组（StationBooks.cookGroups）：三种蛋一页，按煎蛋、按哪种蛋查都是这一页，页上的蛋每秒换一种。"""
    calls = []

    class Registry(object):
        @staticmethod
        def getAllRegisteredItems():
            return [("minecraft:blue_egg", 0), ("arris:fried_egg", 0), ("minecraft:beef", 0)]

        @staticmethod
        def setRecipeByResult(tag, item, records):
            calls.append(("result", tag, item[0], [record["inputs"] for record in records]))

        @staticmethod
        def setRecipeByInput(tag, item, records):
            calls.append(("input", tag, item[0], [record["inputs"] for record in records]))

    eggs = ["minecraft:egg", "minecraft:blue_egg", "minecraft:brown_egg"]
    fdtest.load("Compat.Jei.CookPages").register(Registry(), "skillet")
    assert ("result", "skillet", "arris:fried_egg", [eggs]) in calls and ("input", "skillet", "minecraft:blue_egg", [eggs]) in calls, calls
    assert ("input", "skillet", "minecraft:beef", [["minecraft:beef"]]) in calls
    for module, page in PAGES:
        written.clear()
        recipe = getattr(MODULES[module], page)(None, _Page(), {"input": eggs[0], "inputs": eggs, "output": "arris:fried_egg"}, 0, ("arris:fried_egg", 0))
        recipe.OnCreate()
        shown = [written["/bg/jeiInputItemRender/item_cell/item/item_renderer"][0]]
        for _turn in range(3):
            recipe.OnInterval()
            shown.append(written["/bg/jeiInputItemRender/item_cell/item/item_renderer"][0])
        assert shown == eggs + [eggs[0]], (module, shown)
        assert written["/bg/jeiOutputItemRender/item_cell/item/item_renderer"][0] == "arris:fried_egg"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
