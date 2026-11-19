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
SPRITE_SPAN = 7.2            # 掉落物缩放 1 时贴图边长（0.45 格；原来按 8 算，2026-11-19 实机重量过，见 Shared/Rules/ItemPose.ITEM_SPAN）
CUBE_SPAN = 4.0              # 方块物品的掉落物是个小立方体：缩放 1 时棱长（贴图物品边长的一半；2026-11-17 实机标定，前置包 Client/PropMath）
CUBE_LIFT = 3.2              # 立方体的中心固定在掉落物轴心正上方 0.2 格，不跟缩放和旋转走（引擎定格那一支的 T(0, 0.2, 0)）
FLAT_LIFT = 0.32             # 平躺的贴图中心离它躺着的面多高
KNIFE_SCALE = 0.45 * 16.0 / SPRITE_SPAN     # 刀（和别的工具）画 0.45 个图标大：7.2 像素
KNIFE_ROLL = 135.0           # 竖着的刀顺时针转 135 度：刀柄朝上、刀尖朝下（实机标定）
KNIFE_TIP = KNIFE_SCALE * SPRITE_SPAN / 2.0 * math.sqrt(2.0)       # 刀尖在图标中心正下方多远（贴图对角线的一半）
CARVED_X = 8.0               # 插着的工具画在方块的正中心（方块自己的坐标 8, 8；BoardBehavior.CARVED_X），不是板底座的中间（6.5, 8）
CARVED_HEIGHT = 0.23 * 16.0  # 它的中心离方块底多高（FD CuttingBoardRenderer.renderItemCarved 的 translate(0.5, 0.23, 0.5)）
CARVED_Y = CARVED_HEIGHT - 1.01    # 同一个高度，HoD 从放东西的高度算起（BoardBehavior.CARVED_Y）
CARVED_SCALE = 0.6
# FD renderItemCarved（CuttingBoardRenderer.java:99-109）把插着的工具在贴图平面里转这么多度（Axis.ZP.rotationDegrees）：镐、锄 225，三叉戟 135，
# 别的（剑、刀、斧、锹、剪刀……）180。键是引擎的物品类型（GetItemBasicInfo 的 itemType：pickaxe / hoe / trident / shears / sword / axe / shovel）
CARVED_TURNS = {"pickaxe": 225.0, "hoe": 225.0, "trident": 135.0}
CARVED_TURN = 180.0


def scaleOf(size):
    """画 size 像素的 16 格图标：掉落物的缩放。"""
    return size / SPRITE_SPAN


def uprightLift(scale):
    """立着的贴图物品（插着的工具）的道具中心离它底边多高：贴图轴心在底边中点、缩放 1 时边长 SPRITE_SPAN，中心在边长一半处。
    方块类的东西是立方体，用 blockLift。砧板站点（BoardThing）和没开站时的 Client/BlockItems 都按这两个摆。"""
    return scale * SPRITE_SPAN / 2.0


def dropRoll(javaTurn):
    """JE 里在贴图平面内转的度数（FD 的 Axis.ZP.rotationDegrees(javaTurn)）-> 客户端掉落物的 roll：JE 换成客户端掉落物的这一处，实机看着不对只改这里。
    推导：FD 的渲染器先把贴图的正面转到朝板 FACING 的反方向（物品的 FIXED 显示变换自带半圈，再加 renderItemCarved 的 +180），再绕 Z 正向转 javaTurn；
    从正面看（Z 轴指向看的人的背后）正向就是顺时针。掉落物的 roll 也是"从正面看顺时针转几度"（PropMath.uprightMatrix 的 Rz(roll)），所以数一样；
    实机标定过的一点也对得上：roll 135 刀尖朝下（贴图的刀尖在右上、顺时针 135 度到正下），JE 里三叉戟的 135 度就是笔直朝下。"""
    return float(javaTurn)


def carvedRoll(itemType):
    """插着的工具（引擎的物品类型 itemType）的 roll：镐 / 锄 225、三叉戟 135、别的 180 度（CARVED_TURNS），经 dropRoll 换成掉落物的 roll。"""
    return dropRoll(CARVED_TURNS.get(itemType, CARVED_TURN))


def itemScale(isBlock=False):
    """等着切的东西的缩放：方块类是棱长 BLOCK_SIZE 的立方体（掉落物缩放 1 时棱长 CUBE_SPAN），图标画 ITEM_SIZE 像素。"""
    return BLOCK_SIZE / CUBE_SPAN if isBlock else scaleOf(ITEM_SIZE)


def blockLift(scale, span=SPRITE_SPAN):
    """方块类的东西坐在一个面上时，道具的"中心"要写在面上方多高。道具按贴图物品的规矩摆（轴心 = 中心下方半个贴图边长），
    而引擎把立方体画在轴心上方 CUBE_LIFT：立方体的中心该在面上方半个棱长，所以是 半棱长 - CUBE_LIFT + 半个贴图边长。
    scale 用现在的缩放（铲一铲缩一点时底面一直贴着面）。span 是替我们把中心换成轴心的那一方用的贴图边长：自己画（Client/BlockItems）是
    SPRITE_SPAN；站点里是前置包换的，用它自己的那个数（Api.Client.ITEM_SPAN：2026-11-19 之前的前置包是 8）。"""
    return scale * CUBE_SPAN / 2.0 - CUBE_LIFT + scale * span / 2.0


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
