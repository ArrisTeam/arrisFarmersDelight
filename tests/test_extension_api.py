# -*- coding: utf-8 -*-
# runner: both
"""新联动接口的骨架（Api/ExtensionApi，两端的 ExtensionReady / ExtensionSystem）。

事件协议的常量和机械动力同一套名字、命名空间是 arrisFarmersDelight；门面的标识（side / apiVersion / hostVersion / capabilities / hasCapability），
每端一个；主包版本号等于两个 manifest；ready 每端只播一次、载荷带这一端的门面；拿不到系统、广播出错都不连累农夫乐事（只打一次调用栈）；
两端的接线：服务端 ModServer 的 LoadServerAddonScriptsAfter 经 EventRegistry 到 ExtensionReady，客户端 ExtensionReady 自己 @Listen
LoadClientAddonScriptsAfter；广播用的系统按公布的命名空间、系统名注册，类路径解析得到。
"""
from __future__ import print_function

import ast
import importlib
import io
import json
import os
import re
import sys
import types

import fdtest

Events = fdtest.load("Api.ExtensionApi.Events")
Facade = fdtest.load("Api.ExtensionApi.Facade")
Ready = fdtest.load("Api.ExtensionApi.Ready")
Version = fdtest.load("Api.ExtensionApi.Version")
SCRIPTS = os.path.join(fdtest.BP, fdtest.SCRIPTS)

try:
    _UNICODE = unicode  # noqa: F821 - py2
except NameError:
    _UNICODE = str


class _Capture(object):
    """临时顶替 sys.stdout / sys.stderr，收下打印的东西（py2 里统一成 utf-8 的 str）。"""

    def __init__(self):
        self.parts = []
        self.saved = None

    def write(self, text):
        if str is bytes and isinstance(text, _UNICODE):
            text = text.encode("utf-8")
        self.parts.append(text)

    def flush(self):
        pass

    def __enter__(self):
        self.saved = (sys.stdout, sys.stderr)
        sys.stdout = sys.stderr = self
        return self

    def __exit__(self, *exc):
        sys.stdout, sys.stderr = self.saved
        return False

    def text(self):
        return "".join(self.parts)


class _FakeSystem(object):
    """广播用系统的替身：记下 BroadcastEvent；raises 给了就在广播时抛它（别的模组的处理函数出错、框架没兜住）。"""

    def __init__(self, raises=None):
        self.calls = []
        self.raises = raises

    def BroadcastEvent(self, eventName, payload):
        self.calls.append((eventName, payload))
        if self.raises is not None:
            raise self.raises


def _read(*parts):
    with io.open(os.path.join(SCRIPTS, *parts), encoding="utf-8") as handle:
        return handle.read()


def _tree(*parts):
    """按字节交给 ast（py2 的 ast.parse 不收带编码声明的 unicode）。"""
    with io.open(os.path.join(SCRIPTS, *parts), "rb") as handle:
        return ast.parse(handle.read())


def _text(node):
    """字符串字面量的值（py2 的 ast.Str 是 .s，py3 的 ast.Constant 是 .value）；不是字符串字面量是 None。"""
    value = getattr(node, "value", getattr(node, "s", None))
    return value if isinstance(value, (str, _UNICODE)) else None


# ---------------------------------------------------------------- 事件协议与门面


def testTheEventProtocolIsCreatesUnderOurNamespace():
    assert Events.EXTENSION_API_VERSION == 1
    assert (Events.EXTENSION_API_NAMESPACE, Events.EXTENSION_API_SYSTEM_NAME) == ("arrisFarmersDelight", "ExtensionApi")
    assert (Events.SERVER_EXTENSION_API_READY_EVENT, Events.CLIENT_EXTENSION_API_READY_EVENT) == ("ServerExtensionApiReady", "ClientExtensionApiReady")
    for event, eventId in ((Events.SERVER_EXTENSION_API_READY_EVENT, Events.SERVER_EXTENSION_API_READY_EVENT_ID),
                           (Events.CLIENT_EXTENSION_API_READY_EVENT, Events.CLIENT_EXTENSION_API_READY_EVENT_ID)):
        assert eventId == "arrisFarmersDelight:ExtensionApi:" + event, eventId
    assert Events.SIDES == ("server", "client")
    assert Events.READY_EVENTS == {"server": "ServerExtensionApiReady", "client": "ClientExtensionApiReady"}
    tree = _tree("Api", "ExtensionApi", "Events.py")
    assert not [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))], "只放常量：别的模组导入它不会拉起别的东西"


def testCapabilitiesArePerSideFrozenSetsOfPlainNames():
    for capabilities in (Events.SERVER_CAPABILITIES, Events.CLIENT_CAPABILITIES):
        assert isinstance(capabilities, frozenset), capabilities
        bad = [name for name in capabilities if not (isinstance(name, str) and re.match(r"^[a-z][a-z0-9_]*$", name))]
        assert not bad, "能力名是小写下划线的字符串：%r" % bad


