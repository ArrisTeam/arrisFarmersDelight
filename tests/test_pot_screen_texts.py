# -*- coding: utf-8 -*-
# runner: both
"""经典厨锅界面上玩家看得到的字按玩家的语言给（dolorContainer 的界面：没装沉浸式交互前置、或者 HoD 配置里关了厨锅站点时右键厨锅开的那个）。

字从哪来、谁来查：
- 标题：容器类型的标题（Server/CookingPotHost.TITLE）是 JE 的容器标题键 container.farmersdelight.cooking_pot，库在客户端按玩家的语言查；
  原来是方块名的键 tile.arris:cooking_pot.name，方块名只有中文的语言文件里有，英文的游戏里露出键名；
- "+"按钮下面的"添加食材"：布局源文件 layouts/cooking_pot.json 里文字控件的格式串写语言文件的键，编译进 dolorLayouts.py，库在客户端查；
  按钮本身没有字（"+"画在贴图上）；
- 搜索框的提示（$dc_placeholder）：编译成原版文本框的 $place_holder_text，引擎的文字控件（localize 为真）查；
- 食谱详情上方的标题：界面数据 bookTitle 是可本地化的文字（Data.Lang），没选食谱时是 {"t": 键}，选了是那道菜的 text；
- 食谱格、详情格里的是物品（悬停时引擎按语言给名字；物品名本身还没有英文，不归这里）。
两种界面档用同一个界面，所以每样字在编译出的界面文件里只有一份。改版时删掉的键（换一种配方、携带版的两个页签）两个语言文件里都不留。
旧的原生界面（rp/ui/arrisCookingPot.json + Client/Ui/CookingPotProxy.py，只在 CookingPotHost.DOLOR_SCREEN 关掉时用）换成同样的键。
语言文件里少了键时库和引擎显示键名本身，所以每个键两个语言文件里都要有；英文的字按默认字体估过宽度，放得进标题、搜索框和按钮下面那一行。
"""
from __future__ import print_function

import ast
import io
import json
import os
import re

import fdtest

Layouts = fdtest.load("dolorLayouts")
Book = fdtest.load("Shared.Rules.CookingPotBook")
PotMenu = fdtest.load("Shared.Menus.CookingPot")
Data = fdtest.load("dolorContainer.Common.Data")
SCRIPTS = os.path.join(fdtest.BP, fdtest.SCRIPTS)
TEXTS = os.path.join(fdtest.ROOT, "rp", "texts")
SOURCE = os.path.join(fdtest.ROOT, "layouts", "cooking_pot.json")
COMPILED = os.path.join(fdtest.ROOT, "rp", "ui", "dolor_layout_arrisfarmersdelightscripts_arris_cooking_pot.json")
LEGACY = os.path.join(fdtest.ROOT, "rp", "ui", "arrisCookingPot.json")
CJK = re.compile(u"[一-鿿]")
TEXT = type(u"")
ADD_FOOD = "arris_fd.pot_screen.add_food"
SEARCH = "arris_fd.pot_screen.search"
PICK = "arris_fd.pot_screen.pick_recipe"
REMOVED = ("arris_fd.pot_screen.next_variant", "arris_fd.pot_screen.tab_pot", "arris_fd.pot_screen.tab_book")
# 放字的地方有多宽（界面单位，见 layouts/cooking_pot.json）："+"按钮下面那一行 79；搜索框 74，字从框里 3 起，右边 17 给放大镜，
# 剩 53；详情标题 75（长了折成两行，两行以内一行放得下最好）
ROOM = {ADD_FOOD: 79, SEARCH: 53, PICK: 75}
# 默认字体（default8）的字宽，含 1 像素间隔：大多数 6，下面这些窄；汉字 9
NARROW = {"i": 2, "l": 3, "t": 4, "f": 5, "k": 5, " ": 4, ".": 2, ",": 2, "!": 2, "'": 3, "I": 4, "-": 6}


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


def _walk(value):
    """嵌套的字典 / 列表里的每一对 (键, 值)。"""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            for pair in _walk(item):
                yield pair
    elif isinstance(value, list):
        for item in value:
            for pair in _walk(item):
                yield pair


def _width(text):
    return sum(9 if CJK.match(char) else NARROW.get(char, 6) for char in _u(text))


def testEveryWordTheLibraryWritesIsAKeyBothLanguageFilesHave():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    layout = Layouts.LAYOUTS["arris:cooking_pot"]
    labels = [value for key, value in _walk(layout) if key == "label"]
    assert labels == ["", ""], "只有一个按钮（加号，字在贴图上），经典版、携带版的绑定各记一份：%r" % (labels,)
    formats = [value for key, value in _walk(layout) if key == "format"]
    assert sorted(set(formats)) == [ADD_FOOD, "{bookTitle}"] and len(formats) == 4, \
        "文字控件：详情的标题（界面数据）和按钮下面的那一行（语言文件的键），两种界面档各一份：%r" % (formats,)
    assert ADD_FOOD in chinese and ADD_FOOD in english, "两个语言文件里都要有：%s" % ADD_FOOD
    assert not [value for key, value in _walk(layout) if isinstance(value, (str, TEXT)) and CJK.search(_u(value))], "编译出的绑定表里没有写死的中文"


