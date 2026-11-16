# -*- coding: utf-8 -*-
# runner: both
"""狗粮 / 马饲料的喂食、马驴骡的吸引、兔子被卷心菜吸引（Server/Livestock.py + Shared/Data/Mobs.py），用假引擎驱动。

期望值抄自 JE：
- HorseFeedItem：马 / 骷髅马 / 僵尸马 / 驴 / 骡 / 羊驼（horse_feed_users），驯服的才行，回满血 + 速度 II 与跳跃提升 I 各 6000 刻；
- DogFoodItem：驯服的狼（dog_food_users），回满血 + 速度 I、力量 I、抗性 I 各 6000 刻，返还碗，创造模式不耗；
- CommonEvents.onAnimalsJoinWorld：马、驴、骡被马饲料吸引（horse_feed_tempted），兔子被卷心菜和卷心菜叶吸引。
"""
from __future__ import print_function

import json

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
Livestock = fdtest.load("Server.Livestock")
Mobs = fdtest.load("Shared.Data.Mobs")

HORSE_FEED = {"newItemName": "arris:horse_feed", "newAuxValue": 0, "count": 3}
DOG_FOOD = {"newItemName": "arris:dog_food", "newAuxValue": 0, "count": 3}


def _setUp(hand, creative=False):
    Registry.clearAll()
    Registry.registerHandler("PlayerInteractServerEvent", match=Mobs.FEED_USERS)(Livestock.OnFeedTamedAnimal)
    Registry.registerHandler("AddEntityServerEvent", match=Mobs.livestockComponents)(Livestock.InitLivestockComponents)
    world.entities.clear()
    world.players.clear()
    world.modAttr.clear()
    world.timers = []
    world.sounds[:] = []
    world.components.clear()
    world.addPlayer("p1", hand=dict(hand), creative=creative)


def _interact(victim="v1", expectedItem=None):
    hand = world.players["p1"]["hand"]
    args = {"playerId": "p1", "victimId": victim, "cancel": False, "itemDict": dict(hand)}
    Registry.dispatch("PlayerInteractServerEvent", args, hand["newItemName"])
    world.runTimers()
    return args


def _count():
    return world.players["p1"]["hand"]["count"]


# ---- 数据 ----

def testFeedUsersAreTheJeEntityTags():
    assert sorted(Mobs.FEED_USERS["arris:horse_feed"]) == sorted([
        "minecraft:horse", "minecraft:skeleton_horse", "minecraft:zombie_horse", "minecraft:donkey", "minecraft:mule",
        "minecraft:llama"])
    assert Mobs.FEED_USERS["arris:dog_food"] == ("minecraft:wolf",)


def testFeedEffectsAreFiveMinutes():
    # JE 6000 刻 = 300 秒；速度 II 的等级值是 1
    assert Mobs.FEED_EFFECTS["arris:horse_feed"] == (("speed", 300, 1), ("jump_boost", 300, 0))
    assert Mobs.FEED_EFFECTS["arris:dog_food"] == (("speed", 300, 0), ("strength", 300, 0), ("resistance", 300, 0))


def _json(text):
    return json.loads(text)


def testTemptComponentsKeepTheVanillaItemsAndAddOurs():
    vanillaHorse = ["golden_apple", "appleEnchanted", "golden_carrot"]
    for table in (Mobs.horseComponentsDict, Mobs.donkeyComponentsDict, Mobs.muleComponentsDict):
        tempt = _json(table["minecraft:behavior.tempt"])
        assert tempt["priority"] == 5 and tempt["speed_multiplier"] == 1.2
        assert tempt["items"] == ["arris:horse_feed"] + vanillaHorse
    rabbit = _json(Mobs.rabbitComponentsDict["minecraft:behavior.tempt"])
    assert rabbit["priority"] == 3 and rabbit["speed_multiplier"] == 1
    assert rabbit["items"] == ["golden_carrot", "carrot", "dandelion", "arris:cabbage", "arris:cabbage_leaf"]
    beg = _json(Mobs.wolfComponentsDict["minecraft:behavior.beg"])
    assert beg["items"][0] == "arris:dog_food" and "bone" in beg["items"] and len(beg["items"]) == 13


def testLinkageContractTablesStayNonEmptyJsonStrings():
    # linkage 契约：obtain("horseComponentsDict") / ("wolfComponentsDict") 是同一批活字典，值是 JSON 串，下游可以往里加
    for table in (Mobs.horseComponentsDict, Mobs.wolfComponentsDict):
        assert table
        for name, value in table.items():
            assert name.startswith("minecraft:") and isinstance(_json(value), dict)
    assert Mobs.livestockComponents["minecraft:horse"] is Mobs.horseComponentsDict
    assert Mobs.livestockComponents["minecraft:wolf"] is Mobs.wolfComponentsDict


# ---- 喂食 ----

def testTamedHorseIsHealedBuffedAndTheItemEaten():
    _setUp(HORSE_FEED)
    world.addEntity("v1", "minecraft:horse", tamed=True, health=3.0, maxHealth=30.0)
    args = _interact()
    horse = world.entities["v1"]
    assert args["cancel"] is True
    assert horse["health"] == 30.0
    assert horse["effects"] == [("speed", 300, 1), ("jump_boost", 300, 0)]
    assert _count() == 2 and world.players["p1"]["given"] == []
    assert [name for name, pos in world.sounds] == ["mob.horse.eat"]


