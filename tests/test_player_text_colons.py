# -*- coding: utf-8 -*-
# runner: both
"""给玩家看的字里冒号的写法：不许有全角冒号"："，英文冒号后面要空一格。

游戏的字体把全角标点画得窄、后面不留空，冒号后面的字会挤在一起。写英文冒号加一个空格（": "）；
句末（后面是字符串结束）和换行前的冒号只写英文冒号，不加空格。两条：

1. 没有全角冒号。玩家读得到的每一处都查：
   - rp/texts/*.lang 每一行的值；
   - Shared/Data/Tips 每一句的缺省中文（语言文件里找不到那一句时客户端显示的那句）；
   - 厨锅物品的悬停文字（Shared/Rules/PotItem 的 TIP_ONE / TIP_MANY 和 tipsOf 拼出来的整段）；
   - 砧板摆盘时焦点界面底部的那一行（Shared/Rules/DishStation.statusText 对各种站点数据说的话）；
   - 成就系统的标题和描述（Shared/Data/Advancements.TEXTS）；
   - 指南书的分类名、标题、正文（Shared/Data/GuideBook.config；namespace 是界面上显示在图标旁边的物品 ID，也查全角）；
   - bp/netease_items_beh/*.json、bp/netease_blocks/*.json 里的每个字符串值（物品 / 方块的悬停说明等；去掉注释后解析，解析不了的按文本找）。
2. 英文冒号后面是空格、换行或句末。只查上面的句子（语言文件、Tips、PotItem、statusText、成就文字、指南书的分类 / 标题 / 正文），
   不查物品 / 方块 JSON（里面有 05:00 这样的时间）。先去掉 § 加一个字符的颜色码（玩家看不到："装有3份:§r" 后面接着换行）；
   SHAPES 里的三种写法是例外，只放过冒号落在这些写法里面的那一处，同一句里别的冒号照查：物品 / 方块 / 标签的 ID
   （statusText 没给菜名时把 ID 露在句子里）、网址、时间。不在这张表里的写法一律报，不整类放过。

日志、print、接口的出错信息、注释、文档里的冒号不管。失败信息写明是哪个文件、哪一句、哪一条。照 JE 翻译抄来的句子也一样换（JE 的 zh_cn.json 用全角冒号）。
py2 里引擎的字符串是 utf-8 的字节串：比之前都换成 unicode，"出处"那一栏一律写 unicode 字面量（字节串里的中文和 unicode 拼会抛 UnicodeDecodeError）。
"""
from __future__ import print_function

import io
import json
import os
import re

import fdtest

Tips = fdtest.load("Shared.Data.Tips")
PotItem = fdtest.load("Shared.Rules.PotItem")
DishStation = fdtest.load("Shared.Rules.DishStation")
Advancements = fdtest.load("Shared.Data.Advancements")
GuideBook = fdtest.load("Shared.Data.GuideBook")
PackJson = fdtest.load("Server.Helpers.PackJson")

COLON = b"\xef\xbc\x9a".decode("utf-8")         # 全角冒号 U+FF1A（写成字节：源码里的字符肉眼和英文冒号分不清）
FORMAT_CODE = re.compile(u"§.")                  # § 加一个字符：颜色 / 样式码，玩家看不到
# 英文冒号后面不是空格 / 换行 / 句末也合法的写法：[(叫什么, 正则)]。只放过冒号落在这些写法里面的那一处。
# ID 的命名空间写死这几个（别的词不算：note:this 要报）；数字只认 ASCII（[0-9]，py3 的 \d 连全角数字也认）。
SHAPES = (
    (u"物品 / 方块 / 标签的 ID", re.compile(r"(?:minecraft|arris|farmersdelight|common|netease):[a-z0-9_./]+")),   # minecraft:bowl、#common:knife
    (u"网址", re.compile(r"https?://\S+")),
    (u"时间", re.compile(r"[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?")),                                                       # 05:00、1:30:00
)
TEXT = type(u"")
STRINGS = (str, TEXT)             # py2：字节串和 unicode；py3：str
SCRIPTS = "bp/" + fdtest.SCRIPTS
TEXTS_DIR = os.path.join(fdtest.ROOT, "rp", "texts")
JSON_DIRS = ("bp/netease_items_beh", "bp/netease_blocks")