def testTheFacadeTellsItsSideTheTwoVersionsAndItsCapabilities():
    server, client = Facade.getExtensionApi("server"), Facade.getExtensionApi("client")
    assert server is Facade.getExtensionApi("server") and client is Facade.getExtensionApi("client"), "每端一个，同一端总是同一个对象"
    assert server is not client
    for ext, side, capabilities in ((server, "server", Events.SERVER_CAPABILITIES), (client, "client", Events.CLIENT_CAPABILITIES)):
        assert ext.side == side
        assert ext.apiVersion == Events.EXTENSION_API_VERSION == 1
        assert ext.hostVersion == Version.HOST_VERSION and ext.hostVersion >= (1, 0, 0)
        assert ext.capabilities == capabilities and isinstance(ext.capabilities, frozenset)
        assert all(ext.hasCapability(name) for name in ext.capabilities)
        for name in ("no_such_capability", "", None, 3, ["recipes"], {"a": 1}):
            assert ext.hasCapability(name) is False, name
        for attribute in ("side", "apiVersion", "hostVersion", "capabilities"):
            try:
                setattr(ext, attribute, None)
            except AttributeError:
                pass
            else:
                raise AssertionError("%s 是只读的" % attribute)
        assert side in repr(ext)


def testOnlyTheTwoSidesHaveAFacade():
    for bad in ("both", "Server", "", None, ["server"]):
        for make in (Facade.getExtensionApi, Facade.ExtensionApiFacade):
            try:
                make(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("%r 不是一端" % (bad,))


def testThePackageOffersCreatesFallbackWithoutImportingTheFacade():
    """主会话定的 A1-P7：包级的兜底入口，写法和机械动力一样（ImportModule("...Api.ExtensionApi").getExtensionApi(side)），拿到的和
    Facade.getExtensionApi 的是同一个对象；包的 __init__ 顶层什么都不导入（别的模组导入本包里的 Events 拿常量时 Python 先执行它，不能顺带拉起门面）。"""
    package = fdtest.load("Api.ExtensionApi")
    for side in ("server", "client"):
        assert package.getExtensionApi(side) is Facade.getExtensionApi(side), side
    for bad in ("both", None):
        try:
            package.getExtensionApi(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("%r 不是一端" % (bad,))
    tree = _tree("Api", "ExtensionApi", "__init__.py")
    assert not [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))], "顶层不导入：门面到调用时才导入"


def testTheHostVersionIsTheVersionOfBothManifests():
    assert isinstance(Version.HOST_VERSION, tuple) and len(Version.HOST_VERSION) == 3
    assert all(type(part) is int and part >= 0 for part in Version.HOST_VERSION), Version.HOST_VERSION
    for pack in ("bp", "rp"):
        with io.open(os.path.join(fdtest.ROOT, pack, "manifest.json"), encoding="utf-8-sig") as handle:
            header = json.load(handle)["header"]
        assert tuple(header["version"]) == Version.HOST_VERSION, "%s/manifest.json 是 %r，HOST_VERSION 是 %r：用 tools/version.py set 一起改" % (
            pack, header["version"], Version.HOST_VERSION)


# ---------------------------------------------------------------- ready 广播


def testReadyIsBroadcastOncePerSideWithThatSidesFacade():
    publisher = Ready.Publisher()
    server, client = _FakeSystem(), _FakeSystem()
    assert publisher.publish("server", lambda: server) == Ready.SENT
    assert publisher.publish("server", lambda: server) is None, "同一端只播一次"
    assert len(server.calls) == 1
    event, payload = server.calls[0]
    assert event == "ServerExtensionApiReady"
    assert set(payload) == {"extension", "side", "apiVersion"}
    assert payload["extension"] is Facade.getExtensionApi("server") and payload["side"] == "server" and payload["apiVersion"] == 1
    assert publisher.states == {"server": Ready.SENT, "client": None}, "服务端播过不等于客户端播过（单机两端同一个进程）"
    assert publisher.publish("client", lambda: client) == Ready.SENT
    assert [(event, payload["extension"], payload["side"]) for event, payload in client.calls] == [
        ("ClientExtensionApiReady", Facade.getExtensionApi("client"), "client")]
    assert len(server.calls) == 1


def testNoSystemMeansNoBroadcastAndNoError():
    for systemOf in (lambda: None, lambda: 0):
        publisher = Ready.Publisher()
        with _Capture() as out:
            assert publisher.publish("server", systemOf) == Ready.NO_SYSTEM
        assert "拿不到广播用的系统" in out.text(), out.text()
        assert publisher.publish("server", lambda: _FakeSystem()) is None, "只试一次"

    def broken():
        raise RuntimeError("RegisterSystem failed")

    publisher = Ready.Publisher()
    with _Capture() as out:
        assert publisher.publish("client", broken) == Ready.NO_SYSTEM
    assert out.text().count("Traceback") == 1 and "RegisterSystem failed" in out.text(), out.text()


