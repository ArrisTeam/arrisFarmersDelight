# -*- coding: utf-8 -*-
"""PotServe - 盛菜：从锅里取一份、记"做过几份"、给经验；右键拿着容器直接盛（服务端）

站点的盛出（Compat/Diegesis/PotScoop.py）、从产出格取走（PotLogic.onTaken）和右键盛（经典玩法是 Server/CookingPotHost.py；
前置包在场时是站点拒绝开站那一下，PotLogic.onOpen）共用这里。对应 FD 的 useHeldItemOnMeal / CookingPotBlock.use 与 HoD 的
PotServing：手里拿着这道菜的容器（只比物品名）、锅里有煮好的菜：容器 -1，菜 -1 份，一份菜进背包（放不下掉在脚下），
算"做过一份"（开第 2、3 颗星用），不给经验（FD 的右键盛也不给）。站点的盛出和从产出格取走才给经验（HoD 的 served）。
"""
from . import HandCooking
from .Helpers import PotContainer
from .Helpers.Engine import GetBlockEntityData, GetCarriedItem, compFactory
from .Helpers.Fx import ToAllPlayerPlaySound
from .Helpers.Player import GiveOrDropItem, SetNotCreateItem, SetPlayerUsedCD
from ..Shared.Rules import CookingPot as CookingPotRules

TAKE_SOUND = "bucket.fill_water"      # 右键盛菜的声音（站点里的盛出由客户端按 scooped 事件自己放）


def vesselName(meal):
    """盛这份菜要的容器的物品名；菜不要容器（或没有菜）返回 None。"""
    vessel = CookingPotRules.vesselOf(meal["newItemName"]) if meal else None
    return vessel[0] if vessel else None


def takeServing(blockEntityData):
    """从预览槽里取一份（1 个）：返回这份菜的物品字典；没有菜返回 None。"""
    meal = PotContainer.preview(blockEntityData)
    if not meal:
        return None
    dish = {"newItemName": meal["newItemName"], "newAuxValue": meal.get("newAuxValue") or 0, "count": 1}
    meal["count"] -= 1
    PotContainer.setPreview(blockEntityData, meal)
    return dish


def served(playerId, dimensionId, blockEntityData, dish, count):
    """玩家盛走（或从产出格取走）了 count 份 dish：记"做过几份"，并把锅里记着的经验在他脚下给他（FD 的 awardUsedRecipes：
    记着的是煮了几份，第一次盛走时一并给完，以后的盛走不再给）。"""
    HandCooking.addMade(playerId, dish["newItemName"], count)
    where = compFactory.CreatePos(playerId).GetFootPos()
    if where is not None and blockEntityData is not None:
        PotContainer.awardExperience(blockEntityData, where, dimensionId)


def serveByHand(playerId, dimensionId, blockPos):
    """右键盛菜（FD 的 CookingPotBlock.use）：手里是这道菜的容器、锅里有煮好的菜：盛一份，返回 True。
    手里不是它的容器、没有菜返回 False（那一下照常开界面 / 开站）；按住右键时引擎每刻重发，冷却内也返回 True（拦下但不重复盛）。"""
    data = GetBlockEntityData(dimensionId, blockPos)
    held = GetCarriedItem(playerId, True)
    name = vesselName(PotContainer.preview(data)) if data else None
    if not name or not held or held.get("newItemName") != name or (held.get("count") or 0) <= 0:
        return False
    if SetPlayerUsedCD(playerId):
        return True
    dish = takeServing(data)
    SetNotCreateItem(playerId, held)
    GiveOrDropItem(playerId, dish, dimensionId)
    HandCooking.addMade(playerId, dish["newItemName"], 1)
    ToAllPlayerPlaySound(dimensionId, blockPos, TAKE_SOUND)
    return True
