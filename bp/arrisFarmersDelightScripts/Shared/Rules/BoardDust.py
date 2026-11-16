# -*- coding: utf-8 -*-
"""BoardDust - 砧板每一下飞的碎屑：从哪起、朝哪飞、飞多快、散多开、几颗（双端，纯规则）

对应 Hands-On Delight：client/BoardBehavior.java 的 chopped（1410-1421）、blockDone（1474）、pop（1642-1650）。数一律是站点像素（16 = 1 格）和像素每秒，
站点是写成"玩家在北面"的那一份：+z 朝南，所以 (0, 1, -3) 是往上带着往厨师身前飘。一阵是 (起点, 初速, 散布, 个数)：
    起点        食物顶面上方（平躺 TOP + ITEM_SIZE / 16、方块 TOP + BLOCK_SIZE），x 是操作者落刀的位置（没传就是板面中心）；削皮从原木近侧、
                铲从方块近侧起
    初速        每种工具各一个向量；Diegesis 的粒子在它上面再加随机（0.25 倍长度、至少 0.3，高斯）
    散布        起点的随机范围（高斯，标准差是它的一半）
站点里的人按自己这边的站点坐标飞（BoardEffects），旁观的人按操作者的朝向转到世界坐标飞（BoardWatch），都由 BoardFx.puffAt 放。
"""
from .HandsOn import BoardScene as Scene
from .HandsOn import Cutting
from .HandsOn.BoardIcon import BLOCK_SIZE, ITEM_SIZE

# 每种工具的 (初速, 散布, 个数)；起点见 strokePuff
_STROKES = {
    Cutting.TOOL_CUT: ((0.0, 4.0, 0.0), 1.2, 4),
    Cutting.TOOL_CHOP: ((0.0, 5.0, 0.0), 1.6, 7),
    Cutting.TOOL_STRIP: ((0.0, 1.0, -3.0), 2.0, 12),          # 树皮从原木近侧往身前飘
    Cutting.TOOL_SMASH: ((0.0, 6.0, 0.0), 2.2, 10),
    Cutting.TOOL_DIG: ((0.0, 5.0, -3.0), 1.6, 9),
    Cutting.TOOL_PRY: ((0.0, 3.0, -1.0), 1.0, 4),
    Cutting.TOOL_SNIP: ((0.0, 2.0, 0.0), 0.8, 3),
}
BLOCK_DONE = ((0.0, 5.0, 0.0), 3.0, 18)       # 方块切到底：在方块中心炸开
BLOCK_DONE_DIG = 14                           # 铲的少几颗
FLOUR = ((0.0, 3.0, 0.0), 2.5, 12)            # 做成一道菜：面粉；冰棒是霜（初速 (0, 2, 0)）
FROST_VELOCITY = (0.0, 2.0, 0.0)


def topOf(block):
    """食物顶面离站点地面多高：平躺的图标 TOP + ITEM_SIZE / 16，方块类 TOP + BLOCK_SIZE。"""
    return Scene.TOP + (BLOCK_SIZE if block else ITEM_SIZE / 16.0)


def strokePuff(stroke, block, x, z, middleX, middleZ):
    """一刀的碎屑：stroke 是 Cutting.TOOL_*，(x, z) 是落刀的位置（站点像素），(middleX, middleZ) 是板面中心。返回 (起点, 初速, 散布, 个数)。"""
    velocity, spread, count = _STROKES.get(stroke) or _STROKES[Cutting.TOOL_CUT]
    top = topOf(block)
    if stroke == Cutting.TOOL_STRIP:
        at = (x, Scene.TOP + BLOCK_SIZE * 0.35, z)
    elif stroke == Cutting.TOOL_DIG:
        at = (x, Scene.TOP + BLOCK_SIZE * 0.6, middleZ - BLOCK_SIZE / 2.0)
    else:
        at = (x, top, z)
    return at, velocity, spread, count


def blockDonePuff(stroke, middleX, middleZ):
    """方块切到底（不是削皮）：在方块中心炸开；铲少几颗。"""
    velocity, spread, count = BLOCK_DONE
    return (middleX, Scene.TOP + BLOCK_SIZE / 2.0, middleZ), velocity, spread, BLOCK_DONE_DIG if stroke == Cutting.TOOL_DIG else count


def flourPuff(middleX, middleZ, frost=False):
    """菜做成时的面粉（冰棒是霜）：板面中心上方 1 像素。"""
    velocity, spread, count = FLOUR
    return (middleX, Scene.TOP + 1.0, middleZ), FROST_VELOCITY if frost else velocity, spread, count
