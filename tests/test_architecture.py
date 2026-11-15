# -*- coding: utf-8 -*-
# runner: py3
"""架构守卫：分层与导入方向、机审禁用写法、相对导入可解析、RPC 端点身份注入、文件与函数长度。

规则（违反即失败；确需例外写进下面的 ALLOW 表并注明理由）：
1. Shared/ 不导入引擎（mod.*）、QuModLibs、Server、Client、Compat、Api；Api/ 只导入 Shared/；
   Server/ 与 Client/ 互不导入，也不导入 Compat/（联动模块自己在 modMain 里登记）
2. 行为包脚本（QuModLibs 除外）不出现 import sys、__import__、namedtuple、eval / exec、pickle / marshal 反序列化
   （网易机审与安全规则）；不用星号导入（modMain.py 的 QuMod 模板除外）
3. 每个相对导入都要解析到真实存在的模块 / 包（层级写错只有引擎加载时才炸，且会连累整条导入链）
4. 服务端的 @AllowCall 端点必须同时 @InjectHttpPlayerId：玩家身份只认引擎注入的；端点名在同一端唯一
5. 模块名不与 py2 会被隐式相对导入劫持的标准库 / 引擎顶层名同名（random.py、time.py、common.py……）
6. 代码文件 ≤ 250 行（Shared/Data/ 纯数据表除外）、函数 ≤ 120 行
"""
from __future__ import print_function

import ast
import io
import os

import fdtest

SCRIPTS_DIR = os.path.join(fdtest.BP, fdtest.SCRIPTS)
MAX_FILE_LINES = 250
MAX_FUNCTION_LINES = 120
SHADOW_NAMES = {"random", "time", "math", "copy", "json", "string", "types", "traceback", "common", "mod",
                "collections", "re", "os", "uuid", "weakref", "functools", "itertools"}
# 文件长度例外：路径 → 理由
ALLOW_LONG_FILES = {
    "Client/Ui/CookingPotProxy.py": "历史界面代理，后续由站点界面替换",
}


def _sources():
    for root, dirs, files in os.walk(SCRIPTS_DIR):
        rel = os.path.relpath(root, SCRIPTS_DIR).replace("\\", "/")
        if rel == "QuModLibs" or rel.startswith("QuModLibs/"):
            continue
        for name in files:
            if name.endswith(".py"):
                relPath = (name if rel == "." else rel + "/" + name)
                path = os.path.join(root, name)
                yield relPath, path, io.open(path, encoding="utf-8").read()


def _layer(relPath):
    return relPath.split("/", 1)[0] if "/" in relPath else ""


def _resolveRelative(relPath, node):
    """from ..X import y → 目标模块的点分路径（相对脚本根），以及 names。"""
    pkgParts = relPath.split("/")[:-1]
    if node.level - 1 > len(pkgParts):
        return None
    base = pkgParts[:len(pkgParts) - (node.level - 1)]
    if node.module:
        base = base + node.module.split(".")
    return base


def _exists(parts):
    path = os.path.join(SCRIPTS_DIR, *parts) if parts else SCRIPTS_DIR
    return os.path.isfile(path + ".py") or os.path.isfile(os.path.join(path, "__init__.py"))


def _importTargets(relPath, tree):
    """(层级, 目标顶层名) 列表：只看本脚本根内的相对导入与 mod.* 绝对导入。"""
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                parts = _resolveRelative(relPath, node)
                targets.append(("rel", parts, node))
            elif node.module and node.module.split(".")[0] == "mod":
                targets.append(("engine", None, node))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "mod":
                    targets.append(("engine", None, node))
    return targets


