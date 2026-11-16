# -*- coding: utf-8 -*-
# runner: py3
"""煎蛋几档图标的贴图（rp/textures/items/egg_look_*.png）是 tools/gen_egg_looks.py 从煎蛋的贴图按 JE 的着色规则生成的：
手改了或煎蛋的图换了而没重新生成，这里就不一致（py -3 tools/gen_egg_looks.py 重新生成）。"""
from __future__ import print_function

import os
import subprocess
import sys

import fdtest

TOOL = os.path.join(fdtest.ROOT, "tools", "gen_egg_looks.py")


def testTheTexturesAreWhatTheGeneratorDraws():
    code = subprocess.call([sys.executable, "-B", TOOL, "--check"])
    assert code == 0, "贴图不是最新：py -3 tools/gen_egg_looks.py 重新生成"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
