# -*- coding: utf-8 -*-
# runner: both
"""行为包里的配方 JSON（Api/ExtensionApi/RecipeFiles.py、Server/Helpers/PackJson.py，接线在 Server/ExtensionReady.py）。

- 配方 ID："id" 优先；没写按路径 farmersdelight_recipes/<命名空间>/<其余>.json；直接放在这个目录下又没写 "id" 的不收（no_id）；
  引擎给的路径带不带 farmersdelight_recipes/ 这一层、用不用反斜杠都认；
- 一个文件一条，走 ext.recipes.registerFromJson：标签格的厨锅配方登记上、配得上别的模组的料；坏 JSON、没 ID、legacy:、格式不对的各记一条原因，
  不耽误别的；同一个 ID 两份时后读的覆盖先读的；
- PackJson：经 traceback.sys.modules 拿引擎内部的 server_resource（没有、缺函数、列目录抛异常都是 None）；只要 .json、去重、排好序、剥注释、
  解码 UTF-8，读不了的那个跳过；
- 接线：ready 广播之后读（ready 里登记的同 ID 配方被文件覆盖），读完调一次 onRecipesChanged 的处理函数（types、recipeIds 都是 None），
  每端只读一次；能力名 recipe_json_files（2026-11-26 游戏里核过才登记的：Events.RECIPE_JSON_FILES_VERIFIED）只在服务端。
"""
from __future__ import print_function

import json
import sys
import types

import fdtest

Events = fdtest.load("Api.ExtensionApi.Events")
Facade = fdtest.load("Api.ExtensionApi.Facade")
Files = fdtest.load("Api.ExtensionApi.RecipeFiles")
Ready = fdtest.load("Api.ExtensionApi.Ready")
Recipes = fdtest.load("Api.ExtensionApi.Recipes")
PackJson = fdtest.load("Server.Helpers.PackJson")
Pot = fdtest.load("Shared.Data.CookingPotRecipes")
CookingPot = fdtest.load("Shared.Rules.CookingPot")
ItemTags = fdtest.load("Shared.Rules.ItemTags")
SERVER = Facade.getExtensionApi("server")
MASH = {"type": "farmersdelight:cooking", "ingredients": [{"tag": "common:tomato"}, {"item": "minecraft:dirt"}],
        "result": {"item": "probe:tomato_mash"}, "container": {"item": "minecraft:bowl"}}

try:
    _UNICODE = unicode  # noqa: F821 - py2
except NameError:
    _UNICODE = str


class Port(object):
    """假的引擎口：别的模组把 probe:tomato 登记进了 common:tomato。"""

    def ready(self):
        return True

    def itemsOf(self, tag):
        return ["arris:tomato", "probe:tomato"] if tag == "common:tomato" else []

    def tagsOf(self, name, aux=0):
        return ["common:tomato"] if name == "probe:tomato" else []

    def blocksOf(self, tag):
        return []

    def blockTagsOf(self, name):
        return []


class Sandbox(object):
    """进去时记下厨锅配方表，装上假引擎口；出来时放回、清掉登记的处理函数和服务。"""

    def __enter__(self):
        self.rows = [(row, dict(row)) for row in Pot.CookingPotRecipeList]
        ItemTags.setPort("server", Port())
        return self

    def __exit__(self, *exc):
        ItemTags.setPort("server", None)
        Pot.CookingPotRecipeList[:] = [row for row, _ in self.rows]
        for row, fields in self.rows:
            row.clear()
            row.update(fields)
        CookingPot.rebuildIndex()
        Recipes._handlers[:] = []
        Recipes._services.clear()
        return False


class _Quiet(object):
    """临时收下打印的东西（py2 里统一成 utf-8 的 str）。"""

    def __init__(self):
        self.parts = []

    def write(self, text):
        self.parts.append(text.encode("utf-8") if str is bytes and isinstance(text, _UNICODE) else text)

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


def _mash():
    """锅里：别的模组的番茄（只靠假引擎口进 common:tomato）和一块泥土（农夫乐事没有哪道菜用它）。"""
    return [{"newItemName": "probe:tomato", "newAuxValue": 0, "count": 1}, {"newItemName": "minecraft:dirt", "newAuxValue": 0, "count": 1}]


