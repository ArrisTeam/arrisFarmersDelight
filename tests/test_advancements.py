# -*- coding: utf-8 -*-
# runner: both
"""JE 农夫乐事的 21 条进度接成就系统（arrisAdvancements）：节点表（Shared/Data/Advancements）、推进（Compat/Advancements/AdvTriggers）、
接上以后挂的东西（Compat/Advancements/AdvBridge），成就系统用一个记账的假接口。

- 节点对着 .refs 里 JE 的 21 个 JSON 复算：ID、父子、框、弹窗、播报、隐藏、经验、条件个数和名字、OR / AND，标题和描述对着 JE 的 zh_cn.json
  （没有 .refs 时这几条跳过）；父先子后；图标、条件里的物品 / 方块在本包或原版里都有。
- 推进：要求 any 的做到一个就 setFinish（做到过的不再调）、all 的每个子条件 addProgressUnique 一次。
- 接上以前（没装成就系统）：注册表里没有它的处理函数、Deeds 没有订阅者；接口不对不接。接上以后每一类事件都推进到对的那条。
"""
from __future__ import print_function

import glob
import io
import json
import os

import fdtest

Data = fdtest.load("Shared.Data.Advancements")
Registry = fdtest.load("Server.EventRegistry")
Deeds = fdtest.load("Server.Helpers.Deeds")
Triggers = fdtest.load("Compat.Advancements.AdvTriggers")
Bridge = fdtest.load("Compat.Advancements.AdvBridge")
# 接上以前的样子：导入 AdvBridge 不挂任何东西
BEFORE = dict((event, list(Registry.handlerNames(event))) for event in (
    "EntityPlaceBlockAfterServerEvent", "ItemUseOnAfterServerEvent", "PlayerEatFoodServerEvent", "AddEffectServerEvent", "ProjectileDoHitEffectEvent"))
SUBSCRIBED_BEFORE = dict((deed, list(funcs)) for deed, funcs in Deeds._subscribers.items())
JE = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src")
JE_ADVANCEMENTS = os.path.join(JE, "generated", "resources", "data", "farmersdelight", "advancements", "main")
JE_LANG = os.path.join(JE, "main", "resources", "assets", "farmersdelight", "lang", "zh_cn.json")


class FakeApi(object):
    """记账的成就系统接口：只有用到的几个函数，进度存在 done / subs 里。"""

    def __init__(self):
        self.calls, self.done, self.subs, self.nodes, self.ready = [], set(), {}, [], []

    def registerAdvancements(self, nodes):
        self.nodes = nodes
        return len(nodes)

    def listenOnPlayerReady(self, func):
        self.ready.append(func)

    def isDone(self, playerId, nodeId):
        return (playerId, nodeId) in self.done

    def setFinish(self, playerId, nodeId):
        self.calls.append(("setFinish", playerId, nodeId))
        if (playerId, nodeId) in self.done:
            return False
        self.done.add((playerId, nodeId))
        return True

    def addProgressUnique(self, playerId, nodeId, subKey):
        self.calls.append(("addProgressUnique", playerId, nodeId, subKey))
        seen = self.subs.setdefault((playerId, nodeId), set())
        fresh = subKey not in seen
        seen.add(subKey)
        return fresh


class FakeEnv(object):
    def __init__(self):
        self.types, self.blocks, self.items, self.listened = {}, {}, {}, {}

    def typeOf(self, entityId):
        return self.types.get(entityId)

    def blockAt(self, pos, dimensionId):
        return self.blocks.get(tuple(pos))

    def itemsOf(self, playerId):
        return self.items.get(playerId, [])

    def listen(self, eventName, func):
        self.listened[eventName] = func


def _id(name):
    return Data.NAMESPACE + name


def _text(value):
    """py2 里表里的中文是 utf-8 的 str、json 读出来的是 unicode：比之前换成同一种。"""
    return value.decode("utf-8") if isinstance(value, bytes) and not isinstance(value, type(u"")) else value


def _je():
    files = sorted(glob.glob(os.path.join(JE_ADVANCEMENTS, "*.json")))
    if not files:
        return None
    result = {}
    for path in files:
        with io.open(path, encoding="utf-8") as f:
            result[os.path.basename(path)[:-5]] = json.load(f)
    return result


# ---- 节点表 ----

def testTheNodesFollowJavasAdvancementsOneByOne():
    je = _je()
    if je is None:
        print("跳过：没有 .refs/FarmersDelight")
        return
    with io.open(JE_LANG, encoding="utf-8") as f:
        lang = json.load(f)
    nodes = dict((node["id"], node) for node in Data.NODES)
    assert len(je) == 21 and sorted(nodes) == sorted(_id(name) for name in je)
    for name, advancement in je.items():
        node, display = nodes[_id(name)], advancement["display"]
        assert (node.get("parent") or None) == (advancement.get("parent") or None), name
        assert node["frame"] == display["frame"] and node["hidden"] == display["hidden"], name
        assert node["show_toast"] == display["show_toast"] and node["announce"] == display["announce_to_chat"], name
        assert node.get("xp") == advancement.get("rewards", {}).get("experience"), name
        assert _text(node["title"]) == lang["advancements.farmersdelight.%s.title" % name], name
        assert _text(node["description"]) == lang["advancements.farmersdelight.%s.description" % name], name
        requirement, subs = Data.CRITERIA[name]
        requirements = advancement["requirements"]
        if len(requirements) == 1:
            assert requirement == "any" and node["goal"] == 1, name                         # JE 的 OR：一组里任何一个
        else:
            assert requirement == "all" and node["goal"] == len(requirements) == len(subs), name   # AND：每个一组
        assert sorted(sub for sub, _kind, _keys in subs) == sorted(advancement["criteria"]), name
    assert nodes[_id("root")]["background"] == Data.BACKGROUND and all("background" not in node for node in Data.NODES[1:])


