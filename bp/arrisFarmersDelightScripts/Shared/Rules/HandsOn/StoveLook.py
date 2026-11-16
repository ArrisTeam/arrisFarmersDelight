# -*- coding: utf-8 -*-
"""StoveLook - 烤架上一件长什么样：朝上那面烤到哪一档才重画、该画生的还是熟的、哪些件在冒汽、哪些在等着翻（双端，纯计算）

移植自 Hands-On Delight：client/StoveBehavior.java 的 look（186-188）、draw（190-211，画哪张图）、heat（273-282，分"在烤"和"等着翻"）。
一件的两面分开烤：贴烤架那面（down）先熟，熟了就等厨师翻（冒烟），翻过去之后原来熟的那面朝上（up = 1），另一面开始烤。
JE 把朝上那面烤到哪画成"生的图染上焦色、熟了换成熟的图"；基岩版的客户端掉落物不能染色，所以这里只有两种画法：
朝上那面没熟画生的，熟了画熟的（上面一整面都烤好了，另一面还在烤也一样）。炉灶不收蛋（NOT_ON_GRILL），只有蛋这类"单面"食材
才会朝上那面烤到一半，所以实际上朝上那面不是 0 就是 1。
"""
import math

from .. import EggLook

STEPS = 12                   # 朝上那面每烤 1/12 才重画一次（StoveBehavior.look，186-188）
DONE = 100                   # look() 里"熟了"的那一档
UNSEEN = -1                  # 还没画过 / 没有数据


def look(up):
    """朝上那面烤到 up（0..1）对应的一档：-1 = 没有数据，100 = 熟了，其余 floor(up * 12)。档变了才要重画。"""
    if up < 0.0:
        return UNSEEN
    if up >= 1.0:
        return DONE
    return int(math.floor(up * STEPS))


def isTopDone(up):
    """朝上那面熟了（draw 里的 done）：画熟的样子。"""
    return up >= 1.0


def shownName(rawName, cookedName, up, cracked=False):
    """这一件该画哪张图的物品名：朝上那面熟了画熟的（cookedName，没有配方的就是它自己），否则画生的。
    蛋（cracked）不连壳画：生到快熟是蛋清从灰清成白的几张专用小图标（EggLook），熟了是煎蛋（KitchenLooks.opened + fryingTint）。"""
    if cracked:
        return EggLook.itemOf(up)
    return cookedName if isTopDone(up) else rawName


def waits(byHand, down, up):
    """手放的、贴烤架那面熟了、朝上那面还生：这件在冒烟等着翻（StoveBehavior.heat，279-280）。"""
    return bool(byHand) and down >= 1.0 and up < 1.0


def sortHeat(pieces, now, turnedAt, flight=0.3):
    """烤着的件分成"在烤"（冒汽）和"等着翻"（冒烟）两组，返回 (cooking, waiting) 两个位置序号的列表（heat，273-282）。
    pieces[i] 是 None（没有东西 / 已经烤好 / 刚翻过还在空中）或 (byHand, down, up)；turnedAt[i] 是这件上次翻的时间。
    刚翻过（不到 flight 秒）的算还在空中，两组都不进。"""
    cooking, waiting = [], []
    for place in range(len(pieces)):
        piece = pieces[place]
        if piece is None or now - turnedAt[place] < flight:
            continue
        (waiting if waits(*piece) else cooking).append(place)
    return cooking, waiting
