# -*- coding: utf-8 -*-
# runner: both
"""取别的模组的模块：联动入口那几处（Compat/OtherMods 接住引擎 ImportModule 原样抛出来的异常）。每一处用假的 ImportModule 的五种回答
（抛 ImportError、抛别的异常、返回 None、对方装着却没有这个模块、返回正常的模块）：异常不漏出来、当它没装，出错的日志只打一次、
没有这个模块不打日志；正常的模块照旧接上。
- 成就系统（Compat/Advancements/AdvBoot）：它的 ExtensionApi 系统已经在（已经广播过）时，导入 AdvBoot 就晚接一次——这个入口的导入不能失败；
  接不上的时候 ready 事件那条路照样能用。
- 机械动力的土豆加农炮（Compat/Create/PotatoCannonAmmo；两端的入口 PotatoCannonServer / PotatoCannonClient 导入时就调 hook）：取模块、
  取门面（getExtensionApi 到这时才导入它自己的门面模块）、登记，哪一步是机械动力出错都不漏出入口；单机时两端取同一个模块，日志只打一次。
- 机械动力的配方（Compat/Create/CreateRecipes）：LoadServerAddonScriptsAfter 里取 RecipeApi，事件来两次也只打一次日志、只登记一次。
- arrisJei（Compat/Jei/Registry.GetJeiApiModule）：界面初始化完成（UiInitFinished，JeiClient）时四类配方各取一次，坏的只打一次日志。
引擎、QuModLibs、两端的 Engine 都是这里的假模块（只有用到的几个名字）。
"""
from __future__ import print_function

import sys
import types

import fdtest
import otherkit
from otherkit import Captured, Importer

PACKAGE = fdtest.SCRIPTS


class EngineApi(object):
    """serverApi / clientApi 的替身：GetSystem 对 systems 里的 (命名空间, 系统名) 回答真值，ImportModule 交给 importer。"""

    def __init__(self):
        self.systems = set()
        self.importer = Importer()

    def GetSystem(self, namespace, name):
        return object() if (namespace, name) in self.systems else None

    def ImportModule(self, path):
        return self.importer(path)


class LoaderSystem(object):
    """本包加载器系统的替身：记下挂在它上面的监听 (命名空间, 系统名, 事件名, 方法)。"""

    def __init__(self):
        self.listened = []

    def ListenForEvent(self, namespace, systemName, event, target, method):
        self.listened.append((namespace, systemName, event, method))

    def handler(self, event):
        return [method for _ns, _name, name, method in self.listened if name == event][-1]


serverApi, clientApi = EngineApi(), EngineApi()
systems = {"server": LoaderSystem(), "client": LoaderSystem()}
listened = []          # [(事件名, 函数)]：@Listen 和 ListenForEvent 挂的


def _listen(event):
    def decorate(func):
        listened.append((event, func))
        return func
    return decorate


def _module(name, **names):
    module = types.ModuleType(PACKAGE + "." + name)
    module.__dict__.update(names)
    sys.modules[module.__name__] = module
    return module


def _loader(side):
    return type("LoaderSystem", (object,), {"getSystem": staticmethod(lambda: systems[side])})


_module("QuModLibs.Server", serverApi=serverApi, Listen=_listen, ListenForEvent=lambda event, parent, func: listened.append((event, func)))
_module("QuModLibs.Client", clientApi=clientApi, Listen=_listen)
_module("QuModLibs.Systems.Loader.Server", LoaderSystem=_loader("server"))
_module("QuModLibs.Systems.Loader.Client", LoaderSystem=_loader("client"))
_module("Server.Helpers.Engine", serverApi=serverApi, compFactory=None, levelId="level", ItemPosType=None,
        GetEngineTypeStr=lambda entityId: None)
_module("Client.Engine", clientApi=clientApi, compFactory=None, levelId="level")

Bridge = fdtest.load("Compat.Advancements.AdvBridge")
Ammo = fdtest.load("Compat.Create.PotatoCannonAmmo")
Recipes = fdtest.load("Compat.Create.CreateRecipes")
Registry = fdtest.load("Compat.Jei.Registry")
JeiClient = fdtest.load("Compat.Jei.JeiClient")
ADV_BOOT = PACKAGE + ".Compat.Advancements.AdvBoot"
ADV_API = "dolorAdvancementsScripts.Api.Server"
ADV_SYSTEM = ("dolorAdvancements", "ExtensionApi")
CREATE_SYSTEM = (Ammo.NAMESPACE, Ammo.SYSTEM_NAME)
CANNON_ENTRY = {"server": "Compat.Create.PotatoCannonServer", "client": "Compat.Create.PotatoCannonClient"}
API_OF = {"server": serverApi, "client": clientApi}


