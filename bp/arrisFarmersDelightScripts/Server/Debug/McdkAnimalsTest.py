# -*- coding: utf-8 -*-
"""McdkAnimalsTest - 原版六种动物认农夫乐事的食物（运行时加组件，Server/AnimalFood.py）的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。分两步，中间等约 5 秒（加减组件组下一帧才生效、补丁晚一拍才打，驯服 / 长大也要几拍）：
    from arrisFarmersDelightScripts.Server.Debug import McdkAnimalsTest as T
    T.mcdk_test_animals_start()     # 第一个玩家东边 4 格起一排：每种动物用 /summon 带出生事件生成成年、幼年各一只（鹦鹉只有成年）
    # 等约 5 秒
    T.mcdk_test_animals_collect()   # 交回结果，删掉生成的动物，主手物品换回去
start 之后 0.6 秒读一遍每只的定义栈（GetEntityDefinitions）、GetComponents 里那几个组件带没带本包的物品、规则现在会下发哪几个；
0.8 秒拿本包的食物真喂（PlayerUseItemToEntity，主手换成那件食物）：成年 / 幼年各喂一次，记 PlayerFeedEntityServerEvent 来没来
（成年 = 进求爱、幼年 = 喂长大）；野猫、鹦鹉喂到驯服为止（最多 12 次，每次 0.33）；狼用脚本驯服（SetEntityTamed + on_tame 事件），
狼和驯服了的猫先打掉几点血再喂肉 / 鱼片，看回没回血；2 秒让幼年长大（猫 / 鸡 / 猪 / 狼触发 minecraft:ageable_grow_up，兔子是 grow_up），
3.5 秒再读一遍（长大的应当有 breedable、带本包的物品，ageable 没了）。plans 是服务端读到的定义算出的补丁（读没读到定义、补几处）。
"""
import json
import time

from ...QuModLibs.Server import ListenForEvent
from ..EventRegistry import registerHandler
from ..Helpers.Engine import compFactory, levelId, serverApi, DestroyEntity, GetCarriedItem, SetCarriedItem
from .. import AnimalFood
from ...Shared.Data.Mobs import ANIMAL_FOOD
from ...Shared.Rules import AnimalFood as Rules

# (实体类型, 年龄, /summon 的出生事件, 喂的东西)；原版 3.10 的事件名
CASES = (
    ("minecraft:chicken", "adult", "minecraft:spawn_adult", "arris:rice"),
    ("minecraft:chicken", "baby", "minecraft:entity_born", "arris:rice"),
    ("minecraft:pig", "adult", "minecraft:spawn_adult", "arris:tomato"),
    ("minecraft:pig", "baby", "minecraft:entity_born", "arris:tomato"),
    ("minecraft:rabbit", "adult", "grow_up", "arris:cabbage_leaf"),
    ("minecraft:rabbit", "baby", "minecraft:entity_born", "arris:cabbage_leaf"),
    ("minecraft:cat", "adult", "minecraft:spawn_wild_adult", "arris:cod_slice"),
    ("minecraft:cat", "baby", "minecraft:spawn_wild_baby", "arris:cod_slice"),
    ("minecraft:parrot", "adult", "minecraft:entity_spawned", "arris:tomato_seeds"),
    ("minecraft:wolf", "adult", "minecraft:spawn_wild_adult", "arris:ham"),
    ("minecraft:wolf", "baby", "minecraft:spawn_wild_baby", "arris:ham"),
)
GROW_UP = {"minecraft:rabbit": "grow_up"}
TAME_TRIES = 12
_state = {"entities": {}, "results": {}, "feeds": [], "events": [], "watching": False, "player": None, "hand": None, "started": 0.0,
          "feedListened": False}


def _key(entityType, age):
    return "%s:%s" % (entityType.split(":")[1], age)


def _recordFeed(args):
    # PlayerFeedEntityServerEvent：ModServer 不转它（没有玩法模块用），这里自己动态监听（第一次 start 时挂上）
    if _state["watching"] and args.get("entityId") in _state["entities"].values():
        _state["feeds"].append((args.get("entityId"), (args.get("itemDict") or {}).get("newItemName")))


@registerHandler("EntityDefinitionsEventServerEvent")
def _recordEvent(args):
    if _state["watching"] and args.get("entityId") in _state["entities"].values():
        _state["events"].append((args.get("entityId"), args.get("eventName")))


