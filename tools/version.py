# -*- coding: utf-8 -*-
"""发版用的版本号工具（py -3 运行，只用标准库；发版工作流在 ubuntu-22.04 自带的 Python 3.10 上跑它）

农夫乐事的是 tools/version.py（配置 release.json）；沉浸式交互前置（独立工程 arrisDiegesis）有一份照它写的 tools/dg_version.py（配置 tools/dg_release.json）：
当初两个仓库叠在同一个目录里，所以名字不同、两份只差 CONFIG 那一行；2026-11-25 前置包搬成独立工程以后两边各管各的，不再逐行比。

每次发版都要换 UUID、提升版本号（仓库主人定的规矩，这两个仓库一直这么发）：发版的第一步是 bump --new-uuid（或 set X.Y.Z --new-uuid），
工作流会核对（check --tag 和上一个发版 tag 比，header / module 的 UUID 有一个没换就报错）。
版本号的权威来源是配置里 manifests 的第一个的 header.version。别的位置由本工具一起改，不要手改：
  - 每个 manifest 的 header.version 和 modules[].version；
  - dependencies 里指向本配置另一个 manifest（uuid 等于它的 header.uuid）的那几项的 version：同一套包之间的依赖跟着走；
    别的依赖（别的作品、引擎的模块，比如农夫乐事 bp 依赖的 3ca4eaf4-…）永远不动，show 把它们列出来；
  - 脚本里的版本号常量（下面的 PYTHON_CONSTANTS：脚本读不到 manifest，新联动接口的 ext.hostVersion 读的是 Api/ExtensionApi/Version.py 的 HOST_VERSION）。
--new-uuid：每个 manifest 的 header.uuid、每个 module 的 uuid 各换一个新的 uuid4（不和这几个 manifest 里已有的任何 uuid 重），
同一套里指着旧 header.uuid 的依赖跟着换成新的；别的依赖不动（照机械动力 tools/version.py 的 set --new-uuid）。
改写时保留原文件的排版：缩进（2 / 4 / Tab）、键的顺序、换行符（LF / CRLF）、BOM、末尾有没有换行；
不是这种标准排版的 manifest 不改（改了会打乱格式），报错让人先规整。

用法（仓库根目录下；<工具> 是 tools/version.py 或 tools/dg_version.py）：
    py -3 <工具> show                                第一行是版本号，下面逐处列出版本号和 UUID；不一致时报错、退出码 1
    py -3 <工具> check [--tag vX.Y.Z]                只检查；给了 tag 再核对它形如 vX.Y.Z、等于版本号，
                                                     有上一个发版 tag 时每个 header / module 的 UUID 都要和那一版的不一样
    py -3 <工具> set X.Y.Z [--new-uuid]              改成 X.Y.Z（发版时带 --new-uuid）
    py -3 <工具> bump [--new-uuid]                   末位加一（发版时带 --new-uuid）
    py -3 <工具> notes [--tag vX.Y.Z] [--out 文件]    这一版的更新说明（发版工作流写进 Release 的正文）
上一个发版 tag：HEAD 的历史里版本号比这一版小的 vX.Y.Z tag 里最大的那个（check --tag 和 notes 用同一个）。git 命令用跟踪着配置里
第一个 manifest 的那个仓库：一般就是工作区的 .git；也认两个仓库叠在一起的开发目录（另一个的 git 目录是 .<名字>.git，前置包搬出去之前是 .diegesis.git）。

发版：bump --new-uuid（或 set X.Y.Z --new-uuid）→ 提交 → git tag vX.Y.Z → 推送分支和 tag；发版工作流核对 tag 等于这里的版本号、
UUID 都换了才出包（见工作流文件开头的注释）。
在 GitHub Actions 里（环境变量 GITHUB_ACTIONS=true）报错的第一行带 ::error::，成为运行页面上的注解。
"""
import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "release.json")
# 脚本里的版本号常量：(相对仓库根的路径, 常量名)，文件里正好一处 名字 = (x, y, z)。show / check 和 manifest 一起核对，set / bump 一起改写。
# 写在这里、不写进 release.json：那份配置只管 manifest 和出包
PYTHON_CONSTANTS = (("bp/arrisFarmersDelightScripts/Api/ExtensionApi/Version.py", "HOST_VERSION"),)
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
INDENTS = (2, 4, chr(9))
NOTES_TITLE = 120           # 更新说明里每条提交标题最多几个字符（按字符截，不按字节：汉字不会截成半个）
NOTES_MAX = 200             # 最多列几条：GitHub Release 的正文上限 125000 个字符，这两个仓库的提交标题是很长的中文句子
FIRST_NOTE = "首个通过工作流发布的版本。"


