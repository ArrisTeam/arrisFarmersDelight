# -*- coding: utf-8 -*-
# runner: py3
"""炉灶的两个方块的 JSON（bp/netease_blocks/arris_stove.json 点着的、arris_stove_extinguish.json 熄着的）：熄着的是同一座灶的另一个方块，
照 JE 熄着的炉灶也收食物、冷却、拆了掉东西（AbstractStoveBlockEntity.serverTick / onRemove），所以它要有和点着的一样的方块实体（每刻 tick 才冷却）、
朝向、监听移除；不要烫脚（netease:on_stand_on 只有点着的）；拆了掉的是点着的炉灶物品，不是它自己这个隐藏的方块物品。
火口的火星 / 烟 / 噼啪声（FD 的 StoveBlock.animateTick）和灶上东西的烟（StoveBlockEntity.particleTick）都只在 LIT 时：只有点着的方块写
netease:block_animate_random_tick 和客户端 tick（Client/StoveFlame.py 收这两个事件）。
这些 JSON / 战利品表的改动都要完整重启游戏才生效，离线只能核对写法（实机见前置包仓库的 docs/diegesis/DESIGN.md 第 11 节的清单）。"""
from __future__ import print_function

import io
import json
import os

import fdtest

BLOCKS = os.path.join(fdtest.BP, "netease_blocks")
LOOT = os.path.join(fdtest.BP, "loot_tables")


def _block(fileName):
    with io.open(os.path.join(BLOCKS, fileName + ".json"), encoding="utf-8-sig") as f:
        return json.loads(f.read())["minecraft:block"]


def testTheUnlitBlockHasTheSameBlockEntityAsTheLitOneAndTicksToCool():
    lit, unlit = _block("arris_stove")["components"], _block("arris_stove_extinguish")["components"]
    assert lit["netease:block_entity"] == {"client_tick": True, "movable": False, "tick": True}
    assert unlit["netease:block_entity"] == dict(lit["netease:block_entity"], client_tick=False), \
        "熄着的也要有方块实体，也要服务端 tick（每步冷却 FD 的件），其余标志照点着的；客户端不 tick：没有火就没有烟（particleTick 只在 LIT 时）"


def testOnlyTheLitBlockAsksTheEngineForTheFlameAndSmokeOfFarmersDelightsAnimateTick():
    lit, unlit = _block("arris_stove")["components"], _block("arris_stove_extinguish")["components"]
    tick = lit["netease:block_animate_random_tick"]
    assert tick == {"send_event": True, "trigger_rate": 1.0}, "JE 的 animateTick 每次轮到都放（只有噼啪声是 1/10），所以每次轮到都发事件，1.0 是引擎能给的最高"
    assert "netease:block_animate_random_tick" not in unlit, "StoveBlock.animateTick 开头 !LIT 就返回"


def testTheUnlitBlockFacesAndListensToItsRemovalLikeTheLitOne():
    lit, unlit = _block("arris_stove")["components"], _block("arris_stove_extinguish")["components"]
    for key in ("netease:face_directional", "netease:listen_block_remove", "netease:solid", "netease:render_layer", "netease:tier",
                "minecraft:destroy_time", "minecraft:explosion_resistance", "minecraft:block_light_absorption"):
        assert unlit[key] == lit[key], key
    assert unlit["netease:face_directional"] == {"type": "direction"} and unlit["netease:listen_block_remove"] == {"value": True}


def testOnlyTheLitBlockBurnsAndGivesLight():
    lit, unlit = _block("arris_stove")["components"], _block("arris_stove_extinguish")["components"]
    assert lit["netease:on_stand_on"] == {"send_python_event": True} and "netease:on_stand_on" not in unlit
    assert lit["minecraft:block_light_emission"]["emission"] > 0 and unlit["minecraft:block_light_emission"]["emission"] == 0


def testTheUnlitBlockIsNotInTheCreativeMenuAndDropsTheLitStoveItem():
    litDescription, unlitDescription = _block("arris_stove")["description"], _block("arris_stove_extinguish")["description"]
    assert litDescription["register_to_creative_menu"] is True and unlitDescription["register_to_creative_menu"] is False
    assert litDescription["identifier"] == "arris:stove" and unlitDescription["identifier"] == "arris:stove_extinguish"
    lit, unlit = _block("arris_stove")["components"], _block("arris_stove_extinguish")["components"]
    assert "minecraft:loot" not in lit, "点着的炉灶不写战利品：掉它自己"
    table = unlit["minecraft:loot"]["table"]
    assert table == "loot_tables/stove.json", "熄着的另给一张表：掉的是点着的炉灶（JE 的炉灶不分 LIT，掉 farmersdelight:stove），不是这个隐藏的方块物品"
    with io.open(os.path.join(fdtest.BP, table.replace("/", os.sep)), encoding="utf-8-sig") as f:
        loot = json.loads(f.read())
    assert len(loot["pools"]) == 1 and loot["pools"][0]["rolls"] == 1
    entries = loot["pools"][0]["entries"]
    assert len(entries) == 1 and entries[0]["type"] == "item" and entries[0]["name"] == "arris:stove"
    counts = [function for function in entries[0]["functions"] if function["function"] == "set_count"]
    assert counts and counts[0]["count"] == {"min": 1, "max": 1}


if __name__ == "__main__":
    raise SystemExit(fdtest.run(globals()))
