# -*- coding: utf-8 -*-
# runner: both
"""服务端 FoodEffects（Server/FoodEffects.py）接到事件上的行为：滋养、舒适、死亡清理，以及不再有的"受伤清除"。

Server 模块要在引擎里才导得进来（Helpers/Engine.py 取 compFactory），这里先把一个假的 Engine 模块塞进 sys.modules，
再像 ModServer 那样经 EventRegistry.dispatch 触发事件。
"""
from __future__ import print_function

import sys
import types

import fdtest


class FakeEffects(object):
    """一个实体身上的效果（CreateEffect 的组件）。"""

    def __init__(self):
        self.active = []
        self.log = []

    def GetAllEffects(self):
        return [{"effectName": name, "duration": 100, "amplifier": 0} for name in self.active] or None

    def HasEffect(self, name):
        return name in self.active

    def AddEffectToEntity(self, name, duration, amplifier, showParticles):
        self.log.append(("add", name, duration, amplifier, showParticles))
        self.active.append(name)
        return True

    def RemoveEffectFromEntity(self, name):
        self.log.append(("remove", name))
        if name in self.active:
            self.active.remove(name)
        return True


class FakeAttr(object):
    """一个实体的引擎属性（CreateAttr 的组件）：只做生命值和着火。"""

    def __init__(self):
        self.health = 20.0
        self.top = 20.0
        self.saturation = 0.0
        self.log = []

    def GetAttrValue(self, attrType):
        return self.saturation if attrType == SATURATION else self.health

    def GetAttrMaxValue(self, attrType):
        return self.top

    def SetAttrValue(self, attrType, value, setDefault=1):
        self.log.append(("set", attrType, value, setDefault))
        self.health = value
        return True

    def SetEntityOnFire(self, seconds, burnDamage=1):
        self.log.append(("fire", seconds))
        return True


class FakeGame(object):
    def __init__(self):
        self.timers = []

    def AddRepeatedTimer(self, seconds, func, *params):
        self.timers.append((seconds, func))
        return len(self.timers)


class FakeFactory(object):
    def __init__(self):
        self.effects = {}
        self.attrs = {}
        self.game = FakeGame()

    def CreateGame(self, levelId):
        return self.game

    def CreateEffect(self, entityId):
        return self.effects.setdefault(entityId, FakeEffects())

    def CreateAttr(self, entityId):
        return self.attrs.setdefault(entityId, FakeAttr())


HEALTH = 7  # 假的 AttrType.HEALTH，只要前后一致
SATURATION = 5


class FakeServerApi(object):
    class _Enum(object):
        class AttrType(object):
            HEALTH = HEALTH
            SATURATION = SATURATION

    def GetMinecraftEnum(self):
        return self._Enum

    def GetPlayerList(self):
        return [PLAYER]


FACTORY = FakeFactory()
_engine = types.ModuleType("arrisFarmersDelightScripts.Server.Helpers.Engine")
_engine.compFactory = FACTORY
_engine.levelId = "level"
_engine.serverApi = FakeServerApi()
sys.modules[_engine.__name__] = _engine

Registry = fdtest.load("Server.EventRegistry")
FoodEffects = fdtest.load("Server.FoodEffects")

PLAYER = "player-1"
MODULE = "arrisFarmersDelightScripts.Server.FoodEffects"


def _player(*effects):
    comp = FACTORY.CreateEffect(PLAYER)
    comp.active[:] = list(effects)
    del comp.log[:]
    return comp


def _eat(itemName):
    # ModServer 把物品名当匹配键传给 dispatch
    args = {"playerId": PLAYER, "itemDict": {"newItemName": itemName, "newAuxValue": 0, "count": 1}, "hunger": 0, "nutrition": 0.0}
    Registry.dispatch("PlayerEatFoodServerEvent", args, itemName)


def testHotCocoaClearsOneRandomHarmfulEffect():
    removed = set()
    for _ in range(80):
        comp = _player("speed", "poison", "weakness", "arris:nourishment")
        _eat("arris:hot_cocoa")
        assert len(comp.log) == 1 and comp.log[0][0] == "remove" and comp.log[0][1] in ("poison", "weakness"), comp.log
        removed.add(comp.log[0][1])
    assert removed == set(["poison", "weakness"]), "不该总是清第一个: %r" % removed


def testMilkBottleClearsOneEffect():
    comp = _player("speed", "poison")
    _eat("arris:milk_bottle")
    assert len(comp.log) == 1 and comp.log[0][1] in ("speed", "poison")
    comp = _player()
    _eat("arris:milk_bottle")
    assert comp.log == []


def testVanillaSoupsGrantNourishment():
    comp = _player("speed")
    _eat("minecraft:mushroom_stew")
    assert comp.log == [("add", "arris:nourishment", 180, 0, False)]
    comp = _player()
    _eat("minecraft:beetroot_soup")
    assert comp.log == [("add", "arris:nourishment", 180, 0, False)], "身上没有任何效果也要给"
    comp = _player()
    _eat("minecraft:rabbit_stew")
    assert sorted(comp.log) == sorted([("add", "arris:nourishment", 300, 0, False), ("add", "jump_boost", 10, 1, True)])