def testTheIdComesFromTheFileOrFromItsPath():
    assert Files.idOf("farmersdelight_recipes/a.json", {"id": "probe:cooking/named"}) == "probe:cooking/named"
    assert isinstance(Files.idOf("x.json", {"id": u"probe:cooking/named"}), str), "py2 的 unicode 换成 str"
    for path, recipeId in (("farmersdelight_recipes/probe/cooking/tomato_mash.json", "probe:cooking/tomato_mash"),
                           ("farmersdelight_recipes\\probe\\cooking\\tomato_mash.json", "probe:cooking/tomato_mash"),
                           ("probe/cooking/tomato_mash.json", "probe:cooking/tomato_mash"),
                           (u"farmersdelight_recipes/probe/mash.json", "probe:mash")):
        assert Files.idOf(path, MASH) == recipeId and Files.idOf(path, [1]) == recipeId, path
    for path in ("farmersdelight_recipes/tomato_mash.json", "tomato_mash.json", "farmersdelight_recipes/probe/.json",
                 "farmersdelight_recipes/probe/readme.txt", "farmersdelight_recipes"):
        assert Files.idOf(path, MASH) is None, path


def testEachFileIsOneRecipeAndTheProblemsAreNamed():
    with Sandbox():
        late = dict(MASH, result={"item": "probe:tomato_mash", "count": 3})
        files = [("farmersdelight_recipes/probe/cooking/tomato_mash.json", json.dumps(MASH)),
                 ("farmersdelight_recipes/probe/cooking/broken.json", "{\"type\": "),
                 ("farmersdelight_recipes/orphan.json", json.dumps(MASH)),
                 ("farmersdelight_recipes/probe/cooking/old.json", json.dumps(dict(MASH, id="legacy:cooking/probe/x"))),
                 ("farmersdelight_recipes/probe/cooking/bad.json", json.dumps(dict(MASH, result=None))),
                 ("farmersdelight_recipes/probe/cooking/zz_again.json", json.dumps(dict(late, id="probe:cooking/tomato_mash")))]
        loaded, problems = Files.load(files, SERVER.recipes.registerFromJson)
        assert loaded == ["probe:cooking/tomato_mash", "probe:cooking/tomato_mash"], loaded
        reasons = dict(problems)
        assert sorted(reasons) == ["farmersdelight_recipes/orphan.json", "farmersdelight_recipes/probe/cooking/bad.json",
                                   "farmersdelight_recipes/probe/cooking/broken.json", "farmersdelight_recipes/probe/cooking/old.json"], problems
        assert reasons["farmersdelight_recipes/probe/cooking/broken.json"].startswith("invalid_json")
        assert reasons["farmersdelight_recipes/orphan.json"].startswith("no_id")
        assert reasons["farmersdelight_recipes/probe/cooking/old.json"] == "reserved_namespace"
        assert reasons["farmersdelight_recipes/probe/cooking/bad.json"].startswith("invalid_recipe message=") and "result" in reasons["farmersdelight_recipes/probe/cooking/bad.json"]
        rows = [row for row in Pot.CookingPotRecipeList if row.get("Id") == "probe:cooking/tomato_mash"]
        assert len(rows) == 1 and rows[0]["CookCount"] == 3, "同一个 ID 两份：后读的就地覆盖先读的"
        meal, _pushed = CookingPot.matchRecipe(_mash())
        assert meal["newItemName"] == "probe:tomato_mash" and meal["count"] == 3, "标签格收别的模组的番茄"
        assert SERVER.recipes.getRecipeById("probe:cooking/tomato_mash")["result"] == {"item": "probe:tomato_mash", "count": 3}


