# -*- coding: utf-8 -*-
"""PotSync - 厨锅站点同步给客户端的东西：锅里的料、进度、星星、勺子，以及快捷栏抽屉（服务端）

站点数据（state.setData，进度和星星每秒 4 次）：inputs 6 格料、dish 这些料能做的菜、meal / meals 煮好待盛的菜和份数、
vesselName 盛它要的容器名、heated、batch 这批几份、mode 煮法（PotCooking 的 WAITING / FD_WAY / STIRRED）、
progress 0..1、left 还要几秒、stirring、stars、open 厨师开放的星数、spoon 勺尖 [x, z]、grade / bonus 上一批的星和多送的份数。
"""
from ...Server import HandCooking
from ...Server.Helpers import PotContainer
from ...Server.Helpers.Engine import compFactory, levelId, ItemPosType
from ...Shared.Rules import CookingPot as CookingPotRules
from ...Shared.Rules import PotStation as Rules
from ...Shared.Rules.HandsOn import PotCooking

HOTBAR = 9


def wire(item):
    if not Rules.keyOf(item):
        return {}
    return {"newItemName": item["newItemName"], "newAuxValue": item.get("newAuxValue") or 0, "count": item["count"]}


def vesselOf(meal):
    """盛这道菜要的容器 (物品名, aux)，不要容器返回 None。"""
    recipe = CookingPotRules.findRecipeByResult(meal["newItemName"]) if meal else None
    return recipe.get("Vessel") if recipe else None


def drawerItems(playerId):
    """快捷栏 9 格里能下锅的料，别的格子是 {}。"""
    itemComp = compFactory.CreateItem(playerId)
    items = []
    for slot in range(HOTBAR):
        item = itemComp.GetPlayerItem(ItemPosType.INVENTORY, slot, True)
        kind = Rules.keyOf(item)
        items.append(wire(item) if kind and Rules.isIngredient(kind) else {})
    return items


def stationData(dimensionId, pos, blockEntityData, hand, now):
    served, ready = PotContainer.resultItem(dimensionId, pos), PotContainer.preview(blockEntityData)
    meal = served or ready
    meals = sum(item["count"] for item in (served, ready) if item and item["newItemName"] == meal["newItemName"])
    vessel = vesselOf(meal)
    info = compFactory.CreateItem(levelId).GetItemBasicInfo(vessel[0], vessel[1]) if vessel else None
    progress = hand.clock.progress(Rules.COOK_SECONDS, hand.batch)
    speed = 1.0 if hand.mode == PotCooking.FD_WAY else PotCooking.batchSpeed(hand.batch)
    return {
        "inputs": [wire(item) for item in PotContainer.inputs(dimensionId, pos)],
        "dish": wire(hand.dish) if hand.dish else {},
        "meal": wire(meal) if meal else {},
        "meals": meals,
        "vesselName": (info or {}).get("itemName") or "",
        "heated": hand.heated,
        "batch": hand.batch,
        "mode": hand.mode,
        "progress": round(progress, 2),
        "left": PotCooking.cookSecondsLeft(Rules.COOK_SECONDS, progress, speed) if hand.batch > 0 else 0,
        "stirring": hand.clock.isStirred(now),
        "stars": round(hand.clock.skill.stars(now) * 20.0) / 20.0,
        "open": HandCooking.openStarsOf(hand.spoon.holder, hand.dish),
        "spoon": [round(hand.spoonAt[0], 2), round(hand.spoonAt[1], 2)],
        "grade": hand.clock.grade,
        "bonus": hand.clock.bonus,
    }