def testEveryJeHorseFeedUserAcceptsTheFeedAndTheTraderLlamaDoesNot():
    for entityType in Mobs.FEED_USERS["arris:horse_feed"]:
        _setUp(HORSE_FEED)
        world.addEntity("v1", entityType, tamed=True, health=1.0)
        assert _interact()["cancel"] is True and _count() == 2, entityType
    for entityType in ("minecraft:trader_llama", "minecraft:wolf", "minecraft:cow", "minecraft:pig"):
        _setUp(HORSE_FEED)
        world.addEntity("v1", entityType, tamed=True, health=1.0)
        args = _interact()
        assert args["cancel"] is False and _count() == 3 and world.entities["v1"]["effects"] == [], entityType


def testWildAnimalsAreLeftAlone():
    for hand, entityType in ((HORSE_FEED, "minecraft:horse"), (DOG_FOOD, "minecraft:wolf")):
        _setUp(hand)
        world.addEntity("v1", entityType, tamed=False, health=2.0)
        args = _interact()
        assert args["cancel"] is False and _count() == 3
        assert world.entities["v1"]["health"] == 2.0 and world.entities["v1"]["effects"] == []


def testDogFoodHealsTamedWolfGivesThreeEffectsAndReturnsTheBowl():
    _setUp(DOG_FOOD)
    world.addEntity("v1", "minecraft:wolf", tamed=True, health=2.0, maxHealth=40.0)
    args = _interact()
    wolf = world.entities["v1"]
    assert args["cancel"] is True and wolf["health"] == 40.0
    assert wolf["effects"] == [("speed", 300, 0), ("strength", 300, 0), ("resistance", 300, 0)]
    assert _count() == 2
    assert [(item["itemName"], item["count"]) for item in world.players["p1"]["given"]] == [("minecraft:bowl", 1)]
    assert [name for name, pos in world.sounds] == ["random.eat"]


def testCreativePlayersKeepTheItemAndGetNoBowl():
    _setUp(DOG_FOOD, creative=True)
    world.addEntity("v1", "minecraft:wolf", tamed=True, health=2.0)
    _interact()
    assert world.entities["v1"]["health"] == world.entities["v1"]["maxHealth"] and len(world.entities["v1"]["effects"]) == 3
    assert _count() == 3 and world.players["p1"]["given"] == []


def testHorseFeedDoesNotReturnABowl():
    _setUp(HORSE_FEED)
    world.addEntity("v1", "minecraft:donkey", tamed=True)
    _interact()
    assert world.players["p1"]["given"] == []


def testHoldingTheClickFeedsOnlyOncePerCooldownButStillCancelsTheDefault():
    _setUp(HORSE_FEED)
    world.addEntity("v1", "minecraft:horse", tamed=True, health=1.0)
    hand = world.players["p1"]["hand"]
    first = {"playerId": "p1", "victimId": "v1", "cancel": False, "itemDict": dict(hand)}
    second = {"playerId": "p1", "victimId": "v1", "cancel": False, "itemDict": dict(hand)}
    Registry.dispatch("PlayerInteractServerEvent", first, "arris:horse_feed")
    Registry.dispatch("PlayerInteractServerEvent", second, "arris:horse_feed")
    assert first["cancel"] is True and second["cancel"] is True
    assert _count() == 2 and len(world.entities["v1"]["effects"]) == 2
    world.runTimers()
    Registry.dispatch("PlayerInteractServerEvent", dict(first, cancel=False), "arris:horse_feed")
    assert _count() == 1


def testOwnerIsTheFallbackWhenTheEngineCannotTellIfTamed():
    _setUp(HORSE_FEED)
    world.addEntity("v1", "minecraft:horse", tamed=None, owner="p9", health=1.0)
    assert _interact()["cancel"] is True
    for owner in (None, "", "-1"):
        _setUp(HORSE_FEED)
        world.addEntity("v1", "minecraft:horse", tamed=None, owner=owner, health=1.0)
        assert _interact()["cancel"] is False, repr(owner)


def testOtherItemsAreNotDispatched():
    _setUp({"newItemName": "minecraft:wheat", "newAuxValue": 0, "count": 1})
    world.addEntity("v1", "minecraft:horse", tamed=True, health=1.0)
    assert _interact()["cancel"] is False and world.entities["v1"]["effects"] == []


# ---- 吸引组件 ----

def _addEntity(entityType):
    args = {"id": "e1", "engineTypeStr": entityType}
    Registry.dispatch("AddEntityServerEvent", args, entityType)
    return world.components.get("e1", {})


def testComponentsAreAddedToTheJeTemptedAnimals():
    _setUp(HORSE_FEED)
    for entityType in ("minecraft:horse", "minecraft:donkey", "minecraft:mule"):
        world.components.clear()
        assert "arris:horse_feed" in _json(_addEntity(entityType)["minecraft:behavior.tempt"])["items"], entityType
    world.components.clear()
    assert "arris:cabbage" in _json(_addEntity("minecraft:rabbit")["minecraft:behavior.tempt"])["items"]
    world.components.clear()
    assert "arris:dog_food" in _json(_addEntity("minecraft:wolf")["minecraft:behavior.beg"])["items"]
    for entityType in ("minecraft:llama", "minecraft:cow", "minecraft:cat"):
        world.components.clear()
        assert _addEntity(entityType) == {}, entityType


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
