# -*- coding: utf-8 -*-
"""Stove - 炉灶顶上的 6 个烤位：放入、逐个烤熟弹出、熄火时冷却、破坏时掉落（服务端）

点着的（StoveList，下游可追加自己的炉灶）和熄着的（arris:stove_extinguish，Shared/Rules/GrillBlocks）炉灶都收食物、都掉东西，JE 的 AbstractStoveBlock.use
放食物不看 LIT；只有点着的会烤，熄着的 FD 原样的件每一步冷却（AbstractStoveBlockEntity.coolItems：进度每刻 -2，不低于 0），手放的件不动（HoD）。
点火 / 灭火换方块、数据带过去在 StoveSwap.py（用打火石、铲子等在 StoveFire.py）。
烤位上的东西只存在方块实体数据 "0".."5"，画面由各客户端按广播自己渲染（Helpers/BlockItems.py），不再生成展示实体。
炉灶站点（场景交互前置在场时）手放 / 手翻过的烤位由 HandGrill.py 两面分开烤、等着翻（进度存在方块实体数据 handGrill 里，重启后在第一次 tick 接上）；
右键放上去的照这里每件 30 秒烤好弹出。
站在点燃的炉灶上会被烫（JE 的 stepOn，规则在 Shared/Rules/StoveBurn.py；引擎事件 OnStandOnBlockServerEvent 要方块带 netease:on_stand_on）。
上面盖了东西（锅、煎锅、任何方块，Shared/Rules/StoveCover）：烤架上的东西全丢出来，生的熟的、手放的 FD 的都一样（FD 的 shouldDropItems）；
丢出来和拆炉灶掉的东西都是 FD 的 ItemUtils.dropItems：每件从方块里随机一点掉出来、带随机初速；烤好的从灶面弹出去（Helpers/Drops.py）。
烤架的世界外观（东西、冒烟等翻、烤好的汽和闪）每一步照 StoveLook 广播给附近的人，站点开不开着都一样。
"""
import time

from . import HandGrill, StoveLook, StoveSwap
from .EventRegistry import registerHandler
from .Helpers.BlockItems import DropLegacyDisplays, Publish, PublishStove
from .Helpers.Drops import PopOut, ScatterItem
from .Helpers.Engine import compFactory, GetBlockEntityData, GetBlockName, GetEngineTypeStr, IsLiving, ShowTip
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Items import GetItemType
from .Helpers.Player import SetPlayerUsedCD, SetNotCreateItem
from ..Shared.Data import Tips
from ..Shared.Data.Cooking import CanCookedFoodDict, StoveList
from ..Shared.Rules import GrillBlocks, StoveBurn, StoveCover
from ..Shared.Rules.BlockDisplay import KIND_STOVE
from ..Shared.Rules.Ticks import Pacer

STOVE_SLOTS = 6
# 每个烤位 30 秒（JE：炉灶按营火配方的 600 刻）：计时从 30 倒数到 0
COOK_TIMER = HandGrill.COOK_TIMER
# 拿着这些物品点炉灶时什么都不做（它们是要放到炉灶上的方块）
_PASS_ITEMS = ("arris:cutting_board", "arris:cooking_pot", "arris:skillet_item")
# 每个炉灶每 TICK_STEP 秒处理一次（真实时间节拍，不受 /time set、doDaylightCycle false 影响），计时按步长累加
TICK_STEP = 0.25
_pacer = Pacer(TICK_STEP)
# 烫伤的伤害类型：基岩版里最接近 JE hot_floor 的是 magma（岩浆块），fire_immune 的实体引擎对它免疫；
# 死亡信息是引擎的"死了"，网易的 Hurt 接口给不了 JE 那句"被烤的酥脆"
BURN_CAUSE = "magma"


def InitStoveData(blockEntityData):
    """炉灶 6 个烤位的默认数据；/setblock、结构放出的炉灶没走放置事件，用到时补上。"""
    for index in range(STOVE_SLOTS):
        blockEntityData[str(index)] = {"itemDict": None, "cookTimer": COOK_TIMER}


def EnsureStoveData(blockEntityData):
    if blockEntityData[str(STOVE_SLOTS - 1)] is None:
        InitStoveData(blockEntityData)


@registerHandler("ServerPlaceBlockEntityEvent", match=GrillBlocks.isGrill)
def OnServerStoveCreate(args):
    blockPos = (args["posX"], args["posY"], args["posZ"])
    if StoveSwap.apply(args["dimension"], blockPos):        # 点火 / 灭火换过来的：快照里的东西原样带过来，不是新放的空炉灶
        return
    blockEntityData = GetBlockEntityData(args["dimension"], blockPos)
    if blockEntityData:
        EnsureStoveData(blockEntityData)                      # 已经有数据的（带过来的）不覆盖；新放的是空的，补上默认值


