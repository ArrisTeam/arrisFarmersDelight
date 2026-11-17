# -*- coding: utf-8 -*-
"""linkkit - 联动（Shared/Rules/HandsOnMode、Compat/Diegesis 的 Presence 和两个入口）离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

只用本仓库的东西：旁边没有场景交互前置包也能跑，所以这里不导入 dg* 小工具、也不 import prereq。
- link() / unlink() / Modes：把两端的联动状态拨成已联动 / 还没判定 / 指定的模式。要站点和 HoD 的配置照常生效的测试在导入小工具时 link() 一次
  （optkit、potfake、boardkit、panfake、stovekit、bootkit 都这样）；没联动时 HandsOnOptions 说 HoD 不在。
- Loose / loosen：缺的名字补一个无害替身的模块，把引擎入口换成"什么名字都能 from import"的模块。
- install() -> Env：两端入口要的 QuModLibs（Server / Client）和 Engine 换成记账的假模块，前置包的接口由 env.apis 说了算；
  env.boot(side) 把那一端的入口（ServerBoot / ClientBoot）重新导入一遍，env.fire(side) 发那一端"全部 Addon 脚本加载完成"的事件；
  env.stubRegisters(side, calls, off) 在步骤模块被步骤表导入之后、它的函数被调之前，把那个站点的 register 换成记账的
  （真的 register 要前置包的接口类，这里没有它），所以"没联动时站点模块没被导入"和"联动时是步骤导入了它们"都看得出来。
"""
from __future__ import print_function

import importlib
import sys
import types

import fdtest

PACKAGE = fdtest.SCRIPTS
DIEGESIS = PACKAGE + ".Compat.Diegesis"
ENTRY = ("ServerBoot", "ClientBoot", "Presence", "Steps", "ServerSteps", "ClientSteps")      # 没联动时也会导入的：入口、判定、步骤表
Mode = fdtest.load("Shared.Rules.HandsOnMode")


# ---------------------------------------------------------------- 联动状态

def link():
    """两端都当已联动（只拨状态，不跑步骤）。"""
    for side in Mode.SIDES:
        Mode.decide(side, Mode.LINKED)


def unlink(side=None):
    """回到还没判定（不给 side 是两端），登记过的回调也清掉。"""
    for each in ((side,) if side else Mode.SIDES):
        Mode._modes[each] = Mode.PENDING
        del Mode._callbacks[each][:]


class Modes(object):
    """with Modes(Mode.OUTDATED): ……  进去时两端都拨成这个模式（Modes(server=…, client=…) 各自给，没给的是还没判定），出来时放回原样。"""

    def __init__(self, both=None, server=None, client=None):
        self.wanted = {"server": server or both or Mode.PENDING, "client": client or both or Mode.PENDING}
        self.before = None

    def __enter__(self):
        self.before = dict(Mode._modes)
        Mode._modes.update(self.wanted)
        return self

    def __exit__(self, *exc):
        Mode._modes.update(self.before)
        return False


# ---------------------------------------------------------------- 无害的替身

class _Stub(object):
    """没有预设的名字：能调、能取属性、能迭代，什么也不做。"""

    def __init__(self, name):
        self._name = name

    def __call__(self, *args, **kwargs):
        return _Stub(self._name + "()")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Stub(self._name + "." + name)

    def __iter__(self):
        return iter(())


class Loose(types.ModuleType):
    """缺的名字补一个 _Stub（from X import 名字 就能导入）。"""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = _Stub(name)
        setattr(self, name, value)
        return value


def loosen(name):
    """sys.modules 里已有的模块换成同内容的 Loose。"""
    module = sys.modules[name]
    loose = Loose(name)
    loose.__dict__.update(module.__dict__)
    sys.modules[name] = loose
    return loose


# ---------------------------------------------------------------- 两端入口的假环境

def purge():
    """Compat/Diegesis 里的模块（包本身除外）清掉：之后再导入的才是新的，之前导入过的不算数。
    包对象上的同名属性也要删：from . import X 先看包有没有 X 这个属性，不删就拿到清掉之前的那个旧模块。"""
    package = sys.modules.get(DIEGESIS)
    for name in [name for name in sys.modules if name.startswith(DIEGESIS + ".")]:
        del sys.modules[name]
        if package is not None and hasattr(package, name[len(DIEGESIS) + 1:]):
            delattr(package, name[len(DIEGESIS) + 1:])


def names():
    """现在导入着的 Compat/Diegesis 模块（不带包名前缀）。py2 的 import traceback 会先试一次相对导入、在 sys.modules 里记一个 None：不算。"""
    return sorted(name[len(DIEGESIS) + 1:] for name, module in sys.modules.items() if name.startswith(DIEGESIS + ".") and module is not None)


class _Api(object):
    """serverApi / clientApi 的替身：ImportModule 照 env.apis 回答（没有是 None），记下被问过什么。"""

    def __init__(self, env, side):
        self.env, self.side = env, side

    def ImportModule(self, name):
        self.env.asked[self.side].append(name)
        api = self.env.apis[self.side]
        if isinstance(api, Exception):
            raise api
        return api


