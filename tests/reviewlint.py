# -*- coding: utf-8 -*-
"""reviewlint - 本机复现网易打包机审的代码检查（不是测试本身，跑器只收 test_*.py；用它的是 test_review_lint.py 和前置包的 test_diegesis_review_lint.py）

机审的代码检查就是 Python 2 的 pylint 1.9.5（astroid 1.6.6），同一套版本在本机跑出来的错和机审报的一样（2026-11-22 两个包被打回的 43 处，
本机一处不差地复现出来，文件、行号、错误码都对得上；arrisCreate 的 tools/check_pack_audit.py 也是这么做的）。
pylint 装在引擎同款的 Python 2.7 里：python2 -m pip install --user -r tools/requirements-pylint-py2.txt
查进包的整个脚本根（QuModLibs、拷入的 dolorContainer 都进包，一样查；不进包的游戏内自检由调用的人用 ignore 去掉）。
开全部 E 类，去掉这几样：
  - 本机没有引擎的 mod 包才报的：E0401 / E0611（导入不到）、E1101 / E1102 / E1103（推断不出成员、调用）；
  - 机审不查的：python3 检查器（E1601 print-statement 这一族：单个参数的 print(...) 在 py2 里是 print 语句）、E1111 assignment-from-no-return
    （被打回的那一版里有 29 处，机审一处没报）。
机审报过的码（arrisCreate 那份清单 E1136 E1137 E0602 E1130 E1120 E1121 E1123 E1124 E0632 E0633 E1128 E1133，加上这次的 E0203 E1135）都在里面；
比机审多开的那些现在一处都没有，以后冒出来也照改（改法见各处的注释：`or ()`、类属性写初值、模块级字典的初值别写 None）。
"""
from __future__ import print_function

import io
import multiprocessing
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(ROOT, "tools", "requirements-pylint-py2.txt")
VERSIONS = {"pylint": "1.9.5", "astroid": "1.6.6"}
NOT_CHECKED = ("E0401", "E0611", "E1101", "E1102", "E1103", "E1111", "python3")
REQUIRE_ENV = "FD_REVIEW_LINT"         # 设成 required：没装 pylint 算失败（要它一定跑的地方用）；不设时跳过
SKIP = 77
HIT = re.compile(r":\d+:\d+: (E\d{4}) ")
FATAL, USAGE = 1, 32                   # pylint 退出码里的位：1 是 fatal（比如找不到要查的包），32 是参数不对


def python2():
    """引擎同款的 Python 2.7，和 tools/run_tests.py 同一个找法：环境变量 FD_PY2、py -2.7、python2、python。"""
    candidates = ([[os.environ["FD_PY2"]]] if os.environ.get("FD_PY2") else []) + [["py", "-2.7"], ["python2"], ["python"]]
    for command in candidates:
        try:
            out = subprocess.check_output(command + ["-c", "import sys; print(sys.version_info[0])"], stderr=subprocess.STDOUT)
        except (OSError, subprocess.CalledProcessError):
            continue
        if out.decode("ascii", "replace").strip() == "2":
            return command
    return None


def installed(py2):
    """py2 里装的 {"pylint": 版本, "astroid": 版本}；没装 None。"""
    code = "import pylint, astroid; print(pylint.__version__ + ' ' + astroid.__version__)"
    try:
        out = subprocess.check_output(py2 + ["-c", code], stderr=subprocess.STDOUT)
    except (OSError, subprocess.CalledProcessError):
        return None
    parts = out.decode("ascii", "replace").split()
    return {"pylint": parts[0], "astroid": parts[1]} if len(parts) == 2 else None


def unavailable():
    """跑不了的原因（找不到 Python 2.7、没装或版本不对）；跑得了 None。"""
    py2 = python2()
    if py2 is None:
        return "找不到 Python 2.7（环境变量 FD_PY2、py -2.7、python2、python 都不是）"
    found = installed(py2)
    if found != VERSIONS:
        return "Python 2.7（%s）里没有机审同款的 pylint %s / astroid %s（现在是 %s）：%s -m pip install --user -r tools/requirements-pylint-py2.txt" % (
            " ".join(py2), VERSIONS["pylint"], VERSIONS["astroid"], found, " ".join(py2))
    return None


def skip(why):
    """跑不了时的退出码：缺省跳过（77）；环境变量 FD_REVIEW_LINT=required 时算失败。"""
    if os.environ.get(REQUIRE_ENV) == "required":
        print("失败：要求跑机审的代码检查（%s=required），可是%s" % (REQUIRE_ENV, why))
        return 1
    print("跳过：" + why)
    return SKIP


def lint(packDir, scripts, ignore=()):
    """对 packDir 下的脚本根 scripts 跑机审口径的 pylint，返回命中的行（"路径:行:列: 码 名字: 说明 (所在)"）。
    pylint 自己没跑成（fatal、参数不对）抛 RuntimeError：一处都没报不等于过了。"""
    py2 = python2()
    command = py2 + ["-m", "pylint", "-j", str(min(8, multiprocessing.cpu_count())), "--disable=all", "--enable=E",
                     "--disable=" + ",".join(NOT_CHECKED), "--reports=n", "--persistent=n",
                     "--msg-template={path}:{line}:{column}: {msg_id} {symbol}: {msg} ({obj})"]
    if ignore:
        command.append("--ignore=" + ",".join(ignore))
    command.append(scripts)
    proc = subprocess.Popen(command, cwd=packDir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    out = proc.communicate()[0].decode("utf-8", "replace")
    if proc.returncode & (FATAL | USAGE):
        raise RuntimeError("pylint 没跑成（退出码 %d）：\n%s" % (proc.returncode, out[-3000:]))
    return [line for line in out.splitlines() if HIT.search(line)]


def pinned():
    """tools/requirements-pylint-py2.txt 里钉的 {包名: 版本}。"""
    found = {}
    with io.open(REQUIREMENTS, encoding="utf-8") as handle:       # 文件里有中文注释：不写编码会按本机的编码解（Windows 上 cp1252 / GBK 都解不了）
        for line in handle:
            line = line.split("#", 1)[0].strip()
            if "==" in line:
                name, version = line.split("==", 1)
                found[name.strip().lower()] = version.strip()
    return found