def _freeSlot(blockEntityData):
    """序号最小的空烤位（FD 的 getNextEmptySlot）；都满了返回 None。"""
    for index in range(STOVE_SLOTS):
        slotData = blockEntityData[str(index)]
        if not (slotData and slotData.get("itemDict")):
            return index
    return None


# 优先级 10：ServerItemUseOnEvent 里最后处理（与旧版模块加载顺序一致，见 Server/ModServer.py）
@registerHandler("ServerItemUseOnEvent", match=GrillBlocks.isGrill, priority=10)
def OnServerStoveItemUse(args):
    itemDict = args["itemDict"]
    x, y, z = args["x"], args["y"], args["z"]
    dimensionId = args["dimensionId"]
    playerId = args["entityId"]
    if SetPlayerUsedCD(playerId) is True:
        return
    blockEntityData = GetBlockEntityData(dimensionId, (x, y, z))
    if not blockEntityData:
        return
    EnsureStoveData(blockEntityData)
    DropLegacyDisplays(blockEntityData)
    if StoveCover.covers(GetBlockName((x, y + 1, z), dimensionId)):
        ShowTip(playerId, Tips.STOVE_BLOCKED)
        return
    freeIndex = _freeSlot(blockEntityData)
    if freeIndex is None:
        return
    if itemDict["newItemName"] in CanCookedFoodDict:
        # 烤位上只放一件；先存一份数量为 1 的拷贝，SetNotCreateItem 会就地改手里那件的数量
        slotItem = dict(itemDict)
        slotItem["count"] = 1
        blockEntityData[str(freeIndex)] = {"itemDict": slotItem, "cookTimer": COOK_TIMER}
        hand = HandGrill.peek(dimensionId, (x, y, z))
        if hand is not None:
            hand.grill.farmersDelightsWay(freeIndex)
        SetNotCreateItem(playerId, itemDict)
        PublishStove(dimensionId, (x, y, z), blockEntityData)
        if StoveLook.enabled():
            StoveLook.event(dimensionId, (x, y, z), "placed", {"places": [freeIndex]})
            StoveLook.tick(dimensionId, (x, y, z), blockEntityData, hand, time.time())
        else:
            ToAllPlayerPlaySound(dimensionId, (x + 0.5, y + 0.5, z + 0.5), *GrillBlocks.SOUND_FOOD)       # FD 的 LANTERN_PLACE 0.5 / 1.0
    elif itemDict["newItemName"] not in _PASS_ITEMS and not GrillBlocks.isTool(itemDict["newItemName"], GetItemType(itemDict)):
        ShowTip(playerId, Tips.STOVE_INVALID_ITEM)


def _dropWhenCovered(dimensionId, blockPos, blockEntityData, hand):
    """上面盖了东西：烤架上的东西全丢出来（FD 的 AbstractStoveBlockEntity.serverTick：空炉灶不查，有东西才查）。丢了返回 True。"""
    if not any(HandGrill.slotItem(blockEntityData, index) for index in range(STOVE_SLOTS)):
        return False
    x, y, z = blockPos
    if not StoveCover.covers(GetBlockName((x, y + 1, z), dimensionId)):
        return False
    for index in range(STOVE_SLOTS):
        item = HandGrill.slotItem(blockEntityData, index)
        if item:
            ScatterItem(dimensionId, blockPos, item)
            blockEntityData[str(index)] = {"itemDict": None, "cookTimer": COOK_TIMER}
        if hand is not None:
            hand.grill.farmersDelightsWay(index)
    if hand is not None:
        HandGrill.save(hand, blockEntityData)
    PublishStove(dimensionId, blockPos, blockEntityData)
    return True


def _announceGrilled(dimensionId, blockPos, blockEntityData, hand):
    """刚烤好的几件告诉附近所有人：一团汽、金光、叮的一声（JE 的 EFFECT_GRILLED，站点开不开着都有）。"""
    while hand is not None and hand.just:
        place = hand.just.pop(0)
        StoveLook.event(dimensionId, blockPos, "grilled", {"place": place, "stack": StoveLook.wire(HandGrill.slotItem(blockEntityData, place))})


def _cool(blockEntityData, index, data):
    """熄着的炉灶上 FD 原样的一件冷却一步（GrillBlocks.cooledTimer）；没烤过的、已经凉透的不写。"""
    timer = data.get("cookTimer")
    cooled = GrillBlocks.cooledTimer(timer, TICK_STEP, COOK_TIMER)
    if cooled != timer:
        data["cookTimer"] = cooled
        blockEntityData[str(index)] = data


