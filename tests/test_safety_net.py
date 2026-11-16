# -*- coding: utf-8 -*-
# runner: both
"""安全网（Server/RopeAndNet.py 的 OnFallOnSafetyNet + Shared/Rules/NetBounce.py）对照 JE 的 SafetyNetBlock（FD 1.3.4）。

JE：fallOn —— 实体潜行（isSuppressingBounce）时照常摔（super.fallOn），否则 causeFallDamage(fallDistance, 0.0F) 一点伤害没有；
updateEntityAfterFallOn —— 潜行时竖直速度清零，否则在往下掉（vy < 0）时 vy = -vy × 系数，生物（LivingEntity）0.6，其它实体 0.8。
基岩版的事件只给摔落距离，撞上去的速度用自由落体（重力 0.08、阻力 0.98）推回来。
"""
from __future__ import print_function

import sys
import types

import fakeengine
import fdtest

world = fakeengine.install()
engineModule = sys.modules[fakeengine.ENGINE_MODULE]
quMod = types.ModuleType(fdtest.SCRIPTS + ".QuModLibs.Server")
quMod.AllowCall = lambda func: func
quMod.InjectHttpPlayerId = lambda func: func
sys.modules[quMod.__name__] = quMod

world.sneakState = {}        # 玩家 id -> isSneaking() 的返回（True / False / None）
world.living = set()         # IsLiving 为真的实体
world.motions = []           # [("player" / "entity", 实体 id, 速度向量)]
engineModule.IsLiving = lambda entityId: entityId in world.living
_basePlayer = world._Player


def _player(target):
    methods = _basePlayer(target)
    methods["isSneaking"] = lambda: world.sneakState.get(target, False)
    return methods


world._Player = _player
world._ActorMotion = lambda target: {
    "SetPlayerMotion": lambda motion: world.motions.append(("player", target, motion)) or True,
    "SetMotion": lambda motion: world.motions.append(("entity", target, motion)) or True,
}

Registry = fdtest.load("Server.EventRegistry")
RopeAndNet = fdtest.load("Server.RopeAndNet")
NetBounce = fdtest.load("Shared.Rules.NetBounce")

NET = "arris:safety_net"


def _setUp():
    Registry.clearAll()
    Registry.registerHandler("OnBeforeFallOnBlockServerEvent", match=NET)(RopeAndNet.OnFallOnSafetyNet)
    world.players.clear()
    world.entities.clear()
    world.sneakState.clear()
    world.living.clear()
    world.motions[:] = []
    world.addPlayer("p1")
    world.living.add("p1")
    world.addEntity("cow", "minecraft:cow")
    world.living.add("cow")
    world.addEntity("item1", "minecraft:item")


def _land(entityId, fallDistance, blockName=NET):
    args = {"entityId": entityId, "blockX": 0, "blockY": 64, "blockZ": 0, "blockName": blockName, "fallDistance": fallDistance,
            "cancel": False}
    Registry.dispatch("OnBeforeFallOnBlockServerEvent", args, blockName)
    return args


# ---- 规则 ----

def testJavaBounceFactors():
    assert NetBounce.LIVING_FACTOR == 0.6 and NetBounce.OTHER_FACTOR == 0.8
    assert NetBounce.bounceFactor(True) == 0.6 and NetBounce.bounceFactor(False) == 0.8


def testImpactSpeedFollowsFreeFall():
    # 每刻先按当前速度走一步，再 v = (v + 0.08) × 0.98：速度 0、0.0784、0.1552、0.2305 ……，累计下落 0、0.0784、0.2336、0.4641 ……
    assert NetBounce.impactSpeed(0.0) == 0.0
    assert abs(NetBounce.impactSpeed(0.2) - 0.155232) < 1e-6            # 第 3 刻走的那一步，速度 0.155232
    assert abs(NetBounce.impactSpeed(0.3) - 0.2305) < 1e-3
    last = 0.0
    for fall in range(1, 120):
        speed = NetBounce.impactSpeed(float(fall))
        assert speed >= last and speed <= 3.92 + 1e-9                    # 越落越快，不超过末速度 3.92 格/刻
        last = speed
    assert 3.9 < NetBounce.impactSpeed(5000.0) <= 3.92                   # 末速度 0.08 × 0.98 / (1 - 0.98) = 3.92 格/刻
    assert abs(NetBounce.impactSpeed(10.0) - 3.92 * (1 - 0.98 ** 17)) < 1e-9     # 10 格：第 18 刻走完，撞上去时速度是第 17 刻末的


def testBounceSpeedIsTheImpactTimesTheFactor():
    for fall in (1.0, 3.0, 10.0, 30.0, 80.0):
        assert abs(NetBounce.bounceSpeed(fall, True) - NetBounce.impactSpeed(fall) * 0.6) < 1e-12
        assert abs(NetBounce.bounceSpeed(fall, False) - NetBounce.impactSpeed(fall) * 0.8) < 1e-12
    assert NetBounce.bounceSpeed(NetBounce.MIN_FALL, True) == 0.0       # 落地的小颠簸不弹
    assert NetBounce.bounceSpeed(0.3, False) == 0.0


# ---- 接线 ----

def testPlayerFallingOntoTheNetTakesNoDamageAndBouncesAt60Percent():
    _setUp()
    args = _land("p1", 12.0)
    assert args["cancel"] is True                                      # 引擎不再算摔落伤害
    assert world.motions == [("player", "p1", (0, NetBounce.impactSpeed(12.0) * 0.6, 0))]


def testSneakingPlayersFallAsUsual():
    _setUp()
    world.sneakState["p1"] = True
    args = _land("p1", 12.0)
    assert args["cancel"] is False and world.motions == []             # JE：isSuppressingBounce → super.fallOn


def testPlayersWhoseSneakStateCannotBeReadAreTreatedAsSneaking():
    _setUp()
    world.sneakState["p1"] = None
    assert _land("p1", 12.0)["cancel"] is False and world.motions == []


def testMobsBounceAt60PercentAndOtherEntitiesAt80Percent():
    _setUp()
    _land("cow", 20.0)
    _land("item1", 20.0)
    assert world.motions == [("entity", "cow", (0, NetBounce.impactSpeed(20.0) * 0.6, 0)),
                             ("entity", "item1", (0, NetBounce.impactSpeed(20.0) * 0.8, 0))]


def testSmallDropsAreCushionedButDoNotBounce():
    _setUp()
    args = _land("p1", 0.3)
    assert args["cancel"] is True and world.motions == []              # 没有伤害，也没有颠簸


def testOnlyTheNetIsHandled():
    _setUp()
    Registry.dispatch("OnBeforeFallOnBlockServerEvent", {"entityId": "p1", "fallDistance": 9.0, "blockName": "minecraft:stone", "cancel": False},
                      "minecraft:stone")
    assert world.motions == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
