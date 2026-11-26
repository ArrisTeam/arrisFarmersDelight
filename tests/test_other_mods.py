# -*- coding: utf-8 -*-
# runner: both
"""取别的模组的模块（Compat/OtherMods）：引擎的 ImportModule 在模块不存在时给 None，模块在、它自己导入时出错就把异常原样抛给调用的人
（3.10 实机）。find / call 接住异常、当它没装（返回 None），打一行日志连同调用栈——同一个名字只打一次，之后照样再取（不记成永远没装）。
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


def testFindGivesTheModuleOrNoneAndNeverRaises():
    for name, answer, absent in otherkit.kinds(MODULE):
        otherkit.fresh()
        importer = Importer({PATH: answer})
        with Captured() as out:
            got = OtherMods.find(importer, PATH)
        assert got is (None if absent else MODULE), name
        assert importer.asked == [PATH], name
        raised = 1 if isinstance(answer, Exception) else 0
        assert out.logged(PATH) == raised and out.tracebacks() == raised, (name, out.text)
        assert type(answer).__name__ in out.text or not raised, "日志里有是什么错"


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


def testThePrerequisitesApiIsFoundThroughItAndABrokenOneIsLoggedOnce():
    """Presence 在服务端导入时找一次、"全部 Addon 脚本加载完成"时再找一次：接口导入出错两次都当没装（最后是 STANDALONE），日志只打一次。"""
    for name, answer, absent in otherkit.kinds(type("Api", (object,), {"API_VERSION": 3})):
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
        raised = 1 if isinstance(answer, Exception) else 0
        assert out.logged(SERVER_API) == raised and out.tracebacks() == raised, (name, out.text)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
