# -*- coding: utf-8 -*-
"""fdtest - 离线测试的公共小工具（不是测试本身，跑器只收 test_*.py）

- 把 bp/ 加进 sys.path，按点分路径导入行为包里的纯 Python 模块；
- 极简的用例收集与断言输出：模块里所有 test 开头的函数依次执行，任一失败退出码为 1；
- vanilla()：本机游戏自带的原版资源包（版本号最高的那一份，和生成器的缺省同一个出处 tools/vanilla_pack.py）。
引擎模块（mod.server / mod.client）离线不存在，只能导入不依赖引擎的模块（Shared/、数据表、规则）。
"""
from __future__ import print_function

import importlib
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, "bp")
TOOLS = os.path.join(ROOT, "tools")
SCRIPTS = "arrisFarmersDelightScripts"

if BP not in sys.path:
    sys.path.insert(0, BP)


def load(dotted):
    """导入行为包脚本根下的模块，例如 load("Shared.Data.Cooking")。"""
    return importlib.import_module(SCRIPTS + "." + dotted)


def vanilla(*parts):
    """本机版本号最高的那份原版资源包再接上 parts，例如 vanilla("sounds", "sound_definitions.json")；别写死版本（游戏升级后旧目录会删掉）。
    本机没有游戏目录（别人的机器、只有本仓库的克隆）返回 None：用它的核对照旧跳过，或者只比本包的。"""
    if TOOLS not in sys.path:
        sys.path.append(TOOLS)
    vanillaPack = importlib.import_module("vanilla_pack")
    root = vanillaPack.newest()
    return None if root is None else "/".join((root,) + parts)


def tipText(tip, values=()):
    """服务端的一句提示（Shared/Data/Tips 的 (键, 中文) 加 ShowTip 给的值）在中文的游戏里显示成什么：假引擎的 ShowTip 记下它，
    测试照旧对着玩家看到的那句中文比。值里的词 (键, 中文) 取它的中文。"""
    return tip[1] % tuple(value[1] if isinstance(value, tuple) else value for value in values)


def run(namespace):
    """执行 namespace（通常是 globals()）里所有 test 开头的函数，返回退出码。"""
    names = sorted(k for k, v in namespace.items() if k.startswith("test") and callable(v))
    failed = 0
    for name in names:
        try:
            namespace[name]()
        except Exception:  # noqa: BLE001 - 测试边界：记录后继续跑其余用例
            failed += 1
            print("FAIL %s" % name)
            traceback.print_exc()
        else:
            print("ok   %s" % name)
    print("%d 个用例，失败 %d" % (len(names), failed))
    return 1 if failed else 0
