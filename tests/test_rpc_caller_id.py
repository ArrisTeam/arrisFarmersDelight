# -*- coding: utf-8 -*-
# runner: py3
"""
守卫：客户端能调的服务端端点，玩家 ID 一律取框架注入的调用者 ID，不信客户端传来的。

扫行为包脚本里导入了服务端 QuModLibs 的模块：带 @AllowCall 的函数只要用到 playerId，就必须同时带注入调用者 ID 的
装饰器（@InjectHttpPlayerId，新版 QuModLibs 叫 @InjectRPCPlayerId、旧名留作兼容；写在 @AllowCall 下面），并且 playerId
是它的第一个参数。客户端在参数里填别人的 ID，就能动别人的容器与背包。另外端点按裸函数名注册，同一端重名时后注册的静默
顶掉先注册的，所以裸名不许重复。
"""
from __future__ import print_function

import ast
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INJECTORS = ("InjectHttpPlayerId", "InjectRPCPlayerId")   # 注入调用者 ID 的装饰器（两个名字是同一个）


def _scriptRoot():
    """脚本根：用了工具包的仓库写在 kit.json，别的使用方写在 dolor.json（vendor 装进去的这份两种都认）。"""
    for name in ("kit.json", "dolor.json"):
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            with io.open(path, encoding="utf-8") as handle:
                root = json.load(handle).get("scriptRoot")
            if root:
                return os.path.join(ROOT, *root.split("/"))
    raise SystemExit("找不到脚本根：kit.json 或 dolor.json 里要写 scriptRoot")


SCRIPTS = _scriptRoot()


def _decoratorNames(node):
    names = []
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        names.append(target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", ""))
    return names


def _usesName(node, name):
    return any(isinstance(sub, ast.Name) and sub.id == name for sub in ast.walk(node)) \
        or any(arg.arg == name for arg in node.args.args)


def _modules(side):
    marker = "QuModLibs.%s import" % side
    for folder, dirs, files in os.walk(SCRIPTS):
        dirs[:] = [d for d in dirs if d not in ("QuModLibs", "CreateSDK", "__pycache__")]
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(folder, name)
            with io.open(path, encoding="utf-8") as handle:
                source = handle.read()
            if marker in source:
                yield path, source


def _endpoints(side):
    for path, source in _modules(side):
        for node in ast.walk(ast.parse(source, path)):
            if isinstance(node, ast.FunctionDef) and "AllowCall" in _decoratorNames(node):
                yield os.path.relpath(path, ROOT).replace("\\", "/"), node


def main():
    problems, names = [], {}
    endpoints = list(_endpoints("Server"))
    for rel, node in endpoints:
        names.setdefault(("server", node.name), []).append(rel)
        if not _usesName(node, "playerId"):
            continue
        decorators = _decoratorNames(node)
        found = [name for name in INJECTORS if name in decorators]
        injected = bool(found) and all(decorators.index(name) > decorators.index("AllowCall") for name in found)
        first = node.args.args[0].arg if node.args.args else None
        if not injected or first != "playerId":
            problems.append("%s:%d %s 的玩家 ID 没有取注入的调用者 ID" % (rel, node.lineno, node.name))
    for rel, node in _endpoints("Client"):
        names.setdefault(("client", node.name), []).append(rel)
    for (side, name), places in sorted(names.items()):
        if len(places) > 1:
            problems.append("%s 端点 %s 重名：%s" % (side, name, ", ".join(places)))
    print("服务端端点 %d 个" % len(endpoints))
    if not endpoints:
        print("FAIL: 一个端点都没扫到，扫描规则失效了")
        return 1
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
