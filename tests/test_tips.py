# -*- coding: utf-8 -*-
# runner: both
"""服务端提示按玩家的语言给（Shared/Data/Tips、Shared/Rules/TipWire、Server/Helpers/Engine.ShowTip、Client/Endpoints.OnTip）。

服务端不知道玩家用什么语言：ShowTip 只把"哪一句（语言文件的键 + 中文）、填什么"发给那一个玩家（Call(玩家, "OnTip", 载荷)），那个玩家的客户端
按自己的语言查（Client/Texts），填好用 SetTipMessage 弹在物品栏上方。原来是服务端拼好写死的中文、SetOneTipMessage 发过去。这里核对：
- 每一句都在两个语言文件里，中文和代码里的一样，占位的个数对得上；JE 的句子用 JE 的键，英文照 JE 的 en_us.json（抄在下面，离线可跑）；
- 每一处 ShowTip 说的都是表里的一句、给的值和占位一样多，表里每一句都有人说；别处不再直接弹提示；
- 服务端发的载荷守网易 Call 的规矩（键是 str、列表里一种类型、没有 unicode、没有元组），只发给那个玩家；
- 客户端查得到用当前语言，查不到、或者那里的写法填不上值就用跟着发来的中文（不露键名），值里的词（碗）也按语言查，py2 收到的 unicode 不和字节串混着拼。
"""
from __future__ import print_function

import ast
import io
import os
import re
import sys
import types

import fdtest

Tips = fdtest.load("Shared.Data.Tips")
TipWire = fdtest.load("Shared.Rules.TipWire")
SCRIPTS = os.path.join(fdtest.BP, fdtest.SCRIPTS)
TEXTS = os.path.join(fdtest.ROOT, "rp", "texts")
VENDORED = ("QuModLibs", "dolorContainer")
PLACEHOLDER = re.compile(r"%[sd]")
TEXT = type(u"")
# JE 农夫乐事 1.20 的 en_us.json / zh_cn.json 里这几句（我们的中文就是它的 zh_cn；还剩几个那句 JE 写 %s、我们写 %d，填整数是同一句）
JE_ENGLISH = {
    "block.farmersdelight.cutting_board.invalid_item": u"This doesn't seem cuttable...",
    "block.farmersdelight.cutting_board.invalid_tool": u"Maybe with a different tool...",
    "block.farmersdelight.cutting_board.remaining_items": u"%s remaining...",
    "block.farmersdelight.skillet.invalid_item": u"This can't be cooked...",
    "block.farmersdelight.skillet.underwater": u"Can't cook while flooded...",
    "item.farmersdelight.skillet.how_to_cook": u"Use your other hand to hold ingredients!",
    "item.farmersdelight.skillet.underwater": u"Can't cook underwater...",
    "block.farmersdelight.feast.use_container": u"You need a %s to eat this.",
    "block.farmersdelight.rice.invalid_placement": u"This seed must be planted in shallow water.",
}
JE_CHINESE = {
    "block.farmersdelight.cutting_board.invalid_item": u"这东西可不能切啊……",
    "block.farmersdelight.cutting_board.invalid_tool": u"或许得换个工具……",
    "block.farmersdelight.cutting_board.remaining_items": u"还剩%s个……",
    "block.farmersdelight.skillet.invalid_item": u"这东西可不能被烹饪……",
    "block.farmersdelight.skillet.underwater": u"被水泡着可没法烹饪啊……",
    "item.farmersdelight.skillet.how_to_cook": u"用另一只手拿着原料！",
    "item.farmersdelight.skillet.underwater": u"在水里可没法煎啊……",
    "block.farmersdelight.feast.use_container": u"你需要一个%s以食用它。",
    "block.farmersdelight.rice.invalid_placement": u"这株作物很难在水洼外生存。",
}
# 原版语言文件里碗的名字（基岩版 vanilla/texts 的 item.bowl.name）
BOWL_NAMES = {"en_US": u"Bowl", "zh_CN": u"碗"}


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


def _count(text):
    return len(PLACEHOLDER.findall(_u(text)))


def _sample(tip):
    """填这一句用的值：%d 填 3，%s 填碗这个词（只有 feast.use_container 带 %s）。"""
    return tuple(Tips.BOWL if kind == "%s" else 3 for kind in PLACEHOLDER.findall(_u(tip[1])))


def testEverySentenceIsInBothLanguageFilesAndTheChineseOneIsTheCodes():
    chinese, english = _lang("zh_CN.lang"), _lang("en_US.lang")
    assert len(Tips.SENTENCES) == 13 and len(set(key for key, _ in Tips.SENTENCES)) == 13
    for key, text in Tips.SENTENCES:
        assert key in chinese and key in english, "两个语言文件里都要有：%s" % key
        assert chinese[key] == _u(text), "中文的语言文件和代码里的那句一样（代码里的是查不到时用的）：%s" % key
        assert _count(english[key]) == _count(text), "占位的个数对得上：%s" % key
        assert english[key] % tuple([1] * _count(english[key])), "英文的那句填得上：%s" % key
    assert Tips.STOVE_INVALID_ITEM is Tips.SKILLET_INVALID_ITEM, "炉灶烤不了的那句和煎锅的是同一句话、同一个键"