def _find(tag, entityType):
    for entityId, info in (serverApi.GetEngineActor() or {}).items():
        if (info or {}).get("identifier") == entityType and compFactory.CreateName(entityId).GetName() == tag:
            return entityId
    return None


def _ours(value, entityType, component):
    """GetComponents 给的这个组件里有没有本包追加的第一个条目（值的形状没核实过：整个转成文本找名字）。"""
    for name, _field, extra in ANIMAL_FOOD[entityType]:
        if name == component and extra:
            first = extra[0]["item"] if isinstance(extra[0], dict) else extra[0]
            return first in json.dumps(value)
    return False


def _read(phase):
    for key, entityId in _state["entities"].items():
        entityType = compFactory.CreateEngineType(entityId).GetEngineTypeStr()
        if not entityType:
            _state["results"].setdefault(key, {})[phase] = {"gone": True}
            continue
        stack = compFactory.CreateEntityDefinitions(entityId).GetEntityDefinitions()
        components = compFactory.CreateEntityEvent(entityId).GetComponents() or {}
        plan = AnimalFood.planOf(entityType)
        seen = {}
        for name, _field, _extra in ANIMAL_FOOD[entityType]:
            present = isinstance(components, dict) and name in components
            seen[name] = {"present": present, "ours": present and _ours(components[name], entityType, name)}
        _state["results"].setdefault(key, {})[phase] = {
            "stack": stack, "baby": compFactory.CreateEntityDefinitions(entityId).IsBaby(),
            "tamed": compFactory.CreateEntityDefinitions(entityId).IsTamed(), "components": seen,
            "rule": [name for name, _text in Rules.send(plan, stack)] if plan is not None else None}


def _health(entityId):
    return compFactory.CreateAttr(entityId).GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)


def _use(playerId, entityId, itemName):
    SetCarriedItem(playerId, {"newItemName": itemName, "newAuxValue": 0, "count": 64})
    return compFactory.CreateBlockInfo(playerId).PlayerUseItemToEntity(entityId)


def _tameByScript(playerId, entityId):
    compFactory.CreateTame(entityId).SetEntityTamed(playerId, entityId)
    return compFactory.CreateEntityEvent(entityId).TriggerCustomEvent(entityId, "minecraft:on_tame")


def _healCheck(playerId, entityId, itemName, damage):
    full = _health(entityId)
    compFactory.CreateHurt(entityId).Hurt(damage, serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack, None, None, False)
    hurt = _health(entityId)
    used = _use(playerId, entityId, itemName)
    return {"full": full, "hurt": hurt, "fed": _health(entityId), "used": used}


def _feed():
    playerId = _state["player"]
    for entityType, age, _event, food in CASES:
        key = _key(entityType, age)
        entityId = _state["entities"].get(key)
        if not entityId:
            continue
        fed = {"item": food}
        if entityType in ("minecraft:cat", "minecraft:parrot") and age == "adult":
            tries = 0
            while tries < TAME_TRIES and not compFactory.CreateEntityDefinitions(entityId).IsTamed():
                _use(playerId, entityId, food)
                tries += 1
            fed.update(tameTries=tries, tamed=compFactory.CreateEntityDefinitions(entityId).IsTamed())
        elif entityType == "minecraft:wolf" and age == "adult":
            fed["scriptTamed"] = _tameByScript(playerId, entityId)
        else:
            fed["used"] = _use(playerId, entityId, food)
        _state["results"].setdefault(key, {})["feed"] = fed
    compFactory.CreateGame(levelId).AddTimer(0.6, _heal)


def _heal():
    # 狼脚本驯服之后才有主人；猫驯服了才回血（原版驯服猫回血的写法在顶层 healable，驯服与否不看，这里只量驯服了的那只）
    playerId = _state["player"]
    for key, food, damage in (("wolf:adult", "arris:ham", 4.0), ("cat:adult", "arris:cod_slice", 2.0)):
        entityId = _state["entities"].get(key)
        if entityId:
            _state["results"].setdefault(key, {})["heal"] = _healCheck(playerId, entityId, food, damage)


