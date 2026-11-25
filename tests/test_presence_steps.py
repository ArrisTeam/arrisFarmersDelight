# -*- coding: utf-8 -*-
# runner: both
"""联动步骤表的执行器（Compat/Diegesis/Steps）和两张步骤表（ServerSteps / ClientSteps）：
一步抛异常记成 failed、打印 traceback、后面的步骤照常跑；返回 False 是 skipped，别的是 ok；条件（接口上的功能旗）不满足的步骤 skipped、连模块都不导入；
每个目标 "模块路径:函数名" 都真的存在（按源码 ast 核对，和机械动力系列的 test_kit_steps 一样）、步骤名不重复、表里没有 import。只用本仓库的东西。"""
from __future__ import print_function

import ast
import io
import os
import sys

import fdtest

Steps = fdtest.load("Compat.Diegesis.Steps")
SCRIPTS_DIR = os.path.join(fdtest.BP, fdtest.SCRIPTS)
TABLES = (("ServerSteps", "ServerLink"), ("ClientSteps", "ClientLink"))
EXPECTED = ("board", "pot", "pan", "grill", "table")  # 原来两个入口登记站点的顺序：砧板、厨锅、煎锅、炉灶；然后是前置包原版工作台上的登记
CLIENT_ONLY = {"settings": "SETTINGS"}                # 只有客户端有的步骤（排在最后）和它的条件：玩家开关登进前置包的设置界面
REQUIRES = {"board": None, "pot": None, "pan": None, "grill": "FACING_HOOK", "table": None}     # 两端都有的步骤的条件：炉灶要朝向钩子


class Text(object):
    """顶替 sys.stdout / sys.stderr 收下写进去的字。"""

    def __init__(self):
        self.parts = []

    def write(self, text):
        self.parts.append(text)

    def flush(self):
        pass

    def text(self):
        return "".join(self.parts)


class Quiet(object):
    def __enter__(self):
        self.before = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = Text(), Text()
        return self

    def __exit__(self, *exc):
        self.out, self.err = sys.stdout.text(), sys.stderr.text()
        sys.stdout, sys.stderr = self.before
        return False


def moduleOf(**functions):
    return type("FakeStepModule", (object,), dict((name, staticmethod(func)) for name, func in functions.items()))


class Loader(object):
    def __init__(self, **modules):
        self.modules = dict((fdtest.SCRIPTS + ".Fake." + name, module) for name, module in modules.items())
        self.asked = []

    def __call__(self, path):
        self.asked.append(path)
        if path not in self.modules:
            raise ImportError("No module named %s" % path)
        return self.modules[path]


def _run(steps, loader, api=None):
    with Quiet() as quiet:
        results = Steps.run("server", steps, api or type("Api", (object,), {"API_VERSION": 3}), loader)
    return results, quiet


def testAStepThatRaisesIsFailedAndLoggedAndTheFollowingStepsStillRun():
    ran = []

    def good(ctx):
        ran.append(ctx.side)

    def bad(ctx):
        raise RuntimeError("站点登记出错")
    loader = Loader(A=moduleOf(link=good), B=moduleOf(link=bad), C=moduleOf(link=good))
    results, quiet = _run([("a", "Fake.A:link", None), ("b", "Fake.B:link", None), ("c", "Fake.C:link", None)], loader)
    assert [(name, status) for name, status, _ in results] == [("a", "ok"), ("b", "failed"), ("c", "ok")]
    assert "RuntimeError" in results[1][2], results[1]
    assert ran == ["server", "server"], "出错的那一步之后的步骤照常跑"
    assert "Traceback" in quiet.err and "站点登记出错" in quiet.err, "traceback 打印出来，不吞掉"
    assert "b" in quiet.out, "日志里写明是哪一步"


def testAStepReturningFalseIsSkippedAndAnythingElseIsOk():
    loader = Loader(No=moduleOf(link=lambda ctx: False), NoneBack=moduleOf(link=lambda ctx: None),
                    Class=moduleOf(link=lambda ctx: object), Yes=moduleOf(link=lambda ctx: True), Zero=moduleOf(link=lambda ctx: 0))
    steps = [("no", "Fake.No:link", None), ("none", "Fake.NoneBack:link", None), ("class", "Fake.Class:link", None),
             ("yes", "Fake.Yes:link", None), ("zero", "Fake.Zero:link", None)]
    results, _ = _run(steps, loader)
    assert [status for _, status, _ in results] == ["skipped", "ok", "ok", "ok", "ok"], "只有明写 False 才是没东西可联动"


def testAMissingModuleOrFunctionFailsOnlyThatStep():
    loader = Loader(Ok=moduleOf(link=lambda ctx: True), NoLink=moduleOf(other=lambda ctx: True))
    steps = [("missing", "Fake.Absent:link", None), ("nofunc", "Fake.NoLink:link", None), ("ok", "Fake.Ok:link", None)]
    results, quiet = _run(steps, loader)
    assert [(name, status) for name, status, _ in results] == [("missing", "failed"), ("nofunc", "failed"), ("ok", "ok")]
    assert "ImportError" in results[0][2] and "AttributeError" in results[1][2], results