def testTheJavaModsSentencesKeepItsKeysItsEnglishAndItsChinese():
    english = _lang("en_US.lang")
    ours = [key for key, _ in Tips.SENTENCES if key.startswith("arris_fd.tip.")]
    java = [key for key, _ in Tips.SENTENCES if key not in ours]
    assert sorted(java) == sorted(JE_ENGLISH), "JE 有的九句用 JE 的键：%r" % (java,)
    assert sorted(ours) == ["arris_fd.tip.board_unstorable", "arris_fd.tip.dish_on_board", "arris_fd.tip.display_removed", "arris_fd.tip.stove_blocked"]
    for key, text in Tips.SENTENCES:
        if key in JE_ENGLISH:
            assert english[key] == JE_ENGLISH[key], "英文照 JE：%s" % key
            values = tuple(3 for _ in range(_count(text)))
            if key == Tips.FEAST_USE_CONTAINER[0]:
                values = (u"碗",)
            assert _u(text) % values == JE_CHINESE[key] % values, "中文和 JE 的 zh_cn 说的是同一句：%s" % key
    assert _u(Tips.BOWL[1]) == BOWL_NAMES["zh_CN"] and Tips.WORDS == (Tips.BOWL,)


def _sources():
    """农夫乐事脚本里的每个文件：(相对路径, 语法树)。按字节读：py2 的 ast 不收带编码声明的 unicode。"""
    for root, dirs, files in os.walk(SCRIPTS):
        rel = os.path.relpath(root, SCRIPTS).replace("\\", "/")
        if rel.split("/", 1)[0] in VENDORED:
            continue
        for name in sorted(files):
            if name.endswith(".py") and not (rel == "." and name == "dolorLayouts.py"):
                with io.open(os.path.join(root, name), "rb") as handle:
                    yield (name if rel == "." else rel + "/" + name), ast.parse(handle.read())


def _callee(node):
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else None)


def _tipsAttribute(node):
    """Tips.XXX 这样的写法 -> 表里的那个值；不是就 None。"""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "Tips":
        return getattr(Tips, node.attr, None)
    return None


def testEveryShowTipSaysASentenceFromTheTableWithAsManyValuesAsItHasPlaceholders():
    sites, used = [], set()
    for relPath, tree in _sources():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _callee(node) == "ShowTip"):
                continue
            where = "%s:%d" % (relPath, node.lineno)
            sites.append(where)
            assert not node.keywords and getattr(node, "starargs", None) is None and getattr(node, "kwargs", None) is None, where
            assert not [arg for arg in node.args if type(arg).__name__ == "Starred"], where
            assert len(node.args) >= 2, "ShowTip(玩家, Tips.某句, 值...)：%s" % where
            tip = _tipsAttribute(node.args[1])
            assert tip in Tips.SENTENCES, "说的要是 Shared/Data/Tips 里的一句（不是写死的字）：%s" % where
            values = node.args[2:]
            assert len(values) == _count(tip[1]), "给的值和占位一样多：%s" % where
            for value in values:
                word = _tipsAttribute(value)
                assert word is None or word in Tips.WORDS, "值里的词也要在表里：%s" % where
            used.add(tip)
    assert len(sites) == 14, "砧板 4、炉灶 2、放下的煎锅 2、手里的煎锅 2、盘装的菜、稻米、工作台的砧板菜、展示实体删除器各 1：%r" % (sites,)
    assert used == set(Tips.SENTENCES), "表里每一句都有人说：没人说的 %r" % (set(Tips.SENTENCES) - used,)


def testNothingElseWritesATipOnThePlayersScreen():
    found = []
    for relPath, tree in _sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("SetOneTipMessage", "SetTipMessage"):
                found.append((relPath, node.attr))
    assert found == [("Client/Endpoints.py", "SetTipMessage")], "提示只有客户端的 OnTip 弹（服务端不知道玩家的语言）：%r" % (found,)


def _walk(value, where="载荷"):
    """网易 Call 载荷的规矩：键是 str、列表里一种类型、没有 unicode、没有元组。返回不合的地方。"""
    problems = []
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or (TEXT is not str and isinstance(key, TEXT)):
                problems.append("%s 的键 %r 不是 str" % (where, key))
            problems += _walk(item, "%s.%s" % (where, key))
    elif isinstance(value, list):
        if len(set(type(item) for item in value)) > 1:
            problems.append("%s 的列表里类型不一样" % where)
        for index, item in enumerate(value):
            problems += _walk(item, "%s[%d]" % (where, index))
    elif isinstance(value, tuple):
        problems.append("%s 是元组（到对端会变成列表）" % where)
    elif TEXT is not str and isinstance(value, TEXT):
        problems.append("%s 是 unicode" % where)
    return problems


