# -*- coding: utf-8 -*-
"""把包文件夹打成上架网易用的 zip（py -3 运行，只用标准库；发版工作流在 ubuntu-22.04 自带的 Python 3.10 上跑它）

农夫乐事的是 tools/release_zips.py（配置 release.json），沉浸式交互前置的是 tools/dg_release_zips.py（配置 tools/dg_release.json）：
两个仓库叠在同一个目录里，所以名字不同；两份除了 CONFIG 那一行逐字一样（tests/test_diegesis_release.py 比着）。

源码原样进包，不去注释、docstring 和 print：两个仓库都开源，发出去的就是测试过的那份代码。配置（路径都相对仓库根）：
    manifests   版本号所在的 manifest（第一个是权威来源，见 version 工具）：出包前核对它们的 header.version、modules[].version 都等于 --version
    packs       进 zip 的包文件夹（仓库根下一层）：zip 根目录只有它们（网易要求上传包的根目录只有包文件夹，打包错误代码 24）
    exclude     不进包的文件或目录；进包的 .py 不许导入它们（import、from … import，按点分路径登记 / 导入的字符串也算）
    extraFiles  额外放进包里的文件 [{"from": 仓库里的路径, "to": zip 里的路径}]：只在打包时放，源码树不动
    zipName     zip 名字的前缀，可以不写：没写用 --name（发版工作流给仓库名）
总是不进包的：__pycache__、*.pyc / *.pyo、点开头的文件和目录（行为包 entities/ 里占位的 .gitkeep 除外：网易靠 entities 文件夹认行为包，
空文件夹进不了 git，机械动力的前置包也是这么放的）、.md 开发文档（名字里有 license / licence / notice / copying 的许可文本除外）。
结构检查（网易的规矩，同机械动力 scripts/pack_scripts.py 的 check_pack_layout）：行为包（manifest 的模块类型有 data）里要有 entities/
且里面有文件；资源包（resources）里要有 textures/ 或 shaders/，不能有 entities/（会被当成行为包）。另外进包的 .py 都要能被 Python 3 解析
（两个仓库的代码约定：给引擎的 Python 2.7 写，同时是合法的 Python 3 语法）。
来源信息（仓库、commit、版本、工作流运行的地址，加上包名）写成 JSON 放进 zip 注释：7-Zip 打开压缩包看得到，或者 unzip -z <zip>。
zip 里的目录项和文件按路径排序写入。

用法（仓库根目录下；<工具> 是 tools/release_zips.py 或 tools/dg_release_zips.py）：
    py -3 <工具> --check [--version X.Y.Z]                                                 只检查，不出包
    py -3 <工具> --name <仓库名> --version X.Y.Z [--comment build_info.json] [--out 目录]     出包（缺省写到当前目录）
在 GitHub Actions 里（环境变量 GITHUB_ACTIONS=true）报错的每一条成为运行页面上的注解。
"""
import argparse
import ast
import io
import json
import os
import re
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "release.json")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
NAME_RE = re.compile(r"^[\w.-]+$")
DOTTED_RE = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)+$")
LICENSE_WORDS = ("license", "licence", "notice", "copying")
PLACEHOLDER = ".gitkeep"
COMMENT_MAX = 65535         # zip 注释最多这么多字节


class ReleaseError(Exception):
    pass


def tool():
    """本工具在仓库里的名字：两个仓库的名字不同，提示里要写对。"""
    return "tools/" + os.path.basename(__file__)


def versionTool():
    """同一个仓库里版本号工具的名字（tools/version.py 或 tools/dg_version.py）。"""
    return tool().replace("release_zips", "version")


def configName():
    return os.path.relpath(CONFIG, ROOT).replace(os.sep, "/")


def fail(message):
    actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for i, line in enumerate(message.splitlines() or [""]):
        if actions and (i == 0 or line.startswith("  - ")):
            line = "::error::" + line.strip()
        print(line)


