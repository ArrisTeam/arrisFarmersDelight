# -*- coding: utf-8 -*-
"""run_tests - 跑 tests/ 下的离线测试（开发机，非游戏内）

每个测试文件第 2 行声明用哪个解释器跑：
    # runner: py2    只用 Python 2.7（与网易引擎一致）
    # runner: py3    只用 Python 3
    # runner: both   两个都跑
没有声明的文件视为错误（防止新测试忘了写，悄悄不跑）。

用法：
    py -3 tools/run_tests.py            跑全部
    py -3 tools/run_tests.py cooking    只跑文件名含 cooking 的
Python 2.7 解释器按顺序找：环境变量 FD_PY2、`py -2.7`、`python2`、`python`（版本须为 2.7）。
测试以退出码 0 表示通过；77 表示缺少外部资源而跳过（例如没有 clone .refs；要场景交互前置包源码的用例在旁边没有它时也是，
见 tests/prereq.py）。最后一行汇总：共几项、失败几项，有跳过的再写跳过几项。
"""
from __future__ import print_function

import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
RUNNER_RE = re.compile(r"^#\s*runner:\s*(py2|py3|both)\s*$")
SKIP_CODE = 77


def _probe(cmd):
    try:
        out = subprocess.check_output(cmd + ["-c", "import sys;print(sys.version_info[0])"], stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.decode("ascii", "replace").strip()


def findPy2():
    candidates = []
    if os.environ.get("FD_PY2"):
        candidates.append([os.environ["FD_PY2"]])
    candidates += [["py", "-2.7"], ["python2"], ["python"]]
    for cmd in candidates:
        if _probe(cmd) == "2":
            return cmd
    return None


def runnerOf(path):
    with io.open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if len(lines) < 2:
        return None
    m = RUNNER_RE.match(lines[1].strip())
    return m.group(1) if m else None


def main(argv):
    pattern = argv[1] if len(argv) > 1 else ""
    py2 = findPy2()
    py3 = [sys.executable] if sys.version_info[0] == 3 else ["py", "-3"]
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    results = []
    for name in sorted(os.listdir(TESTS)):
        if not (name.startswith("test_") and name.endswith(".py")) or pattern not in name:
            continue
        path = os.path.join(TESTS, name)
        runner = runnerOf(path)
        if runner is None:
            results.append((name, "-", "ERROR: 第 2 行缺少 # runner: py2|py3|both"))
            continue
        for tag, cmd in (("py2", py2), ("py3", py3)):
            if runner not in (tag, "both"):
                continue
            if cmd is None:
                results.append((name, tag, "ERROR: 找不到 Python 2.7 解释器"))
                continue
            proc = subprocess.Popen(cmd + ["-B", path], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out = proc.communicate()[0].decode("utf-8", "replace")
            if proc.returncode == 0:
                status = "ok"
            elif proc.returncode == SKIP_CODE:
                status = "SKIP"
            else:
                status = "FAIL\n" + out
            results.append((name, tag, status))
    failed = [r for r in results if r[2] not in ("ok", "SKIP")]
    for name, tag, status in results:
        print("[%s] %-48s %s" % (tag, name, status))
    skipped = len([r for r in results if r[2] == "SKIP"])
    print("\n%d 项，失败 %d%s" % (len(results), len(failed), "，跳过 %d" % skipped if skipped else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