def testTheMessageCarriesTheKeyTheChineseAndTheValuesWithinTheEnginesRules():
    message = TipWire.message(Tips.FEAST_USE_CONTAINER, (Tips.BOWL,))
    assert message == {"key": "block.farmersdelight.feast.use_container", "text": Tips.FEAST_USE_CONTAINER[1],
                       "values": [{"key": "item.bowl.name", "text": Tips.BOWL[1]}]}
    assert TipWire.message(Tips.BOARD_REMAINING, (3,))["values"] == [{"v": 3}]
    assert TipWire.message(Tips.STOVE_BLOCKED)["values"] == []
    for tip in Tips.SENTENCES:
        assert not _walk(TipWire.message(tip, _sample(tip))), _walk(TipWire.message(tip, _sample(tip)))
    mixed = TipWire.message(("k", "%d %s"), (2, Tips.BOWL))
    assert not _walk(mixed), "数和词混着也是一列字典"
    assert TipWire.read(mixed) == ("k", "%d %s", (2, Tips.BOWL))


def _unicodeDeep(value):
    """py2 里引擎交到对端的字可能是 unicode：载荷里的字都换成 unicode 再交给客户端。"""
    if isinstance(value, dict):
        return dict((_unicodeDeep(key), _unicodeDeep(item)) for key, item in value.items())
    if isinstance(value, list):
        return [_unicodeDeep(item) for item in value]
    return value.decode("utf-8") if isinstance(value, bytes) else value


# ---------------------------------------------------------------- 服务端：真的 Engine.ShowTip，QuModLibs.Server 换成假的

sent = []


def _installServer():
    class _Enum(object):
        ItemPosType = EntityType = object()

    class _ServerApi(object):
        @staticmethod
        def GetEngineCompFactory():
            return object()

        @staticmethod
        def GetMinecraftEnum():
            return _Enum()

    server = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Server")
    server.serverApi, server.levelId, server.System, server.DestroyEntity = _ServerApi(), "level", object(), lambda entityId: True
    server.Call = lambda playerId, endpoint, *args: sent.append((playerId, endpoint) + args)
    sys.modules[server.__name__] = server
    return fdtest.load("Server.Helpers.Engine")


Engine = _installServer()


def testTheServerSendsWhichSentenceAndWhatToFillInOnlyToThatPlayer():
    del sent[:]
    Engine.ShowTip("p1", Tips.BOARD_REMAINING, 3)
    Engine.ShowTip("p2", Tips.FEAST_USE_CONTAINER, Tips.BOWL)
    assert sent == [("p1", "OnTip", TipWire.message(Tips.BOARD_REMAINING, (3,))),
                    ("p2", "OnTip", TipWire.message(Tips.FEAST_USE_CONTAINER, (Tips.BOWL,)))], "只发给那个玩家（不是 \"*\"），一个载荷"
    assert TipWire.ENDPOINT == "OnTip"


# ---------------------------------------------------------------- 客户端：真的 Endpoints.OnTip 和 Texts，Client/Engine、QuModLibs.Client 换成假的

endpoints, shown, lang = {}, [], {}


def _installClient():
    class _Game(object):
        @staticmethod
        def GetChinese(key):
            return lang.get(_u(key), key)          # 引擎：现在这种语言下的那一句（unicode），找不到原样还键

        @staticmethod
        def SetTipMessage(text):
            shown.append(text)
            return True

    class _Factory(object):
        @staticmethod
        def CreateGame(target):
            assert target == "level"
            return _Game()

    def allowCall(func):
        endpoints[func.__name__] = func
        return func

    client = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Client")
    client.AllowCall = allowCall
    engine = types.ModuleType(fdtest.SCRIPTS + ".Client.Engine")
    engine.compFactory, engine.levelId, engine.playerId = _Factory(), "level", "p1"
    sys.modules[client.__name__], sys.modules[engine.__name__] = client, engine
    return fdtest.load("Client.Endpoints")


Endpoints = _installClient()


def _speak(language, tip, *values):
    """服务端说这一句，载荷照引擎可能的样子（py2 里字变成 unicode）交给客户端，language 的语言文件 + 原版碗的名字；返回玩家看到的那句。"""
    lang.clear()
    if language:
        lang.update(_lang(language + ".lang"))
        lang["item.bowl.name"] = BOWL_NAMES[language]
    del sent[:], shown[:]
    Engine.ShowTip("p1", tip, *values)
    playerId, endpoint, payload = sent[0]
    endpoints[endpoint](_unicodeDeep(payload))
    assert len(shown) == 1 and isinstance(shown[0], str), "弹一句；py2 里是 utf-8 的字节串（和物品名一个类型）：%r" % (shown,)
    return _u(shown[0])


