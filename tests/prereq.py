# -*- coding: utf-8 -*-
"""prereq - 要沉浸式交互前置包（arrisDiegesis）源码的用例先导入它（不是测试本身，跑器只收 test_*.py）

前置包是单独的作品，不在这个仓库里：玩家装了它，农夫乐事才启用亲手做菜的站点（Compat/Diegesis）。开发机上它的两个包放在仓库根下的
diegesisBp/、diegesisRp/，它自己的测试小工具是 tests/dg*.py（都不入库）；站点的用例要拿它的源码一起跑。
只 clone 了本仓库、旁边没有它时，这些用例跳过（退出码 77，跑器记成 SKIP），不算失败。

写法：在第一个 import dg…（或读前置包文件）之前
    import prereq  # noqa: F401
用例经 boardclient / potkit 这类小工具间接用到前置包的，小工具里已经写了，用例自己不用再写。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "diegesisBp", "arrisDiegesisScripts")
KIT = os.path.join(ROOT, "tests", "dgtest.py")

if not (os.path.isdir(PACK) and os.path.isfile(KIT)):
    print("跳过：旁边没有沉浸式交互前置包（diegesisBp/ 和它的测试小工具 tests/dg*.py），它不在这个仓库里")
    sys.exit(77)
