# -*- coding: utf-8 -*-
"""KitchenLooks - 食物被厨师动过之后的样子，各个站点一样：煎着的东西朝上那面的颜色（双端，纯计算）

移植自 Hands-On Delight：client/KitchenLooks.java 的 RAW_EGG / SHELL（25-27）、fryingTint（78-99）、mix（102-110）。
颜色是 32 位 ARGB 的非负整数（Java 的 int 在这里取无符号）。鸡蛋打开了从不躺在蛋壳里（画成煎蛋的样子）、液体倒出来容器不跟着进菜里
这两条要查物品标签（opened / isCracked / isPoured），标签在 Java 里是数据包，这里由调用方判断后把结果传进来。
基岩版的客户端掉落物不能染色，所以炉灶暂时用不上 fryingTint（见 StoveLook）；煎锅里的蛋、手持煎锅的画法可以拿它。
"""
from .Mth import roundInt

RAW_EGG = 0xC8E6E2D8         # 蛋打开了、蛋清还透亮时的颜色：有点透明、发灰（KitchenLooks.java:25）
SHELL = 0xFFEAD9B8           # 蛋壳碎片的颜色（27 行）
SEARED = 0xFFB8875C          # 肉和鱼朝上那面烤过的焦色（StoveBehavior.java:46，SkilletBehavior 用同一个）
SEAR = 0.7                   # 烤到全熟时朝上那面染到目标色的几成（47 行）


def mix(start, end, amount):
    """ARGB 的 start 往 end 走 amount（0..1），四个通道分别算，四舍五入（KitchenLooks.mix，102-110 行）。"""
    color = 0
    for shift in (0, 8, 16, 24):
        a = (start >> shift) & 0xFF
        b = (end >> shift) & 0xFF
        color |= (roundInt(a + (b - a) * amount) & 0xFF) << shift
    return color


def fryingTint(rawColor, cookedColor, cracked, meat, up, seared=SEARED, sear=SEAR):
    """朝上那面烤到 up（0..1）的一件的染色（fryingTint，78-99 行）。熟了（up >= 1）原样画熟的图（白色 = 不染）。
    蛋（cracked）：蛋清从透亮清成白，从不变褐；别的食物：从生的颜色往熟的颜色走（海带变深绿、土豆变金黄），
    肉和鱼（meat）在那之上再多一点焦色。rawColor、cookedColor 是生熟两张图的主色（FoodColors.main）。"""
    if up >= 1.0:
        return 0xFFFFFFFF
    done = max(0.0, up)
    if cracked:
        return mix(RAW_EGG, 0xFFFFFFFF, done)
    target = 0xFF000000
    for shift in (0, 8, 16):
        a = float(max(1, (rawColor >> shift) & 0xFF))
        b = float((cookedColor >> shift) & 0xFF)
        target |= roundInt(min(1.0, b / a) * 255.0) << shift
    if meat:
        target = mix(target, seared, 0.4)
    return mix(0xFFFFFFFF, target, done * sear)