def testTheClientSaysEverySentenceInThePlayersLanguage():
    assert "OnTip" in endpoints, "客户端登记了和 TipWire.ENDPOINT 同名的端点"
    english, chinese = _lang("en_US.lang"), _lang("zh_CN.lang")
    for tip in Tips.SENTENCES:
        values = _sample(tip)
        filled = tuple(BOWL_NAMES["en_US"] if isinstance(value, tuple) else value for value in values)
        assert _speak("en_US", tip, *values) == english[tip[0]] % filled, tip[0]
        filled = tuple(BOWL_NAMES["zh_CN"] if isinstance(value, tuple) else value for value in values)
        assert _speak("zh_CN", tip, *values) == chinese[tip[0]] % filled, tip[0]
    assert _speak("en_US", Tips.BOARD_REMAINING, 3) == u"3 remaining..."
    assert _speak("en_US", Tips.FEAST_USE_CONTAINER, Tips.BOWL) == u"You need a Bowl to eat this."
    assert _speak("zh_CN", Tips.FEAST_USE_CONTAINER, Tips.BOWL) == u"你需要一个碗以食用它。", "中文的游戏里和原来一字不差"


def testWithoutTheLineOrWithAWordingThatCannotTakeTheValuesTheChineseIsShown():
    assert _speak(None, Tips.BOARD_REMAINING, 5) == u"还剩5个……", "语言文件里没有这一句：跟着发来的中文，不露键名"
    assert _speak(None, Tips.FEAST_USE_CONTAINER, Tips.BOWL) == u"你需要一个碗以食用它。", "碗也查不到：词也用中文"
    assert _speak(None, Tips.DISPLAY_REMOVED) == u"§7物品展示实体 §a删除成功!"
    lang.clear()
    lang["block.farmersdelight.cutting_board.remaining_items"] = u"Some left..."
    del sent[:], shown[:]
    Engine.ShowTip("p1", Tips.BOARD_REMAINING, 2)
    endpoints["OnTip"](sent[0][2])
    assert _u(shown[0]) == u"还剩2个……", "资源包把这句写得填不上值：用中文，不出错"
    lang["block.farmersdelight.cutting_board.remaining_items"] = u"%d of %d left"
    del shown[:]
    endpoints["OnTip"](sent[0][2])
    assert _u(shown[0]) == u"还剩2个……"


def testAWordTheLanguageFileLacksFallsBackOnItsOwn():
    lang.clear()
    lang.update(_lang("en_US.lang"))
    del sent[:], shown[:]
    Engine.ShowTip("p1", Tips.FEAST_USE_CONTAINER, Tips.BOWL)
    endpoints["OnTip"](sent[0][2])
    assert _u(shown[0]) == u"You need a 碗 to eat this.", "句子查得到、词查不到：词用中文，句子照当前语言"


def testANumberIsWrittenTheWayTheChineseSentenceWritesItInEveryLanguage():
    """中文写 %d 的一格，英文常写 %s（JE、HoD 的英文就是）：数照中文的 %d 先换成整数，不会写成 3.0。
    还剩几个是整数，可网上过来的数、别处交来的时长都可能是小数（JEI 的秒数就是 6.0：英文原来写成了 6.0 s）。"""
    Texts = Endpoints.Texts
    for language, expected in (("en_US", u"3 remaining..."), ("zh_CN", u"还剩3个……"), (None, u"还剩3个……")):
        lang.clear()
        if language:
            lang.update(_lang(language + ".lang"))
        del shown[:]
        endpoints["OnTip"](TipWire.message(Tips.BOARD_REMAINING, (3.0,)))
        assert _u(shown[0]) == expected, (language, shown)
    lang.clear()
    lang.update(_lang("en_US.lang"))
    assert Texts.fill("handson_delight.book.seconds", "%d 秒", 6.0) == "6 s" and Texts.fill("handson_delight.book.seconds", "%d 秒", 30.0) == "30 s"
    assert Texts.fill("handson_delight.pot.cooking", "%s，还要 %d 秒", ("Soup", 7.9)) == "Soup in 7 s", "和中文的 %d 一样截掉小数"
    assert Texts.fill("arris_fd.pot.scoop", "盛出 %s", "Soup") == "Serve Soup", "只有一个值、不是元组也照旧"
    lang.clear()
    assert Texts.fill("handson_delight.pot.cooking", "%s，还要 %d 秒", ("Soup", 7.9)) == "Soup，还要 7 秒"
    assert Texts.fill("k", "100%% %s", 2.5) == "100% 2.5", "%% 不算占位；中文写 %s 的一格照原样"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
