# -*- coding: utf-8 -*-
"""PotLiquidColor - 厨锅汤面的颜色与透明度计算（双端，纯函数）

移植自 Hands-On Delight：client/PotBehavior.java 的 colour / blend / showColour（1047-1111）、
client/FoodColors.java 的 mix（218-234），以及 Diegesis impl/client/fx/LiquidRenderer.java 的不透明度公式（49-53, 287, 333-335）。

颜色一律是 int：RGB 写 0xRRGGBB，ARGB 写 0xAARRGGBB（无符号 32 位；Java 里 0xF0 << 24 是负数，位模式相同）。
本模块不读任何数据表：食物的颜色（FoodColors.of / main / broth）由调用方算好传进来。时间一律是秒，长度是站点像素。
"""
import math

from .Mth import lerp, roundInt

WATER_ALPHA = 0xA0           # 清水的 alpha（PotBehavior.java:137）
SOUP_ALPHA = 0xF0            # 煮好的汤的 alpha：越煮越稠（PotBehavior.java:138）
OOZE_ALPHA = 0xE0            # 怪物锅的黏液，没下料就几乎和汤一样稠（PotBehavior.java:140）
OOZE_TAKES = 0.35            # 怪物锅的黏液最多取食物颜色的这么多（PotBehavior.java:141）
RAW_TINT = 0.3               # 还没煮，水已经带了这么多食物的颜色（PotBehavior.java:143）
POURED_SHARE = 0.6           # 倒进去的液体（牛奶等）夺走水色的比例（PotBehavior.java:314）
FALLBACK = 0xB0A070          # 没有食物时 FoodColors.mix 的兜底色（FoodColors.java:23）
DEFAULT_BIOME_WATER = 0x44AFF5   # 查不到所在群系的水色（接口没回、别的模组的群系）时的缺省：基岩版引擎自己的缺省水色，平原也是它（JE 平原是 0x3F76E4），见 Rules/PotWater.py
BUBBLE_ALPHA = 0xE0          # 气泡颜色的 alpha（PotBehavior.java:1101）
BUBBLE_WHITEN = 0.6          # 气泡颜色 = 汤色往白色走这么多（PotBehavior.java:1101）
STEAM_COLOR = 0x6CFFFFFF     # 锅的蒸汽比库里的更白（PotBehavior.java:118）
WATER_WAKE_LIFE = 1.2        # 清水上拖尾留多久，秒（PotBehavior.java:191）
SOUP_WAKE_LIFE = 9.0         # 煮好的汤上拖尾留多久，秒（PotBehavior.java:192）
WATER_WAKE_CONTRAST = 0.25   # 清水上拖尾的清晰度 0..1（PotBehavior.java:193）
SOUP_WAKE_CONTRAST = 1.0     # 煮好的汤上拖尾的清晰度（PotBehavior.java:194）
SURFACE_PATH = 0.85          # 看穿液面的"路程"，不透明度公式里的指数（LiquidRenderer.java:53）
NEAR_PATH = 0.6              # 近侧壁（液面处）与随深度加的部分（LiquidRenderer.java:49-50）
NEAR_PATH_DEEP = 0.7
FAR_PATH = 0.35              # 远侧壁（里面）（LiquidRenderer.java:51-52）
FAR_PATH_DEEP = 0.35
CLEAR_MIN = 0.002            # 不透明度公式里"能透过多少"的下限（LiquidRenderer.java:287）
POT_DEPTH_SCALE = 3.25       # 厨锅水箱半高 (8.5 - 2) / 2，壁面随深度变暗的尺度（LiquidRenderer.java:141,326）


def argb(alpha, rgb):
    """alpha（0..255）与 0xRRGGBB 拼成 0xAARRGGBB。对应 `SOUP_ALPHA << 24 | soup`（PotBehavior.java:1075）。"""
    return ((alpha & 0xFF) << 24) | (rgb & 0xFFFFFF)


def blend(start, end, amount):
    """ARGB 逐通道（A、R、G、B）线性混合并四舍五入：start 往 end 走 amount（0..1，不夹）。

    对应 PotBehavior.java:1105-1111：每个通道 Math.round(Mth.lerp(amount, from, to))，Math.round 是 floor(x + 0.5)。
    注意 Java 的这个特性被原样保留：amount 很小时（帧率高）差不到 1 级的通道会原地不动。
    """
    result = 0
    for shift in (0, 8, 16, 24):
        low = (start >> shift) & 0xFF
        high = (end >> shift) & 0xFF
        result |= roundInt(lerp(amount, low, high)) << shift
    return result


