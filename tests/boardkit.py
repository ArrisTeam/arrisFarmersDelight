# -*- coding: utf-8 -*-
"""boardkit - 砧板站点离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）：假引擎（potfake 的，补上物品类型 / 耐久 / 副手）、
真的前置包 Manager、真的砧板站点逻辑装在一起，再给几个驱动用的函数：开站、点击、自定义动作、放东西、拿工具。"""
from __future__ import print_function

import copy

import dgtest
import potfake

fake = potfake.install()
TYPES = {"arris:iron_knife": "sword", "arris:flint_knife": "sword", "minecraft:iron_axe": "axe", "minecraft:iron_pickaxe": "pickaxe",
         "minecraft:iron_sword": "sword", "minecraft:cobblestone": "block", "minecraft:oak_log": "block"}
MAX_DURABILITY = {"arris:iron_knife": 250, "arris:flint_knife": 59, "minecraft:iron_axe": 250, "minecraft:iron_sword": 250}


_Base = potfake.Comp


class BoardComp(_Base):
    """potfake 的组件再加砧板要问的：物品类型、最大耐久、标签、副手。"""

    def GetItemBasicInfo(self, name, aux=0):
        info = dict(_Base.GetItemBasicInfo(self, name, aux))
        info["itemType"] = TYPES.get(name, "food")
        info["maxDurability"] = MAX_DURABILITY.get(name, 0)
        return info

    def GetItemTags(self, name):
        return []

    def GetPlayerItem(self, posType, slot, getUserData=False):
        player = self.fake.world.players[self.owner]
        item = player.get("offhand") if posType == potfake.ItemPosType.OFFHAND else player["inv"][slot]
        return copy.deepcopy(item) if item else None

    def SetEntityItem(self, posType, item, slot):
        player = self.fake.world.players[self.owner]
        player["offhand" if posType == potfake.ItemPosType.OFFHAND else "inv"] = copy.deepcopy(item) if item else None


potfake.Comp = BoardComp
BoardLogic = potfake.load("Compat.Diegesis.BoardLogic")
BoardChop = potfake.load("Compat.Diegesis.BoardChop")
BlockItems = potfake.load("Server.Helpers.BlockItems")
Manager = dgtest.load("Server.Manager")
Registry = dgtest.load("Server.Registry")
Protocol = dgtest.load("Shared.Protocol")
Api = dgtest.load("Api.Server")

BOARD = (10, 64, 10)


def setup(creative=False):
    """干净的假世界：一块砧板、玩家 a（板北边，生存或创造）和 b（板东边）；返回 (Manager, 板的方块实体数据)。"""
    fake.reset()
    Registry.clearAll()
    BoardChop.time = potfake.Clock(fake.world)
    BoardLogic.register(Api)
    fake.world.blocks[(0, BOARD)] = "arris:cutting_board"
    data = fake.blockEntities[(0, BOARD)] = potfake.BEData()
    fake.addPlayer("a", (10.5, 64.0, 8.5), creative=creative)
    fake.addPlayer("b", (12.5, 64.0, 10.5))
    fake.stacks.update({"minecraft:crimson_fungus": 64, "arris:cooked_rice": 64})
    for player in fake.world.players.values():
        player["offhand"] = None
    return Manager.Manager(fake.world), data


def click(target, button=0, kind="PICKUP"):
    return {"type": "click", "target": target, "button": button, "click": kind}


def inv(index):
    return {"kind": "inventory", "index": index}


def custom(name, **data):
    return {"type": "custom", "name": name, "data": data}


def do(manager, playerId, raw):
    return manager.action(playerId, list(BOARD), raw)


def opened(manager, playerId="a"):
    """开站并返回 Opened 的负载。"""
    assert manager.open(playerId, list(BOARD))
    return [s[2] for s in fake.world.take(playerId, Protocol.EP_OPENED)][0]


def carry(manager, slot, name, count, playerId="a", aux=0):
    """背包第 slot 格放 count 个 name，点托盘拿到光标栈上。"""
    fake.give(playerId, slot, name, count, aux)
    assert do(manager, playerId, click(inv(slot)))


def hand(manager, playerId="a"):
    return manager.sessions[playerId].hand


def board(data):
    item = data["cuttingDict"]
    return (item["newItemName"], item["count"]) if item else None


def layers(data):
    return [(layer["newItemName"], layer["count"]) for layer in (data["dishLayers"] or [])]


def count(name, playerId="a"):
    return fake.count(playerId, name)


def effects(playerId="a"):
    """取走并返回这位玩家收到的表现事件：[(名字, 数据)]。"""
    return [(e[2]["name"], e[2]["data"]) for e in fake.world.take(playerId, Protocol.EP_EFFECT)]


def advance(seconds):
    fake.world.time += seconds
