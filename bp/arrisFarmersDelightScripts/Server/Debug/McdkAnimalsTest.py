# -*- coding: utf-8 -*-
"""McdkAnimalsTest - 原版六种动物认农夫乐事的食物（运行时加组件，Server/AnimalFood.py）的游戏内自检（服务端）：测试函数，仅供 MCDK-MCP 的 execute_code / 开发调试调用

不会自动运行，没有 RPC 端点。分两步，中间等约 5 秒（加减组件组下一帧才生效、补丁晚两拍才打，驯服 / 长大也要几拍）：
    from arrisFarmersDelightScripts.Server.Debug import McdkAnimalsTest as T
    T.mcdk_test_animals_start()     # /summon 带出生事件生成成年、幼年各一只（鹦鹉只有成年）：鸡、猪、兔、鹦鹉在第一个玩家东边一排，
                                    # 猫、狼在西边一排、关掉 AI（不然兔子、鸡被吃掉）
    # 等约 5 秒
    T.mcdk_test_animals_collect()   # 交回结果，删掉生成的动物，主手物品换回去
0.6 秒读每只的定义栈、GetComponents 里那几个组件带没带本包的物品、规则现在会下发哪几个；0.8 秒拿本包的食物真喂（PlayerUseItemToEntity）：
成年 / 幼年各喂一次，记 PlayerFeedEntityServerEvent；野猫、鹦鹉喂到驯服（最多 12 次）；狼脚本驯服，狼和猫打掉几点血再喂看回没回血；
1.0 秒给成年鸡的 tempt 手工打一个只带外来物品（苹果）的值，1.3 秒对它 apply，1.7 秒读回：苹果和本包的种子都要在（和别的模组共存）；
2 秒让幼年长大，3.5 秒再读一遍。读不到的（死了、没了）、规则该下发却没看到本包物品的、长大后不对的都进 problems。plans 是服务端读到的定义算出的补丁。
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
PREDATORS = ("minecraft:cat", "minecraft:wolf")
GROW_UP = {"minecraft:rabbit": "grow_up"}
TAME_TRIES = 12
TEMPT = "minecraft:behavior.tempt"
FOREIGN = {"priority": 4, "speed_multiplier": 1.0, "items": ["minecraft:apple"]}     # "别的模组"打的 tempt：只有一个外来物品
_state = {"entities": {}, "results": {}, "feeds": [], "events": [], "watching": False, "player": None, "hand": None, "started": 0.0,
          "feedListened": False, "merge": None}


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


def _findAll():
    """按名字牌找生成的动物（命令放出来的当场列不出来的话晚一点再找）；猫、狼找到就关掉 AI。"""
    for entityType, age, _event, _food in CASES:
        key, tag = _key(entityType, age), "fdtest_" + _key(entityType, age).replace(":", "_")
        for entityId, info in (serverApi.GetEngineActor() or {}).items() if key not in _state["entities"] else ():
            if (info or {}).get("identifier") == entityType and compFactory.CreateName(entityId).GetName() == tag:
                _state["entities"][key] = entityId
                if entityType in PREDATORS:
                    compFactory.CreateControlAi(entityId).SetBlockControlAi(False, False)
                break


def _ours(value, entityType, component):
    """GetComponents 给的这个组件里有没有本包追加的第一个条目（整个转成文本找名字）。"""
    for name, _field, extra in ANIMAL_FOOD[entityType]:
        if name == component and extra:
            return (extra[0]["item"] if isinstance(extra[0], dict) else extra[0]) in json.dumps(value)
    return False


def _read(phase):
    for key, entityId in _state["entities"].items():
        entityType = compFactory.CreateEngineType(entityId).GetEngineTypeStr()
        if not entityType:
            _state["results"].setdefault(key, {})[phase] = {"gone": True}
            continue
        definitions = compFactory.CreateEntityDefinitions(entityId)
        stack, components = definitions.GetEntityDefinitions(), compFactory.CreateEntityEvent(entityId).GetComponents() or {}
        plan = AnimalFood.planOf(entityType)
        seen = {}
        for name, _field, _extra in ANIMAL_FOOD[entityType]:
            present = isinstance(components, dict) and name in components
            seen[name] = {"present": present, "ours": present and _ours(components[name], entityType, name)}
        _state["results"].setdefault(key, {})[phase] = {
            "stack": stack, "baby": definitions.IsBaby(), "tamed": definitions.IsTamed(), "components": seen,
            "rule": [name for name, _text in Rules.send(plan, stack)] if plan is not None else None}


def _health(entityId):
    return compFactory.CreateAttr(entityId).GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)


def _use(playerId, entityId, itemName):
    SetCarriedItem(playerId, {"newItemName": itemName, "newAuxValue": 0, "count": 64})
    return compFactory.CreateBlockInfo(playerId).PlayerUseItemToEntity(entityId)


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
            compFactory.CreateTame(entityId).SetEntityTamed(playerId, entityId)
            fed["scriptTamed"] = compFactory.CreateEntityEvent(entityId).TriggerCustomEvent(entityId, "minecraft:on_tame")
        else:
            fed["used"] = _use(playerId, entityId, food)
        _state["results"].setdefault(key, {})["feed"] = fed
    compFactory.CreateGame(levelId).AddTimer(0.6, _heal)


def _heal():
    # 狼脚本驯服之后才有主人；猫驯服了才量（原版猫回血的写法在顶层 healable，驯服与否不看）
    playerId = _state["player"]
    cause = serverApi.GetMinecraftEnum().ActorDamageCause.EntityAttack
    for key, food, damage in (("wolf:adult", "arris:ham", 4.0), ("cat:adult", "arris:cod_slice", 2.0)):
        entityId = _state["entities"].get(key)
        if entityId:
            full = _health(entityId)
            compFactory.CreateHurt(entityId).Hurt(damage, cause, None, None, False)
            hurt = _health(entityId)
            used = _use(playerId, entityId, food)
            _state["results"].setdefault(key, {})["heal"] = {"full": full, "hurt": hurt, "fed": _health(entityId), "used": used}


def _merge(step):
    """和别的模组共存：先打一个只带外来物品的 tempt（step 0），晚几拍 apply（step 1），再读回（step 2）：外来的和本包的都要在。"""
    entityId = _state["entities"].get("chicken:adult")
    if not entityId:
        return
    eventComp = compFactory.CreateEntityEvent(entityId)
    if step == 0:
        eventComp.AddActorComponent(TEMPT, json.dumps(FOREIGN))
    elif step == 1:
        AnimalFood.apply(entityId)
    else:
        text = json.dumps((eventComp.GetComponents() or {}).get(TEMPT))
        _state["merge"] = {"foreign": "apple" in text, "ours": "arris:rice" in text, "tempt": text}


def _grow():
    for entityType, age, _event, _food in CASES:
        entityId = _state["entities"].get(_key(entityType, age))
        if entityId and age == "baby":
            event = GROW_UP.get(entityType, "minecraft:ageable_grow_up")
            done = compFactory.CreateEntityEvent(entityId).TriggerCustomEvent(entityId, event)
            _state["results"].setdefault(_key(entityType, age), {})["growUp"] = {"event": event, "triggered": done}


def mcdk_test_animals_start():
    """生成、排好之后的读 / 喂 / 合并 / 长大 / 再读；约 5 秒后调 mcdk_test_animals_collect()。"""
    players = serverApi.GetPlayerList()
    if not players:
        return {"case": "animals", "ok": False, "error": "no player"}
    playerId = players[0]
    x, y, z = compFactory.CreatePos(playerId).GetFootPos()
    _state.update(entities={}, results={}, feeds=[], events=[], watching=True, player=playerId, merge=None,
                  hand=GetCarriedItem(playerId, True), started=time.time())
    if not _state["feedListened"]:
        _state["feedListened"] = True
        ListenForEvent("PlayerFeedEntityServerEvent", None, _recordFeed)
    command, summoned, rows = compFactory.CreateCommand(levelId), {}, {True: 0, False: 0}
    for entityType, age, event, _food in CASES:
        west = entityType in PREDATORS                      # 猫、狼放在西边一排：离兔子、鸡远一点
        step = rows[west] = rows[west] + 1
        posX = int(x) - 2 - 2 * step if west else int(x) + 2 + 2 * step
        summoned[_key(entityType, age)] = command.SetCommand("/summon %s %d %d %d 0 0 %s fdtest_%s" % (
            entityType, posX, int(y), int(z) + 3, event, _key(entityType, age).replace(":", "_")), playerId)
    _findAll()
    game = compFactory.CreateGame(levelId)
    for seconds, func, args in ((0.3, _findAll, ()), (0.6, _read, ("before",)), (0.8, _feed, ()), (1.0, _merge, (0,)),
                                (1.3, _merge, (1,)), (1.7, _merge, (2,)), (2.0, _grow, ()), (3.5, _read, ("after",))):
        game.AddTimer(seconds, func, *args)
    return {"case": "animals", "started": True, "summoned": summoned, "found": sorted(_state["entities"])}


def _checks(results):
    problems = ["%s 没生成出来" % _key(entityType, age) for entityType, age, _event, _food in CASES if _key(entityType, age) not in results]
    for key, result in sorted(results.items()):
        for phase in ("before", "after"):
            reading = result.get(phase) or {}
            if reading.get("gone") or not reading:
                problems.append("%s %s：读不到了（死了 / 没了）" % (key, phase))
            for name in reading.get("rule") or ():
                if not (reading.get("components") or {}).get(name, {}).get("ours"):
                    problems.append("%s %s：规则会下发 %s，GetComponents 里没看到本包的物品" % (key, phase, name))
        after = (result.get("after") or {}).get("components") or {}
        if key.endswith(":baby") and after:
            if after.get("minecraft:ageable", {}).get("present") or not after.get("minecraft:breedable", {}).get("ours"):
                problems.append("%s 长大以后：ageable 还在或 breedable 没有本包的物品" % key)
    merge = _state["merge"] or {}
    if not (merge.get("foreign") and merge.get("ours")):
        problems.append("和别的模组共存：成年鸡的 tempt 里外来的苹果和本包的种子没有都在（%r）" % (merge,))
    return problems


def mcdk_test_animals_collect():
    """交回结果（每只的读数、喂食、长大，PlayerFeedEntityServerEvent、定义事件的记录，共存那一例，服务端读到的补丁），删掉生成的动物。"""
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
    return {"case": "animals", "ok": not problems, "problems": problems, "results": _state["results"], "merge": _state["merge"],
            "feedEvents": feeds, "definitionEvents": events, "plans": plans, "seconds": round(time.time() - _state["started"], 2)}