def testParentsComeBeforeChildrenAndOnlyTheRootHasNone():
    seen = set()
    for node in Data.NODES:
        assert node.get("parent") is None or node["parent"] in seen, node["id"]
        seen.add(node["id"])
    assert [node["id"] for node in Data.NODES if not node.get("parent")] == [_id("root")]


def _ours():
    """本包的物品和方块的 identifier（方块也当物品：方块物品的名字就是方块名）。"""
    names = set()
    for folder in ("netease_items_beh", "netease_blocks"):
        for root, _dirs, files in os.walk(os.path.join(fdtest.BP, folder)):
            for name in files:
                with io.open(os.path.join(root, name), encoding="utf-8-sig") as f:
                    data = json.load(f)
                for key in ("minecraft:item", "minecraft:block"):
                    if key in data:
                        names.add(data[key]["description"]["identifier"])
    return names


def testEveryItemAndBlockTheTableNamesExists():
    ours = _ours()
    assert len(ours) > 200, len(ours)
    vanillaBlocks = None
    blocksJson = fdtest.vanilla("blocks.json")
    if blocksJson and os.path.isfile(blocksJson):
        with io.open(blocksJson, encoding="utf-8") as f:
            vanillaBlocks = set("minecraft:" + name for name in json.load(f))
    for node in Data.NODES:
        icon = node["icon"]["item"]
        assert icon in ours or icon.startswith("minecraft:"), icon
    for name, (_requirement, subs) in Data.CRITERIA.items():
        for _sub, kind, keys in subs:
            for key in keys if kind in ("obtain", "eaten", "placed", "harvested") else ():
                if key.startswith("arris:"):
                    assert key in ours, (name, key)
                elif kind == "placed" and vanillaBlocks is not None:
                    assert key in vanillaBlocks, (name, key)
    effects = fdtest.load("Shared.Data.Effects")
    assert Data.CRITERIA["eat_nourishing_food"][1][0][2] == (effects.NOURISHMENT,)
    for item, blocks in Data.PLANTERS.items():
        assert item in ours or item.startswith("minecraft:"), item
        assert any(block in keys for block in blocks for _sub, kind, keys in Data.CRITERIA["plant_all_crops"][1]), item


# ---- 推进 ----

def testAnyNeedsOneAllCountsEachSubOnce():
    api = FakeApi()
    assert Triggers.fire(api, "p1", "obtain", "arris:iron_knife") == 1
    assert Triggers.fire(api, "p1", "obtain", "arris:flint_knife") == 0                # 做到过：不再 setFinish
    assert [call for call in api.calls if call[0] == "setFinish"] == [("setFinish", "p1", _id("craft_knife"))]
    assert Triggers.fire(api, "p1", "obtain", "arris:netherite_knife") == 1             # 下界合金刀也是刀，但刀耕火种做到过：只推进"没这金刚钻"
    assert ("p1", _id("obtain_netherite_knife")) in api.done
    assert Triggers.fire(api, "p1", "placed", "minecraft:wheat") == 1
    assert Triggers.fire(api, "p1", "placed", "arris:rich_soil_wheat0") == 0            # 沃土上的小麦也是小麦：同一个子条件
    assert Triggers.fire(api, "p1", "placed", "arris:rice_stage0") == 2                  # 倾斜稻根 + 轮作的稻米
    assert api.subs[("p1", _id("plant_all_crops"))] == {"wheat", "rice"}
    assert Triggers.fire(api, "p1", "placed", "minecraft:stone") == 0 and Triggers.fire(None, "p1", "cut") == 0
    assert Triggers.fire(api, None, "cut") == 0


# ---- 接上 ----

def testNothingIsHookedBeforeTheAdvancementsSystemArrivesAndABadApiIsRefused():
    for event, names in BEFORE.items():
        assert not [name for name in names if name[0].endswith("AdvBridge")], event
    assert not [func for funcs in SUBSCRIBED_BEFORE.values() for func in funcs if func.__module__.endswith("AdvBridge")]
    current = Bridge.api()
    assert Bridge.attach(None, FakeEnv()) is None and Bridge.attach(object(), FakeEnv()) is None and Bridge.api() is current


def _attached():
    api, env = FakeApi(), FakeEnv()
    assert Bridge.attach(api, env) == 21
    return api, env


