# -*- coding: utf-8 -*-
# runner: both
"""原版猫 / 鸡 / 猪 / 兔子 / 鹦鹉 / 狼认农夫乐事的食物：运行时读生效的实体定义、追加条目、按现在的组件组 AddActorComponent
（规则 Shared/Rules/AnimalFood.py，数据 Shared/Data/Mobs.ANIMAL_FOOD，服务端 Server/AnimalFood.py）。

- 规则：定义里凡是带这个组件的地方都追加、重复的不加、看不懂的不下发；会换这些组件组的事件（连 trigger 转过去的）；
  定义栈怎么折成"现在每个组件由谁提供"（照引擎：后加的盖掉、减组拿掉组里有的，连顶层同名的一起）。
- 本机原版行为包（找不到游戏目录时跳过）：算出来的每一处 = 原版那一处 + 本包的条目接在后面，别的字段一个不动；
  2026-11-26 删掉六份整文件覆盖之前，拿那六份当参照逐处核过（18 处一样；兔子的吸引和原来 Mobs 里写死的 JSON 一样）。
- 别的包改过的定义：在改过的那份上追加，不换回原版。
- 服务端：只认这六种、晚一拍下发、换组事件按定义里的名字认、读不到定义记一次日志不再试、定义栈读不懂只给顶层的。
"""
from __future__ import print_function

import io
import json
import os
import sys
import types

import fakeengine
import fdtest

world = fakeengine.install()
Rules = fdtest.load("Shared.Rules.AnimalFood")
Mobs = fdtest.load("Shared.Data.Mobs")
PackJson = fdtest.load("Server.Helpers.PackJson")
Registry = fdtest.load("Server.EventRegistry")
AnimalFood = fdtest.load("Server.AnimalFood")

CHICKEN = {"minecraft:entity": {
    "description": {"identifier": "minecraft:chicken"},
    "components": {"minecraft:behavior.tempt": {"priority": 4, "items": ["wheat_seeds"]}},
    "component_groups": {
        "minecraft:chicken_baby": {"minecraft:is_baby": {}, "minecraft:ageable": {"duration": 1200, "feed_items": ["wheat_seeds"]}},
        "minecraft:chicken_adult": {"minecraft:breedable": {"require_tame": False, "breed_items": ["wheat_seeds"]}}},
    "events": {
        "minecraft:entity_born": {"add": {"component_groups": ["minecraft:chicken_baby"]}},
        "minecraft:ageable_grow_up": {"remove": {"component_groups": ["minecraft:chicken_baby"]},
                                      "add": {"component_groups": ["minecraft:chicken_adult"]}},
        "minecraft:entity_spawned": {"sequence": [{"randomize": [{"trigger": "minecraft:spawn_adult"}, {"trigger": "minecraft:entity_born"}]}]},
        "minecraft:spawn_adult": {"add": {"component_groups": ["minecraft:chicken_adult"]}},
        "minecraft:sounds": {"add": {"component_groups": ["minecraft:chicken_noise"]}},
        "minecraft:other": {"trigger": {"event": "minecraft:entity_born", "target": "baby"}}}}}
SEEDS = Mobs.CHICKEN_FOOD


def _plan(definition=CHICKEN, entityType="minecraft:chicken"):
    return Rules.plan(definition, Mobs.ANIMAL_FOOD[entityType])


def _sent(plan, stack):
    return dict((name, json.loads(text)) for name, text in Rules.send(plan, stack))


# ---- 规则 ----

def testParseAcceptsTheEnginesTrailingCommasAndChecksTheIdentifier():
    text = '{"minecraft:entity": {"description": {"identifier": "minecraft:chicken",}, "components": {"a": [1, 2,],},},}'
    assert Rules.parse(text, "minecraft:chicken")["minecraft:entity"]["components"] == {"a": [1, 2]}
    quoted = '{"minecraft:entity": {"description": {"identifier": "minecraft:chicken"}, "n": "a,}",},}'
    assert Rules.parse(quoted, "minecraft:chicken")["minecraft:entity"]["n"] == "a,}"     # 字符串里的 ",}" 不动
    assert Rules.parse(text, "minecraft:pig") is None
    assert Rules.parse("not json", "minecraft:chicken") is None and Rules.parse(None, "minecraft:chicken") is None
    assert Rules.definitionPath("minecraft:chicken") == "entities/chicken.json"


