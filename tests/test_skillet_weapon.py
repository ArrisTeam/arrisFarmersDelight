# -*- coding: utf-8 -*-
# runner: both
"""煎锅当武器（Server/SkilletItem.py 的耐久、Server/Tools.py 的打人音效）对 JE 的 SkilletItem，用假引擎驱动。

JE：hurtEnemy / mineBlock 磨损 1 点（基岩版自定义武器打一下磨损 2 点，这里改回 1）；
playSkilletAttackSound：攻击冷却够 80% 响 attack_strong，否则 attack_weak（基岩版没有攻击冷却，按距上次挥煎锅的时间挑）。
"""
from __future__ import print_function

import fakeengine
import fdtest
import skilletkit

world = fakeengine.install()
skilletkit.extend(world)
Registry = fdtest.load("Server.EventRegistry")
SkilletItem = fdtest.load("Server.SkilletItem")
Tools = fdtest.load("Server.Tools")

SKILLET = {"newItemName": "arris:skillet_item", "newAuxValue": 0, "count": 1, "durability": 250}
clock = [500.0]


class _Time(object):
    @staticmethod
    def time():
        return clock[0]


Tools.time = _Time


def _durability(name, before, after, canChange=True):
    Registry.clearAll()
    Registry.registerHandler("ItemDurabilityChangedServerEvent", match="arris:skillet_item")(SkilletItem.OnSkilletDurability)
    args = {"entityId": "p1", "itemDict": {"newItemName": name, "newAuxValue": 0, "count": 1}, "durabilityBefore": before,
            "durability": after, "canChange": canChange}
    Registry.dispatch("ItemDurabilityChangedServerEvent", args, name)
    return args["durability"]


def testEngineWearOfTwoPointsBecomesOne():
    assert _durability("arris:skillet_item", 250, 248) == 249
    assert _durability("arris:skillet_item", 249, 249) == 249            # 引擎本来就磨损 1 点
    assert _durability("arris:skillet_item", 100, 180) == 180            # 修复（铁砧、经验修补）不动


def testLastHitStillBreaksTheSkillet():
    # 基岩版损伤 > 最大耐久才坏：剩 0 时再打一下（引擎写 -2）仍然是坏（-1）
    assert _durability("arris:skillet_item", 0, -2) == -1
    assert _durability("arris:skillet_item", 1, -1) == 0


def testWearIsLeftAloneWhenTheEngineSaysItCannotBeChanged():
    assert _durability("arris:skillet_item", 250, 248, canChange=False) == 248


def testOtherItemsAreNotTouched():
    assert _durability("arris:iron_knife", 250, 248) == 248


def _swing(hand=SKILLET):
    Registry.clearAll()
    Registry.registerHandler("PlayerAttackEntityEvent")(Tools.OnSkilletAttack)
    world.reset()
    world.addPlayer("p1", hand=dict(hand) if hand else None)


def testHitSoundsAreStrongWhenRestedAndWeakWhenSpammed():
    Tools._swings = Tools.AttackClock()
    _swing()
    clock[0] = 500.0
    Registry.dispatch("PlayerAttackEntityEvent", {"playerId": "p1"})
    clock[0] = 500.4
    Registry.dispatch("PlayerAttackEntityEvent", {"playerId": "p1"})
    clock[0] = 501.4                                                       # 离上一次 1 秒：攻击速度 0.9 次 / 秒，够 80%
    Registry.dispatch("PlayerAttackEntityEvent", {"playerId": "p1"})
    assert [name for name, pos in world.sounds] == ["ambient.skillet.attack_strong", "ambient.skillet.attack_weak", "ambient.skillet.attack_strong"]
    assert all(pos == (0.5, 64.0, 0.5) for name, pos in world.sounds)


def testOtherWeaponsMakeNoSkilletSound():
    Tools._swings = Tools.AttackClock()
    _swing(hand={"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1})
    Registry.dispatch("PlayerAttackEntityEvent", {"playerId": "p1"})
    _swing(hand=None)
    Registry.dispatch("PlayerAttackEntityEvent", {"playerId": "p1"})
    assert world.sounds == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