def testTheWordsOfTheRetiredButtonsAndTabsAreGone():
    for language in ("zh_CN.lang", "en_US.lang"):
        words = _lang(language)
        assert not [key for key in REMOVED if key in words], "换一种配方、携带版的两个页签都没有了：%s" % language
        assert sorted(key for key in words if key.startswith("arris_fd.pot_screen.")) == sorted([ADD_FOOD, PICK, SEARCH]), language


def testTheSearchHintIsAKeyTheEngineLooksUpAndTheSourceHasNoWords():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    with io.open(COMPILED, encoding="utf-8") as handle:
        compiled = json.load(handle)
    hints = [value for key, value in _walk(compiled) if key == "$place_holder_text"]
    assert hints == [SEARCH], "两种界面档用同一个内容模板，一个搜索框：%r" % (hints,)
    assert SEARCH in chinese and SEARCH in english
    assert not [value for key, value in _walk(compiled) if isinstance(value, (str, TEXT)) and CJK.search(_u(value))], "界面文件里没有写死的中文"
    with io.open(SOURCE, encoding="utf-8") as handle:
        code = [line for line in handle.read().splitlines() if not line.strip().startswith("//")]
    assert not [line for line in code if CJK.search(line)], "布局源文件里（注释除外）只写键"


def _const(node):
    """字符串常量节点的值（py2 是 Str，py3 是 Constant）；不是为 None。"""
    if type(node).__name__ == "Str":
        return node.s
    if type(node).__name__ == "Constant" and isinstance(node.value, (str, bytes)):
        return node.value
    return None


def _tree(relPath):
    with io.open(os.path.join(SCRIPTS, *relPath.split("/")), "rb") as handle:
        return ast.parse(handle.read())


def testTheTitleIsTheJavaModsContainerKey():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    tree = _tree("Server/CookingPotHost.py")
    titles = [_const(node.value) for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "TITLE" for target in node.targets)]
    assert titles == ["container.farmersdelight.cooking_pot"], titles
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "ContainerType"]
    assert len(calls) == 1 and isinstance(calls[0].args[1], ast.Name) and calls[0].args[1].id == "TITLE", "登记容器类型时的标题就是它"
    assert english[titles[0]] == u"Cooking Pot" and chinese[titles[0]] == u"厨锅", "英文照 JE 的 en_us，中文和方块名一样"


def _render(value, language):
    lang = _lang(language)
    return _u(value.render(lambda key: lang.get(_u(key), key)))


def testTheBookTitleIsALangTextUntilARecipeIsPicked():
    field = PotMenu.CookingPotMenu.data["bookTitle"]
    assert isinstance(field, Data.Lang) and field.scope == Data.VIEWER
    unpicked = field.decode(field.encode(Book.UNPICKED_TITLE))
    assert _render(unpicked, "zh_CN.lang") == u"请选择食谱" and _render(unpicked, "en_US.lang") == u"Pick a recipe"
    picked = field.decode(field.encode(Book.titleOf({"text": u"番茄酱"})))
    assert _render(picked, "en_US.lang") == u"番茄酱", "选了食谱：标题是那道菜的 text，原样显示"
    assert Book.titleOf({"text": 3}) == "3" and Book.titleOf({}) == "", "下游写的 text 不是字：照样能发，不让界面数据的刷新出错"
    for odd in ({"text": 3}, {}, {"text": [1, 2]}):
        field.encode(Book.titleOf(odd))


def testTheEnglishWordsFitWhereTheyAreShown():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    for key, room in sorted(ROOM.items()):
        for language, words in (("zh_CN", chinese), ("en_US", english)):
            assert _width(words[key]) <= room, "%s 的 %s 有 %d 宽，放不进 %d：%s" % (language, key, _width(words[key]), room, words[key])


def testTheOldNativeScreenSaysTheSameKeys():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    with io.open(LEGACY, encoding="utf-8") as handle:
        legacy = json.load(handle)
    words = [value for key, value in _walk(legacy) if key in ("text", "$place_holder_text") and isinstance(value, (str, TEXT))]
    assert not [value for value in words if CJK.search(_u(value))], "旧界面里没有写死的中文：%r" % (words,)
    keys = sorted(set(value for value in words if value.startswith("arris_fd.")))
    assert keys == ["arris_fd.pot_screen.add_food", "arris_fd.pot_screen.pick_recipe", SEARCH], keys
    for key in keys:
        assert key in chinese and key in english
    tree = _tree("Client/Ui/CookingPotProxy.py")
    fallbacks = [node.args for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "of" and isinstance(node.func.value, ast.Name) and node.func.value.id == "Texts"]
    assert [(_const(args[0]), _u(_const(args[1]))) for args in fallbacks] == [(Book.UNPICKED_TITLE["t"], u"请选择食谱")], \
        "代理写的标题经 Texts.of 查，和 dolor 界面同一个键"
    docstrings = set(id(node.body[0].value) for node in ast.walk(tree) if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
                     and node.body and isinstance(node.body[0], ast.Expr) and _const(node.body[0].value) is not None)
    loose = [_u(_const(node)) for node in ast.walk(tree)
             if id(node) not in docstrings and _const(node) is not None and CJK.search(_u(_const(node)))]
    assert loose == [u"请选择食谱"], "代理里的中文（说明除外）只剩 Texts.of 的那句缺省：%r" % (loose,)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
