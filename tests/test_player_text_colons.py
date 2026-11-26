# -*- coding: utf-8 -*-
# runner: both
"""给玩家看的字里不许有全角冒号"："：游戏的字体把全角标点画得窄、后面不留空，冒号后面的字会挤在一起。

写英文冒号加一个空格（": "）；句末（后面是换行或字符串结束）的冒号只写英文冒号，不加空格。
日志、print、接口的出错信息、注释、文档里的全角冒号不管，这里只看玩家读得到的几处：
- rp/texts/*.lang 每一行的值；
- Shared/Data/Tips 每一句的缺省中文（语言文件里找不到那一句时客户端显示的那句）；
- 厨锅物品的悬停文字（Shared/Rules/PotItem 的 TIP_ONE / TIP_MANY 和 tipsOf 拼出来的整段）；
- 砧板摆盘时焦点界面底部的那一行（Shared/Rules/DishStation.statusText 对各种站点数据说的话）；
- 成就系统的标题和描述（Shared/Data/Advancements.TEXTS）；
- bp/netease_items_beh/*.json、bp/netease_blocks/*.json 里的每个字符串值（物品 / 方块的悬停说明等；去掉注释后解析，解析不了的按文本找）。
失败信息写明是哪个文件、哪一句。照 JE 翻译抄来的句子也一样换（JE 的 zh_cn.json 用全角冒号）。
py2 里引擎的字符串是 utf-8 的字节串：比之前都换成 unicode，"出处"那一栏一律写 unicode 字面量（字节串里的中文和 unicode 拼会抛 UnicodeDecodeError）。
"""
from __future__ import print_function

import io
import json
import os

import fdtest

Tips = fdtest.load("Shared.Data.Tips")
PotItem = fdtest.load("Shared.Rules.PotItem")
DishStation = fdtest.load("Shared.Rules.DishStation")
Advancements = fdtest.load("Shared.Data.Advancements")
PackJson = fdtest.load("Server.Helpers.PackJson")

COLON = u"："
TEXT = type(u"")
STRINGS = (str, TEXT)             # py2：字节串和 unicode；py3：str
SCRIPTS = "bp/" + fdtest.SCRIPTS
TEXTS_DIR = os.path.join(fdtest.ROOT, "rp", "texts")
JSON_DIRS = ("bp/netease_items_beh", "bp/netease_blocks")


def _u(text):
    """py2 里引擎的字符串是 utf-8 的字节串，换成 unicode 再比；py3 的 str 原样。"""
    return text.decode("utf-8") if isinstance(text, bytes) else text


def _check(found, where, text):
    """text 里有全角冒号就记一笔：(出处, 那一句)。"""
    sentence = _u(text)
    if COLON in sentence and (where, sentence) not in found:
        found.append((where, sentence))


def _report(found):
    """失败信息：py2 的断言信息要给字节串（带中文的 unicode 在回溯里会被转义），py3 给 str。"""
    lines = u"\n".join(u"  %s: %s" % (where, sentence.replace(u"\n", u"\\n")) for where, sentence in found)
    message = u"给玩家看的字里有全角冒号（写英文冒号加一个空格；句末的只写英文冒号），共 %d 处:\n%s" % (len(found), lines)
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

def testTheCheckerSeesAFullWidthColon():
    # 防止这条测试自己瞎了：全角冒号认得出、英文冒号不报、py2 的字节串也认、JSON 的注释剥得掉、解析不了的按文本找
    found = []
    _check(found, u"a", u"做好了" + COLON + u"点一下")
    _check(found, u"b", u"做好了: 点一下")
    _check(found, u"c", (u"做好了" + COLON).encode("utf-8"))
    assert [where for where, _ in found] == [u"a", u"c"], found
    assert COLON.encode("utf-8") == b"\xef\xbc\x9a"
    parsed = json.loads(PackJson.stripComments(u'{"a": {"b": ["x' + COLON + u'", 1]}, "c": "y"} // 注释' + COLON))
    assert _jsonStrings(parsed, u"") == [(u"/a/b[0]", u"x" + COLON), (u"/c", u"y")]
    files = [(u"t.json", u'{"a": "x' + COLON + u'"}'), (u"u.json", u"{ 坏的" + COLON),
             (u"v.json", PackJson.stripComments(u'{"a": "ok"} /* ' + COLON + u' */ // ' + COLON))]     # 注释里的不算
    assert [where for where, _ in _jsonFindings(files)] == [u"t.json /a", u"u.json:1（JSON 解析不了，按文本找）"]
    report = _u(_report(_jsonFindings(files[:1])))
    assert u"t.json /a" in report and u"x" + COLON in report and u"共 1 处" in report, "失败信息写明是哪个文件、哪一句"


def testTheLanguageFilesHaveNone():
    lines = _langLines()
    assert len(lines) > 100 and set(name for name, _, _, _ in lines) >= set(["rp/texts/zh_CN.lang", "rp/texts/en_US.lang"]), "语言文件读到了"
    found = []
    for name, number, key, value in lines:
        _check(found, u"%s:%d（%s）" % (name, number, key), value)
    assert not found, _report(found)


def testTheServerTipsHaveNone():
    sentences = _sentencesOf(Tips)
    assert len(sentences) >= len(Tips.SENTENCES) > 0, "提示表读到了"
    found = []
    for key, text in sentences:
        _check(found, u"%s/Shared/Data/Tips.py（%s）" % (SCRIPTS, _u(key)), text)
    assert not found, _report(found)


def testThePotItemTooltipHasNone():
    found = []
    here = u"%s/Shared/Rules/PotItem.py" % SCRIPTS
    _check(found, here + u" TIP_ONE", PotItem.TIP_ONE)
    _check(found, here + u" TIP_MANY", PotItem.TIP_MANY)
    _check(found, here + u" tipsOf(.., 1)", PotItem.tipsOf("x", 1))
    _check(found, here + u" tipsOf(.., 3)", PotItem.tipsOf("x", 3))
    assert not found, _report(found)


def testTheBoardStatusLineHasNone():
    dish = {"newItemName": "arris:egg_sandwich", "count": 2}
    stations = ({}, {"layers": []}, {"dish": dish}, {"layers": [{"newItemName": "minecraft:bread", "count": 3}]},
                {"layers": [{}, {}], "ready": "arris:x"})
    found = []
    seen = set()
    for data in stations:
        for nameOf in (None, lambda name: "dish"):
            text = DishStation.statusText(data, nameOf)
            seen.add(text)
            _check(found, u"%s/Shared/Rules/DishStation.py statusText(%s)" % (SCRIPTS, u", ".join(sorted(data)) or u"空的"), text)
    assert len(seen) >= 5, "几种站点数据说的话都看到了：%d 句" % len(seen)
    assert not found, _report(found)


def testTheAdvancementTextsHaveNone():
    assert len(Advancements.TEXTS) >= 21, "JE 的 21 条进度"
    found = []
    for name in sorted(Advancements.TEXTS):
        title, description = Advancements.TEXTS[name]
        _check(found, u"%s/Shared/Data/Advancements.py TEXTS[%s] 标题" % (SCRIPTS, name), title)
        _check(found, u"%s/Shared/Data/Advancements.py TEXTS[%s] 描述" % (SCRIPTS, name), description)
    assert not found, _report(found)


def testTheItemAndBlockJsonHaveNone():
    files = _jsonFiles()
    assert len(files) > 100, "物品和方块的 JSON 读到了：%d" % len(files)
    assert not [path for path, text in files if not text.strip()], "没有空文件"
    found = _jsonFindings(files)
    assert not found, _report(found)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
