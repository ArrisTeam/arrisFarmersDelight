# -*- coding: utf-8 -*-
# runner: py3
"""本包和场景交互前置包各有一份、互相不能导入的常量要一样（两个包不互相导入）。前置包不在这个仓库里：它的源码在旁边才跑（tests/prereq.py）。
抄的时候是一样的，改的时候只改了一边就悄悄对不上——外观广播和内核的旁观范围差几格，离线和游戏里都不报错。按源码里的赋值读，不导入模块。"""
from __future__ import print_function

import os

import prereq  # noqa: F401 - 前置包不在这个仓库里：旁边没有它就跳过（tests/prereq.py）
import fdtest
import test_twin_constants as Twin

KERNEL = os.path.join(fdtest.ROOT, "diegesisBp", "arrisDiegesisScripts")


def testTheLookBroadcastReachesAsFarAsTheKernelsWatchers():
    ours = Twin.constant(Twin.FD, "Server/Helpers/LookWatch.py", "RANGE")
    kernel = Twin.constant(KERNEL, "Shared/Protocol.py", "WATCH_RANGE")
    assert ours == kernel == 32.0, (ours, kernel)             # Diegesis 的 ActiveStation.WATCH_RANGE


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
