# -*- coding: utf-8 -*-
# runner: both
"""守卫：跨端 RPC 参数的反序列化必须是受限实现，行为包脚本里不得出现裸反序列化。

QuModLibs 的跨端 Call 会把对端发来的"签名表"参数反序列化。签名用的是无密钥、
可在本地算出的 hash，只是格式判别，不是安全校验；改包客户端能伪造出通过判别的
payload。所以安全边界只能放在反序列化侧：

1. 仓库里每一份 QuModLibs 的 QStruct.loads / loadSignData 都必须拒绝一切类与
   可调用对象引用（纯数据照常还原，携带 __reduce__ 的 payload 不得执行）；
2. EasyListener 解包对端参数时必须经 _safeUnpackSigned 降级，不得直接
   QStruct.loadSignData(v).onNetUnPack()；
3. 行为包脚本（含 modMain.py 的脚本根目录下）不得出现裸 pickle / cPickle /
   marshal 反序列化或 eval / exec。确有需要时只能走受限 Unpickler。

本文件在主包与各官方附属包里保持同一份内容。
"""
from __future__ import print_function, unicode_literals

import io
import os
import pickle
import re
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_RAW_DESERIALIZE = re.compile(r"\b(?:_?pickle|cPickle|marshal)\.loads\s*\(|(?<![\w.])(?:eval|exec)\s*\(")


def _trackedFiles():
    try:
        out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    except (OSError, subprocess.CalledProcessError):
        out = None
    if out is not None:
        names = out.decode("utf-8").split("\0")
        # 工作区里删掉但还没暂存的文件仍在 ls-files 里，跳过
        return [n.replace("\\", "/") for n in names if n and os.path.isfile(os.path.join(ROOT, n))]
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, name), ROOT).replace("\\", "/"))
    return found


def _read(rel):
    with io.open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


def _loadUtil(quDir):
    # 主包的 Util.py 以 `from Information import Version` 引用同目录模块，
    # 所以加载期间把 QuModLibs 目录放到 sys.path 最前，加载完立即移除。
    path = os.path.join(ROOT, quDir, "Util.py")
    name = str("_qumod_util_%d" % (abs(hash(quDir)),))
    sys.path.insert(0, os.path.join(ROOT, quDir))
    try:
        if sys.version_info[0] == 2:
            import imp

            return imp.load_source(name, path)
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.pop(0)
        sys.modules.pop("Information", None)


class _Hit(object):
    count = 0


def _boom():
    _Hit.count += 1
    return "executed"


class _Evil(object):
    def __reduce__(self):
        return (_boom, ())


def _checkCopy(quDir, failures):
    util = _loadUtil(quDir)
    qstruct = util.QStruct
    sample = {"a": [1, 2.5, (3, "x")], "b": None, "c": True, u"d": u"中文"}
    for proto in range(pickle.HIGHEST_PROTOCOL + 1):
        if qstruct.loads(pickle.dumps(sample, proto)) != sample:
            failures.append("%s: QStruct.loads 还原纯数据失败（protocol %d）" % (quDir, proto))
        payload = pickle.dumps(_Evil(), proto)
        for label, call in (
            ("QStruct.loads", lambda: qstruct.loads(payload)),
            ("QStruct.loadSignData", lambda: qstruct.loadSignData(["sign", payload])),
        ):
            try:
                call()
            except pickle.UnpicklingError:
                pass
            except Exception as e:  # noqa: BLE001 - 任何其他异常都说明没走受限 Unpickler
                failures.append("%s: %s 对恶意 payload 抛了 %r，应为 UnpicklingError" % (quDir, label, e))
            else:
                failures.append("%s: %s 接受了携带可调用对象的 payload（protocol %d）" % (quDir, label, proto))
    if _Hit.count:
        failures.append("%s: 恶意 payload 里的可调用对象被执行了 %d 次" % (quDir, _Hit.count))
        _Hit.count = 0

    sharedRes = quDir + "/Systems/Loader/SharedRes.py"
    if os.path.exists(os.path.join(ROOT, sharedRes)):
        codeLines = [_code(line) for line in _read(sharedRes).splitlines()]
        if any("loadSignData(v).onNetUnPack()" in c for c in codeLines):
            failures.append("%s: 对端参数仍直接 loadSignData(v).onNetUnPack()，应经 _safeUnpackSigned" % sharedRes)
        if not any("_safeUnpackSigned" in c for c in codeLines):
            failures.append("%s: 缺少 _safeUnpackSigned 降级解包" % sharedRes)


def _scriptRoots(files):
    return sorted(set(f.rsplit("/", 1)[0] for f in files if f.endswith("/modMain.py")))


def _code(lineText):
    # 只看代码部分：注释里提到旧写法（说明历史实现）不算违规。
    return lineText.split("#", 1)[0]


def main():
    files = _trackedFiles()
    failures = []

    copies = sorted(f[: -len("/Util.py")] for f in files if f.endswith("/QuModLibs/Util.py"))
    for quDir in copies:
        _checkCopy(quDir, failures)

    roots = _scriptRoots(files)
    for rel in files:
        if not rel.endswith(".py") or not any(rel.startswith(r + "/") for r in roots):
            continue
        for lineNo, line in enumerate(_read(rel).splitlines(), 1):
            if _RAW_DESERIALIZE.search(_code(line)):
                failures.append("%s:%d: 行为包脚本里出现裸反序列化或 eval/exec: %s" % (rel, lineNo, line.strip()))

    print("QuModLibs 副本 %d 份，脚本根目录 %d 个" % (len(copies), len(roots)))
    for quDir in copies:
        print("  " + quDir)
    if failures:
        print("\nFAIL")
        for item in failures:
            print("  - " + item)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
