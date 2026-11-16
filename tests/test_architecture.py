# -*- coding: utf-8 -*-
# runner: py3
"""架构守卫：分层与导入方向、机审禁用写法、相对导入可解析、RPC 端点身份注入、文件与函数长度。

两个包都查：农夫乐事行为包（bp/arrisFarmersDelightScripts）与场景交互前置包（diegesisBp/arrisDiegesisScripts）。
规则（违反即失败；确需例外写进 PACKS 里的 allowLong 并注明理由）：
1. Shared/ 不导入引擎（mod.*）、QuModLibs、Server、Client、Compat、Api；Server/ 与 Client/ 互不导入，也不导入 Compat/。
   农夫乐事的 Api/ 只导入 Shared/；前置包的 Api/Server.py 是服务端门面（不导入 Client），Api/Client.py 反之
2. 脚本（QuModLibs、dolorContainer 等拷入件除外）不出现 import sys、__import__、namedtuple、eval / exec、pickle / marshal 反序列化
   （网易机审与安全规则）；不用星号导入（modMain.py 的 QuMod 模板除外）
3. 每个相对导入都要解析到真实存在的模块 / 包（层级写错只有引擎加载时才炸，且会连累整条导入链）
4. 服务端的 @AllowCall 端点必须同时 @InjectHttpPlayerId：玩家身份只认引擎注入的；端点名在同一端唯一
5. 模块名不与 py2 会被隐式相对导入劫持的标准库 / 引擎顶层名同名（random.py、time.py、common.py……）
6. 代码文件 ≤ 250 行（Shared/Data/ 纯数据表除外）、函数 ≤ 120 行
7. 前置包：调度与计算模块保持纯 Python（离线可测），不导入引擎、QuModLibs 和 Engine / EngineWorld；
   Protocol 里的每个端点名都在对应的一端有 @AllowCall 函数
"""
from __future__ import print_function

import ast
import io
import os

import dgtest
import fdtest

MAX_FILE_LINES = 250
MAX_FUNCTION_LINES = 120
# 只读的拷入件，不进下面的任何规则：QuModLibs 由 kit 拷入；dolorContainer 与 dolorLayouts.py（布局编译产物）由 dolorContainer
# 仓库的 tools/vendor.py 生成，改动与完整性由 tests/test_dolor_vendor.py 守着（行数、模块命名、导入写法都不归本文件管）
VENDORED_DIRS = ("QuModLibs", "dolorContainer")
GENERATED_FILES = ("dolorLayouts.py",)
SHADOW_NAMES = {"random", "time", "math", "copy", "json", "string", "types", "traceback", "common", "mod",
                "collections", "re", "os", "uuid", "weakref", "functools", "itertools"}
_SHARED_RULE = {"forbid": {"Server", "Client", "Compat", "Api", "QuModLibs"}, "engine": False}
PACKS = {
    "fd": {
        "dir": os.path.join(fdtest.BP, fdtest.SCRIPTS),
        "rules": {
            "Shared": _SHARED_RULE,
            "Api": {"forbid": {"Server", "Client", "Compat", "QuModLibs"}, "engine": False},
            "Server": {"forbid": {"Client", "Compat"}, "engine": True},
            "Client": {"forbid": {"Server", "Compat"}, "engine": True},
            # 联动模块按端分：服务端的不碰 Client/，客户端的不碰 Server/
            "Compat/Diegesis/BoardLogic.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/PotLogic.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/PotSync.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/PotScoop.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BookFill.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/PanLogic.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/GrillLogic.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/GrillOpen.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BoardTools.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BoardSlots.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BoardGive.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BoardChop.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BoardAssemble.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/DishCrafts.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/ServerBoot.py": {"forbid": {"Client"}, "engine": True},
            "Compat/Diegesis/BoardView.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/BoardDraw.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/BoardThing.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/BoardCutter.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/BoardFx.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/BoardInv.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotView.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotHud.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotScene.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotSceneFx.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotScenes.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotModel.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotHands.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotOffer.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/BoardGlow.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PotFx.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PanView.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PanScene.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PanScenes.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PanModel.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/PanFx.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/GrillView.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/GrillPieces.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/GrillGhosts.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/GrillSpace.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/GrillFx.py": {"forbid": {"Server"}, "engine": True},
            "Compat/Diegesis/ClientBoot.py": {"forbid": {"Server"}, "engine": True},
        },
        "allowLong": {"Client/Ui/CookingPotProxy.py": "历史界面代理，后续由站点界面替换"},
        "endpoints": [("server", "CookingPotAddFood"), ("client", "OnPlaySound")],
    },
    "diegesis": {
        "dir": os.path.join(dgtest.PACK, dgtest.SCRIPTS),
        "rules": {
            "Shared": _SHARED_RULE,
            "Api/Server.py": {"forbid": {"Client", "QuModLibs"}, "engine": False},
            "Api/Client.py": {"forbid": {"Server", "QuModLibs"}, "engine": False},
            "Server": {"forbid": {"Client"}, "engine": True},
            "Client": {"forbid": {"Server"}, "engine": True},
        },
        "allowLong": {},
        "endpoints": [("server", "DiegesisOpen"), ("client", "DiegesisOpened")],
    },
}
DIEGESIS_PURE = {"Server/Manager.py", "Server/Station.py", "Server/Registry.py", "Server/Session.py",
                 "Server/Runtime.py", "Server/Sync.py", "Server/Dispatch.py", "Server/Upkeep.py", "Server/Admit.py",
                 "Client/Registry.py", "Client/Shot.py",
                 "Client/Hub.py", "Client/PropMath.py", "Api/Server.py"}