class _Notify(object):
    def __init__(self, env):
        self.env = env

    def SetLeftCornerNotify(self, text):
        self.env.notices.append(text)
        return True


class _Game(object):
    def __init__(self, env):
        self.env = env

    def AddTimer(self, seconds, func, *args):
        self.env.timers.append((seconds, func, args))


class _Factory(object):
    def __init__(self, env):
        self.env = env

    def CreateTextNotifyClient(self, levelId):
        return _Notify(self.env)

    def CreateGame(self, levelId):
        return _Game(self.env)


class Env(object):
    """两端入口的假环境（用 install() 装）。字段：apis（前置包接口模块的回答，没装是 None，给异常对象就抛它）、asked、
    listened（[(事件名, 函数)]：@Listen 挂的）、endpoints（[(模块名, 函数名)]：@AllowCall 登记的）、notices、timers。"""

    def __init__(self):
        self.apis = {}
        self.asked = {}
        self.listened = {}
        self.endpoints = {}
        self.notices = []
        self.timers = []
        self.afterLoad = {}
        self.reset()
        for side, quMod, engine in (("server", "QuModLibs.Server", "Server.Helpers.Engine"), ("client", "QuModLibs.Client", "Client.Engine")):
            module = Loose(PACKAGE + "." + quMod)
            module.Listen = self._listen(side)
            module.AllowCall = self._endpoint(side)
            module.InjectHttpPlayerId = lambda func: func
            module.ImportModule = self._load
            setattr(module, side + "Api", _Api(self, side))
            sys.modules[PACKAGE + "." + quMod] = module
            sys.modules[PACKAGE + "." + engine] = Loose(PACKAGE + "." + engine)
        engine = sys.modules[PACKAGE + ".Client.Engine"]
        engine.compFactory, engine.levelId, engine.playerId = _Factory(self), "level", "player"

    def reset(self):
        """每个用例开头：记账清零、前置包都当没装、联动状态回到还没判定、Compat/Diegesis 的模块清掉。"""
        for side in Mode.SIDES:
            self.apis[side], self.asked[side], self.listened[side], self.endpoints[side] = None, [], [], []
        del self.notices[:]
        del self.timers[:]
        self.afterLoad = {}
        unlink()
        purge()

    def _listen(self, side):
        def listen(event):
            def decorate(func):
                self.listened[side].append((event, func))
                return func
            return decorate
        return listen

    def _endpoint(self, side):
        def allow(func):
            self.endpoints[side].append((func.__module__, func.__name__))
            return func
        return allow

    def _load(self, path):
        """QuModLibs 的 ImportModule 的替身：真的导入，导进来之后照 afterLoad 打补丁。"""
        module = importlib.import_module(path)
        for patch in self.afterLoad.get(path, ()):
            patch(module)
        return module

    def stubRegisters(self, side, calls, off=()):
        """那一端四个步骤模块被导入之后，它们用的站点模块里的 register 换成记账的（calls 里记 (站点, api)；
        登记上了返回一个类，off 里的站点返回 None，像 HoD 的配置里关了它）。"""
        for station, link, stationModule in LINKS[side]:
            def register(api, station=station):
                calls.append((station, api))
                return None if station in off else type(station.title() + "Station", (object,), {})
            self.afterLoad.setdefault(PACKAGE + ".Compat.Diegesis." + link, []).append(
                lambda module, register=register, stationModule=stationModule: setattr(getattr(module, stationModule), "register", register))

    def boot(self, side, clean=True):
        """那一端的入口重新导入一遍（它导入时就挂 Presence）。clean 为真先把 Compat/Diegesis 里的模块清掉：之前导入过的不算数。"""
        if clean:
            purge()
        return importlib.import_module(DIEGESIS + (".ServerBoot" if side == "server" else ".ClientBoot"))

    def fire(self, side):
        """发那一端的"全部 Addon 脚本加载完成"事件：挂在它上面的函数都调一遍（原样用事件名找，所以事件名写错了这里也找不到）。"""
        event = "LoadServerAddonScriptsAfter" if side == "server" else "LoadClientAddonScriptsAfter"
        for name, func in list(self.listened[side]):
            if name == event:
                func({})

    def fromPackage(self, side):
        """挂了监听的函数里属于 Compat/Diegesis 的：[(模块名去掉包前缀, 事件名)]。"""
        return sorted((func.__module__[len(DIEGESIS) + 1:], event) for event, func in self.listened[side] if func.__module__.startswith(DIEGESIS + "."))


LINKS = {"server": (("board", "BoardServerLink", "BoardLogic"), ("pot", "PotServerLink", "PotLogic"),
                    ("pan", "PanServerLink", "PanLogic"), ("grill", "GrillServerLink", "GrillLogic")),
         "client": (("board", "BoardClientLink", "BoardView"), ("pot", "PotClientLink", "PotView"),
                    ("pan", "PanClientLink", "PanView"), ("grill", "GrillClientLink", "GrillView"))}
_env = []


def install():
    """装一次假环境（要在导入 Compat/Diegesis 里的任何模块之前调；同一个进程里再调返回同一个）。"""
    if not _env:
        _env.append(Env())
    return _env[0]
