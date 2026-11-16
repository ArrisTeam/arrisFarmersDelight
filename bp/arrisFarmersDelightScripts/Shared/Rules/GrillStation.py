# -*- coding: utf-8 -*-
"""GrillStation - 炉灶站点的纯规则：六个烤位在哪、一面多久、提示文字（双端）

对应 Hands-On Delight：station/StoveCooking.java 的 sideTicks 与 StoveStation 的数据；每个烤位的两面进度在 HandsOn/Grill.py。
炉灶一件 30 秒（和 JE 一样按营火配方的 600 刻，Server/Stove.py），手放的一件按 Grill.sideSeconds 算一面：30 / 1.5 / 2 = 10 秒；不看批量。
能烤什么、蛋只烤一面和煎锅同一张表（PanStation）。烤位坐标与 Shared/Rules/BlockDisplay.STOVE_SLOTS 一致（方块内的比例）。
"""
from ..Data.Cooking import StoveList
from .BlockDisplay import STOVE_SLOTS
from .HandsOn import Grill
from .PanStation import canFry as canGrill, friedOf as grilledOf, isOneSided  # noqa: F401 - 炉灶与煎锅同一张表

STATION_ID = "arris:stove"
STOVE_BLOCKS = StoveList          # 同一个列表对象：附属包追加的炉灶也开站
RECIPE_SECONDS = 30.0             # FD 原样烤一件要多久（Server/Stove.py 的 COOK_TIMER，JE 的营火配方 600 刻）
PLACES = len(STOVE_SLOTS)


def sideSeconds():
    return Grill.sideSeconds(RECIPE_SECONDS)


def slotCenter(place):
    """第 place 个烤位在方块里的位置（方块内的比例 x, z）。"""
    return STOVE_SLOTS[place]


def statusText(data):
    """站点数据（slots：每个烤位 {item, done, byHand, down, up, oneSided}）-> 焦点界面底部的一行提示。"""
    slots = [slot for slot in (data.get("slots") or []) if slot.get("item")]
    if not slots:
        return "点下方物品栏把食材摆上灶台（每格一个）   潜行右键 = 原来的玩法"
    if any(slot.get("done") for slot in slots):
        return "烤好的点一下取下   金线标着的那件该翻了：点它翻面"
    if any(waitsToTurn(slot) for slot in slots):
        return "金线标着的那件该翻了：点它翻过来"
    if all(not slot.get("byHand") for slot in slots):
        return "灶台在自己一件一件地烤   点一下食物 = 翻面（从此两面分开烤）"
    return "正在烤贴着灶台的那面   点一下食物 = 翻面"


def waitsToTurn(slot):
    """这件该翻了：手放的、两面的食材，贴灶台那面熟了、朝上那面还生。"""
    return slot.get("byHand") and not slot.get("oneSided") and (slot.get("down") or 0.0) >= 1.0 \
        and (slot.get("up") or 0.0) < 1.0