def _grow():
    for entityType, age, _event, _food in CASES:
        entityId = _state["entities"].get(_key(entityType, age))
        if entityId and age == "baby":
            event = GROW_UP.get(entityType, "minecraft:ageable_grow_up")
            done = compFactory.CreateEntityEvent(entityId).TriggerCustomEvent(entityId, event)
            _state["results"].setdefault(_key(entityType, age), {})["growUp"] = {"event": event, "triggered": done}


def mcdk_test_animals_start():
    """生成、排好之后的读 / 喂 / 长大 / 再读；约 5 秒后调 mcdk_test_animals_collect()。"""
    players = serverApi.GetPlayerList()
    if not players:
        return {"case": "animals", "ok": False, "error": "no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    _state.update(entities={}, results={}, feeds=[], events=[], watching=True, player=playerId,
                  hand=GetCarriedItem(playerId, True), started=time.time())
    if not _state["feedListened"]:
        _state["feedListened"] = True
        ListenForEvent("PlayerFeedEntityServerEvent", None, _recordFeed)
    command = compFactory.CreateCommand(levelId)
    summoned = {}
    for index, (entityType, age, event, _food) in enumerate(CASES):
        tag = "fdtest_" + _key(entityType, age).replace(":", "_")
        pos = (int(x) + 4 + 2 * index, int(y), int(z) + 3)
        summoned[_key(entityType, age)] = command.SetCommand(
            "/summon %s %d %d %d %s %s" % (entityType, pos[0], pos[1], pos[2], event, tag), playerId)
    _findAll()
    game = compFactory.CreateGame(levelId)
    game.AddTimer(0.3, _findAll)                 # 命令放出来的实体当场列不出来的话，晚一点再找一次
    game.AddTimer(0.6, _read, "before")
    game.AddTimer(0.8, _feed)
    game.AddTimer(2.0, _grow)
    game.AddTimer(3.5, _read, "after")
    return {"case": "animals", "started": True, "summoned": summoned, "found": sorted(_state["entities"])}


def _findAll():
    for entityType, age, _event, _food in CASES:
        key = _key(entityType, age)
        if key not in _state["entities"]:
            entityId = _find("fdtest_" + key.replace(":", "_"), entityType)
            if entityId:
                _state["entities"][key] = entityId


def _checks(results):
    problems = []
    for key, result in sorted(results.items()):
        for phase in ("before", "after"):
            reading = result.get(phase) or {}
            for name in reading.get("rule") or ():
                if not (reading.get("components") or {}).get(name, {}).get("ours"):
                    problems.append("%s %s：规则会下发 %s，GetComponents 里没看到本包的物品" % (key, phase, name))
        after = (result.get("after") or {}).get("components") or {}
        if key.endswith(":baby") and after:
            if after.get("minecraft:ageable", {}).get("present") or not after.get("minecraft:breedable", {}).get("ours"):
                problems.append("%s 长大以后：ageable 还在或 breedable 没有本包的物品" % key)
    return problems


def mcdk_test_animals_collect():
    """交回结果（每只的读数、喂食、长大，PlayerFeedEntityServerEvent、定义事件的记录，服务端读到的补丁），删掉生成的动物。"""
    _state["watching"] = False
    feeds, events = {}, {}
    names = dict((entityId, key) for key, entityId in _state["entities"].items())
    for entityId, item in _state["feeds"]:
        feeds.setdefault(names.get(entityId, entityId), []).append(item)
    for entityId, event in _state["events"]:
        events.setdefault(names.get(entityId, entityId), []).append(event)
    plans = {}
    for entityType in sorted(ANIMAL_FOOD):
        plan = AnimalFood._plans.get(entityType, "unread")
        plans[entityType] = plan if plan in (None, "unread") else {
            "places": sorted("%s@%s" % (name, provider or "components") for name, provider in plan.jsons),
            "events": len(plan.events), "missing": plan.missing, "unreadable": plan.unreadable}
    for entityId in _state["entities"].values():
        DestroyEntity(entityId)
    if _state["player"]:
        SetCarriedItem(_state["player"], _state["hand"] or {"newItemName": "minecraft:air", "count": 0})
    problems = _checks(_state["results"])
    return {"case": "animals", "ok": not problems and bool(_state["results"]), "problems": problems, "results": _state["results"],
            "feedEvents": feeds, "definitionEvents": events, "plans": plans,
            "seconds": round(time.time() - _state["started"], 2)}