class VersionError(Exception):
    pass


def tool():
    """本工具在仓库里的名字（前置包那份叫 dg_version.py）：提示里要写对。"""
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


def constantPattern(name):
    return re.compile(r"^(%s\s*=\s*)\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)" % re.escape(name), re.M)


def loadConstants():
    """[(位置, 绝对路径, 文本, 排版, 正则)]：PYTHON_CONSTANTS 的每一个；文件不在、常量不是正好一处时抛 VersionError（set 在写任何文件之前就查完）。"""
    loaded = []
    for rel, name in PYTHON_CONSTANTS:
        path = os.path.join(ROOT, *rel.split("/"))
        if not os.path.isfile(path):
            raise VersionError("%s 不存在（%s 的 PYTHON_CONSTANTS 里写着它）" % (rel, tool()))
        text, fmt = readText(path)
        pattern = constantPattern(name)
        hits = len(pattern.findall(text))
        if hits != 1:
            raise VersionError("%s 里 %s = (x, y, z) 要正好一处，找到 %d 处" % (rel, name, hits))
        loaded.append(("%s %s" % (rel, name), path, text, fmt, pattern))
    return loaded


def uuidsOf(rel, data):
    """[(位置, uuid)]：header 的和每个 module 的。"""
    found = [("%s header.uuid" % rel, data["header"]["uuid"])]
    for i, module in enumerate(data.get("modules", [])):
        value = module.get("uuid") if isinstance(module, dict) else None
        if not isinstance(value, str) or not value:
            raise VersionError("%s modules[%d] 没有 uuid" % (rel, i))
        found.append(("%s modules[%d].uuid" % (rel, i), value))
    return found


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
    for where, _path, text, _fmt, pattern in loadConstants():
        found.append((where, "%s.%s.%s" % pattern.search(text).groups()[1:]))
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


def checkTag(cfg, tag, version):
    """tag 形如 vX.Y.Z、等于版本号；有上一个发版 tag 时每个 header / module 的 UUID 都要和那一版的不一样。返回要打印的说明。"""
    if not TAG_RE.match(tag or ""):
        raise VersionError("tag %r 不是 vX.Y.Z 的样子：发版工作流只认 v 加三段数字的 tag" % (tag,))
    if tag != "v" + version:
        target = tag[1:]
        raise VersionError("tag %s 和仓库里的版本号 %s 对不上：先 py -3 %s set %s --new-uuid 改版本号、换 UUID，提交，再打 tag %s"
                           % (tag, version, tool(), target, tag))
    base = gitBase(cfg)
    previous = previousTag(base, version)
    if previous is None:
        return ["没有上一个发版 tag：不比 UUID"]
    loaded, _own = loadAll(cfg)
    stale, missing, compared = [], [], 0
    for rel, _path, data, _fmt in loaded:
        used = previousUuids(base, previous, rel)
        if used is None:
            missing.append(rel)
            continue
        current = uuidsOf(rel, data)
        compared += len(current)
        stale += [(where, value) for where, value in current if value in used]
    if stale:
        lines = ["和上一版 %s 比，有 UUID 没换（每次发版都要换 UUID、提升版本号）：" % previous]
        lines += ["  %s 还是 %s" % item for item in stale]
        lines.append("先 py -3 %s set %s --new-uuid 换掉 UUID、提交，再把 tag %s 打到新的提交上"
                     "（以后发版用 py -3 %s bump --new-uuid 或 set X.Y.Z --new-uuid，版本号和 UUID 一步换好）" % (tool(), version, tag, tool()))
        raise VersionError("\n".join(lines))
    info = ["和上一版 %s 比，%d 个 UUID 都换了" % (previous, compared)] if compared else []
    info += ["%s 在上一版 %s 里没有（路径改了？）：这一个不比 UUID" % (rel, previous) for rel in missing]
    return info


