# -*- coding: utf-8 -*-
"""EggLook - 煎蛋从生到熟的几档样子：蛋清从半透明的灰清成白（双端，纯规则）

JE：蛋不连壳躺在锅里，打开的蛋用煎蛋的图标，按 RAW_EGG（0xC8E6E2D8，半透明发灰）往白渐变着色（KitchenLooks.fryingTint 的 isCracked 一支：
mix(RAW_EGG, 白, 朝上那面煎到哪)），熟了（朝上那面到 1）原样画煎蛋（SkilletBehavior.drawPiece / StoveBehavior.draw）；蛋液落进锅时也是 RAW_EGG 着色。
基岩版的客户端掉落物没法着色，所以把几档的颜色烤进专用的小图标：STAGES 档，第 k 档是朝上那面煎到 k / STAGES 那一刻的颜色，
贴图由 tools/gen_egg_looks.py 从煎蛋的贴图按 JE 的着色规则（逐通道相乘，透明度也乘）生成。朝上那面每 1/12 重画一次（PanLayout.look），
三档的分界（1/3、2/3）正好落在其中。这些物品只用来画，不进创造栏、没有配方，也不会出现在任何容器里。
"""
from .HandsOn import KitchenLooks

STAGES = 3
ITEMS = tuple("arris:egg_look_%d" % stage for stage in range(STAGES))     # 第 0 档是刚打进来的蛋清，最后一档快熟了
FRIED = "arris:fried_egg"                                                   # 熟了：原样画煎蛋


def stageOf(up):
    """朝上那面煎到 up（0..1，没画过的 -1 当 0）对应第几档；熟了（>= 1）没有档，画煎蛋本身。"""
    if up >= 1.0:
        return None
    return min(STAGES - 1, int(max(0.0, up) * STAGES))


def itemOf(up):
    """这一刻蛋画成哪个物品：生到快熟是专用的小图标，熟了是煎蛋。"""
    stage = stageOf(up)
    return FRIED if stage is None else ITEMS[stage]


def tintOf(stage):
    """第 stage 档的颜色（ARGB）：JE 的 fryingTint 对蛋的那一支，朝上那面煎到 stage / STAGES。"""
    return KitchenLooks.fryingTint(0, 0, True, False, stage / float(STAGES))
