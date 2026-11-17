# -*- coding: utf-8 -*-
"""stovekit - 炉灶站点离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）：厨锅的假引擎（potfake）补上炉灶要的几个名字，
真的 Manager 和炉灶站点逻辑装在一起，再给几个驱动用的函数：开站、点击、自定义动作、炉灶自己的一步、走一段时间。"""
from __future__ import print_function

import copy
import sys

import dgtest
import fdtest
import potfake

fake = potfake.install()
_engine = sys.modules[fdtest.SCRIPTS + ".Server.Helpers.Engine"]
for _name, _value in (("GetEngineTypeStr", lambda entityId: "minecraft:player"), ("IsLiving", lambda entityId: True),
                      ("ShowTip", lambda playerId, text: None)):
    if not hasattr(_engine, _name):
        setattr(_engine, _name, _value)

GrillLogic = potfake.load("Compat.Diegesis.GrillLogic")
HandGrill = potfake.load("Server.HandGrill")
StoveLook = potfake.load("Server.StoveLook")
LookWatch = potfake.load("Server.Helpers.LookWatch")
Stove = potfake.load("Server.Stove")
BlockItems = potfake.load("Server.Helpers.BlockItems")
Rules = fdtest.load("Shared.Rules.GrillStation")
Manager = dgtest.load("Server.Manager")
Registry = dgtest.load("Server.Registry")
Protocol = dgtest.load("Shared.Protocol")
Api = dgtest.load("Api.Server")

STOVE = (10, 64, 10)
BEEF, EGG, STICK = "minecraft:beef", "minecraft:egg", "minecraft:stick"
ARGS = {"dimension": 0, "posX": STOVE[0], "posY": STOVE[1], "posZ": STOVE[2]}
DEFAULT_REFRESH = LookWatch.REFRESH_SECONDS      # 生产里的缺省：样子没变时每隔这么久再单发给附近的人一份


def setup(creative=False, covered=None, look=True, refresh=DEFAULT_REFRESH):
    """干净的假世界：一个点着的炉灶（方块实体数据初始化好）、玩家 a（炉灶北边，生存或创造）和 b（东边）；返回 (Manager, 炉灶的方块实体数据)。
    look 打开世界外观广播（StoveLook，装了前置包时 ServerBoot 就是打开的），之后 effects() / looks() / broadcasts() 看发出去的东西。
    refresh 是样子没变时再单发给附近的人一份的间隔（秒，缺省是生产里的；None 不重发：只看"样子变了才发"的用例用它）。"""
    fake.reset()
    Registry.clearAll()
    HandGrill._hands.clear()
    StoveLook._sent.clear()
    LookWatch.reset()
    LookWatch.REFRESH_SECONDS = refresh
    StoveLook.enable(look)
    Stove._pacer = Stove.Pacer(Stove.TICK_STEP)
    GrillLogic.time = Stove.time = potfake.Clock(fake.world)
    GrillLogic.register(Api)
    fake.world.blocks[(0, STOVE)] = "arris:stove"
    data = fake.blockEntities[(0, STOVE)] = potfake.BEData()
    Stove.InitStoveData(data)
    if covered:
        fake.world.blocks[(0, (STOVE[0], STOVE[1] + 1, STOVE[2]))] = covered
    fake.addPlayer("a", (10.5, 64.0, 8.5), creative=creative)
    fake.addPlayer("b", (12.5, 64.0, 10.5))
    return Manager.Manager(fake.world), data


def click(target, button=0, kind="PICKUP"):
    return {"type": "click", "target": target, "button": button, "click": kind}


def inv(index):
    return {"kind": "inventory", "index": index}


def slot(index, group="grill"):
    return {"kind": "station", "group": group, "index": index}


def custom(name, **data):
    return {"type": "custom", "name": name, "data": data}


def do(manager, playerId, raw):
    return manager.action(playerId, list(STOVE), raw)


def opened(manager, playerId="a"):
    """开站并返回 Opened 的负载。"""
    assert manager.open(playerId, list(STOVE))
    return [s[2] for s in fake.world.take(playerId, Protocol.EP_OPENED)][0]


def effects(playerId="a"):
    """取走并返回这位玩家收到的炉灶一次性事件（StoveLook 的广播，站点开不开着都发）：[(名字, 数据)]，数据不带 dimensionId / pos / event。"""
    out, rest = [], []
    for call in fake.calls:
        player, key, args = call
        if key == StoveLook.ENDPOINT and player == playerId and args[0].get("event"):
            payload = dict(args[0])
            name = payload.pop("event")
            payload.pop("dimensionId"), payload.pop("pos")
            out.append((name, payload))
        else:
            rest.append(call)
    fake.calls[:] = rest
    return out


def current():
    """炉灶此刻的样子（StoveLook.build 的）整理成 {"down": [...], "up": [...], "hand": [...]}，每个都是长 6 的列表（空位 0.0 / False）。"""
    payload = StoveLook.build(0, STOVE, fake.blockEntities[(0, STOVE)], HandGrill.peek(0, STOVE))
    slots = payload["slots"]
    return {"down": [s.get("down", 0.0) for s in slots], "up": [s.get("up", 0.0) for s in slots], "hand": [bool(s.get("hand")) for s in slots]}


def hand(playerId="a"):
    return fake.world.players[playerId]["inv"][fake.world.players[playerId].get("selected", 0)]


def items(data):
    """炉灶方块实体数据里六个烤位的 (物品名, 数量) 或 None。"""
    out = []
    for place in range(6):
        slotData = data[str(place)]
        item = slotData.get("itemDict") if slotData else None
        out.append((item["newItemName"], item["count"]) if item else None)
    return out


def names(data):
    return [entry[0] if entry else None for entry in items(data)]


def step(seconds, dt=0.05, manager=None):
    """走 seconds 秒：炉灶自己每 0.25 秒一步（Server/Stove.OnStoveTick 的真处理函数），站点每 dt 秒一个 tick。"""
    end, last = fake.world.time + seconds, None
    while fake.world.time < end - 1e-9:
        fake.world.time += dt
        if last is None or fake.world.time - last >= Stove.TICK_STEP - 1e-9:
            last = fake.world.time
            Stove.OnStoveTick(copy.deepcopy(ARGS))
        if manager is not None:
            manager.tick(dt)


def hand_of():
    return HandGrill.handOf(0, STOVE)


def _grouped():
    """StoveLook 发出去的 [(载荷, [收到的玩家])]：同一个载荷对象发给每个附近的人一次。"""
    out, index = [], {}
    for player, key, args in fake.calls:
        if key != StoveLook.ENDPOINT:
            continue
        payload = args[0]
        if id(payload) not in index:
            index[id(payload)] = (payload, [])
            out.append(index[id(payload)])
        index[id(payload)][1].append(player)
    return out


def looks():
    """StoveLook 发出去的状态载荷（带收件人）：[(载荷, [玩家])]。"""
    return [(payload, players) for payload, players in _grouped() if not payload.get("event")]


def broadcasts(name=None):
    """StoveLook 发出去的一次性事件 [(事件名, 负载, [收到的玩家])]；name 给了只要这个名字的。"""
    return [(payload["event"], payload, players) for payload, players in _grouped()
            if payload.get("event") and (name is None or payload["event"] == name)]


def tick(now=None):
    """炉灶自己的一步（只是广播那一截，不走烤的时间）：now 缺省是假世界现在的钟。"""
    data = fake.blockEntities[(0, STOVE)]
    hand = HandGrill.peek(0, STOVE)
    StoveLook.tick(0, STOVE, data, hand, fake.world.time if now is None else now)
