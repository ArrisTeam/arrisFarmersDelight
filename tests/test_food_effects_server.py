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


class FakeFactory(object):
    def __init__(self):
        self.effects = {}

    def CreateEffect(self, entityId):
        return self.effects.setdefault(entityId, FakeEffects())


FACTORY = FakeFactory()
_engine = types.ModuleType("arrisFarmersDelightScripts.Server.Helpers.Engine")
_engine.compFactory = FACTORY
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


def testComfortStillBlocksHarmfulEffects():
    # 舒适虽然没有食物再给了，效果和处理仍在（别的包 / 指令可以给）
    comp = _player("arris:comfort")
    Registry.dispatch("AddEffectServerEvent", {"entityId": PLAYER, "effectName": "poison"})
    assert comp.log == [("remove", "poison")]
    comp = _player("speed")
    Registry.dispatch("AddEffectServerEvent", {"entityId": PLAYER, "effectName": "poison"})
    assert comp.log == [], "没有舒适不清除"
    comp = _player("poison", "speed", "hunger")
    Registry.dispatch("AddEffectServerEvent", {"entityId": PLAYER, "effectName": "arris:comfort"})
    assert sorted(entry[1] for entry in comp.log) == ["hunger", "poison"], "获得舒适时清掉身上的有害效果"


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
