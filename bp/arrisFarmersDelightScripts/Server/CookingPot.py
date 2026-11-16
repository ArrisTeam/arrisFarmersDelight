# -*- coding: utf-8 -*-
"""CookingPot - 厨锅：放置、热源、烹饪 tick、配方书一键放入、拆掉时掉一口带着菜的厨锅（服务端）

容器格与预览槽的读写在 Helpers/PotContainer.py；每一步怎么煮（FD 原样一份一份，或厨师搅着整批）在 HandCooking.py；
每步煮完把锅的样子广播给附近的玩家在 PotLook.py（前置包在场时才开）。
"""
import copy
import time

from ..QuModLibs.Server import AllowCall, InjectHttpPlayerId
from . import CookingPotItem, HandCooking, PotLook
from .EventRegistry import registerHandler
from .Helpers import PotContainer
from .Helpers.Engine import compFactory, levelId, ItemPosType, GetBlockEntityData, GetBlockName
from .Helpers.Heat import RefreshHeat
from ..Shared.Rules.Ticks import Pacer

COOKING_POT = "arris:cooking_pot"
INPUT_SLOTS = PotContainer.INPUT_SLOTS
COOK_SECONDS = HandCooking.COOK_SECONDS
# 每个厨锅每 TICK_STEP 秒处理一次（约 5 Hz，真实时间节拍：不受 /time set、doDaylightCycle false 影响），计时按步长累加
TICK_STEP = 0.2
_pacer = Pacer(TICK_STEP)
# 配方书"一键放入"时玩家离厨锅的最远距离（格）
MAX_REACH = 8.0


@registerHandler("ServerPlaceBlockEntityEvent", match=COOKING_POT)
def OnServerCookingPotCreate(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    blockEntityData["previewItemSlot"] = [{}]
    blockEntityData["timer"] = COOK_SECONDS
    CookingPotItem.attachPending(blockEntityData, dimensionId, blockPos)      # 放下的这口锅带着菜（JE 的 BlockEntityTag）
    belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
    RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId), delay=0.1)


@registerHandler("BlockNeighborChangedServerEvent", match=COOKING_POT)
def OnCookingPotNeighborChanged(args):
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos != (args["posX"], args["posY"] - 1, args["posZ"]):
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    blockEntityData = GetBlockEntityData(args["dimensionId"], blockPos)
    if not blockEntityData:
        return
    # 营火点燃 / 熄灭时名字不变，这里每次都重新读状态
    RefreshHeat(blockEntityData, blockPos, neighborPos, args["dimensionId"], args["toBlockName"])


@registerHandler("ServerBlockEntityTickEvent", match=COOKING_POT)
def OnCookingPotTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    now = time.time()
    if not _pacer.due((dimensionId, blockPos), now):
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    PotContainer.MoveFinishedMeals(blockEntityData, blockPos, dimensionId)
    if blockEntityData["heatEnable"] is None:
        # /setblock、结构等方式放出的厨锅没有走放置事件，这里补上热源状态
        belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
        RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId))
    hand = HandCooking.handOf(dimensionId, blockPos, blockEntityData)
    slots = PotContainer.inputs(dimensionId, blockPos)
    HandCooking.cook(hand, dimensionId, blockPos, blockEntityData, slots, now, TICK_STEP)
    PotLook.tick(dimensionId, blockPos, blockEntityData, hand, slots, now)       # 世界外观广播（前置包在场时才开）


@AllowCall
@InjectHttpPlayerId
def CookingPotAddFood(playerId, args):
    # 配方书"放入食材"：把背包里指定下标的物品各取 1 个放进厨锅前几格。
    # 安全：playerId 由服务端注入；维度取玩家自己的；厨锅位置要真的是厨锅且在交互距离内；
    # 背包下标逐个校验，客户端只能决定"拿自己背包里的哪几格"
    if not playerId or not isinstance(args, dict):
        return
    blockPos = args.get("blockPos")
    indexList = args.get("indexList")
    if not isinstance(blockPos, (list, tuple)) or len(blockPos) != 3 or not isinstance(indexList, (list, tuple)):
        return
    blockPos = (int(blockPos[0]), int(blockPos[1]), int(blockPos[2]))
    dimensionId = compFactory.CreateDimension(playerId).GetEntityDimensionId()
    if GetBlockName(blockPos, dimensionId) != COOKING_POT:
        return
    playerPos = compFactory.CreatePos(playerId).GetFootPos()
    if playerPos is None:
        return
    dx, dy, dz = blockPos[0] + 0.5 - playerPos[0], blockPos[1] + 0.5 - playerPos[1], blockPos[2] + 0.5 - playerPos[2]
    if dx * dx + dy * dy + dz * dz > MAX_REACH * MAX_REACH:
        return
    _addFood(playerId, blockPos, dimensionId, indexList)


def _addFood(playerId, blockPos, dimensionId, indexList):
    itemComp = compFactory.CreateItem(levelId)
    inputItemSlot = [itemComp.GetContainerItem(blockPos, index, dimensionId) or {} for index in range(INPUT_SLOTS)]
    inventoryType = ItemPosType.INVENTORY
    playerAllItemList = compFactory.CreateItem(playerId).GetPlayerAllItems(inventoryType, True)
    changedInventory = {}
    changedSlots = set()
    for slotIndex, invIndex in enumerate(indexList[:INPUT_SLOTS]):
        if not isinstance(invIndex, int) or not 0 <= invIndex < len(playerAllItemList):
            break
        inventoryDict = playerAllItemList[invIndex]
        if not inventoryDict or inventoryDict.get("count", 0) <= 0:
            break
        slotItem = inputItemSlot[slotIndex]
        if not slotItem:
            slotItem = copy.deepcopy(inventoryDict)
            slotItem["count"] = 1
        elif (slotItem["newItemName"] == inventoryDict["newItemName"]
              and slotItem.get("newAuxValue", 0) == inventoryDict.get("newAuxValue", 0)):
            maxStackSize = itemComp.GetItemBasicInfo(slotItem["newItemName"], slotItem.get("newAuxValue", 0))["maxStackSize"]
            if slotItem["count"] >= maxStackSize:
                break
            slotItem["count"] += 1
        else:
            break
        inputItemSlot[slotIndex] = slotItem
        changedSlots.add(slotIndex)
        inventoryDict["count"] -= 1
        playerAllItemList[invIndex] = inventoryDict if inventoryDict["count"] > 0 else None
        changedInventory[(inventoryType, invIndex)] = playerAllItemList[invIndex]
    if not changedSlots:
        return
    compFactory.CreateItem(playerId).SetPlayerAllItems(changedInventory)
    for slotIndex in changedSlots:
        itemComp.SpawnItemToContainer(inputItemSlot[slotIndex], slotIndex, blockPos, dimensionId)


@registerHandler("BlockRemoveServerEvent", match=COOKING_POT)
def OnCookingPotRemove(args):
    # 厨锅没了：掉一口厨锅物品，预览槽里煮好还没装碗的那叠菜跟着它走（JE 的 copy_meal）；别的格子里的东西引擎照常掉
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    _pacer.forget((dimensionId, blockPos))
    HandCooking.forget(dimensionId, blockPos)
    PotLook.forget(dimensionId, blockPos)
    CookingPotItem.dropPot(GetBlockEntityData(dimensionId, blockPos), dimensionId, blockPos)