def norm(path):
    return path.replace("\\", "/").strip("/")


def local(rel):
    return os.path.join(ROOT, *rel.split("/"))


# ---------------------------------------------------------------- 配置


def pathList(cfg, key, required):
    value = cfg.get(key, [])
    if not isinstance(value, list) or (required and not value) or not all(isinstance(item, str) and norm(item) for item in value):
        raise ReleaseError("%s 的 %s 要是%s路径列表" % (configName(), key, "至少有一项的" if required else ""))
    return [norm(item) for item in value]


def loadConfig():
    if not os.path.isfile(CONFIG):
        raise ReleaseError("缺少配置 %s" % configName())
    with io.open(CONFIG, encoding="utf-8") as handle:
        try:
            raw = json.load(handle)
        except ValueError as error:
            raise ReleaseError("%s 不是合法的 JSON：%s" % (configName(), error))
    if not isinstance(raw, dict):
        raise ReleaseError("%s 要是一个 JSON 对象" % configName())
    cfg = {"manifests": pathList(raw, "manifests", True), "packs": pathList(raw, "packs", True),
           "exclude": pathList(raw, "exclude", False), "zipName": raw.get("zipName")}
    nested = [pack for pack in cfg["packs"] if "/" in pack]
    if nested:
        raise ReleaseError("%s 的 packs 要是仓库根下一层的文件夹：%s" % (configName(), "、".join(nested)))
    extras = raw.get("extraFiles", [])
    if not isinstance(extras, list) or not all(isinstance(item, dict) and isinstance(item.get("from"), str)
                                               and isinstance(item.get("to"), str) for item in extras):
        raise ReleaseError('%s 的 extraFiles 要是 [{"from": 仓库里的路径, "to": zip 里的路径}] 的列表' % configName())
    cfg["extraFiles"] = [(norm(item["from"]), norm(item["to"])) for item in extras]
    if cfg["zipName"] is not None and not (isinstance(cfg["zipName"], str) and NAME_RE.match(cfg["zipName"])):
        raise ReleaseError("%s 的 zipName 只能用字母、数字、_ . -：%r" % (configName(), cfg["zipName"]))
    return cfg


# ---------------------------------------------------------------- 哪些文件进包


def isLicense(name):
    lower = name.lower()
    return any(word in lower for word in LICENSE_WORDS)


def droppedDir(name):
    return name.startswith(".") or name == "__pycache__"


def dropped(rel):
    """按规矩总是不进包的（不看配置）返回原因，进包的返回 None。rel 是 zip 里的路径（也就是相对仓库根的路径）。"""
    parts = rel.split("/")
    name = parts[-1]
    if any(droppedDir(part) for part in parts[:-1]) or name.endswith((".pyc", ".pyo")):
        return "字节码或点开头的目录"
    if name.startswith(".") and not (name == PLACEHOLDER and len(parts) == 3 and parts[1] == "entities"):
        return "点开头的文件"
    if name.lower().endswith(".md") and not isLicense(name):
        return "开发文档"
    return None


def isExcluded(rel, excluded):
    return any(rel == path or rel.startswith(path + "/") for path in excluded)


