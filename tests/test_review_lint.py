# -*- coding: utf-8 -*-
# runner: py3
"""网易打包机审的代码检查在本机复现（tests/reviewlint.py：Python 2 的 pylint 1.9.5，和机审同一套）：农夫乐事进包的脚本一处错都不能有。

2026-11-22 v1.0.1 交上去被机审打回 21 处（Compat/Diegesis 和 Shared/Rules/HandsOn 里：对推断为 None 的量取下标 / 迭代、混入类里先读后赋的属性、
lambda 同名默认参数），前置包同一次 22 处；改完之后用这里守着，不等交上去才知道。查的是进 zip 的那些（release.json：游戏内自检
Server/Debug、Client/Debug 不进包，不查）。本机没装那一版 pylint 时整个跳过（装法见 tools/requirements-pylint-py2.txt）；
环境变量 FD_REVIEW_LINT=required 时没装算失败。前置包那一份在它自己的仓库里（tests/test_diegesis_review_lint.py）。
"""
from __future__ import print_function

import os

import fdtest
import reviewlint


def testThePinnedRequirementsAreTheReviewVersions():
    """requirements 里钉的 pylint / astroid 就是 reviewlint 认的那一版（两处一起改）。"""
    found = reviewlint.pinned()
    for name, version in reviewlint.VERSIONS.items():
        assert found.get(name) == version, "tools/requirements-pylint-py2.txt 里 %s 是 %s，reviewlint.VERSIONS 是 %s" % (name, found.get(name), version)


def testTheShippedScriptsPassTheReview():
    hits = reviewlint.lint(fdtest.BP, fdtest.SCRIPTS, ignore=("Debug",))
    for line in hits:
        print(line)
    assert not hits, "机审会打回的错 %d 处（见上面；改法见 tests/reviewlint.py 的说明）" % len(hits)


if __name__ == "__main__":
    why = reviewlint.unavailable()
    raise SystemExit(reviewlint.skip(why) if why else fdtest.run(globals()))