def testEveryPlaceThatHasTheComponentGetsOurItemsAtTheEndOnce():
    plan = _plan()
    assert sorted(plan.jsons) == [("minecraft:ageable", "minecraft:chicken_baby"), ("minecraft:behavior.tempt", Rules.BASE),
                                  ("minecraft:breedable", "minecraft:chicken_adult")]
    assert json.loads(plan.jsons[("minecraft:behavior.tempt", Rules.BASE)]) == {"priority": 4, "items": ["wheat_seeds"] + list(SEEDS)}
    assert json.loads(plan.jsons[("minecraft:ageable", "minecraft:chicken_baby")])["duration"] == 1200
    assert plan.base == frozenset(["minecraft:behavior.tempt"]) and plan.missing == [] and plan.unreadable == []
    assert plan.groups == {"minecraft:chicken_baby": frozenset(["minecraft:ageable"]), "minecraft:chicken_adult": frozenset(["minecraft:breedable"])}
    # 已经有的不重复加（别的包已经加过稻米），单个字符串当一项的列表，看不懂的那一处不下发
    assert json.loads(Rules.patched({"items": ["arris:rice"]}, "items", SEEDS))["items"] == ["arris:rice", "arris:cabbage_seeds", "arris:tomato_seeds"]
    assert json.loads(Rules.patched({"tame_items": "bone"}, "tame_items", ["arris:ham"]))["tame_items"] == ["bone", "arris:ham"]
    healing = Rules.patched({"items": [{"item": "fish", "heal_amount": 2}]}, "items", [{"item": "fish", "heal_amount": 9}, {"item": "x", "heal_amount": 1}])
    assert json.loads(healing)["items"] == [{"item": "fish", "heal_amount": 2}, {"item": "x", "heal_amount": 1}]
    assert Rules.patched({"priority": 4}, "items", SEEDS) is None and Rules.patched("x", "items", SEEDS) is None


def testShapesWeCannotReadAreSkippedAndNothingAtAllIsNone():
    odd = json.loads(json.dumps(CHICKEN))
    odd["minecraft:entity"]["components"]["minecraft:behavior.tempt"]["items"] = {"bad": 1}
    del odd["minecraft:entity"]["component_groups"]["minecraft:chicken_adult"]
    plan = _plan(odd)
    assert plan.unreadable == [("minecraft:behavior.tempt", Rules.BASE)] and plan.missing == ["minecraft:breedable"]
    assert list(plan.jsons) == [("minecraft:ageable", "minecraft:chicken_baby")]
    assert Rules.plan({"minecraft:entity": {"description": {"identifier": "minecraft:chicken"}}}, Mobs.ANIMAL_FOOD["minecraft:chicken"]) is None
    assert Rules.plan({"nope": 1}, Mobs.ANIMAL_FOOD["minecraft:chicken"]) is None


def testTheEventsThatSwapTheseGroupsIncludingTheOnesThatTriggerThem():
    # 直接加减的、在 sequence / randomize 里套着的、trigger 过去的（target 不是 self 的不算：那是对别的实体）；只碰别的组的不算
    assert _plan().events == frozenset(["minecraft:entity_born", "minecraft:ageable_grow_up", "minecraft:spawn_adult", "minecraft:entity_spawned"])


def testTheStackFoldsLikeTheEngine():
    plan = _plan()
    baby = ["+minecraft:chicken", "+minecraft:chicken_baby"]
    assert sorted(_sent(plan, baby)) == ["minecraft:ageable", "minecraft:behavior.tempt"]
    grown = baby + ["+##netease::minecraft:ageable", "+minecraft:chicken_adult", "-minecraft:chicken_baby"]
    assert sorted(_sent(plan, grown)) == ["minecraft:behavior.tempt", "minecraft:breedable"]     # 长大：ageable 跟着幼年组没了
    assert sorted(_sent(plan, ["+minecraft:chicken"])) == ["minecraft:behavior.tempt"]          # 刚出来、组还没加上
    assert sorted(_sent(plan, None)) == ["minecraft:behavior.tempt"]                            # 读不懂：只给顶层的
    assert Rules.current(plan, "garbage") is None
    # 减一个带同名组件的组，顶层那个也拿掉（ENT-01 / ENT-03）；后加的组盖掉顶层的
    swapped = json.loads(json.dumps(CHICKEN))
    swapped["minecraft:entity"]["component_groups"]["minecraft:chicken_baby"]["minecraft:behavior.tempt"] = {"items": ["melon_seeds"]}
    plan = _plan(swapped)
    assert _sent(plan, baby)["minecraft:behavior.tempt"]["items"] == ["melon_seeds"] + list(SEEDS)
    assert "minecraft:behavior.tempt" not in _sent(plan, baby + ["-minecraft:chicken_baby"])