def testBrokenJsonNeverRaisesAndOneBadFileDoesNotStopTheRest():
    """T 复核时复现的：type / tool 的 action、tag 写成列表或字典，数写 NaN / Infinity，Builder 的 tool 给字典——都答"格式不对"，不抛；
    读文件时一个文件出什么错都只记下它，后面的照读。"""
    cut = {"type": "farmersdelight:cutting", "ingredients": [{"item": "a:b"}], "result": [{"item": "a:c"}]}
    broken = [dict(MASH, type=["farmersdelight:cooking"]), dict(MASH, type={"x": 1}), dict(MASH, cookingtime=float("nan")),
              dict(MASH, cookingtime=float("inf")), dict(MASH, experience=float("nan")), dict(MASH, result={"item": "a:b", "count": float("inf")}),
              dict(cut, tool={"type": "farmersdelight:tool_action", "action": ["knife_dig"]}), dict(cut, tool={"tag": {"x": 1}}),
              dict(cut, tool={"type": "farmersdelight:tool_action", "action": "knife_dig"}, result=[{"item": "a:c", "chance": float("nan")}])]
    for data in broken:
        answer = SERVER.recipes.registerFromJson(data, "probe:cooking/broken")
        assert answer["error"] == "invalid_recipe" and answer["message"], (data, answer)
    assert SERVER.recipes.createBuilder("probe:cutting/odd", "cutting").ingredient("a:b").output("a:c").tool({"x": 1}).register()["error"] \
        == "invalid_recipe", "Builder 的 tool 给字典也不抛"
    with Sandbox():
        files = [("farmersdelight_recipes/probe/a.json", json.dumps(dict(MASH, cookingtime=float("nan")))),
                 ("farmersdelight_recipes/probe/b.json", json.dumps(dict(MASH, type=[1]))),
                 ("farmersdelight_recipes/probe/cooking/tomato_mash.json", json.dumps(MASH))]
        loaded, problems = Files.load(files, SERVER.recipes.registerFromJson)
        assert loaded == ["probe:cooking/tomato_mash"] and [path for path, _reason in problems] == [path for path, _text in files[:2]], problems

        def raising(data, recipeId):
            raise RuntimeError("their bug")

        loaded, problems = Files.load(files[2:], raising)
        assert loaded == [] and problems[0][1].startswith("invalid_recipe"), problems


class _Resource(object):
    """server_resource 的替身：列目录给的路径、读文件给的字节；raises 里的路径读的时候抛异常。"""

    def __init__(self, listed, contents, raises=()):
        self.listed, self.contents, self.raises = listed, contents, raises
        self.asked = []

    def list_server_directory(self, path):
        self.asked.append(path)
        if isinstance(self.listed, Exception):
            raise self.listed
        return self.listed

    def load_server_file(self, path):
        if path in self.raises:
            raise IOError("cannot read " + path)
        return self.contents[path]


def _withResource(resource, call):
    saved = sys.modules.get("server_resource")
    if resource is None:
        sys.modules.pop("server_resource", None)
    else:
        sys.modules["server_resource"] = resource
    try:
        with _Quiet() as out:
            return call(), out.text()
    finally:
        if saved is None:
            sys.modules.pop("server_resource", None)
        else:
            sys.modules["server_resource"] = saved


def testPackJsonReadsEveryPackThroughTheEnginesInternalModule():
    commented = u'{\n  // 番茄泥\n  "type": "farmersdelight:cooking", /* 两格\n */ "text": "a//b /* c */"\n}'
    resource = _Resource(["farmersdelight_recipes/b.json", "farmersdelight_recipes/a.json", "farmersdelight_recipes/readme.txt",
                          "farmersdelight_recipes/a.json", "farmersdelight_recipes/gone.json", None],
                         {"farmersdelight_recipes/a.json": commented.encode("utf-8"), "farmersdelight_recipes/b.json": b'{"x": 1}'},
                         raises=("farmersdelight_recipes/gone.json",))
    found, printed = _withResource(resource, lambda: PackJson.files("farmersdelight_recipes"))
    assert [path for path, _text in found] == ["farmersdelight_recipes/a.json", "farmersdelight_recipes/b.json"], found
    assert json.loads(found[0][1]) == {"type": "farmersdelight:cooking", "text": "a//b /* c */"}, "注释剥掉，字符串里的不动"
    assert found[0][1].count("\n") == commented.count("\n"), "块注释里的换行留着（报错的行号对得上）"
    assert resource.asked == ["farmersdelight_recipes"] and "gone.json" in printed, "读不了的那个跳过、记一行"
    assert _withResource(None, lambda: PackJson.files("farmersdelight_recipes"))[0] is None, "没有这个模块"
    assert _withResource(types.ModuleType("server_resource"), lambda: PackJson.files("farmersdelight_recipes"))[0] is None, "缺函数"
    gone, printed = _withResource(_Resource(OSError("no such directory"), {}), lambda: PackJson.files("farmersdelight_recipes"))
    assert gone is None and "farmersdelight_recipes/" in printed, "列目录抛异常：当这条路不通，记一行"
    assert _withResource(_Resource(None, {}), lambda: PackJson.files("farmersdelight_recipes"))[0] == [], "目录在哪个包里都没有"