@registerHandler("ServerBlockEntityTickEvent", match=GrillBlocks.isGrill)
def OnStoveTick(args):
    dimensionId = args["dimension"]
    blockPos = (args["posX"], args["posY"], args["posZ"])
    now = time.time()
    if not _pacer.due((dimensionId, blockPos), now):
        return
    StoveSwap.apply(dimensionId, blockPos)               # 点火 / 灭火换过来、放置事件还没到的：先把带过来的东西写进去
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    EnsureStoveData(blockEntityData)
    lit = GrillBlocks.isLit(args.get("blockName") or GetBlockName(blockPos, dimensionId))
    hand = HandGrill.peek(dimensionId, blockPos) or HandGrill.restore(dimensionId, blockPos, blockEntityData)
    if _dropWhenCovered(dimensionId, blockPos, blockEntityData, hand):
        StoveLook.tick(dimensionId, blockPos, blockEntityData, hand, now)
        return
    handled, finished = HandGrill.grill(hand, blockEntityData, TICK_STEP, lit) if hand is not None else (set(), False)
    if hand is not None:
        HandGrill.save(hand, blockEntityData)
    for index in range(STOVE_SLOTS):
        data = blockEntityData[str(index)]
        if index in handled or not (data and data.get("itemDict")):
            continue
        if not lit:
            _cool(blockEntityData, index, data)              # 熄着：不烤，FD 原样的件冷却（AbstractStoveBlockEntity.serverTick:107 coolItems）
            continue
        data["cookTimer"] = (data.get("cookTimer") or COOK_TIMER) - TICK_STEP
        blockEntityData[str(index)] = data
        if data["cookTimer"] > 0:
            continue
        rawDict = data["itemDict"]
        cookedName = CanCookedFoodDict.get(rawDict["newItemName"])
        # 配方被附属包移除了：原样退回生食，别让它卡在烤位上
        output = {"itemName": cookedName, "auxValue": rawDict.get("newAuxValue", 0), "count": 1} if cookedName else rawDict
        blockEntityData[str(index)] = {"itemDict": None, "cookTimer": COOK_TIMER}
        PopOut(dimensionId, (args["posX"] + 0.5, args["posY"] + 1.0, args["posZ"] + 0.5), output)       # FD cookAndOutputItems:128-130
        finished = True
    settling = StoveSwap.settling(dimensionId, blockPos, now)
    if finished or settling:
        PublishStove(dimensionId, blockPos, blockEntityData)
    if settling:
        StoveLook.forget(dimensionId, blockPos)           # 刚换过方块的这一秒里每一步都重发：客户端的方块实体和场景在换方块时重建，先到的广播可能被盖掉
    if StoveLook.enabled():
        _announceGrilled(dimensionId, blockPos, blockEntityData, hand)
        StoveLook.tick(dimensionId, blockPos, blockEntityData, hand, now)


@registerHandler("OnStandOnBlockServerEvent", match=StoveList)
def OnStandOnStove(args):
    # JE AbstractStoveBlock.burnEntitySteppingOnStove：StoveList 里都是点燃的炉灶；每刻来一次，扎得太密由无敌帧（10 刻）挡着
    entityId = args["entityId"]
    if not IsLiving(entityId):
        return
    if GetEngineTypeStr(entityId) == "minecraft:player" and compFactory.CreatePlayer(entityId).isSneaking() is not False:
        return                                              # 潜行（读不到也按潜行算）：isSteppingCarefully
    foot = compFactory.CreatePos(entityId).GetFootPos()
    size = compFactory.CreateCollisionBox(entityId).GetSize()
    if foot is None or not size:
        return
    stovePos = (args["blockX"], args["blockY"], args["blockZ"])
    frostWalker = lambda: StoveBurn.hasFrostWalker(compFactory.CreateItem(entityId).GetEquItemEnchant(StoveBurn.FOOT_SLOT))
    if StoveBurn.burns(StoveBurn.touchesGrill(stovePos, foot, size[0], size[1]), False, True, frostWalker):
        compFactory.CreateHurt(entityId).Hurt(StoveBurn.DAMAGE, BURN_CAUSE, None, None, False)


@registerHandler("BlockRemoveServerEvent", match=GrillBlocks.isGrill)
def OnStoveRemove(args):
    blockPos = (args["x"], args["y"], args["z"])
    dimensionId = args["dimension"]
    if StoveSwap.claims(dimensionId, blockPos, args["fullName"], time.time()):
        return                                                # 点火 / 灭火换方块：东西跟着带过去，不是拆了（StoveSwap）
    _pacer.forget((dimensionId, blockPos))
    HandGrill.forget(dimensionId, blockPos)
    StoveLook.forget(dimensionId, blockPos)
    blockEntityData = GetBlockEntityData(dimensionId, blockPos)
    if not blockEntityData:
        return
    for index in range(STOVE_SLOTS):
        data = blockEntityData[str(index)]
        itemDict = data.get("itemDict") if data else None
        if itemDict:
            ScatterItem(dimensionId, blockPos, itemDict)
    DropLegacyDisplays(blockEntityData)
    Publish(dimensionId, blockPos, KIND_STOVE, {})
