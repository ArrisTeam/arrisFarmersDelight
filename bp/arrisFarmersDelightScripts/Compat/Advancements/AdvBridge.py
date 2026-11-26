# -*- coding: utf-8 -*-
"""AdvBridge - 接上成就系统以后：登记 21 个节点，挂上推进进度的那些监听（服务端，不碰引擎）

attach(接口模块, env) 由 AdvBoot 在成就系统的 ready 事件里（或热重载以后晚接时）调；env 是要碰引擎的那几样，AdvBoot 给真的、测试给假的：
    env.typeOf(实体)  env.blockAt(坐标, 维度)  env.itemsOf(玩家) -> 物品名  env.listen(引擎事件名, 函数)
接上以后才挂监听，没装成就系统时这里一个处理函数也没有：
- 玩家的进度装好了（成就系统的 listenOnPlayerReady）：发根节点，再按背包里现有的东西补一遍"拥有某物品"（进服时的背包事件比进度装好早，那时加不上）；
- 背包变了（InventoryItemChangedServerEvent，ModServer 不转它，这里接上以后才动态监听）：新那一格的物品 -> 拥有某物品；
- 放下方块（EntityPlaceBlockAfterServerEvent）、种子类对方块用了以后点的那一面外面那一格是不是种上了（ItemUseOnAfterServerEvent：
  种子种作物时引擎报不报放置事件没核实，两条都认，同一个子条件只记一次）、吃（PlayerEatFoodServerEvent）、得到效果（AddEffectServerEvent）、
  烂番茄打中（ProjectileDoHitEffectEvent）——这几个 ModServer 本来就转，这里在注册表上登记处理函数；
- 玩法模块报的事（Server/Helpers/Deeds）：砧板切开一件、手持煎锅煎好一件、脚本替玩家放下方块、右键采摘。
"""
from ...Server.EventRegistry import registerHandler
from ...Server.Helpers import Deeds
from ...Shared.Data import Advancements as Data
from ...Shared.Rules.Placement import placePositions
from . import AdvTriggers as Triggers

ROTTEN_TOMATO = "arris:rotten_tomato"
_REQUIRED = ("registerAdvancements", "listenOnPlayerReady", "setFinish", "addProgressUnique", "isDone")
_state = {"api": None, "env": None, "listened": False}


def api():
    """接上的成就系统接口模块；没接上是 None。"""
    return _state["api"]


def _fire(playerId, kind, key=None):
    return Triggers.fire(_state["api"], playerId, kind, key)


def onPlayerReady(event):
    playerId = (event or {}).get("playerId")
    if not playerId:
        return
    _fire(playerId, "ready")
    for name in _state["env"].itemsOf(playerId) or ():
        _fire(playerId, "obtain", name)


def onInventoryChanged(args):
    _fire(args.get("playerId"), "obtain", (args.get("newItemDict") or {}).get("newItemName"))


def onBlockPlaced(args):
    _fire(args.get("entityId"), "placed", args.get("fullName"))


def onPlanted(args):
    itemName = (args.get("itemDict") or {}).get("newItemName")
    cell = placePositions(args["x"], args["y"], args["z"]).get(args.get("face"))
    name = _state["env"].blockAt(cell, args["dimensionId"]) if cell is not None else None
    if name in Data.PLANTERS.get(itemName, ()):
        _fire(args.get("entityId"), "placed", name)


def onEaten(args):
    _fire(args.get("playerId"), "eaten", (args.get("itemDict") or {}).get("newItemName"))


def onEffect(args):
    _fire(args.get("entityId"), "effect", args.get("effectName"))


def onProjectileHit(args):
    env = _state["env"]
    if args.get("hitTargetType") != "ENTITY" or env.typeOf(args.get("id")) != ROTTEN_TOMATO:
        return
    _fire(args.get("srcId"), "hit", env.typeOf(args.get("targetId")))


def onCut(playerId, detail):
    _fire(playerId, "cut")


def onSkilletCooked(playerId, detail):
    _fire(playerId, "skillet")


def onPlacedByScript(playerId, blockName):
    _fire(playerId, "placed", blockName)


def onHarvested(playerId, blockName):
    _fire(playerId, "harvested", blockName)


def _itemName(args):
    return (args.get("itemDict") or {}).get("newItemName")


def _hook(env):
    registerHandler("EntityPlaceBlockAfterServerEvent", match=Triggers.keysOf("placed"))(onBlockPlaced)
    registerHandler("ItemUseOnAfterServerEvent", match=Data.PLANTERS, keyOf=_itemName)(onPlanted)
    registerHandler("PlayerEatFoodServerEvent", match=Triggers.keysOf("eaten"))(onEaten)
    registerHandler("AddEffectServerEvent")(onEffect)
    registerHandler("ProjectileDoHitEffectEvent")(onProjectileHit)
    for deed, func in ((Deeds.CUT_ON_BOARD, onCut), (Deeds.SKILLET_COOKED, onSkilletCooked),
                       (Deeds.PLACED_BLOCK, onPlacedByScript), (Deeds.HARVESTED, onHarvested)):
        Deeds.subscribe(deed, func)
    if not _state["listened"]:
        _state["listened"] = True
        env.listen("InventoryItemChangedServerEvent", onInventoryChanged)


def attach(module, env):
    """成就系统的接口模块来了：登记节点、挂监听（再来一次只换接口、重新登记节点）。返回登记上的节点数；不像它的接口是 None。"""
    if module is None or any(not hasattr(module, name) for name in _REQUIRED):
        print("[arrisFarmersDelight] 成就系统的接口不对（%r），不接" % (module,))
        return None
    _state["api"], _state["env"] = module, env
    count = module.registerAdvancements([dict(node) for node in Data.NODES])
    module.listenOnPlayerReady(onPlayerReady)
    _hook(env)
    print("[arrisFarmersDelight] 接上了成就系统：登记了 %d / %d 个进度节点" % (count or 0, len(Data.NODES)))
    return count
