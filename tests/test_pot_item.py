# -*- coding: utf-8 -*-
# runner: both
"""厨锅拆下来带着锅里的菜、放回去菜还在：纯规则（Shared/Rules/PotItem.py）和服务端（Server/CookingPotItem.py，假引擎驱动）。

JE：战利品表的 copy_meal 把盛出格里那叠菜写进厨锅物品，CookingPotItem 的悬停文字是"装有 N 份：" + 菜名；
创造模式拆不出物品；厨锅物品堆叠 1；方块 strength(0.5F, 6.0F)。
"""
from __future__ import print_function

import io
import json
import os

import fakeengine
import fdtest

world = fakeengine.install()
Rules = fdtest.load("Shared.Rules.PotItem")
Registry = fdtest.load("Server.EventRegistry")
PotItem = fdtest.load("Server.CookingPotItem")

POS = (3, 64, 5)
SAUCE = {"newItemName": "arris:tomato_sauce", "newAuxValue": 0, "count": 3}


class _Data(dict):
    """像引擎的方块实体数据：缺键读出来是 None。"""

    def __missing__(self, key):
        return None

    def __bool__(self):
        return True

    __nonzero__ = __bool__


def _reset(creative=False, hand=None):
    world.players.clear()
    world.entities.clear()
    world.blocks.clear()
    del world.spawned[:]
    world.addPlayer("p1", hand=hand, creative=creative)
    PotItem._pending._meals.clear()
    PotItem._creativeBreaks._marks.clear()


def _pot(meal=None):
    data = _Data()
    data["previewItemSlot"] = [dict(meal)] if meal else [{}]
    return data


# ---------------------------------------------------------------- 纯规则

def testTheMealRoundTripsThroughTheExtraId():
    extraId = Rules.extraIdOf(SAUCE)
    assert extraId == "arris_pot_meal|arris:tomato_sauce|0|3" and Rules.mealOf(extraId) == SAUCE
    assert Rules.extraIdOf({}) == "" and Rules.extraIdOf(None) == "" and Rules.extraIdOf(dict(SAUCE, count=0)) == ""
    assert Rules.mealOf(Rules.extraIdOf(dict(SAUCE, count=200)))["count"] == Rules.MOST


def testForeignOrBrokenExtraIdsCarryNoMeal():
    for bad in ("", None, 7, "something else", "arris_pot_meal|arris:x|0", "arris_pot_meal||0|3", "arris_pot_meal|arris:x|a|3",
                "arris_pot_meal|arris:x|0|0", "arris_pot_meal|arris:x|0|65", "arris_pot_meal|arris:x|0|-1", "other|arris:x|0|3"):
        assert Rules.mealOf(bad) is None, bad


def testTheTooltipFollowsJava():
    # 引擎（py2）给的物品名是 utf-8 字节串，这里的字面量在 py2 下也是字节串：别混进 unicode
    assert Rules.tipsOf("番茄酱", 1).endswith("§7装有1份：§r\n番茄酱")
    assert "§7装有3份：§r\n番茄酱" in Rules.tipsOf("番茄酱", 3)
    assert Rules.tipsOf("番茄酱", 3).startswith("%name%%category%%enchanting%%attack_damage%"), "原来的名字那几行要留着"
    item = Rules.itemOf(SAUCE, "番茄酱")
    assert item["newItemName"] == "arris:cooking_pot" and item["count"] == 1 and item["extraId"] == Rules.extraIdOf(SAUCE)
    assert Rules.itemOf({}, None) == {"newItemName": "arris:cooking_pot", "newAuxValue": 0, "count": 1}, "空锅就是一口普通的锅"


def testPendingMealsExpire():
    pending = Rules.Pending()
    pending.put("a", SAUCE, 100.0)
    assert pending.take("a", 104.0) == SAUCE and pending.take("a", 104.0) is None
    pending.put("b", SAUCE, 100.0)
    assert pending.take("b", 106.0) is None, "放置被取消的话这笔记录过几秒作废"


# ---------------------------------------------------------------- 服务端