# ---- 本机原版 ----

def _vanillaDefinition(entityType):
    rp = fdtest.vanilla()
    if rp is None:
        return None
    path = os.path.join(os.path.dirname(rp), "..", "behavior_packs", "vanilla", *Rules.definitionPath(entityType).split("/"))
    with io.open(path, encoding="utf-8-sig") as f:
        return Rules.parse(PackJson.stripComments(f.read()), entityType)


# 原版 3.10 里每种动物被补的地方（2026-11-26 和删掉的六份覆盖文件逐处比过）
PLACES = {
    "minecraft:cat": [("minecraft:ageable", "minecraft:cat_baby"), ("minecraft:behavior.tempt", "minecraft:cat_tame"),
                      ("minecraft:behavior.tempt", "minecraft:cat_wild"), ("minecraft:breedable", "minecraft:cat_adult"),
                      ("minecraft:healable", ""), ("minecraft:tameable", "minecraft:cat_wild")],
    "minecraft:chicken": [("minecraft:ageable", "minecraft:chicken_baby"), ("minecraft:behavior.tempt", ""),
                          ("minecraft:breedable", "minecraft:chicken_adult")],
    "minecraft:parrot": [("minecraft:tameable", "minecraft:parrot_wild")],
    "minecraft:pig": [("minecraft:ageable", "minecraft:pig_baby"), ("minecraft:behavior.tempt", ""), ("minecraft:breedable", "minecraft:pig_adult")],
    "minecraft:rabbit": [("minecraft:ageable", "baby"), ("minecraft:behavior.tempt", ""), ("minecraft:breedable", "adult")],
    "minecraft:wolf": [("minecraft:ageable", "minecraft:wolf_baby"), ("minecraft:breedable", "minecraft:wolf_adult"), ("minecraft:healable", "")],
}


def testAgainstTheLocalVanillaPackEachPlaceIsVanillaPlusOurItems():
    if fdtest.vanilla() is None:
        print("跳过：找不到本机原版行为包")
        return
    for entityType, patches in sorted(Mobs.ANIMAL_FOOD.items()):
        definition = _vanillaDefinition(entityType)
        plan = Rules.plan(definition, patches)
        assert sorted(plan.jsons) == PLACES[entityType], (entityType, sorted(plan.jsons))
        fields = dict((name, (field, extra)) for name, field, extra in patches)
        entity = definition["minecraft:entity"]
        for (name, provider), text in plan.jsons.items():
            vanilla = entity["components"][name] if provider == Rules.BASE else entity["component_groups"][provider][name]
            ours, (field, extra) = json.loads(text), fields[name]
            assert dict((k, v) for k, v in ours.items() if k != field) == dict((k, v) for k, v in vanilla.items() if k != field), (entityType, name)
            assert ours[field] == list(vanilla[field]) + [json.loads(json.dumps(entry)) for entry in extra], (entityType, name, provider)
        assert not plan.missing and not plan.unreadable, entityType
    # 换组的事件从定义里读，不是写死成鸡的
    assert {"grow_up", "minecraft:entity_born"} <= _plan(_vanillaDefinition("minecraft:rabbit"), "minecraft:rabbit").events
    assert {"minecraft:on_tame", "minecraft:spawn_wild_baby"} <= _plan(_vanillaDefinition("minecraft:cat"), "minecraft:cat").events
    wolf = _plan(_vanillaDefinition("minecraft:wolf"), "minecraft:wolf").events
    assert "minecraft:ageable_set_baby" in wolf and "minecraft:on_tame" not in wolf      # 狼的驯服只换 wolf_wild（里面的 tameable 不补）


