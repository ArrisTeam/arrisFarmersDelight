# -*- coding: utf-8 -*-
"""potkit - 厨锅站点离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）：假引擎、真的 Manager 和厨锅站点逻辑装在一起，
再给几个驱动用的函数：开站、点击、自定义动作、锅的一步、走一段时间（可以边搅）。"""
from __future__ import print_function

import math

import dgtest
import fdtest
import potfake

fake = potfake.install()
PotLogic = potfake.load("Compat.Diegesis.PotLogic")
PotSync = potfake.load("Compat.Diegesis.PotSync")
HandCooking = potfake.load("Server.HandCooking")
PotContainer = potfake.load("Server.Helpers.PotContainer")
PotServe = potfake.load("Server.PotServe")
PotLook = potfake.load("Server.PotLook")
LookWatch = potfake.load("Server.Helpers.LookWatch")
Recipes = fdtest.load("Shared.Data.CookingPotRecipes")
Manager = dgtest.load("Server.Manager")
Registry = dgtest.load("Server.Registry")
Protocol = dgtest.load("Shared.Protocol")
Api = dgtest.load("Api.Server")

POT = potfake.POT_POS
TOMATO, BOWL, SAUCE = "arris:tomato", "minecraft:bowl", "arris:tomato_sauce"


def setup(heated=True, creative=False):
    """干净的假世界：一口厨锅（有热源）、玩家 a（锅北边，生存或创造）和 b（锅东边）；返回 (Manager, 锅的方块实体数据)。"""
    fake.reset()
    Registry.clearAll()
    HandCooking._hands.clear()
    HandCooking._made.clear()
    PotLook._sent.clear()
    PotLook.enable(False)
    LookWatch.reset()                 # 玩家位置的快照是模块里的：上一个用例的人不带进这一个
    PotLogic.time = potfake.Clock(fake.world)
    PotLogic.register(Api)
    data = fake.placePot(POT, heated)
    fake.addPlayer("a", (10.5, 64.0, 8.5), creative=creative)
    fake.addPlayer("b", (12.5, 64.0, 10.5))
    potStep(fake.world.time)          # 锅先空转一步（游戏里锅一直在 tick，放进来的料才分得出手放还是自动进来的）
    return Manager.Manager(fake.world), data


def click(target, button=0, kind="PICKUP"):
    return {"type": "click", "target": target, "button": button, "click": kind}


def inv(index):
    return {"kind": "inventory", "index": index}


def slot(index, group="ingredients"):
    return {"kind": "station", "group": group, "index": index}


def custom(name, **data):
    return {"type": "custom", "name": name, "data": data}


def do(manager, playerId, raw):
    return manager.action(playerId, list(POT), raw)


def opened(manager, playerId="a"):
    """开站并返回 Opened 的负载。"""
    assert manager.open(playerId, list(POT))
    return [s[2] for s in fake.world.take(playerId, Protocol.EP_OPENED)][0]


def cells():
    return PotContainer.inputs(0, POT)


def shape(items):
    return [(c["newItemName"], c["count"]) if c else None for c in items]


def potStep(now, dt=0.2):
    """锅自己的一步（Server/CookingPot.OnCookingPotTick 的做法，不含热源刷新）。"""
    data = fake.blockEntities[(0, POT)]
    hand = HandCooking.handOf(0, POT, data)
    slots = PotContainer.inputs(0, POT)
    PotContainer.MoveFinishedMeals(data, POT, 0)
    HandCooking.cook(hand, 0, POT, data, slots, now, dt)
    PotLook.tick(0, POT, data, hand, slots, now)
    return hand


def run(manager, seconds, stir=False, step=0.05, playerId="a"):
    """走 seconds 秒：每 step 一个脚本 tick（站点），每 0.2 秒锅一步；stir 为真时按宽圈稳速搅（每 2 个 tick 一下，一秒一圈）。"""
    end, last, ticks = fake.world.time + seconds, None, 0
    while fake.world.time < end - 1e-9:
        fake.world.time += step
        ticks += 1
        if stir and ticks % 2 == 0:
            angle = (fake.world.time - 100.0) * math.pi * 2.0
            manager.action(playerId, list(POT), custom("stir", x=0.9 * math.cos(angle), z=0.9 * math.sin(angle),
                                                       at=fake.world.time - 100.0))
        if last is None or fake.world.time - last >= 0.2 - 1e-9:
            last = fake.world.time
            potStep(fake.world.time)
        manager.tick(step)


def feed(manager, name=TOMATO, count=16, playerId="a", slotIndex=0):
    """玩家 playerId 把 count 个 name 经站点放进锅的食材格 slotIndex（站点没开就先开），再让站点走一刻把料摆好。"""
    if playerId not in manager.sessions:
        opened(manager, playerId)
    fake.give(playerId, 35, name, count)
    do(manager, playerId, click(inv(35)))
    do(manager, playerId, click(slot(slotIndex)))
    manager.tick(0.05)


def alone(seconds, step=0.2):
    """没人开站点：只有锅自己走 seconds 秒（漏斗放进来的料、站点关了之后的锅）。"""
    end = fake.world.time + seconds
    while fake.world.time < end - 1e-9:
        fake.world.time += step
        potStep(fake.world.time, step)


class FixedRandom(object):
    """顶替 PotContainer 里的 random：每次都掷同一个数（经验的零头按概率进一，测试要定下来）。"""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def preview():
    return PotContainer.preview(fake.blockEntities[(0, POT)])


def setMeal(name, count, data=None):
    PotContainer.setPreview(data or fake.blockEntities[(0, POT)], {"newItemName": name, "newAuxValue": 0, "count": count})


def sauceIndex():
    return next(i for i, r in enumerate(Recipes.CookingPotRecipeList) if r["CookResult"][0] == SAUCE)


def orbs():
    return [orb["value"] for orb in fake.orbs.values()]


def effects(playerId="a"):
    """取走并返回这位玩家收到的表现事件：[(名字, 数据)]。"""
    return [(e[2]["name"], e[2]["data"]) for e in fake.world.take(playerId, Protocol.EP_EFFECT)]
