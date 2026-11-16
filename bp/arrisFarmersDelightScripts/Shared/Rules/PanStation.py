# -*- coding: utf-8 -*-
"""PanStation - 煎锅站点的纯规则：能不能煎、蛋只煎一面、一面要多久、徽章与提示文字（双端）

对应 Hands-On Delight：station/SkilletCooking.java 的 takes / isOneSided / sideTicks 与 SkilletStation 的数据。
两面进度的状态机在 HandsOn/Frying.py。本移植的煎锅一件 6 秒（营火 30 秒的 20%，FD 原样），
手放的一批按 Frying.sideSeconds 算一面：6 * sqrt(件数) / 1.5 / 2，一件 2 秒一面、16 件 8 秒一面。
"""
from ..Data.Cooking import CanCookedFoodDict
from .HandsOn import Frying

STATION_ID = "arris:skillet"
PAN_BLOCKS = ("arris:skillet",)
SKILLET_SECONDS = 6.0                         # FD 原样煎一件要多久（Server/Skillet.py 的 COOK_TIMER 从 7 倒数到 1）
ONE_SIDED = frozenset(("minecraft:egg",))     # 只煎一面、不用翻（HoD 的 KitchenTags.ONE_SIDED）


def canFry(itemName):
    return itemName in CanCookedFoodDict


def friedOf(itemName):
    return CanCookedFoodDict.get(itemName)


def isOneSided(itemName):
    return itemName in ONE_SIDED


def sideSeconds(batch):
    return Frying.sideSeconds(SKILLET_SECONDS, batch)


def badgeOf(data):
    """站点数据 -> 顶部徽章：锅里的东西 + 贴锅这面的进度（翻过面就从头涨）；没有星星。空锅 None。"""
    item = data.get("item")
    if not item or not item.get("newItemName"):
        return None
    progress = None if data.get("done") or not data.get("byHand") else data.get("down") or 0.0
    return {"item": item, "stars": None, "progress": progress}


def statusText(data):
    """站点数据 -> 焦点界面底部的一行提示。"""
    item = data.get("item")
    if not item or not item.get("newItemName"):
        return "点下方物品栏把食材放进锅里（最多 16 个）   潜行右键 = 原来的玩法"
    if data.get("done"):
        return "煎好了：点一下锅里的食物取出"
    if not data.get("heated"):
        return "锅下面没有热源：放在炉灶、营火或岩浆块上"
    if not data.get("byHand"):
        return "锅在自己一件一件地煎   按住锅往上一甩：整批一起煎   点一下 = 取出"
    if data.get("oneSided"):
        return "只煎一面，不用翻   点一下 = 取出"
    if (data.get("down") or 0.0) >= 1.0 and (data.get("up") or 0.0) < 1.0:
        return "这面煎好了：按住锅往上一甩翻面"
    side = "第二面" if (data.get("up") or 0.0) >= 1.0 else "第一面"
    return "正在煎%s（这批 %d 个）   按住锅往上一甩 = 翻面   点一下 = 取出" % (side, data.get("batch") or 1)
