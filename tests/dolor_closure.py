# -*- coding: utf-8 -*-
"""
dolorContainer 拷进使用方时带哪些库模块：从入口按导入关系算闭包（docs/ARCHITECTURE.md 第 2.2 节）。库仓库的
tools/vendor.py 与装进使用方的守卫测试 tests/test_dolor_vendor.py 共用这一份（vendor 把它装成使用方的 tests/dolor_closure.py），
不要在使用方改。

入口：
- 两端服务（使用方的 modMain 按名字登记）与引擎按类名载入的界面类（ROOTS）；
- 使用方脚本根下、库目录以外的全部 .py 用到的库模块：相对导入、以脚本根包名开头的绝对导入、字符串里写的库模块全名
  （modMain 按名字登记服务、按类名换界面类；说明文字不算）；
- 编译出的绑定表（脚本根下的 dolorLayouts.py）里各布局的 imports（布局用到的不在标准控件模块里的控件模块）；
- 闭包里的模块写的 SIDE_MODULES（标准件第一次用到时按名字载入的一端模块）。
按语法树找导入，函数里的导入也算（用到时要在）；from 包 import 名字 的名字是模块时算模块；连同各级包的 __init__.py。
库里只用相对导入导入自己，库的绝对导入都是库外的（引擎、标准库）。模块名都相对库包（"Server.Service"；库包本身是 ""）。
"""
from __future__ import print_function

import ast
import io
import os
import re

LIBRARY = "dolorContainer"
ROOTS = ("Server.Service", "Client.Service", "Client.Screen")
TABLE = "dolorLayouts.py"
_STRING = re.compile(r"(?:^|\.)%s((?:\.[A-Za-z_]\w*)+)" % LIBRARY)


class ClosureError(Exception):
    pass


def modulesIn(folder):
    """库包目录里的模块：{模块名: 文件}。"""
    out = {}
    for base, dirs, names in os.walk(folder):
        dirs[:] = sorted(name for name in dirs if name != "__pycache__")
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(base, name), folder).replace(os.sep, "/")[:-3]
            if rel == "__init__":
                rel = ""
            elif rel.endswith("/__init__"):
                rel = rel[:-len("/__init__")]
            out[rel.replace("/", ".")] = os.path.join(base, name)
    return out


def _tree(path):
    with io.open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read(), path)


def _join(parts):
    return ".".join(part for part in parts if part)


def _parents(name):
    """模块所在的各级包（库包本身 "" 在内）。"""
    parts = name.split(".") if name else []
    return [_join(parts[:index]) for index in range(len(parts))]


def _imports(tree, package):
    """
    一份源码里的导入：[(模块全名的各段, 导入的名字, 是不是相对导入)]。package 是它所在的包（各段），相对导入按它补全；
    越过顶层的相对导入不算。
    """
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            if node.level:
                if node.level - 1 > len(package):
                    continue
                base = package[:len(package) - (node.level - 1)] + (node.module.split(".") if node.module else [])
                out.append((base, names, True))
            else:
                out.append(((node.module or "").split("."), names, False))
        elif isinstance(node, ast.Import):
            out.extend((alias.name.split("."), [], False) for alias in node.names)
    return out


def _strings(tree):
    """源码里的字符串（说明文字不算：单独成句的字符串）。"""
    docs = set(id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Expr))
    return [node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs]


def _sideModules(tree, path):
    """模块级 SIDE_MODULES = {"server": (...), "client": (...)} 写的模块。"""
    out = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "SIDE_MODULES"
                                                for target in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                raise ClosureError("%s 的 SIDE_MODULES 要写成字面量（vendor 按它保留模块）" % path)
            for paths in value.values():
                out.extend(paths)
    return out


def _used(parts, names, known):
    """from 模块 import 名字（parts 是相对库包的各段）用到的库模块：模块本身，加上导入的名字里是模块的。"""
    base = _join(parts)
    return [base] + [_join(parts + [name]) for name in names if name != "*" and _join(parts + [name]) in known]


def consumerRoots(scriptRoot, known):
    """使用方脚本根下、库目录以外的 .py 用到的库模块：[(来源, 模块名)]。known 是库的全部模块名。"""
    rootPackage = os.path.basename(os.path.normpath(scriptRoot))
    out = []
    for base, dirs, names in os.walk(scriptRoot):
        atRoot = os.path.normpath(base) == os.path.normpath(scriptRoot)
        dirs[:] = sorted(name for name in dirs if name != "__pycache__" and not (atRoot and name == LIBRARY))
        for name in sorted(names):
            if not name.endswith(".py") or (atRoot and name == TABLE):
                continue
            path = os.path.join(base, name)
            source = os.path.relpath(path, scriptRoot).replace(os.sep, "/")
            package = source[:-3].split("/")[:-1]
            tree = _tree(path)
            for parts, imported, relative in _imports(tree, package):
                if not relative and parts[:1] == [rootPackage]:
                    parts = parts[1:]
                if parts[:1] == [LIBRARY]:
                    out.extend((source, found) for found in _used(parts[1:], imported, known))
            for text in _strings(tree):
                for match in _STRING.finditer(text):
                    parts = match.group(1).split(".")[1:]
                    while parts and _join(parts) not in known:
                        parts = parts[:-1]
                    out.append((source, _join(parts)))
    return out


def tableRoots(path):
    """编译出的绑定表里各布局的 imports：[(来源, 模块名)]。没有绑定表时为空。"""
    if not os.path.isfile(path):
        return []
    layouts = {}
    for node in _tree(path).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "LAYOUTS"
                                                for target in node.targets):
            layouts = ast.literal_eval(node.value)
    return [("%s %s" % (TABLE, name), module) for name, layout in sorted(layouts.items())
            for module in layout.get("imports") or ()]


def closure(modules, known, roots):
    """
    从入口算闭包。modules 是在手的库模块 {模块名: 文件}（vendor 时是整份库，守卫里是拷进来的），known 是库的全部模块名，
    roots 是 [(来源, 模块名)]。返回 (带上的模块名集合, 问题列表)：问题是 (来源, 模块名, 说明)。
    """
    kept, problems = set(), []
    todo = [("入口", name) for name in ROOTS] + list(roots)
    while todo:
        source, name = todo.pop()
        if name in kept:
            continue
        if name not in known:
            problems.append((source, name, "库里没有这个模块"))
            continue
        if name not in modules:
            problems.append((source, name, "没拷进来"))
            continue
        kept.add(name)
        todo.extend((name, parent) for parent in _parents(name))
        path = modules[name]
        tree = _tree(path)
        parts = name.split(".") if name else []
        package = parts if os.path.basename(path) == "__init__.py" else parts[:-1]
        for base, imported, relative in _imports(tree, package):
            if relative:
                todo.extend((name, found) for found in _used(base, imported, known))
        todo.extend((name, side) for side in _sideModules(tree, path))
    return kept, sorted(set(problems))


def checks(kept):
    """闭包算完之后的核对：[(来源, 说明)]。"""
    out = []
    if "Std.Block.Server" in kept and "Std.Block.Client" not in kept:
        out.append(("Std.Block.Server", "用了方块宿主，客户端要导入它的客户端一半 Std/Block/Client.py（对着方块使用时手里的东西"
                                        "不用出去）"))
    return out