def _reimport(relative):
    """入口模块重新导入一遍（它导入时就去取别的模组的模块）：导入失败（异常漏出来）测试就失败。"""
    sys.modules.pop(PACKAGE + "." + relative, None)
    return fdtest.load(relative)


# ---------------------------------------------------------------- 成就系统

class AdvApi(object):
    """成就系统接口模块的替身：AdvBridge 要的几个函数。"""

    def __init__(self):
        self.nodes, self.ready = None, []

    def registerAdvancements(self, nodes):
        self.nodes = nodes
        return len(nodes)

    def listenOnPlayerReady(self, func):
        self.ready.append(func)

    def setFinish(self, playerId, nodeId):
        return True

    def addProgressUnique(self, playerId, nodeId, subKey):
        return True

    def isDone(self, playerId, nodeId):
        return False


def bootAdvancements(answer, ready=True):
    """AdvBoot 重新导入一次：成就系统的 ExtensionApi 系统在不在（ready），它的接口模块怎么回答（answer）。返回 (模块, 打印的)。
    加载器系统每次换一个新的：ready 的监听只在系统上挂一次，挂在旧系统上的是上一次导入的 AdvBoot 的函数——py2 回收了被换掉的模块对象，
    它的全局变量都成了 None，再调就是 TypeError。"""
    otherkit.fresh()
    systems["server"] = LoaderSystem()
    Bridge._state.update(api=None, env=None)
    serverApi.systems = {ADV_SYSTEM} if ready else set()
    serverApi.importer = Importer({ADV_API: answer})
    with Captured() as out:
        module = _reimport("Compat.Advancements.AdvBoot")
    return module, out


def testAdvBootImportsWhateverTheAdvancementsApiAnswersAndOnlyAGoodOneIsAttached():
    for name, answer, absent, loud in otherkit.kinds(AdvApi(), ADV_API):
        module, out = bootAdvancements(answer)
        assert serverApi.importer.asked == [ADV_API], name
        assert Bridge.api() is (None if absent else answer), name
        raised = 1 if loud else 0
        assert out.logged(ADV_API) == raised and out.tracebacks() == raised, (name, out.text)
        with Captured() as again:
            module.hook(systems["server"])          # 再晚接一次（热重载以后）：再出错也不再打一大段
        assert again.tracebacks() == 0 and again.logged(ADV_API) == 0, (name, again.text)
        assert Bridge.api() is (None if absent else answer), name


def testWithoutTheAdvancementsSystemNothingIsAskedAndTheReadyEventStillAttaches():
    module, out = bootAdvancements(ImportError("No module named broken_dependency"), ready=False)
    assert serverApi.importer.asked == [] and Bridge.api() is None, "成就系统没广播过：不去取它的接口"
    module, out = bootAdvancements(ImportError("No module named broken_dependency"))
    assert Bridge.api() is None and out.tracebacks() == 1
    api = AdvApi()
    with Captured():
        systems["server"].handler("ServerApiReady")({"api": api})
    assert Bridge.api() is api, "晚接没接上，之后的 ready 事件照样接得上（AdvBoot 导入成了，监听还在）"


# ---------------------------------------------------------------- 机械动力的土豆加农炮

class Cannon(object):
    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def registerAmmoType(self, typeId, fields):
        if self.fail:
            raise RuntimeError("registerAmmoType blew up")
        self.calls.append(typeId)
        return {"ok": True, "error": None}


class Facade(object):
    def __init__(self, fail=False):
        self.potatoCannon = Cannon(fail)

    def hasCapability(self, name):
        return name == Ammo.CAPABILITY


def facadeModule(facade=None, error=None):
    """机械动力 ExtensionApi 模块的替身：getExtensionApi(side) 给 facade；给了 error 就抛它（它取门面时才导入的门面模块出错）。"""
    def getExtensionApi(side):
        if error is not None:
            raise error
        return facade
    return types.ModuleType("arrisCreateScripts.Api.ExtensionApi"), getExtensionApi


def bootCannon(side, answer, fresh=True):
    """那一端的入口重新导入一次（导入时就 hook），机械动力已经广播过（它的 ExtensionApi 系统在）。返回打印的。"""
    if fresh:
        otherkit.fresh()
    Ammo._attached.clear()
    API_OF[side].systems = {CREATE_SYSTEM}
    API_OF[side].importer = Importer({Ammo.FACADE_MODULE: answer})
    with Captured() as out:
        _reimport(CANNON_ENTRY[side])
    return out


def _cannonModule(facade=None, error=None):
    module, getter = facadeModule(facade, error)
    module.getExtensionApi = getter
    return module