def mixColors(colors):
    """若干 0xRRGGBB 的逐通道整数平均（向下取整）；一个都没有就是 FALLBACK。对应 FoodColors.mix（FoodColors.java:218-234）。"""
    red = green = blue = count = 0
    for color in colors:
        red += (color >> 16) & 0xFF
        green += (color >> 8) & 0xFF
        blue += color & 0xFF
        count += 1
    if count == 0:
        return FALLBACK
    return ((red // count) << 16) | ((green // count) << 8) | (blue // count)


def waterColor(biomeRgb=DEFAULT_BIOME_WATER, liquid=0):
    """没下料时汤面的底色 ARGB：生物群系的水色配 WATER_ALPHA；liquid（0xRRGGBB，非 0）是怪物锅的黏液，配 OOZE_ALPHA。

    对应 PotBehavior.java:1048-1049。
    """
    if liquid:
        return argb(OOZE_ALPHA, liquid)
    return argb(WATER_ALPHA, biomeRgb)


def brothTarget(water, foodColors, meal, progress, dishBroth=None, poured=(), liquid=0):
    """汤面这一刻该有的颜色：返回 (目标 ARGB, mottle)。对应 PotBehavior.colour（1047-1084），状态变了才算，不用每帧。

    water：waterColor() 的底色；foodColors：Java 里 `food` 列表里每件的 0xRRGGBB（有成品时只有成品那一件，
    否则是各食材格加上"盛出"格里的东西）；meal：锅里有煮好的菜；progress：进度控件 0..1；
    dishBroth：这些料做出的菜（或成品）的汤色 0xRRGGBB，不知道做什么菜就给 None（改用 foodColors 的平均）；
    poured：已经倒完的液体颜色列表（还没开始流的别给）——只在没有成品时染水；liquid 同 waterColor。
    mottle = 煮熟程度 cooked：没食物 0，没成品时 0.3 + 0.7 * progress，有成品 1。
    """
    if not meal:
        for liquidRgb in poured:
            water = blend(water, argb(SOUP_ALPHA, liquidRgb), POURED_SHARE)
    colour = water
    mottle = 0.0
    if meal or len(foodColors) > 0:
        cooked = 1.0 if meal else RAW_TINT + (1.0 - RAW_TINT) * progress
        soup = dishBroth if dishBroth is not None else mixColors(foodColors)
        colour = blend(water, argb(SOUP_ALPHA, soup), cooked * OOZE_TAKES if liquid else cooked)
        mottle = cooked
    return colour, mottle


def bubbleTint(shown):
    """气泡和边上泡泡的颜色 ARGB：shown（汤面此刻的显示色）往白走 0.6，alpha 固定 0xE0。对应 PotBehavior.java:1101。"""
    return (BUBBLE_ALPHA << 24) | (blend(shown, 0xFFFFFFFF, BUBBLE_WHITEN) & 0xFFFFFF)


def wakeLook(mottle):
    """拖尾的样子：(留多久（秒）, 清晰度 0..1)，随煮熟程度从清水走向汤。对应 PotBehavior.java:1081。"""
    return (lerp(mottle, WATER_WAKE_LIFE, SOUP_WAKE_LIFE), lerp(mottle, WATER_WAKE_CONTRAST, SOUP_WAKE_CONTRAST))


def clearness(alpha):
    """一份液体能透过多少的对数：ln(max(1 - alpha / 255, 0.002))。alpha 是 ARGB 的 A（0..255）。LiquidRenderer.java:287。"""
    return math.log(max(1.0 - alpha / 255.0, CLEAR_MIN))


def opacity(alpha, path=SURFACE_PATH):
    """看穿 path 份液体后的不透明度 0..1：1 - exp(ln(1 - alpha/255) * path)。液面 path = 0.85。

    清水 alpha 0xA0 -> 0.568（约 57%），煮好的汤 0xF0 -> 0.910（约 91%）。对应 LiquidRenderer.thickness（333-335）。
    """
    return 1.0 - math.exp(clearness(alpha) * path)


def wallLook(alpha, depth, inside=False, depthScale=POT_DEPTH_SCALE):
    """水箱侧壁在液面以下 depth（像素）处的 (明暗系数, 不透明度)：越深越暗越稠。LiquidRenderer.vertexOf（320-331）。

    inside=False 是从外面看近侧的壁（明暗 1 - 0.42 * deep），inside=True 是透过液体看到的远侧壁（0.8 - 0.3 * deep）。
    """
    deep = 1.0 - math.exp(-max(0.0, depth) / (depthScale * 1.1))
    if inside:
        return 0.8 - 0.3 * deep, opacity(alpha, FAR_PATH + FAR_PATH_DEEP * deep)
    return 1.0 - 0.42 * deep, opacity(alpha, NEAR_PATH + NEAR_PATH_DEEP * deep)


def toUnit(color):
    """ARGB -> (r, g, b, a)，各 0..1：给 variable.mod_soup_r/g/b/a 这类浮点变量用。"""
    return (((color >> 16) & 0xFF) / 255.0, ((color >> 8) & 0xFF) / 255.0, (color & 0xFF) / 255.0, ((color >> 24) & 0xFF) / 255.0)
