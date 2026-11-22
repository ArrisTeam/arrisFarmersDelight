# -*- coding: utf-8 -*-
# runner: py3
"""发版的两个工具（tools/version.py、tools/release_zips.py，配置 release.json）和发版工作流（.github/workflows/release.yml）。

工具在临时目录的副本上跑，不碰本仓库的文件：version 的 show / check / set / bump（同一套包之间的依赖跟着变、别的依赖不动、
排版不动、不一致时报错）、tag 的核对、更新说明（没有上一个 tag / 有上一个 tag、标题按字符截短、条数上限、不含合并）；
真打一个本仓库的 zip 看根目录、排除项、许可文件、注释、版本核对，结构检查和导入检查各种写法的报错；进包的模块不导入
不进包的游戏内自检；工作流的触发条件、job 之间的依赖、权限、钉住的 action、它调到的脚本和参数、Windows 上装的第三方库。
没有 PyYAML 时工作流只做文本断言（CI 上没装它）。前置包那一份（tools/dg_*.py）的测试在前置包的仓库里（tests/test_diegesis_release.py）。
"""
from __future__ import print_function

import ast
import copy
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile

import fdtest

ROOT = fdtest.ROOT
TOOLS = os.path.join(ROOT, "tools")
VERSION_TOOL = os.path.join(TOOLS, "version.py")
ZIP_TOOL = os.path.join(TOOLS, "release_zips.py")
CONFIG = os.path.join(ROOT, "release.json")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "release.yml")
DEBUG = ("bp/arrisFarmersDelightScripts/Server/Debug", "bp/arrisFarmersDelightScripts/Client/Debug")
EXTRAS = {"bp/LICENSE": "LICENSE", "bp/THIRD_PARTY_NOTICES.md": "THIRD_PARTY_NOTICES.md"}
THIRD_PARTY = {"PIL": "Pillow"}         # tools/ 里 import 的第三方库 -> pip 的包名：工作流的 Windows job 要装它，版本钉住
PREREQ = re.compile(r"^(dg.*|gen_book_assets|book_textures)\.py$")      # 前置包仓库的工具（同一个目录、另一个仓库）
NOTE_LIMIT = 125000                     # GitHub Release 正文的字符上限
OUTSIDE = "00000000-0000-4000-8000-000000000000"