def testAttachingRegistersTheTreeAndEveryKindOfHappeningMovesTheRightNode():
    api, env = _attached()
    assert [node["id"] for node in api.nodes] == [node["id"] for node in Data.NODES] and api.nodes[0] is not Data.NODES[0]
    env.items["p1"] = ["arris:straw", "minecraft:dirt"]
    api.ready[0]({"playerId": "p1", "progress": {}})
    assert {_id("root"), _id("harvest_straw")} <= set(node for player, node in api.done if player == "p1")
    env.listened["InventoryItemChangedServerEvent"]({"playerId": "p1", "slot": 3, "oldItemDict": None,
                                                      "newItemDict": {"newItemName": "arris:ham", "count": 1}})
    Registry.dispatch("EntityPlaceBlockAfterServerEvent", {"entityId": "p1", "fullName": "minecraft:campfire"}, "minecraft:campfire")
    Registry.dispatch("EntityPlaceBlockAfterServerEvent", {"entityId": "p1", "fullName": "minecraft:stone"}, "minecraft:stone")
    env.blocks[(0, 65, 0)] = "minecraft:pumpkin_stem"
    planting = {"entityId": "p1", "x": 0, "y": 64, "z": 0, "face": 1, "dimensionId": 0, "blockName": "minecraft:farmland",
                "itemDict": {"newItemName": "minecraft:pumpkin_seeds", "count": 1}}
    Registry.dispatch("ItemUseOnAfterServerEvent", planting, "minecraft:farmland")
    Registry.dispatch("ItemUseOnAfterServerEvent", dict(planting, face=2), "minecraft:farmland")     # 点的那一面外面不是南瓜茎：不算
    Registry.dispatch("PlayerEatFoodServerEvent", {"playerId": "p1", "itemDict": {"newItemName": "arris:cookbeef_stew"}}, "arris:cookbeef_stew")
    Registry.dispatch("AddEffectServerEvent", {"entityId": "p1", "effectName": "arris:nourishment"})
    Registry.dispatch("AddEffectServerEvent", {"entityId": "p1", "effectName": "speed"})
    env.types.update(t1="arris:rotten_tomato", t2="arris:rotten_tomato", e1="minecraft:pillager", e2="minecraft:zombie")
    Registry.dispatch("ProjectileDoHitEffectEvent", {"id": "t2", "hitTargetType": "ENTITY", "targetId": "e2", "srcId": "p1"})
    Registry.dispatch("ProjectileDoHitEffectEvent", {"id": "t1", "hitTargetType": "BLOCK", "targetId": "e1", "srcId": "p1"})
    assert ("p1", _id("hit_raider_with_rotten_tomato")) not in api.done
    Registry.dispatch("ProjectileDoHitEffectEvent", {"id": "t1", "hitTargetType": "ENTITY", "targetId": "e1", "srcId": "p1"})
    for deed, detail in ((Deeds.CUT_ON_BOARD, "arris:cabbage"), (Deeds.SKILLET_COOKED, "minecraft:beef"),
                         (Deeds.PLACED_BLOCK, "arris:skillet"), (Deeds.HARVESTED, "arris:tomatoes_vine_stage3"),
                         (Deeds.HARVESTED, "arris:budding_tomatoes_stage6")):
        Deeds.done("p1", deed, detail)
    done = set(node[len(Data.NAMESPACE):] for player, node in api.done if player == "p1")
    assert done == {"root", "harvest_straw", "get_ham", "place_campfire", "eat_nourishing_food", "hit_raider_with_rotten_tomato",
                    "use_cutting_board", "use_skillet", "place_skillet", "harvest_ropelogged_tomato"}, sorted(done)
    assert api.subs == {("p1", _id("plant_all_crops")): {"pumpkin"}, ("p1", _id("master_chef")): {"beef_stew"}}


def testAttachingTwiceDoesNotHookTwice():
    Bridge._state["hooked"] = False
    registered, real = [], Bridge.registerHandler

    def counting(event, **kwargs):
        registered.append(event)
        return real(event, **kwargs)

    Bridge.registerHandler = counting
    try:
        api, env = _attached()
        api2, env2 = _attached()
    finally:
        Bridge.registerHandler = real
    assert len(registered) == 5, registered                                   # 第二次 attach 不再登记处理函数
    assert list(env.listened) == ["InventoryItemChangedServerEvent"] and env2.listened == {}     # 背包事件只动态监听一次
    Deeds.done("p9", Deeds.CUT_ON_BOARD, "arris:cabbage")
    assert [call for call in api2.calls if call[1] == "p9"] == [("setFinish", "p9", _id("use_cutting_board"))] and api.calls == []
    assert len([name for name in Registry.handlerNames("EntityPlaceBlockAfterServerEvent") if name[0].endswith("AdvBridge")]) == 1


def testOnlyTheEffectsATableNamesReachTheHandler():
    # 效果事件很多：按效果名匹配，别的效果到不了处理函数
    _attached()
    entries = [entry for entry in Registry._handlers["AddEffectServerEvent"] if entry.ident[1] == "onEffect"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry.test(entry.keyOf({"effectName": "arris:nourishment"})) and not entry.test(entry.keyOf({"effectName": "speed"}))


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
