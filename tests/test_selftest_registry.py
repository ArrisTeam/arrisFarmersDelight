# -*- coding: utf-8 -*-
# runner: py3
"""游戏内自检（Server/Debug/McdkSelfTest.py）里写死的"右键使用物品的处理函数先后"表不能漏：源码里每个登记到 ServerItemUseOnEvent 的
处理函数都在表里，表里也没有已经不存在的。先后对不对在游戏里由自检自己核（离线没有整包的登记顺序）；这里守的是"加了处理函数忘了改表"——
那样自检的 registry_order 在游戏里才报，离线一路绿。"""
from __future__ import print_function

import ast
import io
import os

import fdtest

ROOT = os.path.join(fdtest.BP, fdtest.SCRIPTS)
EVENT = "ServerItemUseOnEvent"


def _registered():
    """源码里用 @registerHandler("ServerItemUseOnEvent", ...) 登记的函数名（不看 QuModLibs、dolorContainer、Debug）。"""
    found = set()
    for folder, _dirs, files in os.walk(ROOT):
        relative = os.path.relpath(folder, ROOT).replace(os.sep, "/")
        if relative.split("/")[0] in ("QuModLibs", "dolorContainer") or "/Debug" in "/" + relative:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            tree = ast.parse(io.open(os.path.join(folder, name), encoding="utf-8").read())
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                for decorator in node.decorator_list:
                    call = decorator if isinstance(decorator, ast.Call) else None
                    target = call.func if call is not None else None
                    if target is not None and getattr(target, "id", getattr(target, "attr", None)) == "registerHandler" \
                            and call.args and isinstance(call.args[0], ast.Constant) and call.args[0].value == EVENT:
                        found.add(node.name)
    return found


def _table():
    source = io.open(os.path.join(ROOT, "Server", "Debug", "McdkSelfTest.py"), encoding="utf-8").read()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "ITEM_USE_ORDER" for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("McdkSelfTest.py 里没有 ITEM_USE_ORDER")


def testTheSelfTestsOrderTableNamesEveryItemUseHandlerAndNoGhosts():
    table, registered = _table(), _registered()
    assert len(table) == len(set(table)), "表里有重复"
    assert len(registered) >= 9, "源码里找到的太少，多半是这条用例的找法坏了：%r" % sorted(registered)
    missing, ghosts = sorted(registered - set(table)), sorted(set(table) - registered)
    assert not missing, "登记了处理函数、自检的表里没有（游戏里 registry_order 会失败）：%s" % missing
    assert not ghosts, "自检的表里有、源码里已经没有的处理函数：%s" % ghosts


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