def testAConditionThatTheApiLacksSkipsTheStepWithoutImportingItsModule():
    loader = Loader(Hooked=moduleOf(link=lambda ctx: True))
    steps = [("hooked", "Fake.Hooked:link", "SOME_HOOK")]
    results, _ = _run(steps, loader, type("Api", (object,), {"API_VERSION": 3}))
    assert results[0][1] == "skipped" and "SOME_HOOK" in results[0][2] and loader.asked == [], "模块没导入过"
    results, _ = _run(steps, loader, type("Api", (object,), {"API_VERSION": 3, "SOME_HOOK": True}))
    assert results[0][1] == "ok" and len(loader.asked) == 1
    results, _ = _run(steps, loader, type("Api", (object,), {"API_VERSION": 3, "SOME_HOOK": False}))
    assert results[0][1] == "skipped", "旗是假也不跑"


def testTheStepModulePathIsRelativeToTheScriptRootAndTheContextCarriesTheApi():
    assert Steps.SCRIPT_ROOT == fdtest.SCRIPTS
    seen = []
    api = type("Api", (object,), {"API_VERSION": 5})
    loader = Loader(Here=moduleOf(link=lambda ctx: seen.append((ctx.side, ctx.api, ctx.apiVersion))))
    _run([("here", "Fake.Here:link", None)], loader, api)
    assert loader.asked == [fdtest.SCRIPTS + ".Fake.Here"] and seen == [("server", api, 5)]


def testResultsKeepTheOrderOfTheTable():
    loader = Loader(A=moduleOf(link=lambda ctx: True), B=moduleOf(link=lambda ctx: False))
    results, _ = _run([("z", "Fake.A:link", None), ("a", "Fake.B:link", None)], loader)
    assert [name for name, _, _ in results] == ["z", "a"]


# ---------------------------------------------------------------- 两张步骤表

def _tree(name):
    with io.open(os.path.join(SCRIPTS_DIR, "Compat", "Diegesis", name + ".py"), "rb") as f:
        return ast.parse(f.read())         # 字节：py2 的 ast.parse 不收带编码声明的 unicode


def _steps(name):
    for node in _tree(name).body:
        if isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == ["STEPS"]:
            assert isinstance(node.value, ast.List), "%s: STEPS 要写成字面量列表" % name
            return [ast.literal_eval(item) for item in node.value.elts]
    raise AssertionError("%s 里没有 STEPS" % name)


def _definesFunction(path, funcName):
    with io.open(path, "rb") as f:
        return any(isinstance(node, ast.FunctionDef) and node.name == funcName for node in ast.parse(f.read()).body)


def testEveryStepTargetExistsAndTheTablesAreWrittenAsPlainData():
    for table, family in TABLES:
        steps = _steps(table)
        extra = dict(CLIENT_ONLY) if table == "ClientSteps" else {}
        assert [step[0] for step in steps] == list(EXPECTED) + sorted(extra), \
            "%s：一个站点一步，顺序是原来登记的顺序，然后是 table（客户端最后多一步 settings）" % table
        assert len(set(step[0] for step in steps)) == len(steps), "步骤名不重复"
        for entry in steps:
            assert isinstance(entry, tuple) and len(entry) == 3, "(步骤名, 目标, 条件或 None)：%r" % (entry,)
            name, target, requires = entry
            modulePath, _, funcName = target.partition(":")
            assert funcName, "%s 的目标要写成 '模块路径:函数名'：%r" % (name, target)
            path = os.path.join(SCRIPTS_DIR, *modulePath.split(".")) + ".py"
            assert os.path.isfile(path), "%s 的目标 %r：找不到模块" % (name, target)
            assert _definesFunction(path, funcName), "%s 的目标 %r：模块里没有顶层函数 %s" % (name, target, funcName)
            assert modulePath.startswith("Compat.Diegesis.") and modulePath.endswith(family), "%s：服务端的表指服务端的步骤模块，客户端的指客户端的" % target
            assert requires in (None, "FACING_HOOK", "SETTINGS"), "%s 的条件 %r：本包用到的可选功能旗只有朝向钩子、设置" % (name, requires)
        assert dict((step[0], step[2]) for step in steps) == dict(REQUIRES, **extra), "炉灶要朝向钩子，客户端的 settings 要设置"
        assert not [node for node in ast.walk(_tree(table)) if isinstance(node, (ast.Import, ast.ImportFrom))], "步骤表只放数据，不导入业务模块"


def testTheTwoTablesNameTheSameStationsInTheSameOrder():
    server, client = _steps("ServerSteps"), _steps("ClientSteps")
    shared = [(name, requires) for name, _, requires in client if name not in CLIENT_ONLY]
    assert [(name, requires) for name, _, requires in server] == shared, "两端一起有、一起没有（只有客户端的 settings 除外）"
    assert [name for name, _, _ in client][len(shared):] == sorted(CLIENT_ONLY), "只有客户端的步骤排在最后"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
