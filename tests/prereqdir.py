# -*- coding: utf-8 -*-
"""prereqdir - 沉浸式交互前置（独立工程 arrisDiegesis）在本机的哪里（不是测试本身，跑器只收 test_*.py；只给路径，找不到也不跳过）

前置包是单独的作品、单独的工程（AddOn/arrisDiegesis，远端 ArrisTeam/netease-diegesis），不在这个仓库里。找法：
  - 环境变量 FD_PREREQ_DIR 给了（不是空的）就只认它；指向不存在的目录 = 当作没有：在装着前置包的机器上照"只 clone 了农夫乐事"的样子跑全量；
  - 没给就找本仓库旁边的 ../arrisDiegesis（开发机上两个工程并排放在 AddOn/ 下）。
那里有 diegesisBp/arrisDiegesisScripts 和 tests/dgtest.py 才算找到。找到时 DIR 是它的根，下面几个是它里面的路径；找不到全是 None。
要前置包才跑得了的用例 import prereq（找不到就跳过，还把那边的 tests/ 放进 sys.path）；"有它就多查一点"的用例直接用这里的路径。
"""
import os

ENV = "FD_PREREQ_DIR"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # 农夫乐事仓库的根
SIBLING = os.path.join(os.path.dirname(ROOT), "arrisDiegesis")


def find(environ=None):
    """前置包工程的根（绝对路径），找不到 None。environ 缺省是 os.environ（测试里传字典）。"""
    environ = os.environ if environ is None else environ
    given = environ.get(ENV)
    where = os.path.abspath(given) if given else SIBLING
    if os.path.isdir(os.path.join(where, "diegesisBp", "arrisDiegesisScripts")) and os.path.isfile(os.path.join(where, "tests", "dgtest.py")):
        return where
    return None


DIR = find()
BP = os.path.join(DIR, "diegesisBp") if DIR else None                   # 行为包
RP = os.path.join(DIR, "diegesisRp") if DIR else None                   # 资源包
SCRIPTS = os.path.join(BP, "arrisDiegesisScripts") if DIR else None     # 脚本根
TESTS = os.path.join(DIR, "tests") if DIR else None                     # 它的测试和小工具（dgtest、dgstation、dgarch……）
TOOLS = os.path.join(DIR, "tools") if DIR else None
DOCS = os.path.join(DIR, "docs", "diegesis") if DIR else None           # DESIGN.md、CINEMA.md
