# -*- coding: utf-8 -*-
"""panfake - 煎锅站点离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

在厨锅的假引擎（potfake）上补煎锅要的：方块实体数据里的 cookingDict / heatEnable / skilletItem、液体层的水、PanLook 广播的记录；
前置包的 Manager、Registry 是真的。再给几个驱动用的函数：开站、点击、自定义动作、锅的一步（Server/Skillet 那条线，不含热源刷新）、走一段时间。
"""
from __future__ import print_function

import copy

import dgtest
import fdtest
import potfake

fake = potfake.install()
HandFrying = potfake.load("Server.HandFrying")
PanLook = potfake.load("Server.PanLook")
LookWatch = potfake.load("Server.Helpers.LookWatch")
PanLogic = potfake.load("Compat.Diegesis.PanLogic")
PanContents = potfake.load("Server.Helpers.PanContents")
Rules = potfake.load("Shared.Rules.PanStation")
Manager = dgtest.load("Server.Manager")
Registry = dgtest.load("Server.Registry")
Protocol = dgtest.load("Shared.Protocol")
Api = dgtest.load("Api.Server")

PAN = (10, 64, 10)
BEEF, PORK, COOKED, EGG, STICK = "minecraft:beef", "minecraft:porkchop", "minecraft:cooked_beef", "minecraft:egg", "minecraft:stick"


def _liquid(self, pos, dim=0):
    return fake.liquid.get((dim, tuple(pos)))


potfake.Comp.GetLiquidBlock = _liquid


def _setBlockNew(self, pos, blockDict, handling=0, dim=0, *rest):
    """游戏内自检要放方块：煎锅顺带建出方块实体数据。"""
    fake.world.blocks[(dim, tuple(pos))] = blockDict["name"]
    if blockDict["name"] == "arris:skillet":
        fake.blockEntities[(dim, tuple(pos))] = potfake.BEData()
    return True


def _allItems(self, posType, getUserData=False):
    return copy.deepcopy(fake.world.players[self.owner]["inv"])


def _setAllItems(self, changes):
    for (posType, slot), item in changes.items():
        fake.world.players[self.owner]["inv"][slot] = copy.deepcopy(item)
    return True


potfake.Comp.SetBlockNew, potfake.Comp.GetPlayerAllItems, potfake.Comp.SetPlayerAllItems = _setBlockNew, _allItems, _setAllItems


def exposeManager(manager):
    """让游戏内自检里的 serverApi.ImportModule("arrisDiegesisScripts.Server.Runtime").getManager() 拿到这个 Manager。"""
    import sys
    engine = sys.modules[potfake.PACKAGE + ".Server.Helpers.Engine"]
    runtime = type("Runtime", (), {"getManager": staticmethod(lambda: manager)})
    engine.serverApi.ImportModule = lambda name: runtime if name.endswith("Server.Runtime") else None


DEFAULT_REFRESH = LookWatch.REFRESH_SECONDS      # 生产里的缺省：样子没变时每隔这么久再单发给附近的人一份


def setup(heated=True, fireAspect=0, creative=False, refresh=DEFAULT_REFRESH):
    """干净的假世界：一口煎锅（可烧着）、玩家 a（锅北边）和 b（锅东边）；返回 (Manager, 锅的方块实体数据)。
    refresh 是样子没变时再单发给附近的人一份的间隔（秒，缺省是生产里的；None 不重发）。"""
    fake.reset()
    fake.liquid = {}
    Registry.clearAll()
    HandFrying._hands.clear()
    PanLook._sent.clear()
    LookWatch.reset()
    LookWatch.REFRESH_SECONDS = refresh
    PanLook.enable(True)
    PanLogic.time = potfake.Clock(fake.world)
    PanLogic.register(Api)
    fake.world.blocks[(0, PAN)] = "arris:skillet"
    data = fake.blockEntities[(0, PAN)] = potfake.BEData()
    data["heatEnable"] = heated
    data["cookTimer"] = 7.0
    if fireAspect:
        data["skilletItem"] = {"newItemName": "arris:skillet_item", "count": 1, "enchantData": [(13, fireAspect)]}
    fake.addPlayer("a", (10.5, 64.0, 8.5), creative=creative)
    fake.addPlayer("b", (12.5, 64.0, 10.5))
    return Manager.Manager(fake.world), data


def click(target, button=0, kind="PICKUP"):
    return {"type": "click", "target": target, "button": button, "click": kind}


def inv(index):
    return {"kind": "inventory", "index": index}


def pan(index=0):
    return {"kind": "station", "group": "pan", "index": index}


def custom(name, **data):
    return {"type": "custom", "name": name, "data": data}


def do(manager, playerId, raw):
    return manager.action(playerId, list(PAN), raw)


def opened(manager, playerId="a"):
    """开站并返回 Opened 的负载。"""
    assert manager.open(playerId, list(PAN))
    return [s[2] for s in fake.world.take(playerId, Protocol.EP_OPENED)][0]


def inPan():
    item = fake.blockEntities[(0, PAN)]["cookingDict"]
    return (item["newItemName"], item["count"]) if item else None


def hold(playerId, slot, name, count):
    fake.give(playerId, slot, name, count)


def _grouped():
    """PanLook 发出去的 [(载荷, [收到的玩家])]：同一个载荷对象发给每个附近的人一次。"""
    out, index = [], {}
    for player, key, args in fake.calls:
        if key != PanLook.ENDPOINT:
            continue
        payload = args[0]
        if id(payload) not in index:
            index[id(payload)] = (payload, [])
            out.append(index[id(payload)])
        index[id(payload)][1].append(player)
    return out


def events(name=None):
    """PanLook 发出去的一次性事件 [(事件名, 负载, [收到的玩家])]；name 给了只要这个名字的。"""
    return [(payload["event"], payload, players) for payload, players in _grouped()
            if payload.get("event") and (name is None or payload["event"] == name)]


def looks():
    """PanLook 发出去的状态载荷。"""
    return [payload for payload, players in _grouped() if not payload.get("event")]


def step(seconds=0.25, now=None):
    """煎锅自己的一步（Server/Skillet 的 _cook 那条线：手放的归 HandFrying，之后广播）。"""
    data = fake.blockEntities[(0, PAN)]
    hand = HandFrying.handOf(0, PAN, data)
    fire = PanLook.fireAspectOf(data)
    if data["heatEnable"] is True:
        HandFrying.fry(hand, 0, PAN, data, seconds, fire)
    PanLook.tick(0, PAN, data, hand, fake.world.time if now is None else now)
    return hand


def run(manager, seconds, tick=0.25):
    """走 seconds 秒：每个 tick 秒煎锅一步、站点一刻。"""
    end = fake.world.time + seconds
    while fake.world.time < end - 1e-9:
        fake.world.time += tick
        step(tick)
        manager.tick(tick)


def copyOf(value):
    return copy.deepcopy(value)