def setVersion(cfg, version, newUuid=False):
    """改版本号；newUuid 时每个 header / module 换新的 uuid4，同一套里指着旧 header.uuid 的依赖跟着换。返回 (版本号, 换了几个 UUID)。"""
    m = VERSION_RE.match(version or "")
    if not m:
        raise VersionError("版本号要写成 X.Y.Z（三段数字），收到 %r" % (version,))
    triple = [int(part) for part in m.groups()]
    loaded, own = loadAll(cfg)
    constants = loadConstants()
    taken, renamed, replaced = set(), {}, 0
    for rel, _path, data, _fmt in loaded:
        taken.update(value for _where, value in uuidsOf(rel, data))
        taken.update(dep.get("uuid") for dep in data.get("dependencies", []) if isinstance(dep, dict))
    for rel, _path, data, _fmt in loaded:
        data["header"]["version"] = list(triple)
        for module in data.get("modules", []):
            module["version"] = list(triple)
        if newUuid:
            old = data["header"]["uuid"]
            data["header"]["uuid"] = renamed[old] = freshUuid(taken)
            for module in data.get("modules", []):
                module["uuid"] = freshUuid(taken)
            replaced += 1 + len(data.get("modules", []))
    for rel, _path, data, _fmt in loaded:
        for dep in data.get("dependencies", []):
            if internal(dep, rel, own) is not None:
                dep["version"] = list(triple)
                if newUuid:
                    dep["uuid"] = renamed[dep["uuid"]]
    for _rel, path, data, fmt in loaded:
        writeText(path, dumps(data, fmt["indent"]) + ("\n" if fmt["finalNewline"] else ""), fmt)
    for _where, path, text, fmt, pattern in constants:
        writeText(path, pattern.sub(lambda hit: "%s(%d, %d, %d)" % ((hit.group(1),) + tuple(triple)), text), fmt)
    return check(cfg), replaced


def freshUuid(taken):
    while True:
        value = str(uuid.uuid4())
        if value not in taken:
            taken.add(value)
            return value


def bump(cfg, newUuid=False):
    major, minor, patch = [int(part) for part in check(cfg).split(".")]
    return setVersion(cfg, "%d.%d.%d" % (major, minor, patch + 1), newUuid)


# ---------------------------------------------------------------- git：上一个发版 tag、更新说明


