# -*- coding: utf-8 -*-
# runner: both
"""烂番茄（Server/Tools.py 的 OnThrowRottenTomato / OnRottenTomatoHit + Shared/Rules/RottenTomato.py + bp/entities/rotten_tomato.json）
对照 JE 的 RottenTomatoItem / RottenTomatoEntity（FD 1.3.4）：扔的时候 random.bow（JE 的雪球投掷声）音量 0.5、音调 0.4/(r×0.4+0.8)；
砸中 mob.slime.attack（JE 的史莱姆攻击声）音量 1、音调 (r−r)×0.2+1，砸中实体两声、方块一声；飞行照基岩原版雪球（power 1.5、gravity 0.03）。
"""
from __future__ import print_function

import io
import json
import os
import re

import fakeengine
import fdtest

world = fakeengine.install()
thrown = []
world._Projectile = lambda target: {"CreateProjectileEntity": lambda spawnerId, name, param=None: thrown.append((spawnerId, name)) or "p9"}

Registry = fdtest.load("Server.EventRegistry")
Tools = fdtest.load("Server.Tools")
RottenTomato = fdtest.load("Shared.Rules.RottenTomato")

ITEM = "arris:rotten_tomato"
JE_ITEM = os.path.join(fdtest.ROOT, ".refs", "FarmersDelight", "src", "main", "java", "vectorwing", "farmersdelight", "common",
                       "item", "RottenTomatoItem.java")


def _json(path):
    with io.open(path, encoding="utf-8-sig") as handle:
        return json.loads(re.sub(r"//[^\n]*", "", handle.read()))


# ---- 规则 ----

def testThrowAndHitPitchesAreJavas():
    assert abs(RottenTomato.throwPitch(0.0) - 0.5) < 1e-9
    assert abs(RottenTomato.throwPitch(1.0) - 1.0 / 3) < 1e-9
    assert RottenTomato.hitPitch(0.5, 0.5) == 1.0
    assert abs(RottenTomato.hitPitch(1.0, 0.0) - 1.2) < 1e-9 and abs(RottenTomato.hitPitch(0.0, 1.0) - 0.8) < 1e-9
    assert RottenTomato.hitSounds("ENTITY") == 2 and RottenTomato.hitSounds("BLOCK") == 1


def testItFliesLikeTheVanillaSnowball():
    projectile = _json(os.path.join(fdtest.BP, "entities", "rotten_tomato.json"))["minecraft:entity"]["components"]["minecraft:projectile"]
    assert projectile["power"] == 1.5 and projectile["gravity"] == 0.03
    rp = fdtest.vanilla()
    if rp is None:
        print("跳过和原版雪球的比对：本机没有游戏目录")
        return
    snowball = _json(rp.replace("/resource_packs/", "/behavior_packs/") + "/entities/snowball.json")
    vanilla = snowball["minecraft:entity"]["components"]["minecraft:projectile"]
    for key in ("power", "gravity", "anchor", "offset", "angle_offset"):
        assert projectile[key] == vanilla[key], (key, projectile.get(key), vanilla.get(key))
    sounds = _json(rp + "/sounds/sound_definitions.json")
    sounds = sounds.get("sound_definitions", sounds)
    assert sounds[RottenTomato.THROW_SOUND]["sounds"] == ["sounds/random/bow"]        # JE entity.snowball.throw 的采样
    assert sounds[RottenTomato.HIT_SOUND]["sounds"] == ["sounds/mob/slime/attack1", "sounds/mob/slime/attack2"]


def testJavaThrowsAtSnowballSpeed():
    if not os.path.isfile(JE_ITEM):
        print("跳过：没有 JE 的源码")
        return
    source = io.open(JE_ITEM, encoding="utf-8").read()
    assert "shootFromRotation(player, player.getXRot(), player.getYRot(), 0.0F, 1.5F, 1.0F)" in source
    assert "0.5F, 0.4F / (level.random.nextFloat() * 0.4F + 0.8F)" in source


# ---- 服务端 ----

def _setUp():
    Registry.clearAll()
    Registry.registerHandler("ItemUseAfterServerEvent", match=ITEM)(Tools.OnThrowRottenTomato)
    Registry.registerHandler("ProjectileDoHitEffectEvent")(Tools.OnRottenTomatoHit)
    world.players.clear()
    world.entities.clear()
    world.sounds[:] = []
    world.soundArgs[:] = []
    thrown[:] = []
    world.addPlayer("p1", hand={"newItemName": ITEM, "newAuxValue": 0, "count": 3}, pos=(1.5, 64.0, 2.5))


def testThrowingPlaysTheSnowballThrowAtTheFeet():
    _setUp()
    args = {"entityId": "p1", "itemDict": dict(world.players["p1"]["hand"])}
    Registry.dispatch("ItemUseAfterServerEvent", args, ITEM)
    assert thrown == [("p1", ITEM)] and world.players["p1"]["hand"]["count"] == 2
    assert world.sounds == [("random.bow", (1.5, 64.0, 2.5))]
    assert world.soundArgs[0]["volume"] == 0.5 and 1.0 / 3 - 1e-9 <= world.soundArgs[0]["pitch"] <= 0.5


def _hit(projectileId, kind):
    args = {"id": projectileId, "hitTargetType": kind, "targetId": "m1", "x": 3.0, "y": 65.0, "z": 4.0, "srcId": "p1"}
    Registry.dispatch("ProjectileDoHitEffectEvent", args)


def testHittingAnEntitySoundsTwiceAndABlockOnce():
    _setUp()
    world.addEntity("t1", ITEM)
    world.addEntity("a1", "minecraft:arrow")
    _hit("t1", "ENTITY")
    assert world.sounds == [("mob.slime.attack", (3.0, 65.0, 4.0))] * 2
    assert all(data["volume"] == 1.0 and 0.8 - 1e-9 <= data["pitch"] <= 1.2 + 1e-9 for data in world.soundArgs)
    world.sounds[:] = []
    _hit("t1", "BLOCK")
    assert len(world.sounds) == 1
    world.sounds[:] = []
    _hit("a1", "ENTITY")                                       # 别的抛射物不管
    assert world.sounds == []


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
