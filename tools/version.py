# -*- coding: utf-8 -*-
"""发版用的版本号工具（py -3 运行，只用标准库；发版工作流在 ubuntu-22.04 自带的 Python 3.10 上跑它）

农夫乐事的是 tools/version.py（配置 release.json），沉浸式交互前置的是 tools/dg_version.py（配置 tools/dg_release.json）：
两个仓库叠在同一个目录里，所以名字不同；两份除了 CONFIG 那一行逐字一样（tests/test_diegesis_release.py 比着）。

版本号的权威来源是配置里 manifests 的第一个的 header.version。别的位置由本工具一起改，不要手改：
  - 每个 manifest 的 header.version 和 modules[].version；
  - dependencies 里指向本配置另一个 manifest（uuid 等于它的 header.uuid）的那几项的 version：同一套包之间的依赖跟着走；
    别的依赖（别的作品、引擎的模块）不动，show 把它们列出来。
改写时保留原文件的排版：缩进（2 / 4 / Tab）、键的顺序、换行符（LF / CRLF）、BOM、末尾有没有换行；
不是这种标准排版的 manifest 不改（改了会打乱格式），报错让人先规整。

用法（仓库根目录下；<工具> 是 tools/version.py 或 tools/dg_version.py）：
    py -3 <工具> show                                第一行是版本号，下面逐处列出；不一致时报错、退出码 1
    py -3 <工具> check [--tag vX.Y.Z]                只检查；给了 tag 再核对它形如 vX.Y.Z、等于版本号
    py -3 <工具> set X.Y.Z                           改成 X.Y.Z
    py -3 <工具> bump                                末位加一
    py -3 <工具> notes [--tag vX.Y.Z] [--out 文件]    这一版的更新说明（发版工作流写进 Release 的正文）

发版：set → 提交 → git tag vX.Y.Z → 推送分支和 tag；发版工作流核对 tag 等于这里的版本号才出包（见工作流文件开头的注释）。
在 GitHub Actions 里（环境变量 GITHUB_ACTIONS=true）报错的第一行带 ::error::，成为运行页面上的注解。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "release.json")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
INDENTS = (2, 4, chr(9))
NOTES_TITLE = 120           # 更新说明里每条提交标题最多几个字符（按字符截，不按字节：汉字不会截成半个）
NOTES_MAX = 200             # 最多列几条：GitHub Release 的正文上限 125000 个字符，这两个仓库的提交标题是很长的中文句子
FIRST_NOTE = "首个通过工作流发布的版本。"


class VersionError(Exception):
    pass


def tool():
    """本工具在仓库里的名字：两个仓库的名字不同，提示里要写对。"""
    return "tools/" + os.path.basename(__file__)


def configName():
    return os.path.relpath(CONFIG, ROOT).replace(os.sep, "/")


def fail(message):
    lines = message.splitlines() or [""]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        lines[0] = "::error::" + lines[0]
    print("\n".join(lines))


# ---------------------------------------------------------------- 配置与 manifest（保留原有排版）


def loadConfig():
    if not os.path.isfile(CONFIG):
        raise VersionError("缺少配置 %s（写着版本号在哪几个 manifest 里）" % configName())
    with io.open(CONFIG, encoding="utf-8") as handle:
        try:
            cfg = json.load(handle)
        except ValueError as error:
            raise VersionError("%s 不是合法的 JSON：%s" % (configName(), error))
    names = cfg.get("manifests") if isinstance(cfg, dict) else None
    if not names or not all(isinstance(name, str) for name in names):
        raise VersionError("%s 的 manifests 要是至少有一项的路径列表" % configName())
    return cfg


def readText(path):
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8-sig")
    fmt = {"bom": raw.startswith(b"\xef\xbb\xbf"), "crlf": "\r\n" in text}
    return text.replace("\r\n", "\n"), fmt


def writeText(path, text, fmt):
    if fmt["crlf"]:
        text = text.replace("\n", "\r\n")
    data = text.encode("utf-8")
    if fmt["bom"]:
        data = b"\xef\xbb\xbf" + data
    with io.open(path, "wb") as handle:
        handle.write(data)


def dumps(data, indent):
    return json.dumps(data, indent=indent, ensure_ascii=False, separators=(",", ": "))


def loadManifest(rel):
    path = os.path.join(ROOT, *rel.split("/"))
    if not os.path.isfile(path):
        raise VersionError("%s 不存在（%s 的 manifests 里写着它）" % (rel, configName()))
    text, fmt = readText(path)
    try:
        data = json.loads(text)
    except ValueError as error:
        raise VersionError("%s 不是合法的 JSON：%s" % (rel, error))
    for indent in INDENTS:
        out = dumps(data, indent)
        if text in (out, out + "\n"):
            fmt["indent"] = indent
            fmt["finalNewline"] = text.endswith("\n")
            return path, data, fmt
    raise VersionError("%s 不是标准排版的 JSON（json.dumps 缩进 2 / 4 / Tab 写得出原样的那种）：本工具改写会打乱格式，先规整它" % rel)


def loadAll(cfg):
    """[(配置里写的路径, 绝对路径, 内容, 排版)]，外加 {header.uuid: 配置里写的路径}。"""
    loaded, own = [], {}
    for rel in cfg["manifests"]:
        path, data, fmt = loadManifest(rel)
        header = data.get("header") if isinstance(data, dict) else None
        if not isinstance(header, dict) or not header.get("uuid"):
            raise VersionError("%s 没有 header.uuid" % rel)
        own[header["uuid"]] = rel
        loaded.append((rel, path, data, fmt))
    return loaded, own


def versionText(value, where):
    if not (isinstance(value, list) and len(value) == 3 and all(type(part) is int and part >= 0 for part in value)):
        raise VersionError("%s 不是 [x, y, z] 三个非负整数：%r" % (where, value))
    return "%d.%d.%d" % tuple(value)


def internal(dep, rel, own):
    """这项依赖指向本配置里另一个 manifest 时返回那个 manifest 的路径，否则 None。"""
    target = own.get(dep.get("uuid")) if isinstance(dep, dict) else None
    return target if target not in (None, rel) else None


# ---------------------------------------------------------------- 读、查、改


def collect(cfg):
    """([(位置, "x.y.z")], [(位置, 指向谁)])：前一个列表的第一项是权威来源；后一个是本配置以外的依赖（不跟着改）。"""
    loaded, own = loadAll(cfg)
    found, outside = [], []
    for rel, _path, data, _fmt in loaded:
        found.append(("%s header.version" % rel, versionText(data["header"].get("version"), rel + " header.version")))
        for i, module in enumerate(data.get("modules", [])):
            where = "%s modules[%d].version" % (rel, i)
            found.append((where, versionText(module.get("version") if isinstance(module, dict) else None, where)))
        for i, dep in enumerate(data.get("dependencies", [])):
            target = internal(dep, rel, own)
            where = "%s dependencies[%d].version" % (rel, i)
            if target is not None:
                found.append(("%s（依赖 %s）" % (where, target), versionText(dep.get("version"), where)))
            else:
                name = (dep.get("uuid") or dep.get("module_name")) if isinstance(dep, dict) else dep
                outside.append(("%s dependencies[%d]" % (rel, i), name))
    return found, outside


def check(cfg):
    """各处一致时返回版本号，不一致抛 VersionError（逐处列出）。"""
    found, _outside = collect(cfg)
    expected = found[0][1]
    bad = [(where, value) for where, value in found if value != expected]
    if bad:
        lines = ["版本号不一致（以 %s = %s 为准）：" % (found[0][0], expected)]
        lines += ["  %s = %s" % item for item in bad]
        lines.append("用 py -3 %s set <版本号> 一起改" % tool())
        raise VersionError("\n".join(lines))
    return expected


def checkTag(tag, version):
    if not TAG_RE.match(tag or ""):
        raise VersionError("tag %r 不是 vX.Y.Z 的样子：发版工作流只认 v 加三段数字的 tag" % (tag,))
    if tag != "v" + version:
        target = tag[1:]
        raise VersionError("tag %s 和仓库里的版本号 %s 对不上：先 py -3 %s set %s 改版本号、提交，再打 tag %s" % (tag, version, tool(), target, tag))


def setVersion(cfg, version):
    m = VERSION_RE.match(version or "")
    if not m:
        raise VersionError("版本号要写成 X.Y.Z（三段数字），收到 %r" % (version,))
    triple = [int(part) for part in m.groups()]
    loaded, own = loadAll(cfg)
    for rel, _path, data, _fmt in loaded:
        data["header"]["version"] = list(triple)
        for module in data.get("modules", []):
            module["version"] = list(triple)
        for dep in data.get("dependencies", []):
            if internal(dep, rel, own) is not None:
                dep["version"] = list(triple)
    for _rel, path, data, fmt in loaded:
        writeText(path, dumps(data, fmt["indent"]) + ("\n" if fmt["finalNewline"] else ""), fmt)
    return check(cfg)


def bump(cfg):
    major, minor, patch = [int(part) for part in check(cfg).split(".")]
    return setVersion(cfg, "%d.%d.%d" % (major, minor, patch + 1))


# ---------------------------------------------------------------- 更新说明


def git(*args):
    try:
        proc = subprocess.run(["git"] + list(args), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        raise VersionError("找不到 git：%s" % error)
    if proc.returncode != 0:
        raise VersionError("git %s 失败：%s" % (" ".join(args), proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace")


def tagVersion(tag):
    m = TAG_RE.match(tag)
    return tuple(int(part) for part in m.groups()) if m else None


def previousTag(version):
    """HEAD 的历史里（git tag --merged）版本号比 version 小的 vX.Y.Z tag 里最大的那个；没有是 None。"""
    current = tuple(int(part) for part in version.split("."))
    older = []
    for tag in git("tag", "--list", "v*", "--merged", "HEAD").split():
        number = tagVersion(tag)
        if number is not None and number < current:
            older.append((number, tag))
    return max(older)[1] if older else None


def shorten(title):
    return title if len(title) <= NOTES_TITLE else title[:NOTES_TITLE - 1] + "…"


def notes(version, tag=None):
    """更新说明的全文。有上一个 tag：列它以来的提交（不含合并），标题截短、条数有上限；没有：一句固定的话加版本号和 commit。"""
    tag = tag or "v" + version
    head = git("rev-parse", "HEAD").strip()
    previous = previousTag(version)
    if previous is None:
        return "%s\n\n版本 %s，commit %s\n" % (FIRST_NOTE, version, head)
    commits = [line.split("\t", 1) for line in git("log", "--no-merges", "--format=%h%x09%s", previous + "..HEAD").splitlines() if line]
    lines = ["版本 %s，commit %s" % (version, head), ""]
    if not commits:
        lines.append("自 %s 以来没有新的提交（不含合并）。" % previous)
        return "\n".join(lines) + "\n"
    lines += ["自 %s 以来的 %d 条提交（不含合并）：" % (previous, len(commits)), ""]
    lines += ["- %s (%s)" % (shorten(title), short) for short, title in commits[:NOTES_MAX]]
    if len(commits) > NOTES_MAX:
        lines.append("……另有 %d 条，完整的看 git log --no-merges %s..%s" % (len(commits) - NOTES_MAX, previous, tag))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 命令行


def parser():
    p = argparse.ArgumentParser(prog=tool(), description="发版用的版本号工具（配置 %s）" % configName())
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="打印版本号（第一行）并逐处列出")
    c = sub.add_parser("check", help="只检查各处一致")
    c.add_argument("--tag", help="再核对这个 tag 形如 vX.Y.Z、等于版本号")
    s = sub.add_parser("set", help="改成给定的版本号")
    s.add_argument("version", help="X.Y.Z")
    sub.add_parser("bump", help="末位加一")
    n = sub.add_parser("notes", help="这一版的更新说明")
    n.add_argument("--tag", help="这一版的 tag（缺省 v + 版本号）")
    n.add_argument("--out", help="写到这个文件（UTF-8），缺省打印出来")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        cfg = loadConfig()
        if args.cmd == "show":
            version = check(cfg)
            found, outside = collect(cfg)
            print(version)
            for where, value in found:
                print("  %-56s %s" % (where, value))
            for where, name in outside:
                print("  %s 指向本配置以外的 %s：不跟着改" % (where, name))
        elif args.cmd == "check":
            version = check(cfg)
            if args.tag is not None:
                checkTag(args.tag, version)
                print("版本号一致：%s，tag %s 对得上" % (version, args.tag))
            else:
                print("版本号一致：%s" % version)
        elif args.cmd == "set":
            print("已改成 %s" % setVersion(cfg, args.version))
        elif args.cmd == "bump":
            print("已改成 %s" % bump(cfg))
        else:
            text = notes(check(cfg), args.tag)
            if args.out:
                with io.open(args.out, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                print("更新说明写进了 %s（%d 个字符）" % (args.out, len(text)))
            else:
                print(text, end="")
    except VersionError as error:
        fail(str(error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
