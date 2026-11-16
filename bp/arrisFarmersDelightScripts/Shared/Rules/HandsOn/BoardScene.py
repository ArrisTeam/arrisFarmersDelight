# -*- coding: utf-8 -*-
"""BoardScene - 砧板场景的几何：机位、点得到的盒子、板上东西摆在哪、多大（双端）

对应 Hands-On Delight：scenes/cutting_board.json（机位、mouth / surface 碰撞盒、work 节点底下各件的位置）和 client/BoardBehavior.java 的
常量与摆法（58-208、315-330、560-570、1063-1068）。坐标是站点像素（16 = 1 格，原点在方块西北下角，玩家在北面，x 往东长、z 往南长），
高度 y 离板面（板面在 TOP = 1 像素）。一件东西的"偏移"是离板面中心（BASE_X, BASE_Z）的 (x, y, z)；板面中心在方块自己坐标里是 (6.5, 8)：
FD 的板底座 x 1..12、柄 13..15，中心要往底座中间挪，按方块朝向转到站点里（Compat/Diegesis/BoardView 用 PotModelMath 算）。
掉落物缩放 1 时贴图边长 SPRITE_SPAN 像素（客户端道具的标定），所以 HoD 画 size 像素的东西 = 缩放 size / SPRITE_SPAN。
"""
import math

from .BoardIcon import BLOCK_SIZE, ITEM_SIZE
from .BoardMotion import LAYER_STEP, PILE_LIFT, layerJitter, layerTurn

CAMERA = {"pos": (7.5, 35.5, -21.0), "target": (7.5, 1.0, 8.0), "fov": 30.0, "keepWidth": 16.0 / 9.0}   # scenes/cutting_board.json
FLIGHT_SECONDS = 0.4
WORK_PLANE = 3.0             # work_plane：光标栈画在 WORK_PLANE + carryLift 的平面上
MOUTH = ((1.0, 0.0, 1.0), (15.0, 5.2, 15.0))     # drop_zone "hand"：手上拿着东西时整块板都是它
SURFACE = ((1.0, 0.0, 1.0), (15.0, 5.0, 15.0))   # 空手点的
TOP = 1.0                    # 板面（FD 的板 1 像素高）
BASE_X, BASE_Z = 6.5, 8.0    # 东西躺的地方：板底座的中间，方块自己的坐标
LAYER_SIZE = 9.0             # 摆盘的层（除第 0 层）画多大
SPRITE_SPAN = 8.0            # 掉落物缩放 1 时贴图边长
FLAT_LIFT = 0.32             # 平躺的贴图中心离它躺着的面多高
KNIFE_SCALE = 0.45 * 16.0 / SPRITE_SPAN     # 刀（和别的工具）画 0.45 个图标大：7.2 像素
KNIFE_ROLL = 135.0           # 竖着的刀顺时针转 135 度：刀柄朝上、刀尖朝下（实机标定）
KNIFE_TIP = KNIFE_SCALE * SPRITE_SPAN / 2.0 * math.sqrt(2.0)       # 刀尖在图标中心正下方多远（贴图对角线的一半）
CARVED_Y = 0.23 * 16.0 - 1.01      # 插着的工具画在方块中间、0.23 格高（BoardBehavior.CARVED_Y，从放东西的高度算起）
CARVED_SCALE = 0.6


def scaleOf(size):
    """画 size 像素的 16 格图标：掉落物的缩放。"""
    return size / SPRITE_SPAN


def itemScale(isBlock=False):
    """等着切的东西的缩放：方块类按物品画、缩到 BLOCK_SCALE，图标画 ITEM_SIZE 像素。"""
    return scaleOf(BLOCK_SIZE if isBlock else ITEM_SIZE)


def layerPose(index):
    """第 index 层躺的位置：{"x", "y", "z", "turn"}（偏移、离板面的高度、转角度数）。每层 LAYER_STEP 高，带一点固定的偏转偏移。"""
    jitterX, jitterZ = layerJitter(index)
    return {"x": jitterX, "y": index * LAYER_STEP, "z": jitterZ, "turn": layerTurn(index)}


def layerSize(index):
    return ITEM_SIZE if index == 0 else LAYER_SIZE


def pileLift(count):
    """一叠不止一个时，上面那个抬高（pileLift）。"""
    return PILE_LIFT if count > 1 else 0.0


def centerHeight(lift, isBlock=False):
    """一件东西的道具中心离站点地面多高：板面 + 它躺着 / 立着的高度 + 抬高。方块类立着，中心在边长一半；平的贴着面。"""
    return TOP + lift + (BLOCK_SIZE / 2.0 if isBlock else FLAT_LIFT)


def surfaceHeight(count, isBlock=False):
    """板上等着切的东西的顶面离站点地面多高：刀吸附、虚线、碎屑都落在这个面上。"""
    return TOP + (BLOCK_SIZE if isBlock else pileLift(count) + ITEM_SIZE / 16.0)
