# -*- coding: utf-8 -*-
"""Skillet - 放置的煎锅：放入一叠食物、逐个煎熟弹出、取回（服务端）

煎锅物品放成方块（只有潜行才放）、方块里记着那一件煎锅、拆掉原样掉回在 Server/SkilletItem.py，放置本身在 Server/ItemToBlock.py（与派共用一份）。
锅里的东西只存在方块实体数据 cookingDict，画面由各客户端按广播自己渲染（Helpers/BlockItems.py），不再生成展示实体。
煎锅站点（场景交互前置在场时）手放的一批由 HandFrying.py 两面分开煎、等着颠锅；右键放进来的照这里一件一件煎。
一件煎多久照 JE（SkilletBlock.getSkilletCookingTime：6 秒，方块里那件煎锅带火焰附加 I 是 4 秒、II 起 3 秒）；
含水的煎锅（液体层有水）不能煎：放食物提示"被水泡着可没法烹饪啊……"，锅里已有的东西浮出来（JE SkilletBlockEntity.cookingTick：ItemUtils.dropItems，
每叠从方块里随机一点掉出来）。煎好的一件从锅心往上、往侧面带着初速弹出去（cookAndOutputItems:102-105，Helpers/Drops.PopFromPan）；拆了锅锅里的东西也是随机散出来
（SkilletBlock.onRemove 的 Containers.dropItemStack，Helpers/Drops.ScatterItem）。
右键放食物照 JE 的 addItemToCook：锅空着、或锅里是同一种（数据也一样）就放进去，叠到一叠的最大数量为止、剩下的留在手里，每放进去一次这一件的计时从头算；
别的放不进去，什么也不发生。放进去响一声挂灯，锅原本是空的又在热源上再响一声下料，空手取回不响（Shared/Rules/SkilletRules 的 SOUND_*）。
"""
import time

from . import HandFrying, PanLook, SkilletItem
from .EventRegistry import registerHandler
from .Helpers.BlockItems import DropLegacyDisplays, PublishSkillet
from .Helpers.Drops import PopFromPan, ScatterItem
from .Helpers.Engine import compFactory, levelId, GetBlockEntityData, GetBlockName, GetCarriedItem, SetCarriedItem, \
    ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Heat import RefreshHeat
from .Helpers.Items import CanStack, GetMaxStack
from .Helpers.Player import IsCreative, SetPlayerUsedCD
from ..Shared.Data.Cooking import CanCookedFoodDict
from ..Shared.Rules import SkilletRules as Rules
from ..Shared.Rules.BlockDisplay import modelCount
from ..Shared.Rules.Ticks import Pacer

SKILLET = "arris:skillet"
# 每件食物煎 6 秒：计时从 7 倒数到 1（没有火焰附加时；有的话起点见 _timerStart）
COOK_TIMER = 7
# 液体层里的水：JE 的 WATERLOGGED（含水的煎锅不能煎，锅里的东西浮出来）
_WATER = ("minecraft:water", "minecraft:flowing_water")
# 手里拿着这些物品点煎锅时拦截交互（不把它们当食物，也不在煎锅上放方块）
_BLOCKED_ITEMS = ("arris:spatula", "arris:cutting_board", "arris:cooking_pot", "arris:skillet_item")
# 每个煎锅每 TICK_STEP 秒处理一次（真实时间节拍，不受 /time set、doDaylightCycle false 影响），计时按步长累加
TICK_STEP = 0.25
_pacer = Pacer(TICK_STEP)


def _timerStart(blockEntityData):
    """一件食物的倒计时起点：JE SkilletBlock.getSkilletCookingTime（营火配方 600 刻 -> 6 秒，火焰附加 I 4 秒、II 起 3 秒）加 1，
    计时从起点倒数到 1 就是煎好。火焰附加看方块里记着的那件煎锅。"""
    return Rules.cookingSeconds(Rules.CAMPFIRE_TICKS, SkilletItem.fireAspectOf(blockEntityData)) + 1.0


def _isWaterlogged(dimensionId, blockPos):
    liquid = compFactory.CreateBlockInfo(levelId).GetLiquidBlock(blockPos, dimensionId)
    return bool(liquid) and liquid.get("name") in _WATER


