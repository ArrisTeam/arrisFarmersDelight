# -*- coding: utf-8 -*-
"""prereq - 要沉浸式交互前置（独立工程 arrisDiegesis）源码的用例先导入它（不是测试本身，跑器只收 test_*.py）

前置包是单独的作品、单独的工程，不在这个仓库里：玩家装了它，农夫乐事才启用亲手做菜的站点（Compat/Diegesis）。站点的用例要拿它的源码和
它的测试小工具（那边的 tests/dg*.py：dgtest、dgstation、dgkit……）一起跑。它在哪由 tests/prereqdir.py 找：环境变量 FD_PREREQ_DIR，
没给就是本仓库旁边的 ../arrisDiegesis。找到了：把那边的 tests/ 放进 sys.path（排在本仓库的 tests/ 后面），import dg… 拿到的就是那边的小工具，
它们再把那边的 diegesisBp/ 放进 sys.path。找不到（只 clone 了本仓库、FD_PREREQ_DIR 指着不存在的目录）：这些用例跳过（退出码 77，跑器记成 SKIP），不算失败。

写法：在第一个 import dg…（或读前置包的文件）之前
    import prereq  # noqa: F401
用例经 boardclient / potkit 这类小工具间接用到前置包的，小工具里已经写了，用例自己不用再写。前置包里的路径用这里的 BP / RP / SCRIPTS / TESTS / TOOLS / DOCS。
"""
import os
import sys

from prereqdir import BP, DIR, DOCS, RP, SCRIPTS, TESTS, TOOLS  # noqa: F401

if DIR is None:
    print("跳过：找不到沉浸式交互前置（独立工程 arrisDiegesis：环境变量 FD_PREREQ_DIR，没给就是旁边的 ../arrisDiegesis），它不在这个仓库里")
    sys.exit(77)
if os.path.normcase(TESTS) not in [os.path.normcase(path) for path in sys.path]:
    sys.path.append(TESTS)
