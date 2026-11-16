# -*- coding: utf-8 -*-
# runner: both
"""刀与洋葱的战利品事件（Server/Tools.py 的 OnMobLoot），用假引擎驱动（tests/fakeengine.py）。"""
from __future__ import print_function

import fakeengine
import fdtest

world = fakeengine.install()
Registry = fdtest.load("Server.EventRegistry")
Tools = fdtest.load("Server.Tools")
MobLoot = Tools.MobLoot

KNIFE = {"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1}
ALWAYS = lambda percent: True   # noqa: E731
_rolls = []


def _recording(percent):
    _rolls.append(percent)
    return True


def _setUp(hand=KNIFE, victimType="minecraft:cow", **victimFields):
    Registry.clearAll()
    Registry.registerHandler("EntityDieLoottableServerEvent")(Tools.OnMobLoot)
    del _rolls[:]
    world.entities.clear()
    world.players.clear()
    world.addPlayer("p1", hand=hand)
    world.addEntity("victim", victimType, **victimFields)


def _die(attacker="p1", itemList=None):
    args = {"dieEntityId": "victim", "attacker": attacker, "itemList": itemList if itemList is not None else [
        {"newItemName": "minecraft:beef", "newAuxValue": 0, "count": 2}], "dirty": False}
    Registry.dispatch("EntityDieLoottableServerEvent", args)
    return args


def _names(args):
    return [(item["newItemName"], item["count"]) for item in args["itemList"]]


def _withRoll(roll):
    original = (MobLoot.knifeDrops, MobLoot.onionDrops)
    MobLoot.knifeDrops = lambda entity, burning, looting: original[0](entity, burning, looting, roll)
    MobLoot.onionDrops = lambda entity, looting: original[1](entity, looting, roll)
    return original


def _restore(original):
    MobLoot.knifeDrops, MobLoot.onionDrops = original


def testKnifeKillAddsLeatherAndLeavesVanillaDropsAlone():
    _setUp()
    args = _die()
    assert _names(args) == [("minecraft:beef", 2), ("minecraft:leather", 1)], _names(args)
    assert args["dirty"] is True


def testNoKnifeNoExtraDropsAndNoDirtyFlag():
    for hand in (None, {"newItemName": "minecraft:iron_sword", "newAuxValue": 0, "count": 1}):
        _setUp(hand=hand)
        args = _die()
        assert _names(args) == [("minecraft:beef", 2)] and args["dirty"] is False


def testBurningPigDropsSmokedHamOtherwiseHam():
    original = _withRoll(ALWAYS)
    try:
        _setUp(victimType="minecraft:pig", fire=True)
        assert ("arris:smoked_ham", 1) in _names(_die())
        _setUp(victimType="minecraft:pig", fire=False)
        assert ("arris:ham", 1) in _names(_die())
        _setUp(victimType="minecraft:hoglin", fire=False)
        assert ("arris:ham", 1) in _names(_die())
    finally:
        _restore(original)


def testLootingLevelOfTheKnifeRaisesTheHamChance():
    original = _withRoll(_recording)
    try:
        knife = dict(KNIFE, enchantData=[(14, 2)])
        _setUp(hand=knife, victimType="minecraft:pig")
        _die()
        assert _rolls == [70], _rolls
    finally:
        _restore(original)


def testOnionFromZombieWithAnyWeapon():
    original = _withRoll(ALWAYS)
    try:
        _setUp(hand=None, victimType="minecraft:zombie")
        assert ("arris:onion", 1) in _names(_die())
        _setUp(hand={"newItemName": "minecraft:iron_sword", "newAuxValue": 0, "count": 1}, victimType="minecraft:evocation_illager")
        assert ("arris:onion", 1) in _names(_die())
        _setUp(hand=KNIFE, victimType="minecraft:husk")
        assert _names(_die()).count(("arris:onion", 1)) == 1
    finally:
        _restore(original)


def testOnlyPlayersCountAsKillers():
    original = _withRoll(ALWAYS)
    try:
        _setUp(victimType="minecraft:zombie")
        world.addEntity("skeleton", "minecraft:skeleton")
        for attacker in ("skeleton", None, "", "-1"):
            args = _die(attacker=attacker)
            assert args["dirty"] is False, attacker
    finally:
        _restore(original)


def testArrowShotByAPlayerCountsForTheOnion():
    original = _withRoll(ALWAYS)
    try:
        _setUp(hand={"newItemName": "minecraft:bow", "newAuxValue": 0, "count": 1}, victimType="minecraft:pillager")
        world.addEntity("arrow1", "minecraft:arrow", owner="p1")
        assert ("arris:onion", 1) in _names(_die(attacker="arrow1"))
        world.addEntity("arrow2", "minecraft:arrow", owner="skeleton")
        world.addEntity("skeleton", "minecraft:skeleton")
        assert _die(attacker="arrow2")["dirty"] is False
    finally:
        _restore(original)


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