def testLayering():
    rules = {
        "Shared": {"forbid": {"Server", "Client", "Compat", "Api", "QuModLibs"}, "engine": False},
        "Api": {"forbid": {"Server", "Client", "Compat", "QuModLibs"}, "engine": False},
        "Server": {"forbid": {"Client", "Compat"}, "engine": True},
        "Client": {"forbid": {"Server", "Compat"}, "engine": True},
    }
    problems = []
    for relPath, path, source in _sources():
        rule = rules.get(_layer(relPath))
        if rule is None:
            continue
        for kind, parts, node in _importTargets(relPath, ast.parse(source)):
            if kind == "engine" and not rule["engine"]:
                problems.append("%s:%d 导入了引擎模块" % (relPath, node.lineno))
            elif kind == "rel" and parts and parts[0] in rule["forbid"]:
                problems.append("%s:%d 不允许导入 %s" % (relPath, node.lineno, ".".join(parts)))
    assert not problems, "\n".join(problems)


def testBannedConstructsAndStarImports():
    problems = []
    for relPath, path, source in _sources():
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(a.name == "sys" for a in node.names):
                problems.append("%s:%d import sys（机审不允许，用 traceback.sys）" % (relPath, node.lineno))
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names) and relPath != "modMain.py":
                problems.append("%s:%d 星号导入" % (relPath, node.lineno))
            if isinstance(node, ast.Name) and node.id in ("__import__", "namedtuple", "eval", "exec"):
                problems.append("%s:%d 使用了 %s" % (relPath, node.lineno, node.id))
            if isinstance(node, ast.Attribute) and node.attr == "loads" and isinstance(node.value, ast.Name) \
                    and node.value.id in ("pickle", "cPickle", "marshal", "_pickle"):
                problems.append("%s:%d 反序列化 %s.loads" % (relPath, node.lineno, node.value.id))
    assert not problems, "\n".join(problems)


def testRelativeImportsResolve():
    problems = []
    for relPath, path, source in _sources():
        for kind, parts, node in _importTargets(relPath, ast.parse(source)):
            if kind != "rel":
                continue
            if parts is None or not _exists(parts):
                problems.append("%s:%d 相对导入解析不到: %s" % (relPath, node.lineno, "." * node.level + (node.module or "")))
                continue
            for alias in node.names:
                # from . import X：X 是子模块时要存在
                if node.module is None and alias.name != "*" and not _exists(parts + [alias.name]):
                    problems.append("%s:%d 找不到子模块 %s" % (relPath, node.lineno, alias.name))
    assert not problems, "\n".join(problems)


def _decoratorNames(func):
    names = []
    for deco in func.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Attribute):
            names.append(target.attr)
    return names


def testRpcEndpoints():
    problems = []
    seen = {}
    for relPath, path, source in _sources():
        side = "server" if _layer(relPath) == "Server" else ("client" if _layer(relPath) in ("Client", "Compat") else None)
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.FunctionDef) or "AllowCall" not in _decoratorNames(node):
                continue
            key = (side, node.name)
            if key in seen:
                problems.append("%s:%d 端点名 %s 与 %s 重复（后登记的会静默顶掉先登记的）" % (relPath, node.lineno, node.name, seen[key]))
            seen[key] = relPath
            if side == "server" and "InjectHttpPlayerId" not in _decoratorNames(node):
                problems.append("%s:%d 服务端端点 %s 没有 @InjectHttpPlayerId" % (relPath, node.lineno, node.name))
    assert not problems, "\n".join(problems)
    assert ("server", "CookingPotAddFood") in seen and ("client", "OnPlaySound") in seen


def testModuleNamesDoNotShadow():
    problems = [relPath for relPath, path, source in _sources()
                if os.path.splitext(os.path.basename(relPath))[0].lower() in SHADOW_NAMES]
    assert not problems, "会被 py2 隐式相对导入劫持的模块名: %s" % problems


def testFileAndFunctionLength():
    problems = []
    for relPath, path, source in _sources():
        lines = source.count("\n") + 1
        if lines > MAX_FILE_LINES and not relPath.startswith("Shared/Data/") and relPath not in ALLOW_LONG_FILES:
            problems.append("%s 有 %d 行（上限 %d）" % (relPath, lines, MAX_FILE_LINES))
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                length = node.body[-1].lineno - node.lineno + 1
                if length > MAX_FUNCTION_LINES:
                    problems.append("%s:%d 函数 %s 有 %d 行" % (relPath, node.lineno, node.name, length))
    assert not problems, "\n".join(problems)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
