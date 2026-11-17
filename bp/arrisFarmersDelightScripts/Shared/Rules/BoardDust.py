# -*- coding: utf-8 -*-
"""BoardDust - 砧板每一下飞的碎屑：从哪起、朝哪飞、飞多快、散多开、几颗（双端，纯规则）

对应 Hands-On Delight：client/BoardBehavior.java 的 chopped（1410-1421）、blockDone（1474）、pop（1642-1650）。数一律是站点像素（16 = 1 格）和像素每秒，
站点是写成"玩家在北面"的那一份：+z 朝南，所以 (0, 1, -3) 是往上带着往厨师身前飘。一阵是 (起点, 初速, 散布, 个数)：
    起点        食物顶面上方（平躺 TOP + ITEM_SIZE / 16、方块 TOP + BLOCK_SIZE），x 是操作者落刀的位置（没传就是板面中心）；削皮从原木近侧、
                铲从方块近侧起
    初速        每种工具各一个向量；Diegesis 的粒子在它上面再加随机（0.25 倍长度、至少 0.3，高斯）
    散布        起点的随机范围（高斯，标准差是它的一半）
站点里的人按自己这边的站点坐标飞（BoardEffects），旁观的人按操作者的朝向转到世界坐标飞（BoardWatch），都由 BoardFx.puffAt 放。
经典玩法（没有站点的 FD 原样砧板）每切一件飞的 5 颗碎屑是另一套，在文件末尾（CRUMB_*）。
"""
from .HandsOn import Assembly
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
FLOUR_KIND, FROST_KIND = "flour", "frost"
# 做成这几样的菜不飞面粉（pop，1640-1646）：拌的沙拉、摆在碗里的套餐 / 盛宴（食物自己颜色的碎屑飞出来是绿的）、一起切开的（碎屑刀上已经飞过了）。
# 用元组、不用集合：旁观的人收到的 finish 是服务端发来的，坏数据（不能哈希的）照样能比
NO_CRUMBS = (Assembly.FINISH_TOSS, Assembly.FINISH_ARRANGE, Assembly.FINISH_CHOP)


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


def crumbsOf(finish):
    """做成一道菜时飞什么（pop，1640-1648）：冰棒是霜（FROST_KIND）；拌 / 摆 / 一起切开的菜什么也不飞（None）；别的收尾（压、卷、串、揉、夹、成形）是面粉
    （FLOUR_KIND）。闪光不在这里：每一道菜都有。认不出的收尾名按压算（JE 的 finish() 对不认识的名字回 PRESS）。"""
    if finish == Assembly.FINISH_FREEZE:
        return FROST_KIND
    return None if finish in NO_CRUMBS else FLOUR_KIND


def flourPuff(middleX, middleZ, frost=False):
    """菜做成时的面粉（冰棒是霜）：板面中心上方 1 像素。"""
    velocity, spread, count = FLOUR
    return (middleX, Scene.TOP + 1.0, middleZ), FROST_VELOCITY if frost else velocity, spread, count


# 经典玩法每切一件：FD 的 CuttingBoardBlockEntity.spawnCuttingParticles（:148-150）在方块中心、高 0.2 处放 5 颗这件东西的碎屑，各方向散 0.1。
# 基岩版没有"按物品贴图碎开"的粒子，用站点也用的 arris:board_dust 按这件东西的颜色染（Client/Endpoints.PlayCrumbs）；速度（格每秒，向上）是估的，没和 JE 对过
CRUMB_PARTICLE = "arris:board_dust"
CRUMB_AT = (0.5, 0.2, 0.5)             # 方块内的位置，格
CRUMB_COUNT = 5
CRUMB_SPREAD = 0.1                     # 起点的随机范围，格
CRUMB_SPEED = 1.2
CRUMB_COLOR = 0xE0D0A0                 # 没有颜色记录的东西（和 BoardFx.DEFAULT_COLOR 同一个）