def _u(text):
    """py2 里引擎的字符串是 utf-8 的字节串，换成 unicode 再比；py3 的 str 原样。"""
    return text.decode("utf-8") if isinstance(text, bytes) else text


def _check(found, where, text):
    """第 1 条：text 里有全角冒号就记一笔 (出处, 那一句, 哪一条)。"""
    sentence = _u(text)
    entry = (where, sentence, u"全角冒号")
    if COLON in sentence and entry not in found:
        found.append(entry)


def _unspaced(text):
    """第 2 条：英文冒号后面既不是空格、换行也不是句末的那几处 [冒号前后各几个字]。先去掉 § 码，再把 SHAPES 里的写法盖掉（只盖那一段）。"""
    plain = FORMAT_CODE.sub(u"", _u(text))
    for _, shape in SHAPES:
        plain = shape.sub(lambda match: u"_" * len(match.group(0)), plain)
    return [plain[max(0, at - 6):at + 7] for at in range(len(plain)) if plain[at] == u":" and plain[at + 1:at + 2] not in (u"", u" ", u"\n")]


def _prose(found, where, text):
    """玩家读的一句话：两条都查。"""
    _check(found, where, text)
    for around in _unspaced(text):
        entry = (where, _u(text), u"英文冒号后面要空一格（句末、换行前不用）: …%s…" % around.replace(u"\n", u"\\n"))
        if entry not in found:
            found.append(entry)


def _report(found):
    """失败信息：py2 的断言信息要给字节串（带中文的 unicode 在回溯里会被转义），py3 给 str。"""
    lines = u"\n".join(u"  %s [%s]: %s" % (where, problem, sentence.replace(u"\n", u"\\n")) for where, sentence, problem in found)
    message = u"给玩家看的字里冒号的写法不对（不用全角冒号；英文冒号后面空一格，句末和换行前不空），共 %d 处:\n%s" % (len(found), lines)
    return message if str is TEXT else message.encode("utf-8")


def _langLines():
    """[(语言文件的相对路径, 行号, 键, 值)]：# 开头的注释行、没有等号的行跳过，值后面 tab + # 起的行内注释不算。"""
    lines = []
    for name in sorted(os.listdir(TEXTS_DIR)):
        if not name.endswith(".lang"):
            continue
        with io.open(os.path.join(TEXTS_DIR, name), encoding="utf-8-sig") as handle:
            for number, line in enumerate(handle.read().splitlines(), 1):
                if line.lstrip().startswith(u"#") or u"=" not in line:
                    continue
                key, _, value = line.partition(u"=")
                lines.append(("rp/texts/" + name, number, key, value.split(u"\t#", 1)[0]))
    return lines


def _sentencesOf(module):
    """Tips 里的每一句 (键, 中文)：SENTENCES 和 WORDS，再加模块里别的 (键, 中文) 常量（新加的句子忘了列进去也不漏）。"""
    found = list(module.SENTENCES) + list(module.WORDS)
    for name in sorted(vars(module)):
        value = getattr(module, name)
        if name.isupper() and isinstance(value, tuple) and len(value) == 2 and all(isinstance(part, STRINGS) for part in value):
            found.append(value)
    unique = []
    for entry in found:
        if entry not in unique:
            unique.append(entry)
    return unique


def _jsonStrings(node, path):
    """JSON 里的每个字符串值：[(键的路径, 文字)]（键本身不是给玩家看的，不查）。"""
    found = []
    if isinstance(node, dict):
        for key in sorted(node):
            found.extend(_jsonStrings(node[key], path + u"/" + key))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_jsonStrings(item, u"%s[%d]" % (path, index)))
    elif isinstance(node, STRINGS):
        found.append((path, node))
    return found