def testAgainstTheLocalVanillaPackTheRightGroupIsSentForEachState():
    if fdtest.vanilla() is None:
        print("跳过：找不到本机原版行为包")
        return
    cat = _plan(_vanillaDefinition("minecraft:cat"), "minecraft:cat")
    wild = ["+minecraft:cat", "+minecraft:cat_adult", "+minecraft:cat_wild"]
    tame = wild + ["-minecraft:cat_wild", "+minecraft:cat_tame"]
    assert sorted(_sent(cat, wild)) == ["minecraft:behavior.tempt", "minecraft:breedable", "minecraft:healable", "minecraft:tameable"]
    assert "can_get_scared" in _sent(cat, wild)["minecraft:behavior.tempt"]               # 野猫那一组的值
    assert sorted(_sent(cat, tame)) == ["minecraft:behavior.tempt", "minecraft:breedable", "minecraft:healable"]
    assert "can_get_scared" not in _sent(cat, tame)["minecraft:behavior.tempt"]           # 驯服猫那一组的值
    parrot = _plan(_vanillaDefinition("minecraft:parrot"), "minecraft:parrot")
    assert list(_sent(parrot, ["+minecraft:parrot", "+minecraft:parrot_wild"])) == ["minecraft:tameable"]
    assert _sent(parrot, ["+minecraft:parrot", "+minecraft:parrot_wild", "-minecraft:parrot_wild"]) == {}
    wolf = _plan(_vanillaDefinition("minecraft:wolf"), "minecraft:wolf")
    baby = ["+minecraft:wolf", "+minecraft:wolf_baby", "+minecraft:wolf_wild"]
    assert sorted(_sent(wolf, baby)) == ["minecraft:ageable", "minecraft:healable"]
    assert sorted(_sent(wolf, baby + ["+minecraft:wolf_adult", "-minecraft:wolf_baby"])) == ["minecraft:breedable", "minecraft:healable"]


def testAnotherPacksDefinitionIsTheOneWeAppendTo():
    if fdtest.vanilla() is None:
        print("跳过：找不到本机原版行为包")
        return
    theirs = _vanillaDefinition("minecraft:chicken")
    entity = theirs["minecraft:entity"]
    entity["components"]["minecraft:behavior.tempt"] = {"priority": 2, "speed_multiplier": 1.5, "items": ["mymod:corn", "arris:rice"]}
    groups = entity["component_groups"]
    groups["mymod:hen"] = groups.pop("minecraft:chicken_adult")
    groups["mymod:hen"]["minecraft:breedable"]["breed_items"] = ["mymod:corn"]
    entity["events"]["mymod:become_hen"] = {"add": {"component_groups": ["mymod:hen"]}}
    plan = _plan(theirs)
    sent = _sent(plan, ["+minecraft:chicken", "+mymod:hen"])
    assert sent["minecraft:behavior.tempt"] == {"priority": 2, "speed_multiplier": 1.5,
                                                "items": ["mymod:corn", "arris:rice", "arris:cabbage_seeds", "arris:tomato_seeds"]}
    assert sent["minecraft:breedable"]["breed_items"] == ["mymod:corn"] + list(SEEDS)
    assert "mymod:become_hen" in plan.events


# ---- 服务端 ----

class _Resource(object):
    """假的 server_resource：路径 -> 文本；列目录给这一层的条目。"""

    def __init__(self, files):
        self.files, self.loads = files, []

    def load_server_file(self, path):
        self.loads.append(path)
        return self.files.get(path, "").encode("utf-8")

    def list_server_directory(self, path):
        prefix = path + "/"
        return sorted(set(prefix + rest.split("/")[0] for rest in (name[len(prefix):] for name in self.files if name.startswith(prefix))))


def _server(files, stacks):
    resource = _Resource(files)
    module = types.ModuleType("server_resource")
    module.load_server_file, module.list_server_directory = resource.load_server_file, resource.list_server_directory
    sys.modules["server_resource"] = module
    for table in (AnimalFood._plans, AnimalFood._events, AnimalFood._unread):
        table.clear()
    world.entities.clear()
    world.components.clear()
    world.timers = []
    world._EntityDefinitions = lambda target: {"GetEntityDefinitions": lambda: stacks.get(target)}
    return resource


