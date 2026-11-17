# -*- coding: utf-8 -*-
"""PotContainer - 厨锅容器格与预览槽的读写：食材、出一份、加份数、装碗转出、记煮了几份给经验（服务端）

容器格：0-5 食材，6 容器（碗等），7 成品。煮好的成品先进方块实体数据里的预览槽 previewItemSlot，
容器格里有对应容器时再转到 7 号格（MoveFinishedMeals）。FD 原样的烹饪（Server/CookingPot.py）、
手工烹饪（Server/HandCooking.py）和厨锅站点（Compat/Diegesis/PotLogic.py）都经这里改锅里的东西。
站点的槽组 ingredients / served 经 ContainerSlots 直接绑在 0-5 与 7 号容器格上（前置包的 bindSlots）。
煮了几份记在方块实体数据 potUsed（{成品名: 份数}，随锅存档，FD 的 usedRecipeTracker）：盛出时按它给经验（awardExperience）。
"""
import random

from .Engine import compFactory, levelId, System
from ...Shared.Rules import CookingPot as CookingPotRules
from ...Shared.Rules import ItemUserData

INPUT_SLOTS = 6
VESSEL_SLOT = 6
RESULT_SLOT = 7
USED_KEY = "potUsed"


_maxStacks = {}      # (物品名, aux) -> 堆叠上限：运行中不会变，锅每步都要问
_TEXT = type(u"")    # py2 的 unicode；py3 里就是 str


def plain(text):
    """要写进方块实体数据或玩家 ExtraData 的名字转成 str：值和键是 py2 的 unicode 时引擎只打日志、不存（见 Engine.py 的说明）。"""
    return text.encode("utf-8") if _TEXT is not str and isinstance(text, _TEXT) else text


def maxStackOf(itemName, auxValue=0):
    key = (itemName, auxValue or 0)
    if key not in _maxStacks:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(itemName, key[1])
        _maxStacks[key] = (info or {}).get("maxStackSize") or 64
    return _maxStacks[key]


def inputs(dimensionId, blockPos):
    """6 个食材格（空格是 {}）。连 userData 一起读（GetContainerItem 的第四个参数 getUserData 缺省是 False）：改过名、带自定义数据的料，
    摆开、退回、煮掉一部分写回去时数据跟着走（JE 的物品栈本来就带），不然一写回去就被抹掉。"""
    itemComp = compFactory.CreateItem(levelId)
    return [itemComp.GetContainerItem(blockPos, index, dimensionId, True) or {} for index in range(INPUT_SLOTS)]


def _storable(item):
    """写回容器格的物品：没有 userData（引擎读出来是 None）的不带这个键，和以前写的一样；有数据的原样带着。"""
    if item and "userData" in item and item["userData"] is None:
        return dict((key, value) for key, value in item.items() if key != "userData")
    return item


def setInputs(dimensionId, blockPos, before, after):
    """把食材格从 before 改成 after，只写变了的格子。"""
    itemComp = compFactory.CreateItem(levelId)
    for index in range(INPUT_SLOTS):
        old, new = before[index] or {}, after[index] or {}
        if (old.get("newItemName"), old.get("newAuxValue"), old.get("count")) != \
                (new.get("newItemName"), new.get("newAuxValue"), new.get("count")):
            itemComp.SpawnItemToContainer(_storable(new) if new.get("count", 0) > 0 else {}, index, blockPos, dimensionId)


class ContainerSlots(object):
    """前置包 bindSlots 要的存储（size / get / set）：方块自己的容器格 start .. start + count - 1。
    站点读写它就是读写方块的容器：漏斗、经典界面、别的玩家看到的是同一份。get 空格返回 None。"""

    def __init__(self, dimensionId, blockPos, start, count):
        self.dimensionId = dimensionId
        self.blockPos = tuple(blockPos)
        self.start = start
        self.count = count

    def size(self):
        return self.count

    def get(self, index):
        """也带 userData（站点里拿起来、放回去、并进同一叠，数据都不丢）；放不进站点载荷的（Shared/Rules/ItemUserData）照旧不带，
        内核把格子里的物品原样编进状态，编不了会让这口锅的站点同步出错。"""
        item = compFactory.CreateItem(levelId).GetContainerItem(self.blockPos, self.start + index, self.dimensionId, True)
        if not item or not item.get("newItemName") or item.get("count", 0) <= 0:
            return None
        if not ItemUserData.fitsWire(item.get("userData")):
            item = dict((key, value) for key, value in item.items() if key != "userData")
        return item

    def set(self, index, item):
        stored = _storable(item) if item and item.get("count", 0) > 0 else {}
        compFactory.CreateItem(levelId).SpawnItemToContainer(stored, self.start + index, self.blockPos, self.dimensionId)


def resultItem(dimensionId, blockPos):
    return compFactory.CreateItem(levelId).GetContainerItem(blockPos, RESULT_SLOT, dimensionId) or {}


def setResultItem(dimensionId, blockPos, item):
    compFactory.CreateItem(levelId).SpawnItemToContainer(item or {}, RESULT_SLOT, blockPos, dimensionId)


def preview(blockEntityData):
    """预览槽里煮好还没装碗的成品（{} 表示空）。"""
    previewList = blockEntityData["previewItemSlot"] or [{}]
    item = previewList[0] if previewList else {}
    return item if item and item.get("newItemName") and item.get("count", 0) > 0 else {}


def setPreview(blockEntityData, item):
    # 改了嵌套字典必须整体回写，否则区块卸载后恢复原值
    blockEntityData["previewItemSlot"] = [item] if item and item.get("count", 0) > 0 else [{}]