def _jsonFiles():
    """[(相对路径, 剥了注释的文本)]：物品、方块的行为包 JSON（带 BOM 的也收）。"""
    files = []
    for directory in JSON_DIRS:
        base = os.path.join(fdtest.ROOT, directory)
        for name in sorted(os.listdir(base)):
            if name.endswith(".json"):
                with io.open(os.path.join(base, name), encoding="utf-8-sig") as handle:
                    files.append((u"%s/%s" % (directory, name), PackJson.stripComments(handle.read())))
    return files


def _jsonFindings(files):
    """物品 / 方块 JSON 只查第 1 条（悬停说明里有 05:00 这样的时间，英文冒号后面不一定是空格）。"""
    found = []
    for path, text in files:
        try:
            parsed = json.loads(text)
        except ValueError:
            # 解析不了：按文本找，写出哪一行
            for number, line in enumerate(text.splitlines(), 1):
                _check(found, u"%s:%d（JSON 解析不了，按文本找）" % (path, number), line.strip())
            continue
        for where, value in _jsonStrings(parsed, u""):
            _check(found, u"%s %s" % (path, where), value)
    return found


# ---------------------------------------------------------------- 测试

def testTheCheckerFlagsWhatItShouldAndLetsTheRestThrough():
    # 防止这条测试自己瞎了，也钉住例外的范围
    found = []
    _check(found, u"a", u"做好了" + COLON + u"点一下")
    _check(found, u"b", u"做好了: 点一下")
    _check(found, u"c", (u"做好了" + COLON).encode("utf-8"))                 # py2 引擎给的是字节串
    assert [where for where, _, _ in found] == [u"a", u"c"], found
    assert COLON.encode("utf-8") == b"\xef\xbc\x9a"
    # 第 2 条：后面是空格、换行、句末都行，§ 码不算
    for fine in (u"摆: 右键", u"装有3份:", u"装有3份:§r\n番茄酱", u"一次处理一件:\n刀切", u"Hold: Stick in", u"没有冒号"):
        assert _unspaced(fine) == [], fine
    for bad in (u"摆:右键", u"Hold:Stick in", u"note:this", u"装有3份:§r番茄酱", u"%s:%s", u"见:好"):
        assert _unspaced(bad), bad
    # SHAPES 的例外：ID（命名空间是写死的几个）、网址、时间；只放过落在写法里面的那个冒号
    for fine in (u"做成arris:x 也可以", u"用 minecraft:bowl 盛", u"见 #common:knife", u"网址 https://example.com/a:b 里", u"还剩 05:00", u"1:30:00"):
        assert _unspaced(fine) == [], fine
    for bad in (u"minecraft:bowl:装", u"arris:x:右键", u"05:零", u"3:4", u"x:y", u"https:右键"):
        assert _unspaced(bad), bad
    # 两条一起查、失败信息写明哪个文件哪一句哪一条
    found = []
    _prose(found, u"x.lang:1", u"摆:右键")
    _prose(found, u"x.lang:2", u"摆" + COLON + u"右键")
    report = _u(_report(found))
    assert u"x.lang:1" in report and u"摆:右键" in report and u"空一格" in report, report
    assert u"x.lang:2" in report and u"摆" + COLON + u"右键" in report and u"全角冒号" in report and u"共 2 处" in report, report
    # JSON：注释剥得掉、全角冒号认得出、解析不了的按文本找、英文冒号不查后面
    parsed = json.loads(PackJson.stripComments(u'{"a": {"b": ["x' + COLON + u'", 1]}, "c": "y"} // 注释' + COLON))
    assert _jsonStrings(parsed, u"") == [(u"/a/b[0]", u"x" + COLON), (u"/c", u"y")]
    files = [(u"t.json", u'{"a": "x' + COLON + u'"}'), (u"u.json", u"{ 坏的" + COLON),
             (u"v.json", PackJson.stripComments(u'{"a": "ok"} /* ' + COLON + u' */ // ' + COLON)),                  # 注释里的不算
             (u"w.json", u'{"a": "速度 (05:00)", "b": "狗时:\\n速度"}')]
    assert [where for where, _, _ in _jsonFindings(files)] == [u"t.json /a", u"u.json:1（JSON 解析不了，按文本找）"]
    report = _u(_report(_jsonFindings(files[:1])))
    assert u"t.json /a" in report and u"x" + COLON in report and u"共 1 处" in report, "失败信息写明是哪个文件、哪一句"