def _sources(pack):
    scriptsDir = PACKS[pack]["dir"]
    for root, dirs, files in os.walk(scriptsDir):
        rel = os.path.relpath(root, scriptsDir).replace("\\", "/")
        if rel.split("/", 1)[0] in VENDORED_DIRS:
            continue
        for name in files:
            if name.endswith(".py") and not (rel == "." and name in GENERATED_FILES):
                relPath = (name if rel == "." else rel + "/" + name)
                path = os.path.join(root, name)
                yield relPath, path, io.open(path, encoding="utf-8").read()


def _allSources():
    for pack in sorted(PACKS):
        for relPath, path, source in _sources(pack):
            yield pack, relPath, path, source


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


def _exists(pack, parts):
    scriptsDir = PACKS[pack]["dir"]
    path = os.path.join(scriptsDir, *parts) if parts else scriptsDir
    return os.path.isfile(path + ".py") or os.path.isfile(os.path.join(path, "__init__.py"))


def _importTargets(relPath, tree):
    """(种类, 目标路径, 节点) 列表：只看本脚本根内的相对导入与 mod.* 绝对导入。"""
    targets = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                targets.append(("rel", _resolveRelative(relPath, node), node))
            elif node.module and node.module.split(".")[0] == "mod":
                targets.append(("engine", None, node))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "mod":
                    targets.append(("engine", None, node))
    return targets


def testLayering():
    problems = []
    for pack, relPath, path, source in _allSources():
        rules = PACKS[pack]["rules"]
        rule = rules.get(relPath) or rules.get(_layer(relPath))
        if rule is None:
            continue
        for kind, parts, node in _importTargets(relPath, ast.parse(source)):
            if kind == "engine" and not rule["engine"]:
                problems.append("%s/%s:%d 导入了引擎模块" % (pack, relPath, node.lineno))
            elif kind == "rel" and parts and parts[0] in rule["forbid"]:
                problems.append("%s/%s:%d 不允许导入 %s" % (pack, relPath, node.lineno, ".".join(parts)))
    assert not problems, "\n".join(problems)


def testBannedConstructsAndStarImports():
    problems = []
    for pack, relPath, path, source in _allSources():
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import) and any(a.name == "sys" for a in node.names):
                problems.append("%s/%s:%d import sys（机审不允许，用 traceback.sys）" % (pack, relPath, node.lineno))
            if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names) and relPath != "modMain.py":
                problems.append("%s/%s:%d 星号导入" % (pack, relPath, node.lineno))
            if isinstance(node, ast.Name) and node.id in ("__import__", "namedtuple", "eval", "exec"):
                problems.append("%s/%s:%d 使用了 %s" % (pack, relPath, node.lineno, node.id))
            if isinstance(node, ast.Attribute) and node.attr == "loads" and isinstance(node.value, ast.Name) \
                    and node.value.id in ("pickle", "cPickle", "marshal", "_pickle"):
                problems.append("%s/%s:%d 反序列化 %s.loads" % (pack, relPath, node.lineno, node.value.id))
    assert not problems, "\n".join(problems)


def testRelativeImportsResolve():
    problems = []
    for pack, relPath, path, source in _allSources():
        for kind, parts, node in _importTargets(relPath, ast.parse(source)):
            if kind != "rel":
                continue
            if parts is None or not _exists(pack, parts):
                problems.append("%s/%s:%d 相对导入解析不到: %s" % (pack, relPath, node.lineno, "." * node.level + (node.module or "")))
                continue
            for alias in node.names:
                # from . import X：X 是子模块时要存在
                if node.module is None and alias.name != "*" and not _exists(pack, parts + [alias.name]):
                    problems.append("%s/%s:%d 找不到子模块 %s" % (pack, relPath, node.lineno, alias.name))
    assert not problems, "\n".join(problems)


def _targetNames(target):
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return set().union(*[_targetNames(elt) for elt in target.elts]) if target.elts else set()
    return set()


def _definedNames(body):
    """模块顶层定义的名字（函数、类、赋值、导入；也看 if / try 里的）。"""
    names = set()
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names |= _targetNames(target)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(alias.asname or alias.name).split(".")[0] for alias in node.names}
        elif isinstance(node, ast.If):
            names |= _definedNames(node.body) | _definedNames(node.orelse)
        elif isinstance(node, ast.Try):
            names |= _definedNames(node.body) | _definedNames(node.orelse) | _definedNames(node.finalbody)
            for handler in node.handlers:
                names |= _definedNames(handler.body)
    return names


