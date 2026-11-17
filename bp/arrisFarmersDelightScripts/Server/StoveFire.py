# -*- coding: utf-8 -*-
"""StoveFire - 炉灶点火 / 灭火：打火石、火焰弹点着熄着的炉灶，铲子、水桶熄灭点着的（服务端）

JE AbstractStoveBlock.use（java:66-77）：点着的先看 tryToExtinguish（:106-128：铲子 SHOVEL_DIG 磨损 1 点、灭火声；水桶灭火声，非创造模式换成空桶），
熄着的先看 tryToIgnite（:79-104：打火石磨损 1 点、打火声；火焰弹少一个、火焰弹声，创造模式不少），用上了就不再放食物（返回 SUCCESS，也不会再走物品自己的用法）。
点火 / 灭火只改方块状态，烤位上的东西、烤到哪都在（ignite / extinguish 只通知客户端、存盘，:144-164）：这里换方块、数据原样带过去（StoveSwap）。
JE 里没有任何别的东西点火 / 灭火，这边原来也没有：熄着的 arris:stove_extinguish 只能靠命令放出来，补上以后游戏里才有熄着的炉灶。
潜行拿着东西右键是物品自己的用法（原版的 shouldSneakBypass，方块的 use 不被调）：不点不灭。点着的炉灶拿打火石、熄着的拿铲子 / 水桶什么也不发生。
没有熄着孪生方块的炉灶（下游往 StoveList 追加的）点不灭也灭不了，不拦。优先级 11：排在炉灶放食物（10，Stove.py）前面，用上了就认领，不再提示"不能烹饪"。
"""
from . import StoveSwap
from .EventRegistry import registerHandler
from .Helpers.Engine import compFactory, levelId, GetCarriedItem, SetCarriedItem
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import GetItemType
from .Helpers.Player import IsCreative, SetNotCreateItem, SetPlayerUsedCD
from ..Shared.Data.Remainders import CRAFT
from ..Shared.Rules import CuttingStation, GrillBlocks


def _wear(playerId, itemDict, dimensionId, pos):
    """hurtAndBreak(1)：创造模式不磨；不会坏的东西不碰（网易的物品字典里不会坏的东西耐久是 0，照减会把它"用坏"）；耐久附魔免掉的这一下不磨
    （CuttingStation.ignoresWear，和砧板的刀一样）；用到 0 破碎、手空了。不走 Player.SetCarriedDurability：它按引擎的物品类型挡掉 "" 和 block，
    打火石的类型引擎怎么答没处核对，不能让它悄悄不磨。"""
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(itemDict["newItemName"], itemDict.get("newAuxValue") or 0) or {}
    held = GetCarriedItem(playerId, True) or itemDict
    if IsCreative(playerId) or (info.get("maxDurability") or 0) <= 0 or held.get("durability") is None or CuttingStation.ignoresWear(held):
        return
    held["durability"] -= 1
    if held["durability"] <= 0:
        ToAllPlayerPlaySound(dimensionId, pos, "random.break")
        SetCarriedItem(playerId, None)
    else:
        SetCarriedItem(playerId, held)


def _spend(playerId, itemDict, cost, dimensionId, pos):
    """用掉手里的东西：磨损 / 少一个（创造模式不少）/ 换成剩余物（非创造，JE 的 setItemInHand(getCraftingRemainingItem)）。"""
    if cost == GrillBlocks.WEAR:
        _wear(playerId, itemDict, dimensionId, pos)
    elif cost == GrillBlocks.SPEND:
        SetNotCreateItem(playerId, itemDict)
    elif cost == GrillBlocks.EMPTY and not IsCreative(playerId) and CRAFT.get(itemDict["newItemName"]):
        SetCarriedItem(playerId, {"newItemName": CRAFT[itemDict["newItemName"]], "newAuxValue": 0, "count": 1})


@registerHandler("ServerItemUseOnEvent", match=GrillBlocks.isGrill, priority=11)
def OnStoveFire(args):
    itemDict = args["itemDict"]
    blockName = args["blockName"]
    use = GrillBlocks.useOf(GrillBlocks.isLit(blockName), itemDict["newItemName"], GetItemType(itemDict))
    twin = GrillBlocks.twinOf(blockName)
    playerId = args["entityId"]
    if use is None or twin is None or compFactory.CreatePlayer(playerId).isSneaking() is True:
        return
    args["ret"] = True                                 # 引擎自己那一下（放火、倒水）不要，按住右键每刻重发时也一样
    if SetPlayerUsedCD(playerId) is True:
        return True
    pos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    if not StoveSwap.swap(dimensionId, pos, twin):
        return True                                    # 没换成（区块没加载）：什么也不用掉
    ToAllPlayerPlaySound(dimensionId, pos, use[2])
    _spend(playerId, itemDict, use[1], dimensionId, pos)
    return True
