# -*- coding: utf-8 -*-
# runner: py3
"""按字符串登记给引擎 / 框架的模块路径都能解析到文件，类名也存在。

这些路径写错不会有任何离线报错：MOD.Server / MOD.Client 的模块、RegisterScreenProxy 的代理类、
RegisterUI 的界面类。挪文件或改名时忘了同步，只有进游戏打开界面那一刻才会失败。
"""
from __future__ import print_function

import ast
import io
import os
import re

import fdtest

SCRIPTS_DIR = os.path.join(fdtest.BP, fdtest.SCRIPTS)


def _moduleFile(dotted):
    """"arrisFarmersDelightScripts.Client.ModClient" → 文件路径（模块或包）。"""
    parts = dotted.split(".")
    base = os.path.join(fdtest.BP, *parts)
    for candidate in (base + ".py", os.path.join(base, "__init__.py")):
        if os.path.isfile(candidate):
            return candidate
    return None


def _definesClass(path, className):
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    return any(isinstance(node, ast.ClassDef) and node.name == className for node in tree.body)


def _read(rel):
    return io.open(os.path.join(SCRIPTS_DIR, rel), encoding="utf-8").read()


def testModMainEntriesResolve():
    entries = re.findall(r'MOD\.(?:Server|Client)\("([^"]+)"\)', _read("modMain.py"))
    assert entries, "modMain.py 里没找到 MOD.Server / MOD.Client"
    for entry in entries:
        assert _moduleFile(fdtest.SCRIPTS + "." + entry), "modMain 登记的模块不存在: " + entry


def _assertClassPath(dotted):
    modulePath, className = dotted.rsplit(".", 1)
    path = _moduleFile(modulePath)
    assert path, "模块不存在: " + modulePath
    assert _definesClass(path, className), "%s 里没有类 %s" % (modulePath, className)


def testScreenProxyPathResolves():
    screen = fdtest.load("Shared.Data.GuideBook")  # 纯数据模块，确认 Shared 可导入
    assert screen.uiGuideBookScreen
    match = re.search(r'PROXY_PATH = "([^"]+)"', _read(os.path.join("Client", "Ui", "CookingPotScreen.py")))
    assert match, "CookingPotScreen.py 里没找到 PROXY_PATH"
    _assertClassPath(match.group(1))


def testGuideBookUiPathResolves():
    _assertClassPath(fdtest.load("Shared.Data.GuideBook").uiGuideBookPath)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