def _add(entityId, entityType):
    world.addEntity(entityId, entityType)
    Registry.dispatch("AddEntityServerEvent", {"id": entityId, "engineTypeStr": entityType}, entityType)


def testOnlyTheSixAnimalsAreTouchedAndOnlyOneTickLater():
    resource = _server({"entities/chicken.json": json.dumps(CHICKEN)}, {"c1": ["+minecraft:chicken", "+minecraft:chicken_baby"]})
    _add("z1", "minecraft:zombie")
    assert world.timers == [] and resource.loads == []
    _add("c1", "minecraft:chicken")
    assert world.components == {} and len(world.timers) == 1                 # 出现那一拍不打，晚一拍
    world.runTimers()
    assert sorted(world.components["c1"]) == ["minecraft:ageable", "minecraft:behavior.tempt"]
    assert json.loads(world.components["c1"]["minecraft:ageable"])["feed_items"][-3:] == list(SEEDS)
    _add("c2", "minecraft:chicken")
    assert resource.loads == ["entities/chicken.json"]                       # 定义只读一次


def testGroupSwapsFromTheDefinitionTriggerAnotherRoundOthersAreFree():
    _server({"entities/chicken.json": json.dumps(CHICKEN)},
            {"c1": ["+minecraft:chicken", "+minecraft:chicken_baby", "+minecraft:chicken_adult", "-minecraft:chicken_baby"]})
    _add("c1", "minecraft:chicken")
    world.runTimers()
    world.components.clear()
    for event in ("minecraft:sounds", "minecraft:on_tame"):                  # 不换这几个组 / 鸡没有的事件：不算
        Registry.dispatch("EntityDefinitionsEventServerEvent", {"entityId": "c1", "eventName": event}, event)
    world.addEntity("p1", "minecraft:pig")
    Registry.dispatch("EntityDefinitionsEventServerEvent", {"entityId": "p1", "eventName": "minecraft:ageable_grow_up"}, "minecraft:ageable_grow_up")
    assert world.timers == []
    Registry.dispatch("EntityDefinitionsEventServerEvent", {"entityId": "c1", "eventName": "minecraft:ageable_grow_up"}, "minecraft:ageable_grow_up")
    assert world.components == {} and len(world.timers) == 1
    world.runTimers()
    assert sorted(world.components["c1"]) == ["minecraft:behavior.tempt", "minecraft:breedable"]


def testNoDefinitionMeansNothingOnceAndAStrangeFileFallsBackToTheScan():
    resource = _server({"entities/chicken.json": json.dumps({"minecraft:entity": {"description": {"identifier": "mymod:chicken"}}}),
                        "entities/birds/hen.json": json.dumps(CHICKEN)}, {"c1": ["+minecraft:chicken"]})
    _add("c1", "minecraft:chicken")
    world.runTimers()
    assert sorted(world.components["c1"]) == ["minecraft:behavior.tempt"] and "entities/birds/hen.json" in resource.loads
    resource = _server({}, {"r1": ["+minecraft:rabbit"]})
    _add("r1", "minecraft:rabbit")
    _add("r2", "minecraft:rabbit")
    assert world.timers == [] and AnimalFood._plans == {"minecraft:rabbit": None}
    assert resource.loads.count("entities/rabbit.json") == 1                 # 读不到也只试一次


def testAnUnreadableStackSendsOnlyTheTopLevelComponents():
    _server({"entities/chicken.json": json.dumps(CHICKEN)}, {"c1": None})
    _add("c1", "minecraft:chicken")
    world.runTimers()
    assert sorted(world.components["c1"]) == ["minecraft:behavior.tempt"] and AnimalFood._unread == {"minecraft:chicken"}


def testTheEntityCanBeGoneBeforeTheTick():
    _server({"entities/chicken.json": json.dumps(CHICKEN)}, {})
    _add("c1", "minecraft:chicken")
    del world.entities["c1"]
    world.runTimers()
    assert world.components == {}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