def testBreakingThePotDropsItWithItsMeal():
    _reset()
    data = _pot(SAUCE)
    PotItem.dropPot(data, 0, POS)
    assert len(world.spawned) == 1
    item, dimension, where = world.spawned[0]
    assert item["newItemName"] == "arris:cooking_pot" and Rules.mealOf(item["extraId"]) == SAUCE
    assert "装有3份：" in item["customTips"] and where == (3.5, 64.5, 5.5)
    assert data["previewItemSlot"] == [{}], "菜跟着锅走了，方块里不再留一份"


def testAnEmptyPotDropsPlain():
    _reset()
    PotItem.dropPot(_pot(), 0, POS)
    assert [entry[0] for entry in world.spawned] == [{"newItemName": "arris:cooking_pot", "newAuxValue": 0, "count": 1}]
    del world.spawned[:]
    PotItem.dropPot(None, 0, POS)                      # 读不到方块实体数据（/setblock 放的旧锅）：照样掉一口锅
    assert len(world.spawned) == 1 and "extraId" not in world.spawned[0][0]


def testCreativeBreakDropsNothing():
    _reset(creative=True)
    args = {"playerId": "p1", "dimensionId": 0, "x": POS[0], "y": POS[1], "z": POS[2], "fullName": "arris:cooking_pot"}
    Registry.dispatch("ServerPlayerTryDestroyBlockEvent", args, "arris:cooking_pot")
    PotItem.dropPot(_pot(SAUCE), 0, POS)
    assert world.spawned == [], "JE：创造模式拆不出厨锅（菜也没了）"
    PotItem.dropPot(_pot(SAUCE), 0, POS)
    assert len(world.spawned) == 1, "那笔记录只管一次"


def testAPotPushedByAPistonIsNotBroken():
    _reset()
    world.setBlock(POS[0], POS[1], POS[2], "minecraft:moving_block")
    data = _pot(SAUCE)
    PotItem.dropPot(data, 0, POS)
    assert world.spawned == [] and data["previewItemSlot"] == [dict(SAUCE)]


def testPlacingAPotWithAMealPutsItBack():
    held = Rules.itemOf(SAUCE, "番茄酱")
    _reset(hand=held)
    args = {"entityId": "p1", "dimensionId": 0, "x": POS[0], "y": POS[1], "z": POS[2], "fullName": "arris:cooking_pot"}
    Registry.dispatch("ServerEntityTryPlaceBlockEvent", args, "arris:cooking_pot")
    data = _pot()
    PotItem.attachPending(data, 0, POS)
    assert data["previewItemSlot"] == [SAUCE]
    other = _pot()
    PotItem.attachPending(other, 0, POS)
    assert other["previewItemSlot"] == [{}], "只给刚放下的那一口"


def testPlacingAPlainPotOrSomethingElseLeavesThePotEmpty():
    for hand in ({"newItemName": "arris:cooking_pot", "newAuxValue": 0, "count": 1},
                 {"newItemName": "arris:cooking_pot", "newAuxValue": 0, "count": 1, "extraId": "not ours"},
                 {"newItemName": "minecraft:stone", "newAuxValue": 0, "count": 1, "extraId": Rules.extraIdOf(SAUCE)}, None):
        _reset(hand=hand)
        args = {"entityId": "p1", "dimensionId": 0, "x": POS[0], "y": POS[1], "z": POS[2], "fullName": "arris:cooking_pot"}
        Registry.dispatch("ServerEntityTryPlaceBlockEvent", args, "arris:cooking_pot")
        data = _pot()
        PotItem.attachPending(data, 0, POS)
        assert data["previewItemSlot"] == [{}], hand


def testTheBlockFollowsJava():
    path = os.path.join(fdtest.BP, "netease_blocks", "arris_cooking_pot.json")
    components = json.load(io.open(path, encoding="utf-8-sig"))["minecraft:block"]["components"]
    assert components["minecraft:max_stack_size"] == {"value": 1}, "JE：stacksTo(1)"
    assert components["minecraft:destroy_time"]["value"] == 0.5 and components["minecraft:explosion_resistance"]["value"] == 6.0, \
        "JE：strength(0.5F, 6.0F)"
    table = json.load(io.open(os.path.join(fdtest.BP, components["minecraft:loot"]["table"]), encoding="utf-8-sig"))
    assert table["pools"] == [], "厨锅物品由脚本掉（要带着菜），战利品表是空的"


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
