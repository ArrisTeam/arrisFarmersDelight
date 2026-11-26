# -*- coding: utf-8 -*-
# runner: both
"""取别的模组的模块（Compat/OtherMods）。引擎的 ImportModule（3.10 实机，两端）：路径的第一段不是已加载的脚本根给 None；脚本根在、下面没有
这个模块抛 ImportError("No module named <缺的那一截>")；模块在、它自己导入时出错就把异常原样抛给调用的人。find 把前两种都安静地当没装
（返回 None，不打日志、不记进 failures），第三种接住、当它没装，打一行日志连同调用栈——同一个名字只打一次，之后照样再取（不记成永远没装）。
第二种怎么认是 isMissing；call 包的是函数调用、没有所取的路径，抛什么都照第三种。
沉浸式交互前置的判定（Compat/Diegesis/Presence）找它的接口也走 find。各处联动怎么用它见 test_other_mods_entries / _links / _views。
"""
from __future__ import print_function

import types

import fdtest
import linkkit
import otherkit
from otherkit import Captured, Importer

OtherMods = otherkit.OtherMods
Presence = fdtest.load("Compat.Diegesis.Presence")
Mode = linkkit.Mode
PATH, OTHER = "someModScripts.Api.Server", "anotherModScripts.api"
MODULE = types.ModuleType(PATH)
SERVER_API = Presence.API_MODULE["server"]
MEASURED = (("fdprobe3Scripts.Deep.NoSuch", "No module named NoSuch"),                  # 3.10 实机量到的：缺最后一段，文字就是那一段
            ("arrisJeiScripts.api.nothing", "No module named nothing"),
            ("arrisDiegesisScripts.Vanilla.Server.NoHooks", "No module named NoHooks"),
            ("arrisDiegesisScripts.NoSuchPkg.Thing", "No module named NoSuchPkg.Thing"))  # 缺中间的包：从它起的整截
LOOKALIKES = (ImportError("No module named broken_dependency"),   # 缺的不是所取路径的结尾：对方的模块在、它 import 的东西不在（实机文字也是这一种）
              ImportError("No module named " + PATH),             # T 等于整个路径：第一段不在时引擎给 None，走不到异常
              ImportError("No module named erver"),               # 路径的结尾对上了，但不是 "." + T
              ImportError("No module named "),                    # T 是空的
              ValueError("No module named Server"),               # 文字对，类型不是 ImportError
              ImportError("cannot import name Server"))           # ImportError，文字不是这一种


def _other(text):
    """同一段文字换成另一种字符串（py2 的 unicode、py3 的 bytes；原生的 str 是本包写的路径、实机引擎文字最可能的那一种）。"""
    return text.decode("utf-8") if str is bytes else text.encode("utf-8")


def testFindGivesTheModuleOrNoneAndNeverRaises():
    for name, answer, absent, loud in otherkit.kinds(MODULE, PATH):
        otherkit.fresh()
        importer = Importer({PATH: answer})
        with Captured() as out:
            got = OtherMods.find(importer, PATH)
        assert got is (None if absent else MODULE), name
        assert importer.asked == [PATH], name
        raised = 1 if loud else 0
        assert out.logged(PATH) == raised and out.tracebacks() == raised, (name, out.text)
        assert type(answer).__name__ in out.text or not raised, "日志里有是什么错"
        assert (PATH in OtherMods.failures()) is loud, name


def testAModuleMissingUnderAnInstalledScriptRootIsQuietlyAbsent():
    """对方的脚本根在、下面没有这个模块（装的是还没有它的旧版本）：引擎抛 ImportError，这不是出错——和引擎给 None 一样安静：
    返回 None、不打日志、不打调用栈、不记进 failures；每次照样再取。文字是实机量到的四对。"""
    for path, text in MEASURED:
        otherkit.fresh()
        importer = Importer({path: ImportError(text)})
        with Captured() as out:
            assert OtherMods.find(importer, path) is None, path
            assert OtherMods.find(importer, path) is None, path
        assert importer.asked == [path, path], path
        assert out.text == "" and OtherMods.failures() == {}, (path, out.text)
        assert OtherMods.isMissing(path, ImportError(text)) is True, path


def testOtherImportErrorsAndLookalikesAreStillLogged():
    """只有"ImportError、文字正好是 No module named T、所取路径以 .T 结尾"算没有这个模块；别的照旧当出错：打一行日志加调用栈、记进 failures。"""
    for error in LOOKALIKES:
        otherkit.fresh()
        with Captured() as out:
            assert OtherMods.find(Importer({PATH: error}), PATH) is None, repr(error)
        assert out.logged(PATH) == 1 and out.tracebacks() == 1, (repr(error), out.text)
        assert OtherMods.failures() == {PATH: repr(error)}, repr(error)
    for error in LOOKALIKES + (ImportError("No module named Server", "more"), ImportError()):    # 参数不是一个：不是引擎给的那一种
        assert OtherMods.isMissing(PATH, error) is False, repr(error)
    assert OtherMods.isMissing(PATH, ImportError("No module named Server")) is True