def gitRun(base, args):
    try:
        return subprocess.run(base + list(args), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        raise VersionError("找不到 git：%s" % error)


def git(base, *args):
    proc = gitRun(base, args)
    if proc.returncode != 0:
        raise VersionError("git %s 失败：%s" % (" ".join(args), proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace")


def gitBase(cfg):
    """git 命令的开头：工作区的 .git，或者叠在同一个目录里、跟踪着配置里第一个 manifest 的 .<名字>.git；都不跟踪时用工作区的 .git。"""
    candidates = [["git"]] + [["git", "--git-dir=" + path, "--work-tree=" + ROOT]
                              for path in sorted(glob.glob(os.path.join(ROOT, ".*.git"))) if os.path.isdir(path)]
    for base in candidates:
        if gitRun(base, ["ls-files", "--error-unmatch", "--", cfg["manifests"][0]]).returncode == 0:
            return base
    return ["git"]


def tagVersion(tag):
    m = TAG_RE.match(tag)
    return tuple(int(part) for part in m.groups()) if m else None


def previousTag(base, version):
    """HEAD 的历史里（git tag --merged）版本号比 version 小的 vX.Y.Z tag 里最大的那个；没有是 None。"""
    current = tuple(int(part) for part in version.split("."))
    older = []
    for tag in git(base, "tag", "--list", "v*", "--merged", "HEAD").split():
        number = tagVersion(tag)
        if number is not None and number < current:
            older.append((number, tag))
    return max(older)[1] if older else None


def previousUuids(base, tag, rel):
    """那个 tag 上同名 manifest 里的全部 header / module uuid；那一版里没有这个文件返回 None。"""
    spec = "%s:%s" % (tag, rel)
    if gitRun(base, ["cat-file", "-e", spec]).returncode != 0:
        return None
    proc = gitRun(base, ["show", spec])
    try:
        data = json.loads(proc.stdout.decode("utf-8-sig"))
    except ValueError as error:
        raise VersionError("上一版 %s 里的 %s 不是合法的 JSON：%s" % (tag, rel, error))
    header = data.get("header") if isinstance(data, dict) else None
    modules = data.get("modules", []) if isinstance(data, dict) else []
    found = set([header.get("uuid")] if isinstance(header, dict) else [])
    found.update(module.get("uuid") for module in modules if isinstance(module, dict))
    found.discard(None)
    return found


def shorten(title):
    return title if len(title) <= NOTES_TITLE else title[:NOTES_TITLE - 1] + "…"


def notes(cfg, version, tag=None):
    """更新说明的全文。有上一个 tag：列它以来的提交（不含合并），标题截短、条数有上限；没有：一句固定的话加版本号和 commit。"""
    tag = tag or "v" + version
    base = gitBase(cfg)
    head = git(base, "rev-parse", "HEAD").strip()
    previous = previousTag(base, version)
    if previous is None:
        return "%s\n\n版本 %s，commit %s\n" % (FIRST_NOTE, version, head)
    log = git(base, "log", "--no-merges", "--format=%h%x09%s", previous + "..HEAD")
    commits = [line.split("\t", 1) for line in log.splitlines() if line]
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
    sub.add_parser("show", help="打印版本号（第一行）并逐处列出版本号和 UUID")
    c = sub.add_parser("check", help="只检查各处一致")
    c.add_argument("--tag", help="再核对这个 tag 形如 vX.Y.Z、等于版本号，UUID 都和上一个发版 tag 的不一样")
    s = sub.add_parser("set", help="改成给定的版本号")
    s.add_argument("version", help="X.Y.Z")
    s.add_argument("--new-uuid", action="store_true", help="每个 header / module 换新的 UUID（发版时都要带）")
    b = sub.add_parser("bump", help="末位加一")
    b.add_argument("--new-uuid", action="store_true", help="每个 header / module 换新的 UUID（发版时都要带）")
    n = sub.add_parser("notes", help="这一版的更新说明")
    n.add_argument("--tag", help="这一版的 tag（缺省 v + 版本号）")
    n.add_argument("--out", help="写到这个文件（UTF-8），缺省打印出来")
    return p


def changed(version, replaced):
    if replaced:
        return "已改成 %s，换了 %d 个新的 UUID（py -3 %s show 看）" % (version, replaced, tool())
    return "已改成 %s；UUID 没换（发版要带 --new-uuid：每次发版都要换 UUID，工作流的 check --tag 会核对）" % version


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        cfg = loadConfig()
        if args.cmd == "show":
            version = check(cfg)
            found, outside = collect(cfg)
            loaded, _own = loadAll(cfg)
            print(version)
            for where, value in found + [item for rel, _path, data, _fmt in loaded for item in uuidsOf(rel, data)]:
                print("  %-56s %s" % (where, value))
            for where, name in outside:
                print("  %s 指向本配置以外的 %s：不跟着改" % (where, name))
        elif args.cmd == "check":
            version = check(cfg)
            if args.tag is not None:
                info = checkTag(cfg, args.tag, version)
                print("\n".join(["版本号一致：%s，tag %s 对得上" % (version, args.tag)] + info))
            else:
                print("版本号一致：%s" % version)
        elif args.cmd == "set":
            print(changed(*setVersion(cfg, args.version, args.new_uuid)))
        elif args.cmd == "bump":
            print(changed(*bump(cfg, args.new_uuid)))
        else:
            text = notes(cfg, check(cfg), args.tag)
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
