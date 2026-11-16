# -*- coding: utf-8 -*-
# runner: both
"""站在点燃的炉灶上被烫（Server/Stove.py 的 OnStandOnStove + Shared/Rules/StoveBurn.py）对照 JE 的 AbstractStoveBlock（FD 1.3.4）。

JE burnEntitySteppingOnStove：炉灶点燃、实体碰撞盒碰到烤架区（Block.box(3, 0, 3, 13, 1, 13) 平移到炉灶上面一格）、
没潜行（isSteppingCarefully）、不防火（fireImmune）、是生物、脚上没有冰霜行者，才 hurt(STOVE_BURN, 1.0F)。
基岩版：伤害类型取最接近的 magma（对 fire_immune 的实体引擎免疫），Hurt 不带攻击者、不击退。
"""
from __future__ import print_function

import sys

import fakeengine
import fdtest

world = fakeengine.install()
engineModule = sys.modules[fakeengine.ENGINE_MODULE]
world.living = set()
world.sneakState = {}
world.boots = {}              # 实体 id -> 鞋子的附魔表
world.hurts = []              # [(实体 id, 伤害, 类型, 攻击者, 子攻击者, 击退)]
world.sizes = {}              # 实体 id -> (宽, 高)
engineModule.IsLiving = lambda entityId: entityId in world.living
_basePlayer, _baseItem = world._Player, world._Item


def _player(target):
    methods = _basePlayer(target)
    methods["isSneaking"] = lambda: world.sneakState.get(target, False)
    return methods


def _item(target):
    methods = _baseItem(target)
    methods["GetEquItemEnchant"] = lambda slot: world.boots.get(target) if slot == 3 else None
    return methods


world._Player, world._Item = _player, _item
world._CollisionBox = lambda target: {"GetSize": lambda: world.sizes.get(target, (0.6, 1.8))}
world._Hurt = lambda target: {
    "Hurt": lambda damage, cause, attacker=None, child=None, knocked=True, customTag=None:
        world.hurts.append((target, damage, cause, attacker, child, knocked)) or True}

Registry = fdtest.load("Server.EventRegistry")
Stove = fdtest.load("Server.Stove")
StoveBurn = fdtest.load("Shared.Rules.StoveBurn")
Cooking = fdtest.load("Shared.Data.Cooking")

STOVE = (3, 64, 5)


def _setUp():
    Registry.clearAll()
    Registry.registerHandler("OnStandOnBlockServerEvent", match=Cooking.StoveList)(Stove.OnStandOnStove)
    world.players.clear()
    world.entities.clear()
    world.living.clear()
    world.sneakState.clear()
    world.boots.clear()
    world.hurts[:] = []
    world.sizes.clear()
    world.addPlayer("p1", pos=(3.5, 65.0, 5.5))
    world.living.add("p1")


def _stand(entityId="p1", blockName="arris:stove"):
    args = {"entityId": entityId, "blockX": STOVE[0], "blockY": STOVE[1], "blockZ": STOVE[2], "blockName": blockName,
            "posX": 3.5, "posY": 65.0, "posZ": 5.5, "motionX": 0.0, "motionY": 0.0, "motionZ": 0.0, "cancel": False}
    Registry.dispatch("OnStandOnBlockServerEvent", args, blockName)
    return args


# ---- 规则 ----

def testGrillAreaIsTheJavaBoxOnTopOfTheStove():
    low, high = StoveBurn.grillBox(STOVE)
    assert low == (3 + 3 / 16.0, 65.0, 5 + 3 / 16.0) and high == (3 + 13 / 16.0, 65 + 1 / 16.0, 5 + 13 / 16.0)
    assert StoveBurn.DAMAGE == 1.0


