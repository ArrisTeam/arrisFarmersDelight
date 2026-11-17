# -*- coding: utf-8 -*-
# runner: py3
"""两处各抄一份、互相不能导入的常量要一样：服务端和客户端各有一份的（两端不互相导入）。
抄的时候是一样的，改的时候只改了一边就悄悄对不上——旁观的人少听一种声音，离线和游戏里都不报错。
这里按源码里的赋值读（不导入模块：那几个模块都带着引擎）。本包和前置包各有一份的常量在 tests/test_prereq_constants.py（要前置包的源码在旁边才跑）。"""
from __future__ import print_function

import ast
import io
import os

import fdtest

FD = os.path.join(fdtest.BP, fdtest.SCRIPTS)


def constant(root, relative, name):
    """模块最外层 name = <字面量 / frozenset((...)) / 另一个模块的同名常量> 的值。"""
    tree = ast.parse(io.open(os.path.join(root, *relative.split("/")), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == name for target in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", None) == "frozenset":
                return frozenset(ast.literal_eval(value.args[0]))
            return ast.literal_eval(value)
    raise AssertionError("%s 里没有 %s" % (relative, name))


def testTheBoardEventsBystandersHearAreTheSameListOnBothSides():
    server = constant(FD, "Server/BoardLook.py", "OBSERVED")
    client = constant(FD, "Compat/Diegesis/BoardWatch.py", "OBSERVED")
    assert server == client and server, (sorted(server), sorted(client))


def testTheLookBroadcastReachesAsFarAsDiegesisWatchesAStation():
    assert constant(FD, "Server/Helpers/LookWatch.py", "RANGE") == 32.0             # Diegesis 的 ActiveStation.WATCH_RANGE


def testScenesAreDrawnAndHeardAsFarAsInJava():
    """每座锅 / 灶在本客户端的场景：32 格以内每帧算、带粒子声音，40 格以内只画，再远不算（Diegesis：ActiveStation.WATCH_RANGE 32、
    SceneRenderer.RENDER_RANGE 40）。三个场景管理各写了一份。"""
    for module in ("PotScenes", "PanScenes", "StoveScenes"):
        tree = ast.parse(io.open(os.path.join(FD, "Compat", "Diegesis", module + ".py"), encoding="utf-8").read())
        found = [ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple)
                 and [getattr(name, "id", None) for name in node.targets[0].elts] == ["NEAR", "FAR"]]
        assert found == [(32.0, 40.0)], (module, found)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