def plan(cfg):
    """(进包的 [(zip 里的路径, 本机的路径)]（按路径排好）, [问题])。"""
    packs, excluded = cfg["packs"], cfg["exclude"]
    problems = []
    for rel in excluded:
        if rel.split("/")[0] not in packs:
            problems.append("exclude 里的 %s 不在任何一个包文件夹里" % rel)
        elif not os.path.exists(local(rel)):
            problems.append("exclude 里的 %s 不存在：路径写错了，或者东西挪走了（改 %s）" % (rel, configName()))
    files = []
    for pack in packs:
        top = local(pack)
        if not os.path.isfile(os.path.join(top, "manifest.json")):
            problems.append("%s 不是包文件夹（里面没有 manifest.json）" % pack)
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            base = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
            dirnames[:] = sorted(name for name in dirnames if not droppedDir(name) and not isExcluded(base + "/" + name, excluded))
            for name in filenames:
                rel = base + "/" + name
                if dropped(rel) is None and not isExcluded(rel, excluded):
                    files.append((rel, os.path.join(dirpath, name)))
    shipped = set(rel for rel, _path in files)
    for source, target in cfg["extraFiles"]:
        if not os.path.isfile(local(source)):
            problems.append("extraFiles 的 %s 不存在" % source)
        elif "/" not in target or target.split("/")[0] not in packs:
            problems.append("extraFiles 的 %s 要放进某个包文件夹里（zip 根目录只能有包文件夹）" % target)
        elif target in shipped:
            problems.append("extraFiles 的 %s 和包里本来就有的文件重名" % target)
        elif dropped(target) is not None or isExcluded(target, excluded):
            problems.append("extraFiles 的 %s 是不进包的那种文件" % target)
        else:
            files.append((target, local(source)))
            shipped.add(target)
    files.sort()
    return files, problems


def excludedCount(cfg):
    count = 0
    for rel in cfg["exclude"]:
        path = local(rel)
        if os.path.isfile(path):
            count += 1
        for _dirpath, _dirnames, filenames in os.walk(path):
            count += len(filenames)
    return count


# ---------------------------------------------------------------- 检查


def packKind(pack):
    try:
        with io.open(os.path.join(local(pack), "manifest.json"), encoding="utf-8-sig") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        return None
    modules = manifest.get("modules", []) if isinstance(manifest, dict) else []
    types = set(module.get("type") for module in modules if isinstance(module, dict))
    if "data" in types:
        return "behavior"
    if "resources" in types:
        return "resource"
    return None


def layoutProblems(files, cfg):
    problems = []
    names = [rel for rel, _path in files]
    for pack in cfg["packs"]:
        if not os.path.isfile(os.path.join(local(pack), "manifest.json")):
            continue
        inner = [name[len(pack) + 1:] for name in names if name.startswith(pack + "/")]

        def has(folder):
            return any(name.startswith(folder + "/") for name in inner)

        kind = packKind(pack)
        if kind == "behavior":
            if not has("entities"):
                problems.append("%s 是行为包，包里却没有 entities/ 或它是空的（网易靠这个文件夹认行为包；没有实体就放一个 entities/.gitkeep）" % pack)
        elif kind == "resource":
            if not (has("textures") or has("shaders")):
                problems.append("%s 是资源包，包里却没有 textures/ 也没有 shaders/" % pack)
            if has("entities"):
                problems.append("%s 是资源包，不能有 entities/（网易会把它当成行为包）" % pack)
        else:
            problems.append("%s/manifest.json 认不出是行为包还是资源包（modules[].type 要有 data 或 resources）" % pack)
    return problems


def excludedModules(cfg):
    """(模块名, 相对脚本根的写法)：exclude 里的路径换成点分路径。包文件夹下的第一层目录（脚本根）是顶层包；引擎按相对脚本根的点分路径
    登记模块（MOD.Server("Server.ModServer")），那种写法也算（至少两段，免得一个词就算上）。"""
    full, rooted = [], []
    for rel in cfg["exclude"]:
        parts = rel.split("/")[1:]
        if parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            full.append(".".join(parts))
            if len(parts) >= 3:
                rooted.append(".".join(parts[1:]))
    return full, rooted


def under(name, prefixes):
    return next((prefix for prefix in prefixes if name == prefix or name.startswith(prefix + ".")), None)


def moduleOf(rel):
    parts = rel.split("/")[1:]
    parts[-1] = parts[-1][:-3]
    isPackage = parts[-1] == "__init__"
    if isPackage:
        parts = parts[:-1]
    return ".".join(parts), isPackage