def testBothCannonEntriesImportWhateverCreatesFacadeModuleAnswers():
    for side in ("server", "client"):
        facade = Facade()
        for name, answer, absent, loud in otherkit.kinds(_cannonModule(facade), Ammo.FACADE_MODULE):
            out = bootCannon(side, answer)
            assert API_OF[side].importer.asked == [Ammo.FACADE_MODULE], (side, name)
            assert bool(Ammo._attached.get(side)) is (not absent), (side, name)
            raised = 1 if loud else 0
            assert out.logged(Ammo.FACADE_MODULE) == raised and out.tracebacks() == raised, (side, name, out.text)
        assert len(facade.potatoCannon.calls) == 7, "正常的门面：七种弹药照旧登记"


def testInSinglePlayerTheSecondSideDoesNotLogTheSameBrokenModuleAgain():
    broken = ImportError("No module named broken_dependency")
    first = bootCannon("server", broken)
    second = bootCannon("client", broken, fresh=False)
    assert first.tracebacks() == 1 and second.tracebacks() == 0 and second.logged(Ammo.FACADE_MODULE) == 0
    assert clientApi.importer.asked == [Ammo.FACADE_MODULE], "照样去取了"


def testABrokenFacadeOrABrokenRegistrationDoesNotLeakOutOfTheEntry():
    module = _cannonModule(error=ImportError("No module named _facade"))
    label = "%s.%s" % (module.getExtensionApi.__module__, module.getExtensionApi.__name__)
    out = bootCannon("server", module)
    assert not Ammo._attached and out.logged(label) == 1 and out.tracebacks() == 1, out.text
    out = bootCannon("client", _cannonModule(Facade(fail=True)))
    assert not Ammo._attached and out.tracebacks() == 1, "登记时机械动力抛异常：打日志、当没接上"
    facade = Facade()
    with Captured():
        assert Ammo.attach("client", facade) is True and len(facade.potatoCannon.calls) == 7, "之后照样接得上"


# ---------------------------------------------------------------- 机械动力的配方（LoadServerAddonScriptsAfter 里取 RecipeApi）

class Builder(object):
    """机械动力 RecipeApi.createBuilder 给的东西的替身：链式调用都收下，register 记下配方 id。"""

    def __init__(self, registered, recipeId):
        self.registered, self.recipeId = registered, recipeId

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: self

    def register(self):
        self.registered.append(self.recipeId)


class RecipeApi(object):
    def __init__(self):
        self.registered = []

    def createBuilder(self, recipeId, kind):
        return Builder(self.registered, recipeId)


def testCreateRecipesAreRegisteredOnlyWithAGoodRecipeApiAndTheEventNeverRaises():
    (onLoaded,) = [func for event, func in listened if event == "LoadServerAddonScriptsAfter" and func.__module__ == Recipes.__name__]
    good = RecipeApi()
    for name, answer, absent, loud in otherkit.kinds(good, Recipes.RECIPE_API):
        otherkit.fresh()
        Recipes._REGISTERED = False
        serverApi.importer = Importer({Recipes.RECIPE_API: answer})
        with Captured() as out:
            onLoaded({})
            onLoaded({})                                   # 事件再来一次（热重载以后）
        assert Recipes._REGISTERED is (not absent), name
        assert serverApi.importer.asked == [Recipes.RECIPE_API] * (2 if absent else 1), (name, serverApi.importer.asked)
        raised = 1 if loud else 0
        assert out.logged(Recipes.RECIPE_API) == raised and out.tracebacks() == raised, (name, out.text)
    assert len(good.registered) == 12, "石磨 8 + 搅拌 3 + 灌注 1，只登记一次"


# ---------------------------------------------------------------- arrisJei（界面初始化完成时每类配方各取一次）

def testEveryJeiCategoryTakesArrisJeiThroughOtherModsAndABrokenOneIsLoggedOnce():
    registry = object()
    good = types.ModuleType(Registry.JEI_MODULE)
    good.JeiRecipeRegistry = type("JeiRecipeRegistry", (object,), {"getInstance": staticmethod(lambda: registry)})
    for name, answer, absent, loud in otherkit.kinds(good, Registry.JEI_MODULE):
        otherkit.fresh()
        clientApi.importer = Importer({Registry.JEI_MODULE: answer})
        with Captured() as out:
            assert Registry.GetJeiApiModule() is (None if absent else registry), name
        raised = 1 if loud else 0
        assert out.logged(Registry.JEI_MODULE) == raised and out.tracebacks() == raised, (name, out.text)
    (onUiInit,) = [func for event, func in listened if event == "UiInitFinished" and func.__module__ == JeiClient.__name__]
    otherkit.fresh()
    clientApi.importer = Importer({Registry.JEI_MODULE: ImportError("No module named broken_dependency")})
    with Captured() as out:
        onUiInit({})
    assert clientApi.importer.asked == [Registry.JEI_MODULE] * 4, "四类配方各取一次（砧板摆盘要联动了才登记）"
    assert out.logged(Registry.JEI_MODULE) == 1 and out.tracebacks() == 1, out.text


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