def testTouchingTheGrillNeedsTheCollisionBoxToOverlapIt():
    player = (0.6, 1.8)
    assert StoveBurn.touchesGrill(STOVE, (3.5, 65.0, 5.5), *player)               # 站在正中
    assert StoveBurn.touchesGrill(STOVE, (4.1, 65.0, 5.5), *player)               # 碰盒西缘 3.8 < 3.8125，还压着烤架区
    assert not StoveBurn.touchesGrill(STOVE, (4.12, 65.0, 5.5), *player)          # 碰盒西缘 3.82 过了烤架区东沿
    assert StoveBurn.touchesGrill(STOVE, (2.9, 65.0, 5.5), *player)               # 另一侧同理（碰盒东缘 3.2 > 3.1875）
    assert not StoveBurn.touchesGrill(STOVE, (2.88, 65.0, 5.5), *player)
    assert not StoveBurn.touchesGrill(STOVE, (3.5, 65.0625, 5.5), *player)        # 跳起来离开烤架区上沿：碰盒下沿贴着，不算
    assert StoveBurn.touchesGrill(STOVE, (3.5, 65.06, 5.5), *player)
    assert not StoveBurn.touchesGrill(STOVE, (3.5, 63.0, 5.5), *player)           # 站在炉灶下面两格


def testFrostWalkerBootsAreRecognised():
    assert StoveBurn.hasFrostWalker([(25, 1)]) and StoveBurn.hasFrostWalker([(3, 2), (25, 2)])
    assert not StoveBurn.hasFrostWalker([(25, 0)]) and not StoveBurn.hasFrostWalker([(3, 4)])
    assert not StoveBurn.hasFrostWalker(None) and not StoveBurn.hasFrostWalker([])


def testEveryJavaExemptionStopsTheBurn():
    plain, frost = (lambda: False), (lambda: True)
    assert StoveBurn.burns(True, False, True, plain)
    assert not StoveBurn.burns(False, False, True, plain)      # 没碰到烤架区
    assert not StoveBurn.burns(True, True, True, plain)        # 潜行
    assert not StoveBurn.burns(True, False, False, plain)      # 不是生物
    assert not StoveBurn.burns(True, False, True, frost)       # 冰霜行者


def testBootsAreOnlyReadWhenTheOtherConditionsHold():
    reads = []
    asked = lambda: reads.append(1) or False
    assert not StoveBurn.burns(False, False, True, asked) and not StoveBurn.burns(True, True, True, asked) and not StoveBurn.burns(True, False, False, asked)
    assert reads == []
    assert StoveBurn.burns(True, False, True, asked) and reads == [1]


# ---- 接线 ----

def testStandingOnALitStoveHurtsOneHalfHeartWithoutKnockback():
    _setUp()
    _stand()
    assert world.hurts == [("p1", 1.0, "magma", None, None, False)]


def testSneakingPlayersAreSafeAndSoAreUnreadableOnes():
    _setUp()
    world.sneakState["p1"] = True
    _stand()
    world.sneakState["p1"] = None
    _stand()
    assert world.hurts == []


def testMobsBurnToo():
    _setUp()
    world.addEntity("zombie", "minecraft:zombie", pos=(3.4, 65.0, 5.6))
    world.living.add("zombie")
    world.sizes["zombie"] = (0.6, 1.95)
    _stand("zombie")
    assert world.hurts == [("zombie", 1.0, "magma", None, None, False)]


def testNonLivingEntitiesAreIgnored():
    _setUp()
    world.addEntity("item1", "minecraft:item", pos=(3.5, 65.0, 5.5))
    world.sizes["item1"] = (0.25, 0.25)
    _stand("item1")
    world.addEntity("boat", "minecraft:boat", pos=(3.5, 65.0, 5.5))
    _stand("boat")
    assert world.hurts == []


def testFrostWalkerBootsProtect():
    _setUp()
    world.boots["p1"] = [(25, 2)]
    _stand()
    assert world.hurts == []
    world.boots["p1"] = [(3, 3)]                                # 别的附魔不算
    _stand()
    assert len(world.hurts) == 1


def testStandingOnTheEdgeOutsideTheGrillIsSafe():
    _setUp()
    world.players["p1"]["pos"] = (4.2, 65.0, 5.5)
    _stand()
    assert world.hurts == []


def testOnlyLitStovesAreInTheList():
    _setUp()
    assert "arris:stove" in Cooking.StoveList and "arris:stove_extinguish" not in Cooking.StoveList
    _stand(blockName="arris:stove_extinguish")                  # 熄灭的炉灶是另一个方块，处理函数根本不会被叫到
    _stand(blockName="minecraft:stone")
    assert world.hurts == []
    Cooking.StoveList.append("downstream:stove")                # 下游往 StoveList 追加的炉灶一样会烫
    try:
        _stand(blockName="downstream:stove")
    finally:
        Cooking.StoveList.remove("downstream:stove")
    assert len(world.hurts) == 1


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
