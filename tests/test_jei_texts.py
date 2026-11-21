# -*- coding: utf-8 -*-
# runner: both
"""JEI 配方页上我们自己写的字按玩家的语言给（Compat/Jei：厨锅、砧板、煎锅、炉灶四个分类的名字，煎锅 / 炉灶配方页上的秒数；砧板摆盘那一类原来就是）。

分类名在客户端界面就绪、登记分类时经 Texts.of 按玩家的语言查，秒数在配方页建出来时经 Texts.fill 写；语言文件里没有时用代码里的中文。
JE 的 JEI 有的分类用它的键（jei.farmersdelight.cooking / cutting，英文照 JE 的 en_us）；煎锅、炉灶在 JE 归原版的营火一类，这里是我们的键 arris_fd.jei.*；
秒数和站点食谱书页脚是同一句，用 HoD 的键 handson_delight.book.seconds。
这里核对：Compat/Jei 里写死的中文（说明、注释除外）都是 (键, 中文) 的缺省或 Texts 调用的缺省，键两个语言文件里都有、中文和代码里的一样、占位的个数对得上；
登记分类时给的名字都经 Texts.of 查。
"""
from __future__ import print_function

import ast
import io
import os
import re

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


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