class _Broadcaster(object):
    """广播用系统的替身：BroadcastEvent 时把载荷交给 onReady（替别的模组的 ready 处理函数），记下先后。"""

    def __init__(self, onReady, log):
        self.onReady, self.log = onReady, log

    def BroadcastEvent(self, eventName, payload):
        self.log.append("ready")
        self.onReady(payload["extension"])


def testTheFilesAreReadAfterTheReadyBroadcastAndThenTheHandlersAreToldOnce():
    registry = fdtest.load("Server.EventRegistry")
    ready = fdtest.load("Server.ExtensionReady")
    with Sandbox():
        log, events = [], []

        def theirReady(ext):
            ext.recipes.onRecipesChanged(lambda event: events.append((event.types, event.recipeIds)))
            assert ext.recipes.registerFromJson(dict(MASH, result={"item": "probe:early_mash"}), "probe:cooking/tomato_mash")["ok"]

        def files(directory):
            log.append("files:" + directory)
            return [("farmersdelight_recipes/probe/cooking/tomato_mash.json", json.dumps(MASH)),
                    ("farmersdelight_recipes/orphan.json", json.dumps(MASH))]

        system = _Broadcaster(theirReady, log)
        saved = (ready._system, ready._files)
        Ready.reset()
        ready._system, ready._files = (lambda: system), files
        try:
            with _Quiet() as out:
                registry.dispatch("LoadServerAddonScriptsAfter", {})
                registry.dispatch("LoadServerAddonScriptsAfter", {})
            assert log == ["ready", "files:farmersdelight_recipes"], "先广播 ready，再读文件，每端一次：%r" % log
            assert events == [(None, None)], "读完调一次处理函数：%r" % events
            assert CookingPot.matchRecipe(_mash())[0]["newItemName"] == "probe:tomato_mash", "ready 里登记的同 ID 配方被文件覆盖"
            report = ready.scanReport()
            assert report["state"] == "read" and report["files"] == 2 and report["loaded"] == ["probe:cooking/tomato_mash"]
            assert [path for path, _reason in report["problems"]] == ["farmersdelight_recipes/orphan.json"] and "orphan.json" in out.text()
            Ready.reset()
            system.onReady = lambda ext: None
            ready._files = lambda directory: None
            with _Quiet() as out:
                registry.dispatch("LoadServerAddonScriptsAfter", {})
            assert ready.scanReport()["state"] == "unavailable" and "farmersdelight_recipes/" in out.text(), "引擎没有这条路：记一行，照常往下走"
            assert events == [(None, None), (None, None)], events
        finally:
            ready._system, ready._files = saved
            Ready.reset()


def testTheCapabilityIsRegisteredOnTheServerOnly():
    """2026-11-26 游戏里核过（另一个行为包里的文件读到了），能力名登记上；只在服务端（文件只有服务端读）。"""
    assert Events.RECIPE_JSON_FILES_VERIFIED is True
    assert "recipe_json_files" in Events.SERVER_CAPABILITIES and "recipe_json_files" not in Events.CLIENT_CAPABILITIES
    assert SERVER.hasCapability("recipe_json_files") and not Facade.getExtensionApi("client").hasCapability("recipe_json_files")


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
