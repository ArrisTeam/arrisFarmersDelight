# -*- coding: utf-8 -*-
# runner: py3
"""
守卫：dolorContainer 库是原样拷进来的。dolor.lock 由库仓库的 tools/vendor.py 写，记着库的提交号与每个文件的哈希
（库的文件、组件界面文件、编译出的布局文件与绑定表、装进来的测试）。这里比对：记着的文件都在、内容没变（按 LF 算哈希），
库的目录里没有多出来的文件，本库的组件界面文件在 ui/_ui_defs.json 里登记了、而且只登记了这一份，布局文件都登记了；
编译的输入（布局源文件、登记布局组件的模块）与编译时一样：改了、加了、删了都要重新编译；
vendor 只拷使用方用得到的库模块（按导入闭包，tests/dolor_closure.py）：按现在的代码重算，用到了没拷进来的要重新 vendor；
组件界面文件只留用到的模板（tests/dolor_uiprune.py）：界面文件与布局引用的、拷进来的模块运行时按名字用的模板都要在里面。
要改库或布局请到 dolorContainer 仓库改（布局源文件在本仓库的话改完也要重新 vendor），再运行那边的 tools/vendor.py；
本文件也由它装入。
"""
from __future__ import print_function

import glob
import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_FILE_PATTERN = re.compile(r"^ui/dolor_container(_[0-9a-f]{8})?\.json$")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dolor_closure  # noqa: E402  与本文件一起由 vendor 装入
import dolor_uiprune  # noqa: E402  与本文件一起由 vendor 装入


def _digest(path):
    with io.open(path, "rb") as handle:
        return hashlib.sha256(handle.read().replace(b"\r\n", b"\n")).hexdigest()


def _load(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return json.load(handle)


def _inputs(config):
    """编译的输入（同库的 tools/layouts.inputs）：布局源文件与登记布局组件的模块，{相对仓库根的路径: 完整路径}。"""
    paths = []
    for pattern in config.get("layouts") or ():
        paths.extend(sorted(glob.glob(os.path.join(ROOT, pattern))))
    scriptRoot = os.path.join(ROOT, *config["scriptRoot"].split("/"))
    for name in config.get("components") or ():
        if name.endswith(".py"):   # 包外的编译期说明：仓库里的文件路径
            paths.append(os.path.join(ROOT, *name.split("/")))
            continue
        base = os.path.join(scriptRoot, *name.split("."))
        paths.append(base + ".py" if os.path.isfile(base + ".py") else os.path.join(base, "__init__.py"))
    return dict((os.path.relpath(path, ROOT).replace("\\", "/"), path) for path in paths if os.path.isfile(path))


def _closureProblems(config, lock, package):
    """按使用方现在的代码重算要带的库模块：用到了没拷进来的、方块宿主缺客户端一半的。"""
    scriptRoot = os.path.join(ROOT, *config["scriptRoot"].split("/"))
    modules = dolor_closure.modulesIn(package)
    known = set(lock.get("libraryModules") or modules)
    roots = dolor_closure.consumerRoots(scriptRoot, known) + \
        dolor_closure.tableRoots(os.path.join(scriptRoot, dolor_closure.TABLE))
    kept, missing = dolor_closure.closure(modules, known, roots)
    out = ["%s 用到的库模块 %s %s：重新运行 dolorContainer 仓库的 tools/vendor.py" % (source, name or "（库包）", why)
           for source, name, why in missing]
    return out + ["%s：%s" % item for item in dolor_closure.checks(kept)]


def _templateProblems(config, lock, package):
    """界面文件与布局引用的模板、拷进来的模块运行时按名字建或挂的模板（UI_TEMPLATES）都在界面文件里。"""
    resourcePack = os.path.join(ROOT, *config["resourcePack"].split("/"))
    path = os.path.join(resourcePack, *lock["uiFile"].split("/"))
    if not os.path.isfile(path):
        return []   # 缺文件上面已经报过
    data = dolor_uiprune.load(path)
    roots = []
    for name in lock.get("layoutFiles", ()):
        layout = os.path.join(resourcePack, *name.split("/"))
        if os.path.isfile(layout):
            roots.extend((name, found) for found in dolor_uiprune.references(dolor_uiprune.load(layout), data["namespace"]))
    for module, modulePath in sorted(dolor_closure.modulesIn(package).items()):
        roots.extend((module or "（库包）", found) for found in dolor_uiprune.uiTemplates(modulePath))
    _, missing = dolor_uiprune.closure(data, roots)
    return ["%s 用到的界面模板 %s 不在 %s 里：重新运行 dolorContainer 仓库的 tools/vendor.py" % (source, name, lock["uiFile"])
            for source, name in missing]


def main():
    config, lock = _load("dolor.json"), _load("dolor.lock")
    problems = []
    if lock.get("libCommit", "").endswith("-dirty"):
        problems.append("dolor.lock 记的是库仓库的未提交内容（%s）：库提交之后重新 vendor" % lock["libCommit"])
    for rel, expected in sorted(lock["files"].items()):
        path = os.path.join(ROOT, *rel.split("/"))
        if not os.path.isfile(path):
            problems.append("缺少 %s" % rel)
        elif _digest(path) != expected:
            problems.append("被改动：%s（改库请到 dolorContainer 仓库，再运行它的 tools/vendor.py）" % rel)
    package = os.path.join(ROOT, *(config["scriptRoot"] + "/dolorContainer").split("/"))
    for folder, dirs, files in os.walk(package):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            rel = os.path.relpath(os.path.join(folder, name), ROOT).replace("\\", "/")
            if rel not in lock["files"]:
                problems.append("库目录里多出来的文件：%s" % rel)
    defs = _load(os.path.join(config["resourcePack"], "ui", "_ui_defs.json")).get("ui_defs", [])
    ours = [entry for entry in defs if UI_FILE_PATTERN.match(entry)]
    if ours != [lock["uiFile"]]:
        problems.append("ui/_ui_defs.json 里本库的界面文件应只有 %s，现在是 %s" % (lock["uiFile"], ours))
    for name in lock.get("layoutFiles", ()):
        if name not in defs:
            problems.append("ui/_ui_defs.json 没有登记布局文件 %s" % name)
    recorded, current = lock["inputs"], _inputs(config)
    for rel in sorted(set(recorded) | set(current)):
        if rel not in current:
            problems.append("编译过的 %s 不在了：重新编译（运行 dolorContainer 仓库的 tools/vendor.py）" % rel)
        elif rel not in recorded:
            problems.append("%s 还没编译过（运行 dolorContainer 仓库的 tools/vendor.py）" % rel)
        elif _digest(current[rel]) != recorded[rel]:
            problems.append("%s 改了没重新编译（运行 dolorContainer 仓库的 tools/vendor.py）" % rel)
    problems.extend(_closureProblems(config, lock, package))
    problems.extend(_templateProblems(config, lock, package))
    print("库 %s，%d 个文件" % (lock.get("libCommit"), len(lock["files"])))
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