def testImportedNamesExist():
    """from .X import name：name 要在 X 里定义（或是 X 包的子模块）。实机：删掉的常量还被别处导入，整条导入链在游戏里才炸。"""
    problems = []
    cache = {}
    for pack, relPath, path, source in _allSources():
        for kind, parts, node in _importTargets(relPath, ast.parse(source)):
            if kind != "rel" or not parts or node.module is None or parts[0] == "QuModLibs":
                continue
            scriptsDir = PACKS[pack]["dir"]
            modulePath = os.path.join(scriptsDir, *parts) + ".py"
            packagePath = os.path.join(scriptsDir, *parts)
            target = modulePath if os.path.isfile(modulePath) else os.path.join(packagePath, "__init__.py")
            if not os.path.isfile(target):
                continue
            if target not in cache:
                cache[target] = _definedNames(ast.parse(io.open(target, encoding="utf-8").read()).body)
            for alias in node.names:
                if alias.name == "*" or alias.name in cache[target]:
                    continue
                if target.endswith("__init__.py") and _exists(pack, parts + [alias.name]):
                    continue
                problems.append("%s/%s:%d %s 里没有 %s" % (pack, relPath, node.lineno, ".".join(parts), alias.name))
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


def _endpoints(pack):
    """{(端, 函数名): 文件}；重复与缺身份注入记进 problems。"""
    seen, problems = {}, []
    for relPath, path, source in _sources(pack):
        layer = _layer(relPath)
        side = "server" if layer == "Server" else ("client" if layer in ("Client", "Compat") else None)
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.FunctionDef) or "AllowCall" not in _decoratorNames(node):
                continue
            key = (side, node.name)
            if key in seen:
                problems.append("%s/%s:%d 端点名 %s 与 %s 重复（后登记的会静默顶掉先登记的）" % (pack, relPath, node.lineno, node.name, seen[key]))
            seen[key] = relPath
            if side == "server" and "InjectHttpPlayerId" not in _decoratorNames(node):
                problems.append("%s/%s:%d 服务端端点 %s 没有 @InjectHttpPlayerId" % (pack, relPath, node.lineno, node.name))
    return seen, problems


def testRpcEndpoints():
    problems = []
    for pack in sorted(PACKS):
        seen, found = _endpoints(pack)
        problems += found
        for key in PACKS[pack]["endpoints"]:
            if key not in seen:
                problems.append("%s 缺少端点 %s" % (pack, key))
    assert not problems, "\n".join(problems)


def testDiegesisProtocolEndpointsExistOnTheRightSide():
    Protocol = dgtest.load("Shared.Protocol")
    seen, _ = _endpoints("diegesis")
    toServer = (Protocol.EP_OPEN, Protocol.EP_CLOSE, Protocol.EP_ACTION)
    toClient = (Protocol.EP_OPENED, Protocol.EP_DENIED, Protocol.EP_CLOSED, Protocol.EP_STATE, Protocol.EP_EFFECT)
    missing = [("server", n) for n in toServer if ("server", n) not in seen]
    missing += [("client", n) for n in toClient if ("client", n) not in seen]
    assert not missing, "Protocol 里的端点没有对应的 @AllowCall 函数: %s" % missing


def testDiegesisPureModulesStayPure():
    problems = []
    for relPath, path, source in _sources("diegesis"):
        if relPath not in DIEGESIS_PURE:
            continue
        for kind, parts, node in _importTargets(relPath, ast.parse(source)):
            if kind == "engine" or (parts and (parts[0] == "QuModLibs" or parts[-1] in ("Engine", "EngineWorld"))):
                problems.append("%s:%d 纯逻辑模块导入了 %s" % (relPath, node.lineno, ".".join(parts or ["mod"])))
    assert not problems, "\n".join(problems)


def testModuleNamesDoNotShadow():
    problems = ["%s/%s" % (pack, relPath) for pack, relPath, path, source in _allSources()
                if os.path.splitext(os.path.basename(relPath))[0].lower() in SHADOW_NAMES]
    assert not problems, "会被 py2 隐式相对导入劫持的模块名: %s" % problems


def testFileAndFunctionLength():
    problems = []
    for pack, relPath, path, source in _allSources():
        lines = source.count("\n") + 1
        if lines > MAX_FILE_LINES and not relPath.startswith("Shared/Data/") and relPath not in PACKS[pack]["allowLong"]:
            problems.append("%s/%s 有 %d 行（上限 %d）" % (pack, relPath, lines, MAX_FILE_LINES))
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                length = node.body[-1].lineno - node.lineno + 1
                if length > MAX_FUNCTION_LINES:
                    problems.append("%s/%s:%d 函数 %s 有 %d 行" % (pack, relPath, node.lineno, node.name, length))
    assert not problems, "\n".join(problems)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
