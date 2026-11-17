# -*- coding: utf-8 -*-
"""stovefirekit - 熄着的炉灶、炉灶点火 / 灭火离线测试的共用小工具（不是测试本身，跑器只收 test_*.py）

在 stovekit（厨锅假引擎 + 真的 Manager + 炉灶站点逻辑）上补：
- 换方块的接口 SetBlockNew / GetBlockStates / SetBlockStates / GetBlockNew，照官方文档：换成别的名字时旧方块先发 BlockRemoveServerEvent，方块实体换成新的
  （数据不跟着走），再发 ServerPlaceBlockEntityEvent；同名返回 False；
- 物品类型和耐久（GetItemBasicInfo）、潜行（isSneaking）、事件分发走真的 EventRegistry（处理函数出错测试就失败，不吞）；
- 引擎事件的先后离线定不了（Strata 的模拟也只是推断），所以几种都能摆：events = "sync"（SetBlockNew 里同步到）/ "late"（返回之后 flush 才到）/ "silent"
  （根本没有）；entity = "now"（SetBlockNew 返回时方块实体就在）/ "later"（flush 时才建出来）/ "never"（一直没有）。
"""
from __future__ import print_function

import copy
import sys

import fdtest
import stovekit as K

fake, potfake = K.fake, K.potfake
EventRegistry = fdtest.load("Server.EventRegistry")
StoveSwap = potfake.load("Server.StoveSwap")
GrillBlocks = fdtest.load("Shared.Rules.GrillBlocks")

LIT, UNLIT = "arris:stove", "arris:stove_extinguish"
FLINT, CHARGE = "minecraft:flint_and_steel", "minecraft:fire_charge"
WATER, BUCKET, SHOVEL, PICK = "minecraft:water_bucket", "minecraft:bucket", "minecraft:iron_shovel", "minecraft:iron_pickaxe"
STOVE = K.STOVE
KEY = (0, STOVE)


class _Loud(object):
    """顶替 EventRegistry 里的 traceback：处理函数抛了异常，测试就跟着失败（分发本来会吞掉打印）。"""

    @staticmethod
    def print_exc():
        raise sys.exc_info()[1]


EventRegistry.traceback = _Loud


def _deliver(event, args, key):
    """把一个引擎事件交给真的分发。放置事件到的时候方块实体要在（entity = "later" 时这时才建）；那个方块已经又被换掉了，它的方块实体早没了，事件也不来。"""
    if event == "ServerPlaceBlockEntityEvent":
        at = (args["dimension"], (args["posX"], args["posY"], args["posZ"]))
        if fake.world.blocks.get(at) != args["blockName"]:
            return
        if fake.mode["entity"] == "later" and at not in fake.blockEntities:
            fake.blockEntities[at] = potfake.BEData()
    EventRegistry.dispatch(event, args, key)


def _emit(event, args, key):
    mode = fake.mode["events"]
    if mode == "sync":
        _deliver(event, args, key)
    elif mode == "late":
        fake.queue.append((event, args, key))


def _setBlockNew(self, pos, blockDict, handling=0, dimensionId=-1, isLegacy=False, updateNeighbors=True):
    key = (dimensionId, tuple(pos))
    name = blockDict["name"]
    old = fake.world.blocks.get(key, "minecraft:air")
    if old == name or fake.failSet:
        return False
    fake.sets += 1
    if fake.sets == 2 and fake.swapMode is not None:
        fake.mode = fake.swapMode              # 第一次 SetBlockNew 是自检自己摆炉灶，从第二次（换方块）起才是要试的那种先后
    x, y, z = pos
    _emit("BlockRemoveServerEvent", {"x": x, "y": y, "z": z, "fullName": old, "auxValue": fake.blockAux.get(key, 0), "dimension": dimensionId}, old)
    fake.world.blocks[key] = name
    fake.states[key] = {"direction": 0}
    fake.blockAux[key] = 0
    fake.blockEntities.pop(key, None)
    if fake.mode["entity"] == "now":
        fake.blockEntities[key] = potfake.BEData()
    _emit("ServerPlaceBlockEntityEvent", {"blockName": name, "dimension": dimensionId, "posX": x, "posY": y, "posZ": z}, name)
    return True


def _getBlockStates(self, pos, dimensionId=-1):
    key = (dimensionId, tuple(pos))
    return dict(fake.states.get(key, {"direction": fake.blockAux.get(key, 0)}))


def _setBlockStates(self, pos, states, dimensionId=-1):
    key = (dimensionId, tuple(pos))
    fake.states[key] = dict(states)
    fake.blockAux[key] = states.get("direction", 0) * (4 if fake.holiday else 1)      # 假日创造者实验玩法的世界里 direction 状态 1 / 2 / 3 的 aux 是 4 / 8 / 12
    return True


def _itemInfo(self, name, aux=0):
    return {"maxStackSize": fake.stackOf(name), "itemName": "name:" + name, "itemType": fake.itemTypes.get(name, "food"),
            "maxDurability": fake.durable.get(name, 0)}