def testUnicodeIsComparedAsUtf8BytesInPy2AndNothingEverRaises():
    """py2 里引擎给的文字、本包写的路径都是字节串（实机只看到了文字，没看到是哪一种字符串）：文字或路径是 unicode 时先转成 utf-8 字节串再比，
    不和字节串混着比（非 ASCII 的字节串和 unicode 混着比会抛 UnicodeDecodeError）。py3 的 bytes 不比，不算没有这个模块（照出错打日志）。都不抛。"""
    py2 = str is bytes
    path, text = "someModScripts.\xe4\xb8\xad", "No module named \xe4\xb8\xad"      # 非 ASCII（py2 里是 utf-8 字节串）
    assert OtherMods.isMissing(path, ImportError(text)) is True, "都是原生的 str：非 ASCII 也照样比"
    for args in ((path, ImportError(_other(text))), (_other(path), ImportError(text)), (_other(path), ImportError(_other(text))),
                 (PATH, ImportError(_other("No module named Server")))):
        assert OtherMods.isMissing(*args) is py2, args
    assert OtherMods.isMissing(PATH, ImportError(_other(text))) is False, "转过来比了，结尾对不上"
    otherkit.fresh()
    with Captured() as out:
        assert OtherMods.find(Importer({path: ImportError(_other(text))}), path) is None
    loud = 0 if py2 else 1
    assert out.logged(path) == loud and out.tracebacks() == loud, out.text


def testTheSameBrokenModuleIsLoggedOnceButAskedAgainEveryTime():
    otherkit.fresh()
    broken = ImportError("No module named broken_dependency")
    importer = Importer({PATH: broken})
    with Captured() as out:
        for _ in range(5):
            assert OtherMods.find(importer, PATH) is None
        assert OtherMods.find(importer, OTHER) is None
    assert importer.asked == [PATH] * 5 + [OTHER], "每次照样再取：可能只是那一次没导入成"
    assert out.logged(PATH) == 1 and out.tracebacks() == 1 and out.logged(OTHER) == 0, out.text
    assert OtherMods.failures() == {PATH: repr(broken)}
    importer.answers[PATH] = MODULE
    with Captured() as out:
        assert OtherMods.find(importer, PATH) is MODULE, "这次导入成了：照样给"
    assert out.text == ""


def testEachBrokenModuleGetsItsOwnLine():
    otherkit.fresh()
    importer = Importer({PATH: ImportError("a"), OTHER: KeyError("b")})
    with Captured() as out:
        for _ in range(3):
            OtherMods.find(importer, PATH)
            OtherMods.find(importer, OTHER)
    assert out.logged(PATH) == 1 and out.logged(OTHER) == 1 and out.tracebacks() == 2, out.text
    assert sorted(OtherMods.failures()) == sorted([PATH, OTHER])


def getExtensionApi(side):
    """像机械动力的门面：取的时候才导入它自己的门面模块。"""
    if side == "broken":
        raise ImportError("No module named _facade")
    if side == "missing":
        raise ImportError("No module named getExtensionApi")      # 文字像"没有这个模块"，结尾又正好是函数名
    return {"side": side}


def testCallGuardsAFunctionOfAnotherModTheSameWay():
    otherkit.fresh()
    label = "%s.getExtensionApi" % __name__
    with Captured() as out:
        assert OtherMods.call(getExtensionApi, "server") == {"side": "server"}
        assert OtherMods.call(getExtensionApi, "broken") is None
        assert OtherMods.call(getExtensionApi, "broken") is None
    assert out.logged(label) == 1 and out.tracebacks() == 1, out.text
    assert list(OtherMods.failures()) == [label]
    otherkit.fresh()
    with Captured() as out:
        assert OtherMods.call(getExtensionApi, "missing") is None
    assert out.logged(label) == 1 and out.tracebacks() == 1, "call 没有所取的路径：抛什么都当出错"


def testThePrerequisitesApiIsFoundThroughItAndABrokenOneIsLoggedOnce():
    """Presence 在服务端导入时找一次、"全部 Addon 脚本加载完成"时再找一次：接口导入出错、不在、没有这个模块两次都当没装（最后是 STANDALONE），
    出错的日志只打一次，另外两种不打。"""
    for name, answer, absent, loud in otherkit.kinds(type("Api", (object,), {"API_VERSION": 3}), SERVER_API):
        otherkit.fresh()
        linkkit.unlink()
        Presence._sides.clear()
        listened = []
        importer = Importer({SERVER_API: answer})
        with Captured() as out:
            Presence.attach("server", [], listen=lambda event: (lambda func: listened.append(func) or func), find=importer, load=None)
            for func in listened:
                func({})
        expected = Mode.STANDALONE if absent else Mode.LINKED
        assert Mode.mode("server") == expected, (name, Mode.mode("server"))
        assert importer.asked == [SERVER_API] * (2 if absent else 1), (name, importer.asked)
        raised = 1 if loud else 0
        assert out.logged(SERVER_API) == raised and out.tracebacks() == raised, (name, out.text)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