def importTargets(node, module, isPackage):
    """这条 import 可能导入的模块（点分的全名）。py2 的隐式相对导入（包里的 import X 先找同一个包里的 X）也算上。"""
    package = module if isPackage else module.rpartition(".")[0]
    implicit = True
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    else:
        base = node.module or ""
        if node.level:
            parts = package.split(".") if package else []
            if node.level - 1 > len(parts):
                return []
            base = ".".join(parts[:len(parts) - (node.level - 1)] + ([node.module] if node.module else []))
            implicit = False
        names = [base] + [(base + "." if base else "") + alias.name for alias in node.names if alias.name != "*"]
    if implicit and package:
        names += [package + "." + name for name in names if name]
    return [name for name in names if name]


def codeProblems(files, cfg):
    full, rooted = excludedModules(cfg)
    problems = []
    for rel, path in files:
        if not rel.endswith(".py"):
            continue
        with io.open(path, "rb") as handle:
            source = handle.read()
        try:
            tree = ast.parse(source, filename=rel)
        except (SyntaxError, ValueError) as error:
            problems.append("%s:%s Python 3 解析不了：%s" % (rel, getattr(error, "lineno", "?"), getattr(error, "msg", error)))
            continue
        module, isPackage = moduleOf(rel)
        for node in (ast.walk(tree) if full else ()):
            hit = None
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                hit = next((found for found in (under(name, full) for name in importTargets(node, module, isPackage)) if found), None)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.split(":", 1)[0]
                if DOTTED_RE.match(text):
                    hit = under(text, full) or under(text, rooted)
            if hit:
                problems.append("%s:%d 导入了不进包的 %s（exclude 里的，游戏里没有它）" % (rel, node.lineno, hit))
    return problems