def testAHandlerThatRaisesDoesNotStopFarmersDelight():
    publisher = Ready.Publisher()
    system = _FakeSystem(raises=KeyError("their handler"))
    with _Capture() as out:
        assert publisher.publish("server", lambda: system) == Ready.RAISED
    assert len(system.calls) == 1
    text = out.text()
    assert text.count("Traceback") == 1 and "their handler" in text and "ready 事件的处理函数出错" in text, text
    assert publisher.publish("server", lambda: system) is None and len(system.calls) == 1
    try:
        publisher.publish("both", lambda: system)
    except ValueError:
        pass
    else:
        raise AssertionError("side 不对要报")


# ---------------------------------------------------------------- 两端的接线


def testTheServerBroadcastsWhenEveryAddonScriptHasLoaded():
    registry = fdtest.load("Server.EventRegistry")
    ready = fdtest.load("Server.ExtensionReady")
    assert (ready.__name__, "OnServerExtensionApiReady") in registry.handlerNames("LoadServerAddonScriptsAfter")
    tree = _tree("Server", "ModServer.py")
    forwarded = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and any(isinstance(deco, ast.Call) and getattr(deco.func, "id", None) == "Listen"
                                                     and _text(deco.args[0]) == "LoadServerAddonScriptsAfter" for deco in node.decorator_list):
            forwarded += [_text(call.args[0]) for call in ast.walk(node) if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "dispatch"]
    assert forwarded == ["LoadServerAddonScriptsAfter"], "ModServer 把这个事件原样转给 EventRegistry：%r" % forwarded
    assert re.search(r"^from \. import ExtensionReady\b", _read("Server", "ModServer.py"), re.M), "ModServer 导入它（导入即登记）"
    system = _FakeSystem()
    Ready.reset()
    ready._system = lambda: system
    ready._files = lambda directory: []      # 行为包里的配方 JSON：test_recipe_files 管
    registry.dispatch("LoadServerAddonScriptsAfter", {})
    registry.dispatch("LoadServerAddonScriptsAfter", {})
    assert [(event, payload["side"]) for event, payload in system.calls] == [("ServerExtensionApiReady", "server")]
    assert Ready.status("server") == Ready.SENT and Ready.status("client") is None


def testTheClientBroadcastsWhenEveryAddonScriptHasLoaded():
    listened = []
    stub = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Client")
    stub.Listen = lambda event: (lambda func: listened.append((event, func)) or func)
    importlib.import_module(fdtest.SCRIPTS + ".QuModLibs")
    sys.modules[stub.__name__] = stub
    ready = fdtest.load("Client.ExtensionReady")
    assert listened == [("LoadClientAddonScriptsAfter", ready.OnClientExtensionApiReady)], listened
    assert re.search(r"^from \. import ExtensionReady\b", _read("Client", "ModClient.py"), re.M), "ModClient 导入它（导入即登记）"
    system = _FakeSystem()
    Ready.reset()
    ready._system = lambda: system
    ready.OnClientExtensionApiReady({})
    ready.OnClientExtensionApiReady()
    assert [(event, payload["extension"]) for event, payload in system.calls] == [("ClientExtensionApiReady", Facade.getExtensionApi("client"))]


class _EngineSide(object):
    """serverApi / clientApi 的替身：系统基类、GetSystem、RegisterSystem（照引擎：按最后一个点拆开导入、构造类、记下来）。"""

    class BaseSystem(object):
        def __init__(self, namespace, systemName):
            self.key = (namespace, systemName)

    def __init__(self):
        self.systems = {}
        self.registered = []

    def GetServerSystemCls(self):
        return self.BaseSystem

    GetClientSystemCls = GetServerSystemCls

    def GetSystem(self, namespace, systemName):
        return self.systems.get((namespace, systemName))

    def RegisterSystem(self, namespace, systemName, classPath):
        moduleName, className = classPath.rsplit(".", 1)
        system = getattr(importlib.import_module(moduleName), className)(namespace, systemName)
        self.registered.append(classPath)
        self.systems[(namespace, systemName)] = system
        return system


def testTheBroadcastingSystemsUseThePublishedNamesAndAClassPathThatResolves():
    for side, engineModule, apiName, module in (("server", "Server.Helpers.Engine", "serverApi", "Server.ExtensionSystem"),
                                                ("client", "Client.Engine", "clientApi", "Client.ExtensionSystem")):
        engine = _EngineSide()
        stub = types.ModuleType(fdtest.SCRIPTS + "." + engineModule)
        setattr(stub, apiName, engine)
        sys.modules[stub.__name__] = stub
        systemModule = fdtest.load(module)
        system = systemModule.getSystem()
        assert isinstance(system, engine.BaseSystem) and system.key == ("arrisFarmersDelight", "ExtensionApi"), (side, system)
        assert engine.registered == [systemModule.__name__ + "." + ("ExtensionApiServerSystem" if side == "server" else "ExtensionApiClientSystem")]
        assert systemModule.getSystem() is system and len(engine.registered) == 1, "有了就用现成的"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