def toolEnv(**extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("GITHUB_ACTIONS", None)
    env.update(extra)
    return env


def run(tool, *args, **options):
    """跑一个工具：(退出码, 输出)；输出的换行统一成 \\n（Windows 上管道里是 \\r\\n）。"""
    proc = subprocess.run([sys.executable, "-B", tool] + list(args), cwd=options.get("cwd", ROOT), env=options.get("env") or toolEnv(),
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def layoutOf(raw):
    """(内容, 排版)：排版是能原样写回它的 json.dumps 参数，外加换行符、BOM、末尾换行。"""
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    data = json.loads(text)
    for indent in (2, 4, "\t"):
        out = json.dumps(data, indent=indent, ensure_ascii=False, separators=(",", ": "))
        if text in (out, out + "\n"):
            return data, {"indent": indent, "crlf": b"\r\n" in raw, "bom": raw.startswith(b"\xef\xbb\xbf"), "final": text.endswith("\n")}
    raise AssertionError("不是标准排版的 JSON")


def render(data, layout):
    text = json.dumps(data, indent=layout["indent"], ensure_ascii=False, separators=(",", ": ")) + ("\n" if layout["final"] else "")
    raw = (text.replace("\n", "\r\n") if layout["crlf"] else text).encode("utf-8")
    return b"\xef\xbb\xbf" + raw if layout["bom"] else raw


class Sandbox(object):
    """临时目录里的一份仓库：两个工具、release.json、配置里的 manifest。用完 close()。"""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="fdrelease")
        os.makedirs(self.path("tools"))
        for tool in (VERSION_TOOL, ZIP_TOOL):
            shutil.copy(tool, self.path("tools"))
        shutil.copy(CONFIG, self.root)
        with io.open(CONFIG, encoding="utf-8") as handle:
            self.manifests = json.load(handle)["manifests"]
        for rel in self.manifests:
            os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
            shutil.copy(os.path.join(ROOT, *rel.split("/")), self.path(rel))

    def path(self, rel):
        return os.path.join(self.root, *rel.split("/"))

    def read(self, rel):
        with io.open(self.path(rel), "rb") as handle:
            return handle.read()

    def write(self, rel, data):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with io.open(self.path(rel), "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)

    def version(self, *args, **options):
        return run(self.path("tools/version.py"), *args, cwd=self.root, **options)

    def zip(self, *args, **options):
        return run(self.path("tools/release_zips.py"), *args, cwd=self.root, **options)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def currentVersion():
    with io.open(os.path.join(ROOT, "bp", "manifest.json"), encoding="utf-8-sig") as handle:
        return "%d.%d.%d" % tuple(json.load(handle)["header"]["version"])


def onlyNumbersChanged(before, after):
    """改写前后只有版本号数组里那几行数字变了：行数、缩进、键的顺序、换行符、末尾换行都没动。"""
    old, new = before.split(b"\n"), after.split(b"\n")
    if len(old) != len(new):
        return False
    return all(a == b or (re.match(br"^\s*\d+,?\r?$", a) and re.match(br"^\s*\d+,?\r?$", b)) for a, b in zip(old, new))


# ---------------------------------------------------------------- version


def testShowAndCheckOnThisRepo():
    code, out = run(VERSION_TOOL, "show")
    assert code == 0, out
    assert out.splitlines()[0] == currentVersion(), out
    assert "bp/manifest.json header.version" in out and "rp/manifest.json modules[0].version" in out, out
    code, out = run(VERSION_TOOL, "check")
    assert code == 0 and currentVersion() in out, out


def testSetMovesEveryManifestAndTheDependencyBetweenThemButNothingElse():
    """set 改两个 manifest 的 header / modules，bp 依赖 rp 的那一项跟着改，依赖别的作品的不动；排版（缩进、键序、换行符、末尾换行）不动。"""
    box = Sandbox()
    try:
        bp, bpLayout = layoutOf(box.read("bp/manifest.json"))
        rp, rpLayout = layoutOf(box.read("rp/manifest.json"))
        bp.setdefault("dependencies", []).extend([{"uuid": rp["header"]["uuid"], "version": [1, 0, 0]},
                                                  {"uuid": OUTSIDE, "version": [9, 9, 9]}])
        bpLayout.update(crlf=True, final=False)         # 一个 CRLF 没有末尾换行、一个 LF 有：CI 上检出的是 LF，两种都要试到
        rpLayout.update(crlf=False, final=True)
        box.write("bp/manifest.json", render(bp, bpLayout))
        box.write("rp/manifest.json", render(rp, rpLayout))
        before = {rel: box.read(rel) for rel in box.manifests}
        code, out = box.version("set", "2.3.4")
        assert code == 0 and "2.3.4" in out, out
        for rel, data, layout in (("bp/manifest.json", bp, bpLayout), ("rp/manifest.json", rp, rpLayout)):
            want = copy.deepcopy(data)
            want["header"]["version"] = [2, 3, 4]
            for module in want["modules"]:
                module["version"] = [2, 3, 4]
            for dep in want.get("dependencies", []):
                if dep["uuid"] == rp["header"]["uuid"]:
                    dep["version"] = [2, 3, 4]
            after = box.read(rel)
            assert layoutOf(after)[0] == want, rel
            assert after == render(want, layout), rel
            assert onlyNumbersChanged(before[rel], after), rel
        deps = layoutOf(box.read("bp/manifest.json"))[0]["dependencies"]
        assert [dep["version"] for dep in deps if dep["uuid"] == OUTSIDE] == [[9, 9, 9]], "依赖别的作品的版本号不跟着改"
        code, out = box.version("bump")
        assert code == 0 and "2.3.5" in out, out
        code, out = box.version("show")
        assert code == 0 and out.splitlines()[0] == "2.3.5", out
        assert "dependencies[%d]" % (len(deps) - 1) in out and OUTSIDE in out and "不跟着改" in out, out
    finally:
        box.close()


def testCheckNamesEveryPlaceThatDisagrees():
    box = Sandbox()
    try:
        assert box.version("set", "1.0.0")[0] == 0
        rp, rpLayout = layoutOf(box.read("rp/manifest.json"))
        rp["header"]["version"] = [1, 0, 9]
        box.write("rp/manifest.json", render(rp, rpLayout))
        bp, bpLayout = layoutOf(box.read("bp/manifest.json"))
        bp.setdefault("dependencies", []).append({"uuid": rp["header"]["uuid"], "version": [0, 9, 0]})
        box.write("bp/manifest.json", render(bp, bpLayout))
        for command in ("check", "show", "bump"):
            code, out = box.version(command)
            assert code == 1, (command, out)
            assert "rp/manifest.json header.version = 1.0.9" in out and "0.9.0" in out and "tools/version.py set" in out, out
        code, out = box.zip("--check", "--version", "1.0.0")
        assert code == 1 and "rp/manifest.json header.version 是 1.0.9，不是 --version 1.0.0" in out, out
    finally:
        box.close()


def testSetRefusesWhatItCannotWriteBack():
    box = Sandbox()
    try:
        for bad in ("1.0", "v1.0.0", "1.0.0.1", "a.b.c"):
            code, out = box.version("set", bad)
            assert code == 1 and "X.Y.Z" in out, (bad, out)
        ugly = b'{"format_version": 2, "header": {"uuid": "u", "version": [1, 0, 0]}, "modules": []}'
        box.write("rp/manifest.json", ugly)
        code, out = box.version("set", "1.2.3")
        assert code == 1 and "标准排版" in out, out
        assert box.read("rp/manifest.json") == ugly, "改不回原样的不改"
    finally:
        box.close()


def testTheTagMustBeVXYZAndEqualTheVersion():
    version = currentVersion()
    code, out = run(VERSION_TOOL, "check", "--tag", "v" + version)
    assert code == 0 and "v" + version in out, out
    code, out = run(VERSION_TOOL, "check", "--tag", "v99.0.0")
    assert code == 1 and "py -3 tools/version.py set 99.0.0" in out and "再打 tag v99.0.0" in out, out
    for bad in ("1.0.0", "v1.0", "v1.0.0-rc1", "V1.0.0", "", "v1.0.0 "):
        code, out = run(VERSION_TOOL, "check", "--tag", bad)
        assert code == 1 and "vX.Y.Z" in out, (bad, out)
    code, out = run(VERSION_TOOL, "check", "--tag", "v99.0.0", env=toolEnv(GITHUB_ACTIONS="true"))
    assert code == 1 and out.startswith("::error::tag v99.0.0"), "在 GitHub Actions 里报错成为注解：" + out


# ---------------------------------------------------------------- 更新说明


def gitEnv(box):
    """隔开本机的 git 配置（用户名、签名、钩子都不沾），提交人用占位的名字。"""
    empty = box.path("gitconfig")
    if not os.path.isfile(empty):
        box.write("gitconfig", "")
    return toolEnv(GIT_CONFIG_GLOBAL=empty, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                   GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.invalid",
                   GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.invalid")


def git(box, *args, **options):
    proc = subprocess.run(["git"] + list(args), cwd=box.root, env=gitEnv(box), input=options.get("stdin"),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, (args, proc.stderr.decode("utf-8", "replace"))
    return proc.stdout.decode("utf-8").strip()


class History(object):
    """拿 git fast-import 一次造出一串提交（几百个也只开一个进程）。commit 返回 mark；tag(name, mark) 打轻量 tag。"""

    def __init__(self):
        self.stream, self.mark, self.when = [], 0, 1700000000

    def commit(self, title, ref="refs/heads/main", parent=None, merge=None):
        self.mark += 1
        self.when += 60
        data = title.encode("utf-8")
        lines = [b"commit " + ref.encode("ascii"), b"mark :%d" % self.mark,
                 b"committer test <test@example.invalid> %d +0000" % self.when, b"data %d" % len(data), data]
        if parent:
            lines.append(b"from :%d" % parent)
        if merge:
            lines.append(b"merge :%d" % merge)
        self.stream.append(b"\n".join(lines) + b"\n\n")
        return self.mark

    def tag(self, name, mark):
        self.stream.append(b"reset refs/tags/" + name.encode("ascii") + b"\nfrom :%d\n\n" % mark)

    def load(self, box):
        git(box, "init", "-q")
        git(box, "fast-import", "--quiet", stdin=b"".join(self.stream))
        git(box, "symbolic-ref", "HEAD", "refs/heads/main")
        return git(box, "rev-parse", "HEAD")


def hasGit():
    try:
        return subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    except OSError:
        return False


def testTheFirstReleaseGetsOneSentenceVersionAndCommit():
    if not hasGit():
        print("跳过：没有 git")
        return
    box = Sandbox()
    try:
        assert box.version("set", "1.0.0")[0] == 0
        history = History()
        for i in range(5):
            history.commit("feat: 第 %d 条" % i)
        head = history.load(box)
        code, out = box.version("notes", env=gitEnv(box))
        assert code == 0, out
        assert out == "首个通过工作流发布的版本。\n\n版本 1.0.0，commit %s\n" % head, out
        assert "第 0 条" not in out, "没有上一个 tag：不列历史"
        code, out = box.version("notes", "--out", "notes.txt", env=gitEnv(box))
        assert code == 0, out
        with io.open(box.path("notes.txt"), encoding="utf-8") as handle:
            assert handle.read().startswith("首个通过工作流发布的版本。")
    finally:
        box.close()


def testNotesSincePreviousTagAreCutShortAndCapped():
    """上一个 tag = HEAD 的历史里比当前版本小的 vX.Y.Z 里最大的；列它以来的提交（不含合并），标题按字符截到 120，最多 200 条。"""
    if not hasGit():
        print("跳过：没有 git")
        return
    box = Sandbox()
    try:
        assert box.version("set", "1.0.0")[0] == 0
        history = History()
        first = history.commit("初始提交")
        history.tag("v0.5.0", first)
        history.tag("v0.9.0", first)
        titles = {}
        for i in range(250):
            if i == 125:
                side = history.commit("旁支上的提交", ref="refs/heads/side", parent=first)
                history.commit("合并旁支", merge=side)
            title = ("feat: 第 %03d 条，" % i + "很长的中文标题" * 30) if i % 2 else "fix: 第 %03d 条" % i
            if i == 249:
                title = ("feat: 正好一百二十个字" + "满" * 120)[:120]
            mark = history.commit(title)
            titles[mark] = title
            if i == 10:
                history.tag("v2.0.0", mark)          # 比当前版本大的不算
                history.tag("v1.0.0-rc1", mark)      # 不是 vX.Y.Z 的不算
        history.tag("v1.0.0", mark)                  # 这一版自己的 tag 不算
        head = history.load(box)
        code, out = box.version("notes", "--tag", "v1.0.0", env=gitEnv(box))
        assert code == 0, out
        lines = out.splitlines()
        assert lines[0] == "版本 1.0.0，commit %s" % head, lines[0]
        assert "自 v0.9.0 以来的 251 条提交（不含合并）：" in lines, out[:400]
        bullets = [line for line in lines if line.startswith("- ")]
        assert len(bullets) == 200, len(bullets)
        assert lines[-1] == "……另有 51 条，完整的看 git log --no-merges v0.9.0..v1.0.0", lines[-1]
        assert "合并旁支" not in out and "初始提交" not in out
        shown = [re.match(r"^- (.*) \([0-9a-f]{7,}\)$", line).group(1) for line in bullets]
        assert all(len(title) <= 120 for title in shown)
        assert shown[0] == titles[mark] and len(shown[0]) == 120, "正好 120 个字符的不截"
        cut = [title for title in shown if title.endswith("…")]
        assert cut and all(len(title) == 120 for title in cut), "截短的连省略号一共 120 个字符"
        assert all(any(full.startswith(title[:-1]) for full in titles.values()) for title in cut), "按字符截，不留半个字"
        assert len(out) < NOTE_LIMIT // 4, len(out)
        git(box, "tag", "v0.9.9", "HEAD")
        code, out = box.version("notes", env=gitEnv(box))
        assert code == 0 and "自 v0.9.9 以来没有新的提交" in out, out
    finally:
        box.close()


# ---------------------------------------------------------------- 出包


def trackedFiles(folders):
    try:
        out = subprocess.check_output(["git", "ls-files", "-z", "--"] + list(folders), cwd=ROOT)
    except (OSError, subprocess.CalledProcessError):
        return None
    return [name for name in out.decode("utf-8").split("\0") if name and os.path.isfile(os.path.join(ROOT, name))]


def testTheConfigKeepsTheSelfTestsOutAndTheLicensesIn():
    with io.open(CONFIG, encoding="utf-8") as handle:
        cfg = json.load(handle)
    assert cfg["packs"] == ["bp", "rp"] and cfg["manifests"] == ["bp/manifest.json", "rp/manifest.json"]
    assert sorted(cfg["exclude"]) == sorted(DEBUG), "只给 MCDK 调试时手动调的游戏内自检不进包"
    assert dict((item["to"], item["from"]) for item in cfg["extraFiles"]) == EXTRAS
    assert "zipName" not in cfg, "zip 的名字取仓库名（工作流给 --name）"


def testTheCheckPassesOnThisRepoAndNothingShippedImportsTheSelfTests():
    code, out = run(ZIP_TOOL, "--check", "--version", currentVersion())
    assert code == 0 and "检查通过" in out, out
    assert "exclude 里的" in out, out
    spec = importlib.util.spec_from_file_location("fd_release_zips_probe", ZIP_TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    cfg = tool.loadConfig()
    files, problems = tool.plan(cfg)
    assert not problems, problems
    assert tool.excludedModules(cfg) == (["arrisFarmersDelightScripts.Server.Debug", "arrisFarmersDelightScripts.Client.Debug"],
                                         ["Server.Debug", "Client.Debug"])
    assert tool.codeProblems(files, cfg) == [], "进包的模块导入了不进包的游戏内自检"
    assert any(rel.endswith("/modMain.py") for rel, _path in files)


def testTheZipOfThisRepoHoldsThePacksTheLicensesAndNoSelfTests():
    version = currentVersion()
    out = tempfile.mkdtemp(prefix="fdzip")
    try:
        info = {"repository": "owner/arrisFarmersDelight", "commit": "0" * 40, "version": version,
                "workflowRun": "https://github.com/owner/arrisFarmersDelight/actions/runs/1"}
        infoPath = os.path.join(out, "build_info.json")
        with io.open(infoPath, "w", encoding="utf-8") as handle:
            json.dump(info, handle)
        code, text = run(ZIP_TOOL, "--name", "arrisFarmersDelight", "--version", "99.0.0", "--out", out)
        assert code == 1 and "不是 --version 99.0.0" in text, text
        assert not os.path.exists(os.path.join(out, "arrisFarmersDelight_v99.0.0.zip")), "版本号对不上不出包"
        code, text = run(ZIP_TOOL, "--version", version, "--out", out)
        assert code == 1 and "--name" in text, text
        code, text = run(ZIP_TOOL, "--name", "arrisFarmersDelight", "--version", version, "--comment", infoPath, "--out", out)
        assert code == 0, text
        with zipfile.ZipFile(os.path.join(out, "arrisFarmersDelight_v%s.zip" % version)) as archive:
            names = archive.namelist()
            comment = archive.comment
            extras = dict((target, archive.read(target)) for target in EXTRAS)
            manifest = archive.read("bp/manifest.json")
            dirs = [entry.filename for entry in archive.infolist() if entry.is_dir()]
        files = [name for name in names if not name.endswith("/")]
        assert names == sorted(names), "按路径排序写入"
        assert set(name.split("/")[0] for name in names) == {"bp", "rp"}, "根目录只有包文件夹"
        assert set(dirs) >= {"bp/", "rp/", "bp/entities/", "rp/textures/"}, dirs[:10]
        assert not [name for name in files if name.startswith(tuple(path + "/" for path in DEBUG))], "游戏内自检不进包"
        assert not [name for name in files if "__pycache__" in name or name.endswith(".pyc") or "/." in name]
        assert [name for name in files if name.endswith(".md")] == ["bp/THIRD_PARTY_NOTICES.md"], "开发文档不进包，许可文本进"
        for target, source in EXTRAS.items():
            with io.open(os.path.join(ROOT, source), "rb") as handle:
                assert extras[target] == handle.read(), target
        with io.open(os.path.join(ROOT, "bp", "manifest.json"), "rb") as handle:
            assert manifest == handle.read()
        assert json.loads(comment.decode("utf-8")) == dict(info, package="arrisFarmersDelight"), comment
        tracked = trackedFiles(["bp", "rp"])
        if tracked is not None:
            want = set(name for name in tracked if not name.startswith(tuple(path + "/" for path in DEBUG))) | set(EXTRAS)
            assert not sorted(want - set(files)), "入了库的文件没进包：%s" % sorted(want - set(files))[:10]
            assert not sorted(set(files) - want), "包里多了没入库的文件（本机工作区里的东西会打进本机出的包）：%s" % sorted(set(files) - want)[:10]
    finally:
        shutil.rmtree(out, ignore_errors=True)


def writeFixture(root, files, cfg):
    os.makedirs(os.path.join(root, "tools"))
    shutil.copy(ZIP_TOOL, os.path.join(root, "tools"))
    files = dict(files, **{"release.json": json.dumps(cfg)})
    for rel, content in files.items():
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "wb") as handle:
            handle.write(content.encode("utf-8") if isinstance(content, str) else content)


def manifest(kind, version=(1, 0, 0)):
    return json.dumps({"format_version": 2, "header": {"uuid": "u-" + kind, "version": list(version)},
                       "modules": [{"type": kind, "uuid": "m-" + kind, "version": list(version)}]}, indent=2)


def testTheCheckReportsEveryBrokenRule():
    """行为包没有 entities/、资源包两条、exclude 不存在、extraFiles 两种、Python 3 解析不了、各种写法导入不进包的模块。"""
    root = tempfile.mkdtemp(prefix="fdzipbad")
    try:
        writeFixture(root, {
            "LICENSE": "x",
            "bp/manifest.json": manifest("data"),
            "bp/pkg/__init__.py": "",
            "bp/pkg/modMain.py": 'MOD.Server("Server.Debug.T")\nSTEPS = [("x", "Server.Debug.T:run", None)]\nMOD.Client("Server.DebugTools")\n',
            "bp/pkg/Server/__init__.py": "from . import Debug\n",
            "bp/pkg/Server/A.py": "from .Debug import T\nfrom .DebugTools import x\n",
            "bp/pkg/Server/B.py": "import pkg.Server.Debug.T\n",
            "bp/pkg/Server/C.py": "from pkg.Server import Debug\n",
            "bp/pkg/Server/D.py": "import Debug\n",
            "bp/pkg/Server/E.py": "from ..Server.Debug.T import run\n",
            "bp/pkg/Server/F.py": 'print "py2 only"\n',
            "bp/pkg/Server/Fine.py": '"""说的是 pkg.Server.Debug 的事。"""\nfrom .DebugTools import x\nimport json\nNAME = "pkg.Server.DebugTools"\n',
            "bp/pkg/Server/DebugTools.py": "x = 1\n",
            "bp/pkg/Server/Debug/__init__.py": "",
            "bp/pkg/Server/Debug/T.py": "def run():\n    pass\n",
            "rp/manifest.json": manifest("resources"),
            "rp/entities/x.json": "{}",
        }, {"manifests": ["bp/manifest.json", "rp/manifest.json"], "packs": ["bp", "rp"],
            "exclude": ["bp/pkg/Server/Debug", "bp/nowhere"],
            "extraFiles": [{"from": "MISSING", "to": "bp/MISSING"}, {"from": "LICENSE", "to": "LICENSE"}]})
        code, out = run(os.path.join(root, "tools", "release_zips.py"), "--check", cwd=root)
        assert code == 1, out
        for expected in ("bp 是行为包，包里却没有 entities/", "rp 是资源包，包里却没有 textures/ 也没有 shaders/", "rp 是资源包，不能有 entities/",
                         "exclude 里的 bp/nowhere 不存在", "extraFiles 的 MISSING 不存在", "extraFiles 的 LICENSE 要放进某个包文件夹里",
                         "bp/pkg/Server/F.py:1 Python 3 解析不了",
                         "bp/pkg/modMain.py:1 导入了不进包的 Server.Debug", "bp/pkg/modMain.py:2 导入了不进包的 Server.Debug",
                         "bp/pkg/Server/__init__.py:1 导入了不进包的 pkg.Server.Debug", "bp/pkg/Server/A.py:1 导入了不进包的 pkg.Server.Debug",
                         "bp/pkg/Server/B.py:1 导入了", "bp/pkg/Server/C.py:1 导入了", "bp/pkg/Server/D.py:1 导入了", "bp/pkg/Server/E.py:1 导入了"):
            assert expected in out, (expected, out)
        for innocent in ("Fine.py", "A.py:2", "modMain.py:3", "Debug/T.py"):
            assert innocent not in out, (innocent, out)
        assert "包的检查没过，15 个问题" in out, out
        code, out = run(os.path.join(root, "tools", "release_zips.py"), "--check", cwd=root, env=toolEnv(GITHUB_ACTIONS="true"))
        assert code == 1 and out.count("::error::") == 16, "第一行和每一条问题都成为注解：" + out
    finally:
        shutil.rmtree(root, ignore_errors=True)


def testJunkStaysOutThePlaceholderStaysInAndTheZipIsWhole():
    root = tempfile.mkdtemp(prefix="fdzipok")
    try:
        files = {
            "LICENSE": "license text", "docs/NOTICE.md": "notice",
            "bp/manifest.json": manifest("data", (1, 2, 3)), "bp/entities/.gitkeep": "", "bp/.hidden.json": "{}", "bp/.cache/a.json": "{}",
            "bp/pkg/__init__.py": "", "bp/pkg/A.py": "from . import B\n", "bp/pkg/B.py": "x = 1\n", "bp/pkg/B.pyc": b"\0",
            "bp/pkg/__pycache__/A.cpython-313.pyc": b"\0", "bp/pkg/README.md": "dev", "bp/pkg/LICENSE.md": "license",
            "bp/pkg/Debug/T.py": "x = 1\n", "bp/pkg/Debug/data.json": "{}",
            "rp/manifest.json": manifest("resources", (1, 2, 3)), "rp/textures/a.png": b"png", "rp/textures/.gitkeep": "", "rp/.DS_Store": b"\0",
        }
        cfg = {"manifests": ["bp/manifest.json", "rp/manifest.json"], "packs": ["bp", "rp"], "exclude": ["bp/pkg/Debug"],
               "extraFiles": [{"from": "LICENSE", "to": "bp/LICENSE"}, {"from": "docs/NOTICE.md", "to": "bp/legal/NOTICE.md"}]}
        writeFixture(root, files, cfg)
        tool = os.path.join(root, "tools", "release_zips.py")
        code, out = run(tool, "--name", "demo", "--version", "1.2.3", "--out", "dist", cwd=root)
        assert code == 0, out
        with zipfile.ZipFile(os.path.join(root, "dist", "demo_v1.2.3.zip")) as archive:
            names = archive.namelist()
            infos = archive.infolist()
            comment = archive.comment
            assert archive.read("bp/legal/NOTICE.md") == b"notice"
        assert [name for name in names if not name.endswith("/")] == [
            "bp/LICENSE", "bp/entities/.gitkeep", "bp/legal/NOTICE.md", "bp/manifest.json", "bp/pkg/A.py", "bp/pkg/B.py", "bp/pkg/LICENSE.md",
            "bp/pkg/__init__.py", "rp/manifest.json", "rp/textures/a.png"], names
        assert [info.filename for info in infos if info.is_dir()] == ["bp/", "bp/entities/", "bp/legal/", "bp/pkg/", "rp/", "rp/textures/"], names
        assert names == sorted(names)
        assert json.loads(comment.decode("utf-8")) == {"package": "demo"}
        assert "exclude 里的 2 个文件不进包" in out, out
        cfg["zipName"] = "Other"
        with io.open(os.path.join(root, "release.json"), "w", encoding="utf-8") as handle:
            json.dump(cfg, handle)
        code, out = run(tool, "--name", "demo", "--version", "1.2.3", "--out", "dist", cwd=root)
        assert code == 0 and os.path.isfile(os.path.join(root, "dist", "Other_v1.2.3.zip")), "配置里写了 zipName 就用它"
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- 工作流


def workflowText():
    with io.open(WORKFLOW, encoding="utf-8") as handle:
        return handle.read()


def loadTool(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CALL_RE = re.compile(r"\bpython3?\s+(tools/[\w.]+\.py)([^\n]*)")


def toolCalls(text):
    """工作流的命令（注释不算）里调到的工具和参数：引号里带 $ 的变量换成占位，管道、重定向、命令替换的后半截不要。"""
    calls = []
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        for m in CALL_RE.finditer(line):
            rest = re.sub(r'"[^"]*\$[^"]*"', "X", m.group(2))
            calls.append((m.group(1), shlex.split(re.split(r"[|>)]", rest)[0])))
    return calls


def testTheWorkflowRunsOnVersionTagsPinsEveryActionAndCallsTheToolsAsTheyAre():
    text = workflowText()
    assert '\non:\n  push:\n    tags: ["v[0-9]+.[0-9]+.[0-9]+"]\n  workflow_dispatch:\n' in text
    assert "\npermissions:\n  contents: read\n" in text
    pins = re.findall(r"^\s*(?:-\s+)?uses:\s*(\S+)(.*)$", text, re.M)
    assert len(pins) == 6, pins
    for ref, rest in pins:
        assert re.match(r"^actions/[\w-]+(/[\w-]+)?@[0-9a-f]{40}$", ref), ref
        assert re.match(r"^ # v\d+\.\d+\.\d+$", rest), (ref, rest)
    assert re.search(r"^\s+PY27_MSI_SHA256: [0-9a-f]{64}$", text, re.M)
    assert "PY27_URL: https://www.python.org/ftp/python/2.7.18/python-2.7.18.amd64.msi\n" in text
    calls = toolCalls(text)
    used = sorted(set(tool for tool, _args in calls))
    assert used == ["tools/release_zips.py", "tools/run_tests.py", "tools/version.py"], used
    parsers = {"tools/version.py": loadTool(VERSION_TOOL, "fd_version_probe").parser(),
               "tools/release_zips.py": loadTool(ZIP_TOOL, "fd_release_zips_probe2").parser()}
    for tool, args in calls:
        assert os.path.isfile(os.path.join(ROOT, *tool.split("/"))), tool
        if tool in parsers:
            try:
                parsers[tool].parse_args(args)
            except SystemExit:
                raise AssertionError("工作流给 %s 的参数它不认：%s" % (tool, args))
        else:
            assert args == [], (tool, args)
    for command in (["check", "--tag", "X"], ["check"], ["show"], ["notes", "--tag", "X", "--out", "changelog.txt"], ["notes", "--out", "changelog.txt"]):
        assert ("tools/version.py", command) in calls, command
    assert ("tools/release_zips.py", ["--check", "--version", "X"]) in calls
    assert ("tools/release_zips.py", ["--name", "X", "--version", "X", "--comment", "build_info.json", "--out", "dist"]) in calls
    assert 'gh release create "$GITHUB_REF_NAME" dist/*.zip --verify-tag --title "$GITHUB_REF_NAME" --notes-file changelog.txt' in text


def inlinePython(text):
    """工作流里 python3 - <<'EOF' … EOF 那几段内嵌的 Python（去掉 YAML 的缩进）。"""
    return [textwrap.dedent(block) for block in re.findall(r"python3 - <<'EOF'\n(.*?)\n[ ]*EOF\n", text, re.S)]


def testTheInlinePythonWritesTheBuildInfo():
    """「来源信息」那一步内嵌的 Python 照 GitHub 给的环境变量写出 build_info.json：四个键、末尾有换行（离线没人跑它，写坏了只有推 tag 才知道）。"""
    blocks = inlinePython(workflowText())
    assert len(blocks) == 1, blocks
    work = tempfile.mkdtemp(prefix="fdinfo")
    try:
        env = toolEnv(GITHUB_REPOSITORY="owner/arrisFarmersDelight", GITHUB_SHA="0" * 40, VERSION="1.2.3",
                      GITHUB_SERVER_URL="https://github.com", GITHUB_RUN_ID="42")
        proc = subprocess.run([sys.executable, "-"], input=blocks[0].encode("utf-8"), cwd=work, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.returncode == 0, proc.stdout.decode("utf-8", "replace")
        with io.open(os.path.join(work, "build_info.json"), encoding="utf-8") as handle:
            text = handle.read()
        assert text.endswith("}\n"), repr(text[-5:])
        assert json.loads(text) == {"repository": "owner/arrisFarmersDelight", "commit": "0" * 40, "version": "1.2.3",
                                    "workflowRun": "https://github.com/owner/arrisFarmersDelight/actions/runs/42"}, text
    finally:
        shutil.rmtree(work, ignore_errors=True)


def testTheWindowsJobInstallsWhatTheToolsImport():
    """测试经 --check 调到的生成器 import 的第三方库，Windows 的 job 都 pip install 了，版本钉住（前置包的工具不算）。"""
    needed = set()
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith(".py") or PREREQ.match(name):
            continue
        with io.open(os.path.join(TOOLS, name), "rb") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules = [node.module.split(".")[0]]
            else:
                continue
            needed.update(module for module in modules if module not in sys.stdlib_module_names and module != "__future__"
                          and not os.path.isfile(os.path.join(TOOLS, module + ".py")))
    unknown = sorted(needed - set(THIRD_PARTY))
    assert not unknown, "tools/ 里 import 了 %s：加进工作流 test job 的 pip install（钉版本），再写进本文件的 THIRD_PARTY" % unknown
    text = workflowText()
    for module in sorted(needed):
        assert re.search(r'pip install [^\n]*"%s==\d+(\.\d+)*"' % THIRD_PARTY[module], text), module


def needsOf(job):
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else list(needs)


def expressionsIn(value):
    if isinstance(value, dict):
        return [found for item in value.values() for found in expressionsIn(item)]
    if isinstance(value, list):
        return [found for item in value for found in expressionsIn(item)]
    return re.findall(r"\$\{\{(.*?)\}\}", value) if isinstance(value, str) else []


def testTheJobsHangTogether():
    try:
        import yaml
    except ImportError:
        print("没有 PyYAML：工作流只做了文本断言")
        return
    doc = yaml.safe_load(workflowText())
    on = doc.get("on", doc.get(True))           # YAML 1.1 把键 on 读成 True
    assert on == {"push": {"tags": ["v[0-9]+.[0-9]+.[0-9]+"]}, "workflow_dispatch": None}, on
    assert doc["permissions"] == {"contents": "read"}
    jobs = doc["jobs"]
    assert list(jobs) == ["check", "test", "release"]
    assert needsOf(jobs["check"]) == [] and needsOf(jobs["test"]) == ["check"] and needsOf(jobs["release"]) == ["check", "test"]
    assert [jobs[name]["runs-on"] for name in jobs] == ["ubuntu-22.04", "windows-2022", "ubuntu-22.04"]
    assert "permissions" not in jobs["check"] and "permissions" not in jobs["test"]
    assert jobs["release"]["permissions"] == {"contents": "write"}, "只有建 Release 的 job 能写"
    assert jobs["check"]["outputs"] == {"version": "${{ steps.version.outputs.version }}"}
    versionStep = [step for step in jobs["check"]["steps"] if step.get("id") == "version"][0]
    assert 'echo "version=$VERSION" >> "$GITHUB_OUTPUT"' in versionStep["run"]
    assert jobs["release"]["env"]["VERSION"] == "${{ needs.check.outputs.version }}"
    for name, job in jobs.items():
        ids = set(step.get("id") for step in job["steps"])
        known = set(doc.get("env", {})) | set(job.get("env", {}))
        conditions = [step["if"] for step in job["steps"] if "if" in step]
        for expression in expressionsIn(job) + conditions:
            for ref in re.findall(r"\bsteps\.([\w-]+)\.", expression):
                assert ref in ids, (name, expression)
            for ref in re.findall(r"\bneeds\.([\w-]+)\.", expression):
                assert ref in needsOf(job), (name, expression)
            for ref in re.findall(r"\benv\.(\w+)", expression):
                assert ref in known, (name, expression)
            contexts = set(re.findall(r"\b([a-z]+)\.[\w-]+", expression))
            assert contexts <= {"steps", "needs", "env", "secrets", "github", "outputs"}, (name, expression)
    for step in jobs["test"]["steps"]:
        if "run" in step:
            assert step.get("shell") in ("bash", "pwsh"), "Windows 上的缺省 shell 是 pwsh：每一步写明 %s" % step["name"]
    gate = [step for step in jobs["test"]["steps"] if "tools/run_tests.py" in step.get("run", "")]
    assert len(gate) == 1 and gate[0]["shell"] == "bash" and "失败 0" in gate[0]["run"] and "tr -d" in gate[0]["run"]
    setup = [step for step in jobs["test"]["steps"] if step.get("uses", "").startswith("actions/setup-python@")]
    assert len(setup) == 1 and setup[0]["with"] == {"python-version": "3.13"}
    create = [step for step in jobs["release"]["steps"] if "gh release create" in step.get("run", "")]
    assert len(create) == 1 and create[0]["if"] == "github.event_name == 'push'", "手动运行不建 Release"
    assert create[0]["env"]["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    for name in ("check", "release"):
        checkout = jobs[name]["steps"][0]
        assert checkout["uses"].startswith("actions/checkout@") and checkout["with"]["fetch-depth"] == 0, name


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