def testTheLanguageFilesColonsAreRight():
    lines = _langLines()
    assert len(lines) > 100 and set(name for name, _, _, _ in lines) >= set(["rp/texts/zh_CN.lang", "rp/texts/en_US.lang"]), "语言文件读到了"
    found = []
    for name, number, key, value in lines:
        _prose(found, u"%s:%d（%s）" % (name, number, key), value)
    assert not found, _report(found)


def testTheServerTipsColonsAreRight():
    sentences = _sentencesOf(Tips)
    assert len(sentences) >= len(Tips.SENTENCES) > 0, "提示表读到了"
    found = []
    for key, text in sentences:
        _prose(found, u"%s/Shared/Data/Tips.py（%s）" % (SCRIPTS, _u(key)), text)
    assert not found, _report(found)


def testThePotItemTooltipColonsAreRight():
    found = []
    here = u"%s/Shared/Rules/PotItem.py" % SCRIPTS
    _prose(found, here + u" TIP_ONE", PotItem.TIP_ONE)
    _prose(found, here + u" TIP_MANY", PotItem.TIP_MANY)
    _prose(found, here + u" tipsOf(.., 1)", PotItem.tipsOf("x", 1))
    _prose(found, here + u" tipsOf(.., 3)", PotItem.tipsOf("x", 3))
    assert not found, _report(found)


def testTheBoardStatusLineColonsAreRight():
    dish = {"newItemName": "arris:egg_sandwich", "count": 2}
    stations = ({}, {"layers": []}, {"dish": dish}, {"layers": [{"newItemName": "minecraft:bread", "count": 3}]},
                {"layers": [{}, {}], "ready": "arris:x"})
    found = []
    seen = set()
    for data in stations:
        for nameOf in (None, lambda name: "dish"):                  # 没给菜名时句子里露出来的是物品 ID（SHAPES 放过它）
            text = DishStation.statusText(data, nameOf)
            seen.add(text)
            _prose(found, u"%s/Shared/Rules/DishStation.py statusText(%s)" % (SCRIPTS, u", ".join(sorted(data)) or u"空的"), text)
    assert len(seen) >= 5, "几种站点数据说的话都看到了：%d 句" % len(seen)
    assert not found, _report(found)


def testTheAdvancementTextsColonsAreRight():
    assert len(Advancements.TEXTS) >= 21, "JE 的 21 条进度"
    found = []
    for name in sorted(Advancements.TEXTS):
        title, description = Advancements.TEXTS[name]
        _prose(found, u"%s/Shared/Data/Advancements.py TEXTS[%s] 标题" % (SCRIPTS, name), title)
        _prose(found, u"%s/Shared/Data/Advancements.py TEXTS[%s] 描述" % (SCRIPTS, name), description)
    assert not found, _report(found)


def testTheGuideBookColonsAreRight():
    config = GuideBook.config
    here = u"%s/Shared/Data/GuideBook.py" % SCRIPTS
    pages = sum(len(config[category]) for category in config)
    assert len(config) >= 4 and pages >= 30, "指南书读到了：%d 类 %d 页" % (len(config), pages)
    found = []
    for category in sorted(config):
        _prose(found, u"%s 分类「%s」" % (here, _u(category)), category)
        for page in config[category]:
            where = u"%s %s/%s" % (here, _u(category), _u(page["title"]))
            _prose(found, where + u" 标题", page["title"])
            _prose(found, where + u" 正文", page["content"])
            _check(found, where + u" namespace", page["namespace"])    # 物品 ID（界面上显示在图标旁边）：只查全角，英文冒号是 ID 自己的
    assert not found, _report(found)


def testTheItemAndBlockJsonHaveNoFullWidthColon():
    files = _jsonFiles()
    assert len(files) > 100, "物品和方块的 JSON 读到了：%d" % len(files)
    assert not [path for path, text in files if not text.strip()], "没有空文件"
    found = _jsonFindings(files)
    assert not found, _report(found)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