def versionProblems(cfg, version):
    triple = [int(part) for part in version.split(".")]
    problems = []
    for rel in cfg["manifests"]:
        try:
            with io.open(local(rel), encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as error:
            problems.append("%s 读不了：%s" % (rel, error))
            continue
        header = data.get("header") if isinstance(data, dict) else None
        places = [("header.version", header.get("version") if isinstance(header, dict) else None)]
        places += [("modules[%d].version" % i, module.get("version") if isinstance(module, dict) else None)
                   for i, module in enumerate(data.get("modules", []) if isinstance(data, dict) else [])]
        for where, value in places:
            if value != triple:
                shown = ".".join(str(part) for part in value) if isinstance(value, list) else repr(value)
                problems.append("%s %s 是 %s，不是 --version %s（先 py -3 %s set %s --new-uuid 改版本号、换 UUID，提交，再打 tag）"
                                % (rel, where, shown, version, versionTool(), version))
    return problems


# ---------------------------------------------------------------- 出包


def commentOf(path, name):
    info = {}
    if path:
        try:
            with io.open(path, encoding="utf-8") as handle:
                info = json.load(handle)
        except (OSError, ValueError) as error:
            raise ReleaseError("--comment %s 读不了：%s" % (path, error))
        if not isinstance(info, dict):
            raise ReleaseError("--comment %s 要是一个 JSON 对象" % path)
    data = json.dumps(dict(info, package=name), ensure_ascii=False, indent=2).encode("utf-8")
    if len(data) > COMMENT_MAX:
        raise ReleaseError("来源信息 %d 字节，zip 注释最多 %d 字节" % (len(data), COMMENT_MAX))
    return data


def directories(files):
    found = set()
    for rel, _path in files:
        parts = rel.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            found.add("/".join(parts[:i]) + "/")
    return found


def dirInfo(arc):
    source = local(arc.rstrip("/"))
    stamp = time.localtime(os.stat(source).st_mtime if os.path.isdir(source) else time.time())[:6]
    info = zipfile.ZipInfo(arc, date_time=stamp if stamp[0] >= 1980 else (1980, 1, 1, 0, 0, 0))
    info.external_attr = (0o40755 << 16) | 0x10     # 目录：unix 的 drwxr-xr-x 加 MS-DOS 的目录位（和 zip -r 一样）
    return info


def writeZip(files, path, comment):
    entries = sorted([(arc, None) for arc in directories(files)] + list(files))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
        for arc, source in entries:
            if source is None:
                archive.writestr(dirInfo(arc), b"")
            else:
                archive.write(source, arc)
        archive.comment = comment


def verifyZip(path, files, cfg, comment):
    """出包后再打开读一遍：校验和、注释、排序、根目录、文件一个不多一个不少。"""
    with zipfile.ZipFile(path) as archive:
        broken = archive.testzip()
        names = archive.namelist()
        stored = archive.comment
    problems = []
    if broken is not None:
        problems.append("%s 的校验和不对" % broken)
    if stored != comment:
        problems.append("注释没写对")
    if names != sorted(names):
        problems.append("条目没按路径排序")
    extra = sorted(set(name.split("/")[0] for name in names) - set(cfg["packs"]))
    if extra:
        problems.append("根目录多了 %s（只能有包文件夹）" % "、".join(extra))
    if [name for name in names if not name.endswith("/")] != [rel for rel, _path in files]:
        problems.append("里面的文件和要打进去的对不上")
    if problems:
        raise ReleaseError("出的包 %s 不对：\n%s" % (path, "\n".join("  - " + item for item in problems)))


def summary(files, cfg):
    counts = ["%s %d 个" % (pack, len([rel for rel, _path in files if rel.startswith(pack + "/")])) for pack in cfg["packs"]]
    text = "%s，共 %d 个文件（含 extraFiles 的 %d 个）" % ("、".join(counts), len(files), len(cfg["extraFiles"]))
    if cfg["exclude"]:
        text += "；exclude 里的 %d 个文件不进包" % excludedCount(cfg)
    return text


# ---------------------------------------------------------------- 命令行


def parser():
    p = argparse.ArgumentParser(prog=tool(), description="把包文件夹打成上架网易用的 zip（配置 %s）" % configName())
    p.add_argument("--check", action="store_true", help="只检查，不出包")
    p.add_argument("--name", help="仓库名：配置里没写 zipName 时作 zip 名字的前缀")
    p.add_argument("--version", help="版本号 X.Y.Z：写进 zip 的名字，并核对 manifest 都是它")
    p.add_argument("--comment", help="来源信息 JSON（发版工作流写的 build_info.json），写进 zip 注释")
    p.add_argument("--out", default=".", help="zip 写到哪个目录（缺省当前目录）")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        cfg = loadConfig()
        if args.version is not None and not VERSION_RE.match(args.version):
            raise ReleaseError("--version 要写成 X.Y.Z（三段数字），收到 %r" % (args.version,))
        name = cfg["zipName"] or args.name
        problems = []
        if not args.check:
            if args.version is None:
                problems.append("出包要给 --version X.Y.Z")
            if not name or not NAME_RE.match(name):
                problems.append("出包要给 --name <仓库名>（只能用字母、数字、_ . -；%s 里没写 zipName）" % configName())
        files, found = plan(cfg)
        problems += found + layoutProblems(files, cfg) + codeProblems(files, cfg)
        if args.version is not None:
            problems += versionProblems(cfg, args.version)
        if problems:
            raise ReleaseError("包的检查没过，%d 个问题：\n%s" % (len(problems), "\n".join("  - " + item for item in problems)))
        if args.check:
            print("检查通过：%s" % summary(files, cfg))
            return 0
        comment = commentOf(args.comment, name)
        if not os.path.isdir(args.out):
            os.makedirs(args.out)
        path = os.path.join(args.out, "%s_v%s.zip" % (name, args.version))
        writeZip(files, path, comment)
        verifyZip(path, files, cfg, comment)
        print("%s  <- %s；%d 字节" % (os.path.basename(path), summary(files, cfg), os.path.getsize(path)))
    except ReleaseError as error:
        fail("%s：%s" % (tool(), error))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