def _attr(health, top=20.0):
    attr = FACTORY.CreateAttr(PLAYER)
    attr.health, attr.top = health, top
    del attr.log[:]
    return attr


def testMelonJuiceHealsTwoPointsAndNeverPastTheMax():
    attr = _attr(10.0)
    comp = _player("speed")
    _eat("arris:melon_juice")
    assert attr.log == [("set", HEALTH, 12.0, 0)], "回 2 点；第三个参数 0 = 不改属性默认值"
    assert comp.log == [], "不再靠瞬间治疗效果"
    attr = _attr(19.0)
    _eat("arris:melon_juice")
    assert attr.log == [("set", HEALTH, 20.0, 0)], "不超过上限"
    attr = _attr(20.0)
    _eat("arris:melon_juice")
    assert attr.log == [], "满血不用设置"
    attr = _attr(25.0, 30.0)
    _eat("arris:melon_juice")
    assert attr.log == [("set", HEALTH, 27.0, 0)], "生命上限被别的包改过也照回 2 点"


def testMelonPopsicleExtinguishesTheEater():
    attr = _attr(20.0)
    comp = _player()
    _eat("arris:melon_popsicle")
    assert attr.log == [("fire", 0)] and comp.log == [], "秒数 <= 0 即灭火；不再给抗火"


def testOrdinaryFoodDoesNotTouchEffects():
    comp = _player("poison", "speed")
    attr = _attr(10.0)
    _eat("minecraft:apple")
    _eat("arris:cooked_rice")
    assert comp.log == [] and attr.log == []


def testNourishmentCancelsHungerLossButNotEating():
    _player("arris:nourishment")
    loss = {"playerId": PLAYER, "hunger": 15, "hungerBefore": 16}
    Registry.dispatch("PlayerHungerChangeServerEvent", loss)
    assert loss.get("cancel") is True
    meal = {"playerId": PLAYER, "hunger": 20, "hungerBefore": 14}
    Registry.dispatch("PlayerHungerChangeServerEvent", meal)
    assert not meal.get("cancel"), "吃东西涨饥饿值不拦"
    _player("minecraft:speed")
    plain = {"playerId": PLAYER, "hunger": 15, "hungerBefore": 16}
    Registry.dispatch("PlayerHungerChangeServerEvent", plain)
    assert not plain.get("cancel"), "没有滋养不拦"


def testComfortNoLongerBlocksHarmfulEffects():
    # JE 1.3.4 的舒适不挡负面效果（旧版这里有个 AddEffectServerEvent 处理函数，已经去掉）
    assert [name for module, name in Registry.handlerNames("AddEffectServerEvent") if module == MODULE] == []
    comp = _player("arris:comfort")
    Registry.dispatch("AddEffectServerEvent", {"entityId": PLAYER, "effectName": "poison"})
    assert comp.log == []


def _comfortCase(effects, health=15.0, saturation=0.0, top=20.0):
    _player(*effects)
    attr = FACTORY.CreateAttr(PLAYER)
    attr.health, attr.saturation, attr.top = health, saturation, top
    del attr.log[:]
    FoodEffects.comfortTick()
    return attr.health


def testComfortHealsOnePointWhenNothingElseWould():
    # JE ComfortEffect：每 80 刻，没有生命恢复、饱和度用完了、没满血时回 1 点
    assert _comfortCase(["arris:comfort"]) == 16.0
    assert _comfortCase(["arris:comfort", "regeneration"]) == 15.0
    assert _comfortCase(["arris:comfort"], saturation=2.0) == 15.0
    assert _comfortCase(["arris:comfort"], health=20.0) == 20.0
    assert _comfortCase(["arris:comfort"], health=19.5) == 20.0          # 不超过上限
    assert _comfortCase([]) == 15.0


def testTheComfortTimerStartsOnceEveryFourSeconds():
    Registry.dispatch("ClientLoadAddonsFinishServerEvent", {"playerId": PLAYER})
    Registry.dispatch("ClientLoadAddonsFinishServerEvent", {"playerId": PLAYER})
    assert [seconds for seconds, _func in FACTORY.game.timers] == [4.0]


def testDeathClearsBothEffects():
    comp = _player("arris:comfort", "arris:nourishment")
    Registry.dispatch("PlayerDieEvent", {"id": PLAYER})
    assert sorted(entry[1] for entry in comp.log) == ["arris:comfort", "arris:nourishment"]


def testDamageDoesNotClearNourishmentOrComfort():
    # JE 里受伤不会让滋养 / 舒适消失（旧版这里有个 DamageEvent 处理函数，已经去掉）
    comp = _player("arris:comfort", "arris:nourishment")
    assert (MODULE, "OnPlayerDamageRemoveEffects") not in Registry.handlerNames("DamageEvent")
    Registry.dispatch("DamageEvent", {"entityId": PLAYER, "srcId": "zombie-1", "damage": 6})
    assert comp.log == [] and comp.active == ["arris:comfort", "arris:nourishment"]


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