def addMeals(blockEntityData, meal, count):
    """预览槽加 count 份 meal（预览槽空着或已是同一道菜）。"""
    current = preview(blockEntityData)
    if current:
        current["count"] += count
        setPreview(blockEntityData, current)
    else:
        setPreview(blockEntityData, {"newItemName": meal["newItemName"], "newAuxValue": meal.get("newAuxValue", 0),
                                     "count": count})


def spill(dimensionId, blockPos, item):
    """用料剩下的空容器掉在锅上方（FD 的 ejectIngredientRemainder：厨师不在场、没人接时）。"""
    x, y, z = blockPos
    System.CreateEngineItemEntity(item, dimensionId, (x + 0.5, y + 1.0, z + 0.5))


def cookOnce(dimensionId, blockPos, blockEntityData, slots, meal, pushItemList, times=1, sink=None):
    """煮出 times 份：每个非空食材格扣 times 件（slots 就地更新），吐出余料，预览槽加 times 份成品，记下煮了 times 份。
    sink(物品) 返回真表示余料有人接了（厨师在工位时交给他）；没人接就 spill 掉在锅上方。"""
    for pushItem in pushItemList or []:
        output = {"newItemName": pushItem[0], "newAuxValue": pushItem[1], "count": times}
        if sink is None or not sink(output):
            spill(dimensionId, blockPos, output)
    itemComp = compFactory.CreateItem(levelId)
    for index, item in enumerate(slots):
        if not item:
            continue
        item["count"] -= times
        itemComp.SpawnItemToContainer(_storable(item) if item["count"] > 0 else {}, index, blockPos, dimensionId)
        if item["count"] <= 0:
            slots[index] = {}
    addMeals(blockEntityData, meal, times * (meal.get("count") or 1))
    addUsed(blockEntityData, meal["newItemName"], times)


def addUsed(blockEntityData, resultName, times):
    """记下这道菜又煮了 times 份（FD 的 usedRecipeTracker；整体回写才会存档）。"""
    used = dict((plain(name), count) for name, count in (blockEntityData[USED_KEY] or {}).items())
    used[plain(resultName)] = used.get(plain(resultName), 0) + times
    blockEntityData[USED_KEY] = used


def spawnOrb(value, where, dimensionId):
    """在 where 放一个 value 点经验的经验球。"""
    if value <= 0:
        return
    orbId = System.CreateEngineEntityByTypeStr("minecraft:xp_orb", where, (0, 0), dimensionId)
    if orbId:
        compFactory.CreateExp(orbId).SetOrbExperience(value)


def awardExperience(blockEntityData, where, dimensionId):
    """把记着的份数换成经验球放在 where，记着的清零（FD 的 awardUsedRecipes）：每道菜按"煮了几份 x 一份的经验"，
    整数部分照给、零头按概率进一。煮了几份是按煮出来的算的，星星多送的份数不算。返回给了多少经验。"""
    used = blockEntityData[USED_KEY]
    if not used:
        return 0
    blockEntityData[USED_KEY] = None
    total = 0
    for name, times in used.items():
        total += CookingPotRules.experienceOrb(CookingPotRules.servingExperienceOf(name), times, random.random())
    spawnOrb(total, where, dimensionId)
    return total


def MoveFinishedMeals(blockEntityData, blockPos, dimensionId):
    """把预览槽里煮好的成品转到产出格；需要容器的成品同时消耗容器格里等量的容器。"""
    x, y, z = blockPos
    previewItemSlot = preview(blockEntityData)
    if not previewItemSlot:
        return
    resultItemName = previewItemSlot["newItemName"]
    resultAuxValue = previewItemSlot.get("newAuxValue", 0)
    recipeDict = CookingPotRules.findRecipeByResult(resultItemName)
    if recipeDict is None:
        return
    itemComp = compFactory.CreateItem(levelId)
    resultItemSlot = itemComp.GetContainerItem(blockPos, RESULT_SLOT, dimensionId)
    if resultItemSlot and resultItemSlot["newItemName"] != resultItemName:
        return
    resultCount = resultItemSlot["count"] if resultItemSlot else 0
    maxStackSize = maxStackOf(resultItemName, resultAuxValue)
    vessel = recipeDict.get("Vessel")
    vesselItemSlot = None
    if vessel:
        vesselItemSlot = itemComp.GetContainerItem(blockPos, VESSEL_SLOT, dimensionId, True)       # 剩下的容器写回去，数据跟着走
        # 只比较物品名（与旧实现一致）
        if not vesselItemSlot or vesselItemSlot.get("newItemName") != vessel[0]:
            return
    amount = CookingPotRules.transferAmount(previewItemSlot["count"], resultCount, maxStackSize,
                                            vesselItemSlot["count"] if vesselItemSlot else None)
    if amount <= 0:
        return
    if vesselItemSlot:
        vesselItemSlot["count"] -= amount
        itemComp.SpawnItemToContainer(_storable(vesselItemSlot) if vesselItemSlot["count"] > 0 else {}, VESSEL_SLOT, blockPos, dimensionId)
    resultDict = {"newItemName": resultItemName, "newAuxValue": resultAuxValue, "count": resultCount + amount, "enchantData": []}
    itemComp.SpawnItemToContainer(resultDict, RESULT_SLOT, blockPos, dimensionId)
    previewItemSlot["count"] -= amount
    setPreview(blockEntityData, previewItemSlot)
    awardExperience(blockEntityData, (x + 0.5, y + 1, z + 0.5), dimensionId)