@registerHandler("ServerBlockUseEvent", match=SKILLET)
def OnServerSkilletBlockUse(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimensionId"]
    playerId = args["playerId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    DropLegacyDisplays(blockEntityData)
    carriedDict = GetCarriedItem(playerId, True)
    if carriedDict:
        if carriedDict["newItemName"] in CanCookedFoodDict:
            _addFood(dimensionId, blockPos, blockEntityData, carriedDict, playerId)
        elif carriedDict["newItemName"] in _BLOCKED_ITEMS:
            # ServerBlockUseEvent 的拦截字段是 cancel（ret 属于 ServerItemUseOnEvent）
            args["cancel"] = True
        else:
            ShowTip(playerId, Rules.TIP_INVALID_ITEM)
        return
    cookingDict = blockEntityData["cookingDict"]
    if cookingDict:
        HandFrying.byFarmersDelight(dimensionId, blockPos, blockEntityData)
        if not IsCreative(playerId):                                # 取回没有声音；创造模式取下来的东西不给玩家，就这么没了（SkilletBlock.java:71-77）
            SetCarriedItem(playerId, cookingDict)
        blockEntityData["cookingDict"] = None
        PublishSkillet(dimensionId, blockPos, None)
    blockEntityData["cookTimer"] = _timerStart(blockEntityData)


def _addFood(dimensionId, blockPos, blockEntityData, carriedDict, playerId):
    """JE SkilletBlockEntity.addItemToCook：含水的提示；锅空着、或锅里是同一种（数据也一样）就放进去，叠到一叠的最大数量为止，剩下的留在手里。"""
    if _isWaterlogged(dimensionId, blockPos):
        ShowTip(playerId, Rules.TIP_UNDERWATER_BLOCK)
        return
    pan = blockEntityData["cookingDict"]
    have = pan["count"] if pan else 0
    if pan and not CanStack(pan, carriedDict):
        return
    moved = min(carriedDict["count"], GetMaxStack(carriedDict) - have)
    if moved <= 0:
        return
    HandFrying.byFarmersDelight(dimensionId, blockPos, blockEntityData)
    stack = dict(pan) if pan else dict(carriedDict)
    stack["count"] = have + moved
    blockEntityData["cookingDict"] = stack
    PublishSkillet(dimensionId, blockPos, stack)
    if not IsCreative(playerId):
        left = dict(carriedDict)
        left["count"] -= moved
        SetCarriedItem(playerId, left if left["count"] > 0 else None)
    blockEntityData["cookTimer"] = _timerStart(blockEntityData)
    center = (blockPos[0] + 0.5, blockPos[1] + 0.5, blockPos[2] + 0.5)
    if not pan and blockEntityData["heatEnable"] is True:          # 锅原本是空的又在热源上：先一声下料（SkilletBlockEntity.java:188-190）
        ToAllPlayerPlaySound(dimensionId, center, *Rules.SOUND_ADD_FOOD)
    ToAllPlayerPlaySound(dimensionId, center, *Rules.SOUND_PLACE)  # 每次放进去都再一声挂灯（SkilletBlock.java:83）


def _refreshSkilletHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName):
    if not RefreshHeat(blockEntityData, blockPos, belowPos, dimensionId, belowName):
        blockEntityData["cookTimer"] = _timerStart(blockEntityData)


@registerHandler("BlockNeighborChangedServerEvent", match=SKILLET)
def OnSkilletNeighborChanged(args):
    neighborPos = (args["neighborPosX"], args["neighborPosY"], args["neighborPosZ"])
    if neighborPos != (args["posX"], args["posY"] - 1, args["posZ"]):
        return
    blockPos = (args["posX"], args["posY"], args["posZ"])
    blockEntityData = GetBlockEntityData(args["dimensionId"], blockPos)
    if blockEntityData:
        # 营火点燃 / 熄灭时名字不变，这里每次都重新读状态
        _refreshSkilletHeat(blockEntityData, blockPos, neighborPos, args["dimensionId"], args["toBlockName"])


@registerHandler("ServerPlaceBlockEntityEvent", match=SKILLET)
def OnServerSkilletCreate(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    dimensionId = args["dimension"]
    ToAllPlayerPlaySound(dimensionId, blockPos, "dig.stone")
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if blockEntityData:
        SkilletItem.attachPending(blockEntityData, dimensionId, blockPos)
        belowPos = (args["posX"], args["posY"] - 1, args["posZ"])
        blockEntityData["cookTimer"] = _timerStart(blockEntityData)
        _refreshSkilletHeat(blockEntityData, blockPos, belowPos, dimensionId, GetBlockName(belowPos, dimensionId))


def _floodDrop(blockEntityData, dimensionId, blockPos):
    """JE cookingTick：含水的煎锅里的东西全部掉出来（不管熟没熟）。"""
    cookingDict = blockEntityData["cookingDict"]
    if not cookingDict:
        return
    HandFrying.byFarmersDelight(dimensionId, blockPos, blockEntityData)
    ScatterItem(dimensionId, blockPos, cookingDict)
    blockEntityData["cookingDict"] = None
    blockEntityData["cookTimer"] = _timerStart(blockEntityData)
    PublishSkillet(dimensionId, blockPos, None)


@registerHandler("ServerBlockEntityTickEvent", match=SKILLET)
def OnSkilletTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    now = time.time()
    if not _pacer.due((dimensionId, blockPos), now):
        return
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    _cook(dimensionId, blockPos, blockEntityData)
    if PanLook.enabled():
        # 世界外观广播（前置包在场时才开）：锅里的东西、热源、两面熟度变了就发给附近的人
        PanLook.tick(dimensionId, blockPos, blockEntityData, HandFrying.handOf(dimensionId, blockPos, blockEntityData), now)


def _cook(dimensionId, blockPos, blockEntityData):
    if _isWaterlogged(dimensionId, blockPos):
        _floodDrop(blockEntityData, dimensionId, blockPos)
        return
    if blockEntityData["heatEnable"] is not True:
        return
    hand = HandFrying.peek(dimensionId, blockPos)
    if hand is None and blockEntityData[HandFrying.SAVE_KEY]:
        hand = HandFrying.handOf(dimensionId, blockPos, blockEntityData)      # 重启之后：存档里有两面进度，接着煎
    if hand is not None and HandFrying.fry(hand, dimensionId, blockPos, blockEntityData, TICK_STEP, SkilletItem.fireAspectOf(blockEntityData)):
        return
    cookingDict = blockEntityData["cookingDict"]
    if not cookingDict or cookingDict.get("newItemName") not in CanCookedFoodDict:
        return
    if blockEntityData["cookTimer"] is None:
        blockEntityData["cookTimer"] = _timerStart(blockEntityData)
    blockEntityData["cookTimer"] -= TICK_STEP
    if blockEntityData["cookTimer"] > 1.0:
        return
    stack = GetMaxStack(cookingDict)
    layersBefore = modelCount(cookingDict["count"], stack)       # 展示的层数（FD 的 getModelCount）：变了才重发
    cookingDict["count"] -= 1
    blockEntityData["cookTimer"] = _timerStart(blockEntityData)
    output = {"itemName": CanCookedFoodDict[cookingDict["newItemName"]], "auxValue": cookingDict.get("newAuxValue", 0), "count": 1}
    PopFromPan(dimensionId, blockPos, output)
    if cookingDict["count"] <= 0:
        blockEntityData["cookingDict"] = None
        PublishSkillet(dimensionId, blockPos, None)
    else:
        # 改了嵌套字典必须整体回写：只改取回来的字典，区块卸载后数量会恢复原样（刷熟食）
        blockEntityData["cookingDict"] = cookingDict
        if modelCount(cookingDict["count"], stack) != layersBefore:
            PublishSkillet(dimensionId, blockPos, cookingDict)


@registerHandler("BlockRemoveServerEvent", match=SKILLET)
def OnSkilletRemove(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    _pacer.forget((dimensionId, blockPos))
    HandFrying.forget(dimensionId, blockPos)
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if blockEntityData:
        DropLegacyDisplays(blockEntityData)
        cookingDict = blockEntityData["cookingDict"]
        if cookingDict:
            ScatterItem(dimensionId, blockPos, cookingDict)
        PublishSkillet(dimensionId, blockPos, None)
    # 方块的战利品表是空的，煎锅自己在这里掉（连耐久、附魔一起；方块实体丢了也掉一把新的，不能凭空没了）
    SkilletItem.dropStored(blockEntityData, dimensionId, blockPos)