def _install():
    Comp = potfake.Comp
    Comp.isSneaking = lambda self: self.owner in fake.sneaking
    Comp.SetBlockNew = _setBlockNew
    Comp.GetBlockStates = _getBlockStates
    Comp.SetBlockStates = _setBlockStates
    Comp.GetBlockNew = lambda self, pos, dim=-1: {"name": fake.world.blocks.get((dim, tuple(pos)), "minecraft:air"),
                                                 "aux": fake.blockAux.get((dim, tuple(pos)), 0)}
    Comp.GetItemBasicInfo = _itemInfo


_install()


def setup(events="sync", entity="now", swapMode=None, **kwargs):
    """stovekit.setup（点着的炉灶在 STOVE，玩家 a 在北边、b 在东边）之后补上换方块要的东西；返回 (Manager, 方块实体数据)。
    swapMode 给了（{"events": ..., "entity": ...}）：第一次 SetBlockNew 照 events / entity 参数，从第二次起换成它（游戏内自检先自己摆炉灶、再换方块）。"""
    manager, data = K.setup(**kwargs)
    fake.states, fake.queue, fake.sneaking, fake.tips, fake.failSet, fake.holiday = {}, [], set(), [], False, False
    fake.mode = {"events": events, "entity": entity}
    fake.swapMode, fake.sets = swapMode, 0
    fake.itemTypes = {SHOVEL: "shovel", PICK: "pickaxe", FLINT: "", CHARGE: "", WATER: "bucket", BUCKET: "bucket"}
    fake.durable = {FLINT: 65, SHOVEL: 250, PICK: 250}
    fake.blockAux[KEY] = 0
    StoveSwap.time = K.Stove.time
    StoveSwap._swaps.clear()
    K.Stove.ShowTip = lambda playerId, text: fake.tips.append((playerId, text))
    return manager, data


def facing(aux):
    """炉灶朝向：direction 状态（0 南 1 西 2 北 3 东），点火 / 灭火要原样带过去。"""
    fake.blockAux[KEY] = aux
    fake.states[KEY] = {"direction": aux}


def setBlock(name):
    """直接把炉灶摆成这个方块（不走事件，朝向不动）：模拟 /setblock，或"炉灶已经是熄着的"。"""
    fake.world.blocks[KEY] = name


def blockName():
    return fake.world.blocks[KEY]


def lay(data, place, name="minecraft:beef", timer=30, count=1):
    data[str(place)] = {"itemDict": {"newItemName": name, "newAuxValue": 0, "count": count}, "cookTimer": timer}


def give(playerId, name, count=1, slot=0, durability=None, creative=None):
    fake.give(playerId, slot, name, count)
    if durability is not None:
        fake.world.players[playerId]["inv"][slot]["durability"] = durability
    if creative is not None:
        fake.world.players[playerId]["creative"] = creative


def use(playerId="a", slot=0, face=1, cooldown=False):
    """右键点炉灶：手里是 slot 那格的东西，事件参数照引擎给的，走真的 EventRegistry。返回 (事件参数, 有没有处理函数认领)。
    cooldown 假：先把交互冷却（0.2 秒）过掉；真：照原样带着冷却点（按住右键每刻重发的情形）。"""
    if not cooldown:
        fake.attrs.pop((playerId, "arrisUsedCD"), None)
    held = copy.deepcopy(fake.world.players[playerId]["inv"][slot])
    args = {"itemDict": held, "x": STOVE[0], "y": STOVE[1], "z": STOVE[2], "dimensionId": 0, "entityId": playerId,
            "blockName": blockName(), "face": face, "ret": False}
    return args, EventRegistry.dispatch("ServerItemUseOnEvent", args, blockName())


def flush():
    """晚到的引擎事件现在到（按它们发生的先后）。"""
    queue, fake.queue = fake.queue, []
    for event, args, key in queue:
        _deliver(event, args, key)


def runTimers():
    timers, fake.timers = fake.timers, []
    for _delay, function, args in timers:
        function(*args)


def data():
    """炉灶位置现在的方块实体数据。"""
    return fake.blockEntities.get(KEY)


def kept(blockEntityData):
    """炉灶自己的键（六个烤位、cookingIndex、手放的进度）原样的一份，比较用。"""
    return dict((key, blockEntityData[key]) for key in StoveSwap.KEYS if blockEntityData[key] is not None)


def sounds():
    return [call[2][0]["soundName"] for call in fake.calls if call[1] == "OnPlaySound"]


def groundItems():
    """地上的东西的名字（炉灶烤好弹出的用 itemName，拆了、丢出来的用 newItemName，两种字典都认）。"""
    return [item.get("newItemName") or item.get("itemName") for item, _dim, _pos in fake.spawned]


def tickEvent(blockName, seconds=0.3):
    """引擎的 ServerBlockEntityTickEvent 走一次真的分发（先让假钟走 seconds 秒：炉灶的节拍器第一次见到只错相位、不放行）。"""
    fake.world.time += seconds
    args = {"dimension": 0, "posX": STOVE[0], "posY": STOVE[1], "posZ": STOVE[2], "blockName": blockName}
    return EventRegistry.dispatch("ServerBlockEntityTickEvent", args, blockName)


def held(playerId="a", slot=0):
    return fake.world.players[playerId]["inv"][slot]
