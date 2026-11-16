# -*- coding: utf-8 -*-
"""PotSync - 厨锅站点同步给客户端的东西：控件（进度、星星、勺子……）与站点数据（服务端）

控件（都 locked，只有服务端写，变了才发；声明在 Shared/Rules/PotStation.buildSchema）：
    progress 0..1 / heated / stirring / spoon_x / spoon_z（世界朝向，-1..1，没人搅时是 0）/ stars 0..3
站点数据 data（Call 载荷：键 str、list 元素同类型）——共享的部分：
    dish    这些料现在能做的菜（物品线格式，count 是一份出几个）或 {}        meal   煮好待盛的菜（count 是份数）或 {}
    vessel  盛它的容器（物品线格式，count 1）或 {}，vessel_name 它的名字        cook_left  还要几秒（一位小数）
    batch   这批几份   mode  锅上一步的煮法（PotCooking 的 WAITING / FD_WAY / STIRRED）   grade / bonus  上一批的星数 / 多送的份数
    open_stars  厨师做这道菜开了几颗星（1..3；锅里没有可做的菜时是最后一次算的）   sunk  装着下锅就沉的料的食材格号
每位玩家自己的两项 made（他盛出过几份这道菜）、here（勺子在他手里）由 PotLogic.userData 合并进他收到的 data。
"""
from ...Server import HandCooking
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import compFactory, levelId
from ...Shared.Rules import CookingPot as CookingPotRules
from ...Shared.Rules import PotStation
from ...Shared.Rules.HandsOn import PotCooking

_vesselNames = {}      # (名字, aux) -> 物品的显示名


def wire(item):
    """物品线格式：空是 {}。"""
    if not PotStation.keyOf(item):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def vesselOf(meal):
    """盛这道菜要的容器 (物品名, aux)，不要容器返回 None。"""
    return CookingPotRules.vesselOf(meal["newItemName"]) if meal else None


def vesselName(vessel):
    key = (vessel[0], vessel[1])
    if key not in _vesselNames:
        info = compFactory.CreateItem(levelId).GetItemBasicInfo(key[0], key[1]) or {}
        _vesselNames[key] = info.get("itemName") or ""
    return _vesselNames[key]


def controls(hand, now):
    """六个控件现在该是什么值（没人搅时勺子在中间）。"""
    stirred = hand.clock.isStirred(now)
    return {"progress": hand.clock.progress(hand.total, hand.batch), "heated": 1.0 if hand.heated else 0.0,
            "stirring": 1.0 if stirred else 0.0, "spoon_x": hand.spoonAt[0] if stirred else 0.0,
            "spoon_z": hand.spoonAt[1] if stirred else 0.0, "stars": hand.clock.skill.stars(now)}


def sharedData(blockEntityData, hand, items):
    """站点数据里共享的部分。items 是站点里 6 个食材格（物品或 None）。"""
    meal = PotContainer.preview(blockEntityData)
    vessel = vesselOf(meal)
    progress = hand.clock.progress(hand.total, hand.batch)
    speed = 1.0 if hand.mode == PotCooking.FD_WAY else PotCooking.batchSpeed(hand.batch)
    dish = CookingPotRules.matchRecipe(items)[0] if any(items) else None     # 锅里的料现在做什么：按容器读，不等锅的下一步
    if dish:
        hand.lastOpen = HandCooking.openStarsOf(hand.spoon.holder, dish)
    return {
        "dish": wire(dish), "meal": wire(meal),
        "vessel": {"newItemName": vessel[0], "newAuxValue": vessel[1], "count": 1} if vessel else {},
        "vessel_name": vesselName(vessel) if vessel else "",
        "cook_left": round(hand.total * (1.0 - progress) / speed, 1) if hand.batch > 0 else 0.0,
        "batch": hand.batch, "mode": hand.mode, "grade": hand.clock.grade, "bonus": hand.clock.bonus,
        "open_stars": hand.lastOpen, "sunk": PotStation.sunkSlots(items),
    }


def dishNameOf(shared):
    """这口锅现在算"哪道菜"：能做的菜，没有就是煮好待盛的；都没有返回 None（"做过几份"按它查）。"""
    return (shared.get("dish") or shared.get("meal") or {}).get("newItemName")
