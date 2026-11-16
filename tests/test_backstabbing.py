# -*- coding: utf-8 -*-
# runner: both
"""背刺魔咒：纯规则（Shared/Rules/Backstabbing.py）和服务端的伤害处理（Server/Backstabbing.py，假引擎驱动）。

数值照 JE 的 BackstabbingEnchantment：来袭方向在水平面上的分量和目标视线的点积 < -0.5 算背后，伤害乘 级 * 0.2 + 1.2。
"""
from __future__ import print_function

import io
import json
import os

import fakeengine
import fdtest

world = fakeengine.install()
Rules = fdtest.load("Shared.Rules.Backstabbing")
Registry = fdtest.load("Server.EventRegistry")
fdtest.load("Server.Backstabbing")

ZOMBIE, PLAYER, ARROW = "zombie", "p1", "arrow"


def _knife(level):
    enchants = [("arris:backstabbing", level)] if level else []
    return {"newItemName": "arris:iron_knife", "newAuxValue": 0, "count": 1, "modEnchantData": enchants}


def _hit(playerPos, level, yaw=0.0, damage=5.0, projectilePos=None, attacker=PLAYER):
    world.players.clear()
    world.entities.clear()
    world.sounds[:] = []
    world.addPlayer(PLAYER, hand=_knife(level), pos=playerPos)
    world.addEntity(ZOMBIE, "minecraft:zombie", pos=(0.5, 64.0, 0.5), rot=(0.0, yaw))
    world.addEntity("wolf", "minecraft:wolf", pos=playerPos)
    args = {"srcId": attacker, "entityId": ZOMBIE, "damage": damage, "projectileId": "", "cause": "entity_attack",
            "knock": True, "ignite": False}
    if projectilePos is not None:
        world.addEntity(ARROW, "minecraft:arrow", pos=projectilePos)
        args["projectileId"] = ARROW
    Registry.dispatch("DamageEvent", args)
    return args["damage"]


def testTheEnchantLevelComesFromTheItem():
    assert Rules.levelOf(_knife(2)) == 2 and Rules.levelOf(_knife(0)) == 0
    assert Rules.levelOf(None) == 0 and Rules.levelOf({"modEnchantData": [("other:enchant", 3)]}) == 0
    assert Rules.levelOf({"modEnchantData": [["arris:backstabbing", 9]]}) == Rules.MAX_LEVEL == 3


def testLookFollowsYawAndPitch():
    def close(a, b):
        return all(abs(x - y) < 1e-6 for x, y in zip(a, b))
    assert close(Rules.lookOf((0.0, 0.0)), (0.0, 0.0, 1.0)), "偏航 0 朝南"
    assert close(Rules.lookOf((0.0, 90.0)), (-1.0, 0.0, 0.0)), "偏航 90 朝西"
    assert close(Rules.lookOf((90.0, 0.0)), (0.0, -1.0, 0.0)), "俯仰 90 朝下"


def testBehindIsACone():
    south = Rules.lookOf((0.0, 0.0))
    here = (0.0, 64.0, 0.0)
    assert Rules.isBehind(south, here, (0.0, 64.0, -2.0)), "正背后"
    assert not Rules.isBehind(south, here, (0.0, 64.0, 2.0)), "正面"
    assert not Rules.isBehind(south, here, (2.0, 64.0, 0.0)), "正侧面"
    assert Rules.isBehind(south, here, (1.0, 64.0, -1.0)), "斜后 45 度：点积 -0.707"
    assert not Rules.isBehind(south, here, (2.0, 64.0, -1.0)), "偏到 63 度：点积 -0.447"
    assert not Rules.isBehind(south, here, (0.0, 70.0, -1.0)), "从高处打下来：JE 归一化后才去掉竖直分量，水平分量不够"
    assert not Rules.isBehind(south, here, here)


def testDamagePerLevel():
    assert abs(Rules.damageOf(5.0, 1) - 7.0) < 1e-6 and abs(Rules.damageOf(5.0, 2) - 8.0) < 1e-6
    assert abs(Rules.damageOf(5.0, 3) - 9.0) < 1e-6


def testAStabFromBehindHurtsMore():
    assert abs(_hit((0.5, 64.0, -1.5), 2) - 8.0) < 1e-6
    assert world.sounds and world.sounds[0][0] == "game.player.attack.strong"
    assert abs(_hit((0.5, 64.0, 2.5), 2, yaw=180.0) - 8.0) < 1e-6, "目标转过身去，原来的正面成了背后"


def testNoBonusFromTheFrontOrWithoutTheEnchant():
    assert _hit((0.5, 64.0, 2.5), 3) == 5.0 and world.sounds == []
    assert _hit((0.5, 64.0, -1.5), 0) == 5.0
    assert _hit((0.5, 64.0, -1.5), 3, attacker="wolf") == 5.0, "JE 只认玩家造成的伤害"


def testAProjectileCountsFromWhereItIs():
    assert abs(_hit((0.5, 64.0, 2.5), 1, projectilePos=(0.5, 65.0, -0.5)) - 7.0) < 1e-6, "JE 用伤害来源的位置：弹射物在背后"
    assert _hit((0.5, 64.0, -1.5), 1, projectilePos=(0.5, 65.0, 1.5)) == 5.0


def testTheEnchantFileMatchesJava():
    for pack in ("bp", "rp"):
        path = os.path.join(fdtest.ROOT, pack, "netease_enchants", "arris_backstabbing.json")
        body = json.load(io.open(path, encoding="utf-8"))["netease:enchant"]
        assert body["identifier"] == Rules.ENCHANT and body["max_level"] == Rules.MAX_LEVEL
        assert body["cost"] == [15 + level * 9 for level in range(Rules.MAX_LEVEL)], "JE 的 getMinCost：15 + (级 - 1) * 9"
        assert body["frequency"] == "uncommon" and body["primary_slots"] == ["sword"]
    lang = io.open(os.path.join(fdtest.ROOT, "rp", "texts", "zh_CN.lang"), encoding="utf-8").read()
    assert u"enchantment.arris.backstabbing=背刺" in lang, "背刺"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
