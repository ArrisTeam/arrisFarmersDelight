# -*- coding: utf-8 -*-
# runner: py3
"""两处各抄一份、互相不能导入的常量要一样：服务端和客户端各有一份的（两端不互相导入），本包和前置包各有一份的（两个包不互相导入）。
抄的时候是一样的，改的时候只改了一边就悄悄对不上——旁观的人少听一种声音、外观广播和内核的旁观范围差几格，离线和游戏里都不报错。
这里按源码里的赋值读（不导入模块：那几个模块都带着引擎）。"""
from __future__ import print_function

import ast
import io
import os

import fdtest

FD = os.path.join(fdtest.BP, fdtest.SCRIPTS)
KERNEL = os.path.join(fdtest.ROOT, "diegesisBp", "arrisDiegesisScripts")


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


def testTheLookBroadcastReachesAsFarAsTheKernelsWatchers():
    ours = constant(FD, "Server/Helpers/LookWatch.py", "RANGE")
    kernel = constant(KERNEL, "Shared/Protocol.py", "WATCH_RANGE")
    assert ours == kernel == 32.0, (ours, kernel)             # Diegesis 的 ActiveStation.WATCH_RANGE


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
